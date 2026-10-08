use metricraft_core::expression::Expr;

#[test]
fn deep_diagnostics_are_iterative_and_fail_without_changing_the_owner() {
    std::thread::Builder::new()
        .stack_size(128 * 1024)
        .spawn(|| {
            let mut root = Expr::apply("metric", "up", "", &[]).unwrap();
            for _ in 0..100_000 {
                root = Expr::apply("abs", "", "", &[root]).unwrap();
            }
            assert!(root
                .inspect(true, 1024 * 1024, 10_000)
                .unwrap_err()
                .contains("max_items"));
            let report = root.inspect(true, 1024 * 1024, 100_001).unwrap();
            assert!(report.contains("\"node_count\":100001"));
            assert!(report.contains("\"depth\":100000"));
            assert!(root
                .inspect(false, 100, 100_001)
                .unwrap_err()
                .contains("max_output_bytes"));
            assert_eq!(root.inspect(true, 1024 * 1024, 100_001).unwrap(), report);
        })
        .unwrap()
        .join()
        .unwrap();
}
