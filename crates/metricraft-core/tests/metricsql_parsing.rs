use metricraft_core::expression::{BuildOptions, Expr, Mode, ParseErrorKind, ParseOptions};

fn parse(source: &str) -> Expr {
    Expr::parse(source, Mode::MetricsQl).unwrap()
}

#[test]
fn saved_vm_alert_edits_share_the_query_and_keep_literal_windows_as_metadata() {
    let original = parse(r#"sum by(job)(rate(requests_total{status=~"5.."}[2.5m])) > 100"#);
    let text = original.build(Mode::MetricsQl).unwrap();
    let edited = original
        .replace_at(
            &[1],
            &parse("200"),
            Mode::MetricsQl,
            BuildOptions::default(),
        )
        .unwrap();
    assert!(original
        .at_path(&[0])
        .unwrap()
        .shares_node(&edited.at_path(&[0]).unwrap()));
    assert_eq!(original.build(Mode::MetricsQl).unwrap(), text);
    assert!(edited.build(Mode::MetricsQl).unwrap().ends_with(" > 200)"));
    assert_eq!(parse("up[2i]").children().len(), 1);
    assert_eq!(parse("up[2i]").children()[0].node_kind(), "selector");
}

#[test]
fn common_vm_queries_roundtrip_without_a_second_ast() {
    for source in [
        "rate(up)",
        "sum by(job)(rate(up))",
        "avg_over_time((a + b)[5m])",
        "a default b if c or d",
        "a ifnot b and c",
        "abs(a,)",
        "histogram_quantiles(\"phi\", .5, .9, rate(bucket[5m]))",
        "a + on(job) group_left(zone) b",
        "up[5m:2i] offset -1h @ end()",
        "up[:1m]",
        "up[:]",
        "up @ start() offset 1h",
        "(up) offset 1h",
        "sum by(NaN,without)(up)",
        "1 > 2",
        "0_7 + 08",
        "{}",
        "{job=~\".*\"}",
        "up{__name__=~\"u.*\"}",
        "up{job=`a\rb`}",
        "-2*3",
        "2^-2*3",
        "2^-2^2",
        "-2*-3%2",
        "--2*3",
        "(-2)*3",
        "+-2*3",
        "(up @ 100) offset 1h",
        "(up offset 1h) offset 2h",
        "+p offset 0[5m]",
        "-p offset 0[5m]",
        "(-p)[5m]",
        "-p offset 1h offset 2h",
        "-p offset 1h @ 100 @ 200",
        "(p @ 100)[5m]",
        "rate(up[0.5m])",
        "up offset .5",
    ] {
        let text = parse(source).build(Mode::MetricsQl).unwrap();
        assert_eq!(
            parse(&text).build(Mode::MetricsQl).unwrap(),
            text,
            "{source}"
        );
    }
    assert_eq!(
        parse("up # comment\r + ignored")
            .build(Mode::MetricsQl)
            .unwrap(),
        "up"
    );
    assert_eq!(
        parse("up{job=`a\rb`}").build(Mode::MetricsQl).unwrap(),
        "up{job=\"ab\"}"
    );
    assert!(Expr::parse("rate(up)", Mode::PromQl).is_err());
    assert!(Expr::parse("abs(up,)", Mode::PromQl).is_err());
}

#[test]
fn builder_signed_operands_keep_their_own_multiplicative_scope_in_vm() {
    let left = Expr::apply("number", "-2", "", &[]).unwrap();
    let expr = Expr::apply("*", "", "", &[left, parse("3")]).unwrap();
    assert_eq!(expr.build(Mode::MetricsQl).unwrap(), "((-2) * 3)");
    assert_eq!(
        parse("(-2)*3").build(Mode::MetricsQl).unwrap(),
        "((-(2)) * 3)"
    );
    assert_eq!(parse("+-2*3").build(Mode::MetricsQl).unwrap(), "-((2 * 3))");
}

#[test]
fn deferred_extensions_and_invalid_syntax_are_not_reinterpreted() {
    for source in [
        "WITH (x = up) x",
        "up{job=\"api\" or job=\"worker\"}",
        "up{job=\"a\"+\"b\"}",
        "abs(up) keep_metric_names",
        "up offset 1h-5m",
        "up @ (end()-1)",
        "1m",
        "1MiB",
        "0x1E+2",
        "温度",
        "foo.bar",
        r#"up{"job\u0041"="x"}"#,
        "up[$__interval]",
        "up @ +1700000000 offset 1h",
        "up @ -1 offset 1h",
        "up @ +1[5m]",
    ] {
        assert_eq!(
            Expr::parse(source, Mode::MetricsQl).unwrap_err().kind,
            ParseErrorKind::Unsupported,
            "{source}"
        );
    }
    for source in [
        "a + bool b",
        "up @ 1 @ 2",
        "up offset 1h[5m]",
        "up[5m][1m]",
        "up + @",
        "1e1_0",
        "-a*b[5m][1m]",
        "+a*b[5m][1m]",
        "-a*b offset 1h offset 2h",
        "rate(up[.5m])",
        "up offset .5m",
        "up[1h.5m]",
    ] {
        assert!(Expr::parse(source, Mode::MetricsQl).is_err(), "{source}");
    }
    for options in [
        ParseOptions {
            max_tokens: 2,
            ..Default::default()
        },
        ParseOptions {
            max_depth: 1,
            ..Default::default()
        },
        ParseOptions {
            max_work: 2,
            ..Default::default()
        },
    ] {
        assert_eq!(
            Expr::parse_with_options("sum(rate(up))", Mode::MetricsQl, options)
                .unwrap_err()
                .kind,
            ParseErrorKind::Limit
        );
    }
}

#[test]
fn modifier_named_metrics_remain_data_in_every_rhs_position() {
    for word in [
        "bool",
        "on",
        "ignoring",
        "group_left",
        "group_right",
        "prefix",
        "fill",
        "fill_left",
        "fill_right",
    ] {
        for name in [word.to_owned(), word.to_ascii_uppercase()] {
            for source in [
                format!("a + ({name})"),
                format!("a + ({name}{{job=\"api\"}} offset 1m)"),
                format!("a + on(job) group_left(zone) ({name})"),
            ] {
                let text = parse(&source).build(Mode::MetricsQl).unwrap();
                assert!(text.contains(&format!("__name__=\"{name}\"")), "{text}");
                assert_eq!(
                    parse(&text).build(Mode::MetricsQl).unwrap(),
                    text,
                    "{source}"
                );
            }
            // The builder shares the same emitter; no parse-only wrapper or
            // extra AST node is needed to keep the RHS unambiguous.
            let metric = Expr::apply("metric", &name, "", &[]).unwrap();
            let sum = Expr::apply("+", "", "", &[parse("a"), metric.clone()]).unwrap();
            assert!(sum.at_path(&[1]).unwrap().shares_node(&metric));
            for mode in [Mode::PromQl, Mode::MetricsQl] {
                let text = sum.build(mode).unwrap();
                assert_eq!(Expr::parse(&text, mode).unwrap().build(mode).unwrap(), text);
            }
        }
    }
}

#[test]
fn aggregate_metric_names_and_exact_name_constraints_follow_vm() {
    for source in [
        "(sum) or up",
        "(SUM) or up",
        "sum{job=\"api\"} or up",
        "sum offset 1h or up",
        "(topk_avg) and (COUNT_VALUES)",
        "up{\"up\"}",
        "{\"up\",\"up\"}",
        "up{__name__=\"up\"}",
        "{__name__=\"\",__name__=\"up\"}",
        "up{__name__=~\"down\",__name__!=\"up\"}",
    ] {
        let text = parse(source).build(Mode::MetricsQl).unwrap();
        assert_eq!(
            parse(&text).build(Mode::MetricsQl).unwrap(),
            text,
            "{source}"
        );
    }
    for source in [
        "sum or up",
        "SUM and up",
        "topk_avg if up",
        "up{__name__=\"down\"}",
        "{__name__=\"up\",__name__=\"down\"}",
        "{\"up\",__name__=\"down\"}",
        "{__name__=\"up\",\"down\"}",
        "up{\"down\"}",
        "{__name__=\"up\",__name__=\"\"}",
    ] {
        assert!(Expr::parse(source, Mode::MetricsQl).is_err(), "{source}");
    }
    // PromQL permits contradictory unnamed exact-name filters (an empty match).
    let source = "{__name__=\"up\",__name__=\"down\"}";
    assert!(Expr::parse(source, Mode::PromQl).is_ok());
}

#[test]
fn function_case_and_contextual_keywords_follow_the_selected_dialect() {
    for (source, expected) in [
        ("RATE(UP[5m])", "rate(UP[5m])"),
        (
            "LaBeL_SeT(UP,\"label\",\"MiXeD\")",
            "label_set(UP, \"label\", \"MiXeD\")",
        ),
    ] {
        assert_eq!(parse(source).build(Mode::MetricsQl).unwrap(), expected);
        assert!(Expr::parse(source, Mode::PromQl).is_err());
    }
    for op in ["and", "or", "unless", "default", "if", "ifnot"] {
        for name in [
            "fill",
            "fill_left",
            "fill_right",
            "FILL",
            "FILL_LEFT",
            "FILL_RIGHT",
        ] {
            for matching in ["", "on(job)"] {
                assert!(
                    Expr::parse(&format!("up {op} {matching} {name}"), Mode::MetricsQl).is_err()
                );
                let text = parse(&format!("up {op} {matching} ({name})"))
                    .build(Mode::MetricsQl)
                    .unwrap();
                assert_eq!(parse(&text).build(Mode::MetricsQl).unwrap(), text);
            }
        }
    }
    let source = "a + on(job) group_left() prefix";
    assert!(Expr::parse(source, Mode::MetricsQl).is_err());
    assert!(Expr::parse(source, Mode::PromQl).is_ok());
    let text = parse("a + on(job) group_left() (prefix)")
        .build(Mode::MetricsQl)
        .unwrap();
    assert_eq!(parse(&text).build(Mode::MetricsQl).unwrap(), text);
}
