use metricraft_core::expression::{BuildOptions, Expr, Mode, ParseErrorKind, ParseOptions};
#[path = "support/parsing.rs"]
mod fuzz_support;

fn parse(source: &str) -> Expr {
    Expr::parse(source, Mode::PromQl).unwrap()
}
fn build(source: &str) -> String {
    parse(source).build(Mode::PromQl).unwrap()
}

#[test]
fn saved_alert_roundtrips_and_edits_share_the_unmodified_query() {
    let source =
        r#"sum by (service) (rate(http_requests_total{job="api",instance=~"api-.*"}[5m])) > 100"#;
    let original = parse(source);
    let rendered = original.build(Mode::PromQl).unwrap();
    assert_eq!(build(&rendered), rendered);
    let query = original.at_path(&[0]).unwrap();
    let edited = original
        .replace_at(&[1], &parse("200"), Mode::PromQl, BuildOptions::default())
        .unwrap();
    assert!(edited.at_path(&[0]).unwrap().shares_node(&query));
    assert!(!edited.shares_node(&original));
    assert!(edited.build(Mode::PromQl).unwrap().ends_with(" > 200)"));
    assert_eq!(original.build(Mode::PromQl).unwrap(), rendered);
    drop(original);
    assert!(edited.build(Mode::PromQl).is_ok());
}

#[test]
fn precedence_and_associativity_preserve_meaning() {
    for (source, expected) in [
        ("1 + 2 * 3", "(1 + (2 * 3))"),
        ("2 ^ 3 ^ 2", "(2 ^ (3 ^ 2))"),
        ("8 / 4 / 2", "((8 / 4) / 2)"),
        ("-2 ^ 2", "-((2 ^ 2))"),
        ("(-2) ^ 2", "((-(2)) ^ 2)"),
        ("1 < bool 2", "(1 < bool 2)"),
        ("a or b and c", "(a or (b and c))"),
        ("a AND b UNLESS c", "((a and b) unless c)"),
        ("010 + 0x10 + .5e2", "((8 + 16) + 50)"),
    ] {
        assert_eq!(build(source), expected, "{source}");
    }
}

#[test]
fn builders_preserve_a_signed_power_base_too() {
    let negative = Expr::apply("number", "-2", "", &[]).unwrap();
    let two = parse("2");
    let power = Expr::apply("^", "", "", &[negative, two]).unwrap();
    assert_eq!(power.build(Mode::PromQl).unwrap(), "((-2) ^ 2)");
    assert_eq!(build(&power.build(Mode::PromQl).unwrap()), "((-(2)) ^ 2)");
}

#[test]
fn selectors_strings_modifiers_and_functions_roundtrip() {
    for source in [
        "sum(rate(up[5m])) by (job)",
        "sum without (instance) (up)",
        "a / on(job) group_left(zone) b",
        "up @ start() offset -1h",
        "max_over_time((up + other)[1h:5m])",
        "up[1h:] @ end()",
        r#"{"温度", "job-name"="a\"b\n", zone!~`ap.*`}"#,
        r#"label_replace(up, 'host', '$1', 'instance', `([^:]+):.*`)"#,
        "up # comment\r + other",
        r#"up{job="\xC3\xA9\u4e2d\U0001F600\101"}"#,
        "sum BY (job,) (up)",
        "with",
        ":",
        ":metric:name",
        "vector(-Inf)",
        "vector(NaN)",
    ] {
        let text = build(source);
        assert_eq!(build(&text), text, "{source}");
    }
    assert_eq!(build("up # comment\r + other"), "(up + other)");
    assert_eq!(
        build(r#"up{job="\xC3\xA9\u4e2d\U0001F600\101"}"#),
        "up{job=\"é中😀A\"}"
    );
}

#[test]
fn malformed_or_semantically_invalid_queries_fail_without_raw_fallbacks() {
    for source in [
        "",
        "up trailing",
        "up; other",
        "rate(up[5m]",
        "up{job=api}",
        "rate(up)",
        "{}",
        "{job=~\".*\"}",
        "up{job=~\"(?=a)\"}",
        "up{job=\"bad\\q\"}",
        "up + bool other",
        "1 > 2",
        "sum by(job) (up) without(zone)",
        "unknown(up)",
        "up + on(job) on(zone) other",
        "up * group_left(zone) other",
        "abs(up,)",
        "up offset 1h offset 2h",
        "up @ 1 @ 2",
        "(up)[5m]",
        "(up + x)[5m]",
        "up{\"another\"}",
        "up{job=\"a\",zone=\"b\"} garbage",
        "1e999",
        "0x",
        "0xFFFFFFFFFFFFFFFF",
        "1__000",
        "up\u{000b}+other",
        r#"up{job="\ud800"}"#,
    ] {
        let error = Expr::parse(source, Mode::PromQl).unwrap_err();
        assert!(
            error.start <= error.end && error.end <= source.len(),
            "{source}: {error}"
        );
        assert!(source.is_char_boundary(error.start) && source.is_char_boundary(error.end));
    }
}

#[test]
fn unsupported_and_dialect_errors_are_explicit() {
    assert_eq!(
        Expr::parse("up", Mode::MetricsQl).unwrap_err().kind,
        ParseErrorKind::Unsupported
    );
    assert_eq!(
        Expr::parse("up[(step())]", Mode::PromQl).unwrap_err().kind,
        ParseErrorKind::Unsupported
    );
    assert_eq!(
        Expr::parse("median(up)", Mode::PromQl).unwrap_err().kind,
        ParseErrorKind::Dialect
    );
    assert_eq!(
        Expr::parse(r#"up{job="\xff"}"#, Mode::PromQl)
            .unwrap_err()
            .kind,
        ParseErrorKind::Unsupported
    );
}

#[test]
fn feature_flags_are_not_enabled_implicitly() {
    let source = "limitk(2, up)";
    assert!(Expr::parse(source, Mode::PromQl).is_err());
    let mut options = ParseOptions::default();
    options.build.experimental_functions = true;
    assert!(Expr::parse_with_options(source, Mode::PromQl, options).is_ok());
    for (source, flag) in [("rate(up[5m] smoothed)", 4), ("a + fill(0) b", 8)] {
        assert!(Expr::parse(source, Mode::PromQl).is_err());
        options.build.syntax_features = flag;
        let parsed = Expr::parse_with_options(source, Mode::PromQl, options).unwrap();
        let rendered = parsed
            .build_with_options(Mode::PromQl, options.build)
            .unwrap();
        assert!(Expr::parse_with_options(&rendered, Mode::PromQl, options).is_ok());
    }
}

#[test]
fn budgets_cover_input_tokens_recursion_work_and_expansion() {
    for options in [
        ParseOptions {
            max_input_bytes: 2,
            ..ParseOptions::default()
        },
        ParseOptions {
            max_tokens: 2,
            ..ParseOptions::default()
        },
        ParseOptions {
            max_work: 1,
            ..ParseOptions::default()
        },
        ParseOptions {
            max_depth: 1,
            ..ParseOptions::default()
        },
        ParseOptions {
            max_depth: 129,
            ..ParseOptions::default()
        },
    ] {
        assert_eq!(
            Expr::parse_with_options("up + other", Mode::PromQl, options)
                .unwrap_err()
                .kind,
            ParseErrorKind::Limit
        );
    }
    let mut options = ParseOptions::default();
    options.build.limits.max_expanded_nodes = 2;
    assert_eq!(
        Expr::parse_with_options("up + other", Mode::PromQl, options)
            .unwrap_err()
            .kind,
        ParseErrorKind::Limit
    );
    let deep = format!("{}up{}", "(".repeat(5000), ")".repeat(5000));
    assert_eq!(
        Expr::parse(&deep, Mode::PromQl).unwrap_err().kind,
        ParseErrorKind::Limit
    );
    let labels = (0..1000)
        .map(|i| format!("label_{i}"))
        .collect::<Vec<_>>()
        .join(",");
    assert_eq!(
        Expr::parse(&format!("sum by ({labels}) (up)"), Mode::PromQl)
            .unwrap_err()
            .kind,
        ParseErrorKind::Limit
    );
}

#[test]
fn utf8_error_offsets_point_to_the_unexpected_character() {
    let input = "up{job=\"中文\"} ☃";
    let error = Expr::parse(input, Mode::PromQl).unwrap_err();
    assert_eq!(&input[error.start..error.end], "☃");
}

#[test]
fn review_regressions_preserve_grouping_and_reject_invalid_syntax() {
    let options = ParseOptions {
        build: BuildOptions {
            experimental_functions: true,
            syntax_features: 14,
            ..Default::default()
        },
        ..Default::default()
    };
    for text in [
        r#"sum by("NaN","Inf","without")(up)"#,
        "sum by(foo:bar)(up)",
        "sum by(on)(up)",
        "a + on(group_left) b",
        r#"sum by("on")(up)"#,
        r#"up{job="\uFFFD"}"#,
        r#"{"\uFFFD"}"#,
        "0x12E+2",
        "0x_E+2",
        "0xEE1",
        "a + on(foo:bar) group_left(:zone) b",
        r#"a / on("Inf") group_left("without") b"#,
        "rate(up[5m] offset 1h smoothed)",
        "rate(up[5m] @ 0 anchored)",
        "rate(up[5m] offset 1h @ 0 smoothed)",
        "rate(up[5m] @ start() smoothed)",
        "rate(up[5m] offset 1h @ end() anchored)",
        "up > bool on() 0",
        "a + ignoring() 1",
        "1 + on() group_left(job) a",
        "1 > bool ignoring() 2",
        r#"up{job=~`[a]\Q[x]\E`}"#,
        r#"up{job=~`[^]]\Qa\E`}"#,
        r#"up{job=~`\Q\\E()`}"#,
        r#"up{job=~`\Q\\\E[ab]`}"#,
        "info(up,{})",
    ] {
        let expr = Expr::parse_with_options(text, Mode::PromQl, options).unwrap();
        let rendered = expr
            .build_with_options(Mode::PromQl, options.build)
            .unwrap();
        let next = Expr::parse_with_options(&rendered, Mode::PromQl, options).unwrap();
        assert_eq!(
            next.build_with_options(Mode::PromQl, options.build)
                .unwrap(),
            rendered
        );
        fuzz_support::exercise(text.as_bytes());
    }
    for text in [
        "info(up,({}))",
        r#"info(up,({job="x"}))"#,
        "sum by(without)(up)",
        r#"up{job="\x+1"}"#,
        r#"up{job="\u+123"}"#,
        r#"up{job="\U+0000041"}"#,
        r#"up{job=~`a++`}"#,
        r#"up{job=~`a{2}*`}"#,
        r#"up{job=~`(?<é>.)`}"#,
        r#"up{job=~`[\Qa\E]`}"#,
        r#"up{job=~`[]\Qa\E]`}"#,
        r#"up{job=~`[^]\Qa\E]`}"#,
        r#"up{job=~`[[:alpha:]\Qa\E]`}"#,
        r#"up{job=~`\Q\\E(`}"#,
        r#"up{job=~`\Q\\\E(?x)a`}"#,
        r#"{job=~`\Q\\E*`}"#,
        "up > bool on(job) 0",
        "up + on() fill(0) 1",
        r#"up{foo:bar="x"}"#,
        r#"{job!~"a{00}"}"#,
        "up{job=\"\u{fffd}\"}",
        "0x_1e",
        "0x1_e",
        "0x1_EF",
        "0x1E+2",
        "0x1E-2",
    ] {
        assert!(
            Expr::parse_with_options(text, Mode::PromQl, options).is_err(),
            "{text}"
        );
    }
}

#[test]
fn builder_and_parser_agree_on_re2_quote_termination() {
    let selector = Expr::apply("selector", "", "", &[]).unwrap();
    for (pattern, valid) in [(r"\Q\\E*", false), (r"\Q\\E()", true)] {
        let expr = Expr::apply("=~", "job", pattern, std::slice::from_ref(&selector)).unwrap();
        assert_eq!(expr.build(Mode::PromQl).is_ok(), valid, "{pattern}");
    }
}

#[test]
fn replacement_characters_roundtrip_without_changing_label_values() {
    for source in [
        r#"sum by("\ufffd","a\ufffd")(up)"#,
        r#"a + on("a\ufffd") group_left("\ufffd") b"#,
    ] {
        let expr = Expr::parse(source, Mode::PromQl).unwrap();
        let text = expr.build(Mode::PromQl).unwrap();
        assert!(!text.contains('\u{fffd}'));
        assert!(text.contains(r"\ufffd"));
        assert_eq!(expr.complexity().output_bytes, text.len());
        let next = Expr::parse(&text, Mode::PromQl).unwrap();
        assert_eq!(next.build(Mode::PromQl).unwrap(), text);
        // The MetricsQL ident decoder treats this scalar as an invalid escape.
        assert!(expr.build(Mode::MetricsQl).unwrap_err().contains("U+FFFD"));
    }
}

#[test]
fn regex_counts_with_re2_literal_semantics_are_explicitly_deferred() {
    for count in ["00", "01", "0,01", "01,2", "00,", "00,01"] {
        let source = format!("{{job=~\"a{{{count}}}\"}}");
        assert_eq!(
            Expr::parse(&source, Mode::PromQl).unwrap_err().kind,
            ParseErrorKind::Unsupported,
            "{source}"
        );
    }
}

#[test]
fn empty_re2_quotes_are_explicitly_deferred() {
    for source in [
        r#"up{job=~`\Q\E`}"#,
        r#"up{job=~`\Q`}"#,
        r#"{job!~`a+\Q\E?`}"#,
        r#"{job=~`a+\Q\E?`}"#,
        r#"up{job=~`a*\Q\E*`}"#,
    ] {
        assert_eq!(
            Expr::parse(source, Mode::PromQl).unwrap_err().kind,
            ParseErrorKind::Unsupported,
            "{source}"
        );
    }
}

#[test]
fn deterministic_parser_mutations_cover_valid_and_malformed_inputs() {
    for seed in [
        r#"sum by(job)(rate(up{job=~"api.*"}[5m])) > 100"#,
        r#"{"温度","job-name"="a\"b\n"} @ start() offset -1h"#,
        "a / on(job) group_left(zone) fill(-1) b",
        "2^3^2 + 0xE + 010",
        r#"up{job=~`\Qapi.*\E|\p{L}+`}"#,
        "max_over_time((up + other)[1h:5m])",
        "up offset 0[5m]",
        "up[(step())]",
    ] {
        fuzz_support::exercise(seed.as_bytes());
        for i in 0..seed.len() {
            fuzz_support::exercise(&seed.as_bytes()[..i]);
            for byte in b"{}[]():@,+-*/^=~!#_0129eEx\\\"'`\n\r\0" {
                let mut mutated = seed.as_bytes().to_vec();
                mutated[i] = *byte;
                fuzz_support::exercise(&mutated);
            }
        }
    }
}
