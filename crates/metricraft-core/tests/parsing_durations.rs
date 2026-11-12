use metricraft_core::expression::{BuildOptions, Expr, Mode, ParseErrorKind, ParseOptions};

#[path = "support/parsing.rs"]
mod fuzz_support;

fn options() -> ParseOptions {
    ParseOptions {
        build: BuildOptions {
            syntax_features: 2,
            ..BuildOptions::default()
        },
        ..ParseOptions::default()
    }
}

fn parse(source: &str) -> Expr {
    Expr::parse_with_options(source, Mode::PromQl, options()).unwrap()
}

#[test]
fn computed_duration_roundtrips_are_stable() {
    for source in [
        "rate(up[5m * 2])",
        "up[(5 + 2) * 1m]",
        "up[step()]",
        "up[((0))]",
        "up[-(0)]",
        "up[2 ^ 3 ^ 2]",
        "up[(-2) ^ 2]",
        "up[-2 ^ 2]",
        "up[2 ^ -2]",
        "up[min_of(range(), max_of(step(), 5m))]",
        "up[range():step()]",
        "up[range():]",
        "up[5m:step()]",
        "up[step():5m]",
        "up[(5m):1m]",
        "up[5m:(1m)]",
        "up offset -(1h * 2)",
        "up offset (0)",
        "up offset step() ^ 2",
        "up offset (1h) + 2",
        "up offset -(2)^2 + 1",
        "up offset --2^2 + 1",
        "(up offset (1h)) + 2",
        "up offset step() @ 0 + 1",
        "up @ 0 offset step() + 1",
        "up offset -range() + 1",
        "up offset min_of(1h, 2 * step())",
        "rate(up[5m * 2] offset (step()) @ end() smoothed)",
        "rate(up[5m] @ start() offset (1h * 2) anchored)",
    ] {
        fuzz_support::exercise(source.as_bytes());
        let expr = parse(source);
        let rendered = expr
            .build_with_options(Mode::PromQl, options().build)
            .unwrap();
        assert_eq!(
            parse(&rendered)
                .build_with_options(Mode::PromQl, options().build)
                .unwrap(),
            rendered,
            "{source}"
        );
    }
}

#[test]
fn precedence_and_offset_boundary_match_prometheus() {
    for (source, expected) in [
        ("up[2 ^ 3 ^ 2]", "up[(2 ^ (3 ^ 2))]"),
        ("up[8 / 4 / 2]", "up[((8 / 4) / 2)]"),
        ("up[1 + 2 * 3]", "up[(1 + (2 * 3))]"),
        ("up offset -2 ^ 2", "(up offset -2 ^ 2)"),
        ("up offset (1h + 2)", "up offset ((3600 + 2))"),
        ("up offset 1h + 2", "(up offset 1h + 2)"),
        ("up[range():step()]", "(up)[range():step()]"),
        ("up offset step() + 1", "((up offset (step())) + 1)"),
        ("up offset (1h) + 2", "up offset (((3600) + 2))"),
        ("(up offset (1h)) + 2", "((up offset ((3600))) + 2)"),
    ] {
        assert_eq!(
            parse(source)
                .build_with_options(Mode::PromQl, options().build)
                .unwrap(),
            expected
        );
    }
}

#[test]
fn computed_duration_edit_only_rebuilds_the_changed_path() {
    let original = parse("rate(up[5m * 2])");
    let duration = original.at_path(&[0, 1]).unwrap();
    let changed = original
        .replace_at(&[0, 1, 1], &parse("3"), Mode::PromQl, options().build)
        .unwrap();
    assert!(changed
        .at_path(&[0, 0])
        .unwrap()
        .shares_node(&original.at_path(&[0, 0]).unwrap()));
    assert!(changed
        .at_path(&[0, 1, 0])
        .unwrap()
        .shares_node(&duration.at_path(&[0]).unwrap()));
    assert!(!changed.shares_node(&original));
    assert_eq!(
        original
            .build_with_options(Mode::PromQl, options().build)
            .unwrap(),
        "rate(up[(300 * 2)])"
    );
    drop(original);
    assert_eq!(
        changed
            .build_with_options(Mode::PromQl, options().build)
            .unwrap(),
        "rate(up[(300 * 3)])"
    );
}

#[test]
fn feature_gate_and_duration_grammar_are_explicit() {
    for source in [
        "up[1+1]",
        "up[(1)]",
        "up[range():step()]",
        "up offset step()",
    ] {
        assert_eq!(
            Expr::parse(source, Mode::PromQl).unwrap_err().kind,
            ParseErrorKind::Validation
        );
        assert!(parse(source).build(Mode::PromQl).is_err());
    }
    for source in ["up[+1]", "up[+5m:+1m]", "up offset -1h"] {
        assert!(Expr::parse(source, Mode::PromQl)
            .unwrap()
            .build(Mode::PromQl)
            .is_ok());
    }
    for source in [
        "up[1 / 0]",
        "up[1 % -0]",
        "up[0]",
        "up[-1]",
        "up[1:0]",
        "up[abs(1)]",
        "up[up]",
        "up[step(1)]",
        "up[min_of(1)]",
        "up[max_of(1, 2, 3)]",
        "up offset (1h) + down",
        "up[1 > 0]",
        "up[1 + on() 2]",
        "up[9223372037 + 1]",
        "up @ (1 + 2)",
        "up offset (1+2) offset 1",
    ] {
        assert!(
            Expr::parse_with_options(source, Mode::PromQl, options()).is_err(),
            "{source}"
        );
    }
}

#[test]
fn duration_recursion_and_work_respect_the_existing_budgets() {
    let nested = format!("up[{}1{}]", "(".repeat(20), ")".repeat(20));
    let functions = format!("up[{}1{}]", "min_of(1,".repeat(20), ")".repeat(20));
    let powers = format!("up[{}1]", "1^".repeat(20));
    for source in [&nested, &functions, &powers] {
        let limited = ParseOptions {
            max_depth: 8,
            ..options()
        };
        assert_eq!(
            Expr::parse_with_options(source, Mode::PromQl, limited)
                .unwrap_err()
                .kind,
            ParseErrorKind::Limit
        );
    }
    let source = format!("up[1{}]", "+1".repeat(100));
    let limited = ParseOptions {
        max_work: 30,
        ..options()
    };
    assert_eq!(
        Expr::parse_with_options(&source, Mode::PromQl, limited)
            .unwrap_err()
            .kind,
        ParseErrorKind::Limit
    );
}

#[test]
fn literal_duration_budgets_measure_the_retained_spelling() {
    let mut limits = options();
    limits.build.limits.max_output_bytes = 10;
    let expr = Expr::parse_with_options("up[1118ms]", Mode::PromQl, limits).unwrap();
    assert_eq!(
        expr.build_with_options(Mode::PromQl, limits.build).unwrap(),
        "up[1118ms]"
    );
    limits.build.limits.max_output_bytes = 9;
    assert_eq!(
        Expr::parse_with_options("up[1118ms]", Mode::PromQl, limits)
            .unwrap_err()
            .kind,
        ParseErrorKind::Limit
    );
    limits.build.limits.max_output_bytes = 10;
    assert!(Expr::parse_with_options("up[1118ms+1]", Mode::PromQl, limits).is_err());
}
