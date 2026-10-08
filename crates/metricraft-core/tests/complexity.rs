use metricraft_core::expression::{BuildLimits, Expr, Mode};

fn metric() -> Expr {
    Expr::apply("metric", "up", "", &[]).unwrap()
}

#[test]
fn output_and_expansion_limits_are_exact_and_do_not_mutate_shared_inputs() {
    let base = Expr::apply("=", "job", "a\"\\\n\u{1}中文", &[metric()]).unwrap();
    let mut root = base.clone();
    for _ in 0..9 {
        root = Expr::apply("+", "", "", &[root.clone(), root]).unwrap();
    }
    let cost = root.complexity();
    let exact = BuildLimits {
        max_output_bytes: cost.output_bytes,
        max_expanded_nodes: cost.expanded_nodes,
    };
    let text = root.build_with_limits(Mode::PromQl, exact).unwrap();
    assert_eq!(text.len(), cost.output_bytes);
    assert!(root
        .build_with_limits(
            Mode::PromQl,
            BuildLimits {
                max_output_bytes: cost.output_bytes - 1,
                ..exact
            }
        )
        .unwrap_err()
        .contains("max_output_bytes"));
    assert!(root
        .build_with_limits(
            Mode::PromQl,
            BuildLimits {
                max_expanded_nodes: cost.expanded_nodes - 1,
                ..exact
            }
        )
        .unwrap_err()
        .contains("max_expanded_nodes"));
    assert_eq!(root.build_with_limits(Mode::PromQl, exact).unwrap(), text);
    assert_eq!(
        base.build(Mode::PromQl).unwrap(),
        "up{job=\"a\\\"\\\\\\n\\u0001中文\"}"
    );
}

#[test]
fn tiny_shared_dag_with_exponential_output_is_rejected_even_after_size_overflow() {
    let mut root = metric();
    for _ in 0..256 {
        root = Expr::apply("+", "", "", &[root.clone(), root]).unwrap();
    }
    assert_eq!(root.complexity().output_bytes, usize::MAX);
    assert_eq!(root.complexity().expanded_nodes, usize::MAX);
    assert!(root
        .build(Mode::PromQl)
        .unwrap_err()
        .contains("max_output_bytes"));
}

#[test]
fn selector_alternatives_and_common_filters_share_without_expanding() {
    let base = metric();
    let mut root = base.clone();
    for _ in 0..256 {
        root = Expr::apply("selector_or", "", "", &[root.clone(), root]).unwrap();
    }
    assert_eq!(root.complexity().output_bytes, usize::MAX);
    let filtered = Expr::apply("=", "job", "api", &[root.clone()]).unwrap();
    assert_eq!(filtered.complexity().output_bytes, usize::MAX);
    for q in [root, filtered] {
        assert!(q
            .build(Mode::MetricsQl)
            .unwrap_err()
            .contains("max_output_bytes"));
        assert!(q.inspect(false, 64_000, 1024).is_ok());
    }
    assert_eq!(base.build(Mode::PromQl).unwrap(), "up");
}

#[test]
fn deep_expression_and_matcher_chains_render_and_drop_on_a_small_stack() {
    std::thread::Builder::new()
        .stack_size(256 * 1024)
        .spawn(|| {
            let limits = BuildLimits {
                max_output_bytes: 1024 * 1024,
                max_expanded_nodes: 100_001,
            };
            let mut root = metric();
            for _ in 0..100_000 {
                root = Expr::apply("abs", "", "", &[root]).unwrap();
            }
            assert_eq!(
                root.build_with_limits(Mode::PromQl, limits).unwrap().len(),
                500_002
            );
            // Debug output must not recursively expand a deep DAG either.
            assert!(format!("{root:?}").len() < 200);
            drop(root);
            let mut root = metric();
            for _ in 0..100_000 {
                root = Expr::apply("=", "x", "y", &[root]).unwrap();
            }
            let text = root.build_with_limits(Mode::PromQl, limits).unwrap();
            assert_eq!(text.len(), root.complexity().output_bytes);
            assert!(text.starts_with("up{x=\"y\",x=\"y\""));
            drop(root);
        })
        .unwrap()
        .join()
        .unwrap();
}

#[test]
fn wide_shared_arguments_are_counted_per_output_occurrence() {
    let args = vec![metric(); 10_000];
    let root = Expr::apply("union", "", "", &args).unwrap();
    assert_eq!(root.complexity().expanded_nodes, 10_001);
    let text = root.build(Mode::MetricsQl).unwrap();
    assert_eq!(root.complexity().output_bytes, text.len());
    assert!(root.build(Mode::PromQl).is_err());
}

#[test]
fn generated_compositions_have_correct_cached_sizes() {
    let mut seed = 17u64;
    for _ in 0..100 {
        let mut q = metric();
        for _ in 0..40 {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            q = match seed % 6 {
                0 => Expr::apply("abs", "", "", &[q]).unwrap(),
                1 => Expr::apply("sum", "", "", &[q]).unwrap(),
                2 => Expr::apply("+", "", "", &[q, metric()]).unwrap(),
                3 => Expr::apply("negate", "", "", &[q]).unwrap(),
                4 => {
                    let sub = Expr::apply("subquery", "1h", "5m", &[q]).unwrap();
                    Expr::apply("max_over_time", "", "", &[sub]).unwrap()
                }
                _ => Expr::apply("default", "", "", &[q, metric()]).unwrap(),
            };
            assert_eq!(
                q.build(Mode::MetricsQl).unwrap().len(),
                q.complexity().output_bytes
            );
        }
    }
}

#[test]
fn metric_identity_cannot_be_reconfigured() {
    assert!(Expr::apply("rename_metric", "down", "", &[metric()]).is_err());
}
