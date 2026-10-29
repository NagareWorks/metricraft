use metricraft_core::expression::{BuildOptions, Expr, Mode};

fn metric(name: &str) -> Expr {
    Expr::apply("metric", name, "", &[]).unwrap()
}
fn number(value: &str) -> Expr {
    Expr::apply("number", value, "", &[]).unwrap()
}
fn string(value: &str) -> Expr {
    Expr::apply("string", value, "", &[]).unwrap()
}
fn rate(name: &str, window: &str) -> Expr {
    let range = Expr::apply("range", window, "", &[metric(name)]).unwrap();
    Expr::apply("call", "rate", "", &[range]).unwrap()
}

#[test]
fn threshold_edit_shares_query_and_preserves_original() {
    let query = rate("requests_total", "5m");
    let original = Expr::apply(">", "", "", &[query.clone(), number("100")]).unwrap();
    assert_eq!(original.node_kind(), "binary");
    assert_eq!(original.value_type(), "instant");
    assert_eq!(original.children().len(), 2);
    assert!(original.at_path(&[]).unwrap().shares_node(&original));
    let updated = original
        .replace_at(&[1], &number("200"), Mode::PromQl, BuildOptions::default())
        .unwrap();
    assert!(updated.at_path(&[0]).unwrap().shares_node(&query));
    assert!(!updated.shares_node(&original));
    assert_eq!(
        original.build(Mode::PromQl).unwrap(),
        "(rate(requests_total[5m]) > 100)"
    );
    assert_eq!(
        updated.build(Mode::PromQl).unwrap(),
        "(rate(requests_total[5m]) > 200)"
    );
    let unchanged = original
        .replace_at(&[0], &query, Mode::PromQl, BuildOptions::default())
        .unwrap();
    assert!(unchanged.shares_node(&original));
    let retained = updated.at_path(&[0]).unwrap();
    drop(updated);
    drop(original);
    drop(query);
    assert_eq!(
        retained.build(Mode::PromQl).unwrap(),
        "rate(requests_total[5m])"
    );
}

#[test]
fn editing_one_occurrence_preserves_shared_sibling() {
    let shared = rate("requests_total", "5m");
    let original = Expr::apply("+", "", "", &[shared.clone(), shared.clone()]).unwrap();
    let replacement = rate("requests_total", "10m");
    let updated = original
        .replace_at(&[0], &replacement, Mode::PromQl, BuildOptions::default())
        .unwrap();
    assert!(updated.at_path(&[1]).unwrap().shares_node(&shared));
    assert!(updated.at_path(&[0]).unwrap().shares_node(&replacement));
    assert!(original.at_path(&[0]).unwrap().shares_node(&shared));
    assert_eq!(
        updated.build(Mode::PromQl).unwrap(),
        "(rate(requests_total[10m]) + rate(requests_total[5m]))"
    );
}

#[test]
fn changed_path_does_not_expand_a_shared_dag() {
    let mut original = number("1");
    for _ in 0..14 {
        original = Expr::apply("+", "", "", &[original.clone(), original.clone()]).unwrap();
    }
    let updated = original
        .replace_at(
            &[0; 14],
            &number("2"),
            Mode::PromQl,
            BuildOptions::default(),
        )
        .unwrap();
    assert!(updated
        .at_path(&[1])
        .unwrap()
        .shares_node(&original.at_path(&[1]).unwrap()));
    // A deep copy would exceed this unique-node diagnostic budget.
    assert!(!updated.inspect(true, 65536, 1000).unwrap().is_empty());
}

#[test]
fn edits_recheck_types_dialects_scopes_and_limits() {
    let original = rate("requests_total", "5m");
    let computed = Expr::apply("+", "", "", &[metric("a"), metric("b")]).unwrap();
    assert!(original
        .replace_at(&[0], &number("1"), Mode::PromQl, BuildOptions::default())
        .is_err());
    // A computed expression under a bare range is valid only in MetricsQL.
    assert!(original
        .replace_at(&[0, 0], &computed, Mode::PromQl, BuildOptions::default())
        .is_err());
    assert!(original
        .replace_at(&[0, 0], &computed, Mode::MetricsQl, BuildOptions::default())
        .is_ok());
    let reference = Expr::apply("reference", "missing", "instant", &[]).unwrap();
    assert!(original
        .replace_at(&[], &reference, Mode::MetricsQl, BuildOptions::default())
        .is_err());
    let mut options = BuildOptions::default();
    options.limits.max_output_bytes = 1;
    assert!(original
        .replace_at(&[], &original, Mode::PromQl, options)
        .is_err());
    assert!(original.at_path(&[99]).is_err());
    assert!(original.at_path(&[0; 1025]).is_err());
    assert!(original
        .replace_at(&[0; 1025], &original, Mode::PromQl, BuildOptions::default())
        .is_err());
    let scalar = original
        .replace_at(&[], &number("5"), Mode::PromQl, BuildOptions::default())
        .unwrap();
    assert_eq!(scalar.value_type(), "scalar");
    assert_eq!(
        original.build(Mode::PromQl).unwrap(),
        "rate(requests_total[5m])"
    );
}

#[test]
fn ancestor_reconstruction_retains_grouping_matching_and_portable_calls() {
    let sum = Expr::apply("sum", "", "", &[metric("a")]).unwrap();
    let grouped = Expr::apply("by", "", "", &[sum, string("job")]).unwrap();
    let replaced = grouped
        .replace_at(&[0], &metric("b"), Mode::PromQl, BuildOptions::default())
        .unwrap();
    assert_eq!(replaced.build(Mode::PromQl).unwrap(), "sum by (job) (b)");
    let binary = Expr::apply("+", "", "", &[metric("a"), metric("b")]).unwrap();
    let matched = Expr::apply("on", "", "", &[binary, string("job")]).unwrap();
    let matched = Expr::apply("group_left", "", "", &[matched, string("zone")]).unwrap();
    let replaced = matched
        .replace_at(&[1], &metric("c"), Mode::PromQl, BuildOptions::default())
        .unwrap();
    assert_eq!(
        replaced.build(Mode::PromQl).unwrap(),
        "(a + on (job) group_left (zone) c)"
    );
    let histogram = Expr::apply(
        "histogram_quantiles_auto",
        "",
        "",
        &[string("phi"), number("0.5"), metric("a")],
    )
    .unwrap();
    let options = BuildOptions {
        experimental_functions: true,
        ..BuildOptions::default()
    };
    let replaced = histogram
        .replace_at(&[2], &metric("b"), Mode::PromQl, options)
        .unwrap();
    assert_eq!(
        replaced.build_with_options(Mode::PromQl, options).unwrap(),
        "histogram_quantiles(b, \"phi\", 0.5)"
    );
}
