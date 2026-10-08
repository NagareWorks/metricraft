//! Exercise the public ABI using only pointers a C caller can legitimately pass.
use metricraft_core::Expr;
use metricraft_ffi::expression::{
    mc_expr_build, mc_expr_build_with_options, mc_expr_free, mc_expr_inspect, mc_expr_new,
};
use metricraft_ffi::{mc_abi_version, mc_error_free, mc_last_error, mc_string_free};
use std::ffi::{CStr, CString};
use std::ptr;
use std::sync::{Arc, Barrier};

unsafe fn make(op: &str, a: &str, b: &str, children: &[*const Expr]) -> *mut Expr {
    let (op, a, b) = (
        CString::new(op).unwrap(),
        CString::new(a).unwrap(),
        CString::new(b).unwrap(),
    );
    mc_expr_new(
        op.as_ptr(),
        a.as_ptr(),
        b.as_ptr(),
        children.as_ptr(),
        children.len(),
    )
}

unsafe fn error_message() -> String {
    let error = mc_last_error();
    assert!(!error.is_null());
    assert_ne!((*error).code, 0);
    let message = CStr::from_ptr((*error).message)
        .to_str()
        .unwrap()
        .to_owned();
    mc_error_free(error);
    message
}

unsafe fn build(expr: *const Expr, mode: u32) -> String {
    let text = mc_expr_build(expr, mode);
    assert!(!text.is_null(), "{}", error_message());
    let value = CStr::from_ptr(text).to_str().unwrap().to_owned();
    mc_string_free(text);
    value
}

#[test]
fn diagnostic_failures_preserve_owners_and_clear_after_success() {
    unsafe {
        assert!(mc_expr_inspect(ptr::null(), 0, 0, 0, 0, 0).is_null());
        assert!(error_message().contains("null expression"));
        let root = make("metric", "up", "", &[]);
        for (kind, mode, bytes, flags, expected) in [
            (3, 0, 0, 0, "diagnostic kind"),
            (0, 9, 0, 0, "query mode"),
            (0, 0, 0, 16, "option flags"),
            (0, 0, 1, 0, "max_output_bytes"),
        ] {
            assert!(mc_expr_inspect(root, kind, mode, bytes, 0, flags).is_null());
            assert!(error_message().contains(expected));
            let report = mc_expr_inspect(root, 0, 0, 0, 0, 0);
            assert!(!report.is_null());
            assert!(mc_last_error().is_null());
            mc_string_free(report);
        }
        assert_eq!(build(root, 0), "up");
        mc_expr_free(root);
    }
}

#[test]
fn build_options_validate_flags_and_do_not_change_the_expression() {
    unsafe {
        let metric = make("metric", "up", "", &[]);
        let label = make("string", "job", "", &[]);
        let query = make("call", "sort_by_label", "", &[metric, label]);
        assert!(!query.is_null());
        assert!(mc_expr_build_with_options(query, 0, 0, 0, 16).is_null());
        assert!(error_message().contains("unknown build option"));
        assert!(mc_expr_build(query, 0).is_null());
        assert!(error_message().contains("experimental_functions"));
        let text = mc_expr_build_with_options(query, 0, 0, 0, 1);
        assert!(!text.is_null());
        assert_eq!(
            CStr::from_ptr(text).to_str().unwrap(),
            "sort_by_label(up, \"job\")"
        );
        mc_string_free(text);
        assert!(mc_last_error().is_null());
        assert!(mc_expr_build(query, 0).is_null());
        assert_eq!(build(metric, 0), "up");
        for expr in [query, label, metric] {
            mc_expr_free(expr);
        }
    }
}

#[test]
fn invalid_inputs_report_errors_and_success_clears_them() {
    unsafe {
        assert_eq!(mc_abi_version(), 4);
        let empty = c"".as_ptr();
        assert!(mc_expr_new(ptr::null(), empty, empty, ptr::null(), 0).is_null());
        assert!(error_message().contains("null text"));
        let invalid_utf8 = [255u8, 0];
        assert!(mc_expr_new(invalid_utf8.as_ptr().cast(), empty, empty, ptr::null(), 0).is_null());
        assert!(error_message().contains("UTF-8"));
        assert!(mc_expr_new(empty, empty, empty, ptr::null(), 1).is_null());
        assert!(error_message().contains("child array"));
        assert!(mc_expr_new(empty, empty, empty, ptr::null(), 1025).is_null());
        assert!(error_message().contains("child array"));
        assert!(make("sum", "", "", &[ptr::null()]).is_null());
        assert!(error_message().contains("null child"));
        assert!(make("metric", "up\ndown", "", &[]).is_null());
        assert!(error_message().contains("invalid metric"));

        let source = make("metric", "up", "", &[]);
        assert!(!source.is_null());
        assert!(mc_last_error().is_null());
        assert!(mc_expr_build(source, 99).is_null());
        assert!(error_message().contains("mode"));
        assert_eq!(build(source, 0), "up");
        assert!(mc_last_error().is_null());
        assert!(mc_expr_build(ptr::null(), 0).is_null());
        assert!(error_message().contains("null expression"));
        mc_expr_free(source);
        mc_expr_free(ptr::null_mut());
        mc_error_free(ptr::null_mut());
        mc_string_free(ptr::null_mut());
    }
}

#[test]
fn shared_branches_survive_intermediate_release_and_failed_operations() {
    unsafe {
        let source = make("metric", "requests_total", "", &[]);
        let filtered = make("=", "job", "api", &[source]);
        let window = make("range", "5m", "", &[filtered]);
        let rate = make("rate", "", "", &[window]);
        let sum = make("sum", "", "", &[rate]);
        let avg = make("avg", "", "", &[rate]);
        assert!(!sum.is_null() && !avg.is_null());
        for expr in [source, filtered, window, rate] {
            mc_expr_free(expr);
        }
        assert!(make("=", "job", "changed", &[sum]).is_null());
        assert!(error_message().contains("selector"));
        assert_eq!(build(sum, 0), "sum (rate(requests_total{job=\"api\"}[5m]))");
        mc_expr_free(sum);
        assert_eq!(build(avg, 1), "avg (rate(requests_total{job=\"api\"}[5m]))");
        mc_expr_free(avg);
    }
}

#[test]
fn dialect_failure_preserves_expression_and_owned_error_snapshot() {
    unsafe {
        let source = make("metric", "up", "", &[]);
        let implicit = make("rate", "", "", &[source]);
        mc_expr_free(source);
        assert!(mc_expr_build(implicit, 0).is_null());
        let snapshot = mc_last_error();
        assert!(!snapshot.is_null());
        assert_eq!(build(implicit, 1), "rate(up)");
        assert!(mc_last_error().is_null());
        assert!(CStr::from_ptr((*snapshot).message)
            .to_str()
            .unwrap()
            .contains("MetricsQL-only"));
        mc_error_free(snapshot);
        mc_expr_free(implicit);
    }
}

#[test]
fn errors_are_isolated_between_concurrent_callers() {
    let barrier = Arc::new(Barrier::new(8));
    let workers: Vec<_> = (0..8)
        .map(|i| {
            let barrier = barrier.clone();
            std::thread::spawn(move || unsafe {
                let invalid = format!("invalid_{i}(");
                assert!(make("call", &invalid, "", &[]).is_null());
                barrier.wait();
                assert!(error_message().contains(&invalid));
                let source = make("metric", "up", "", &[]);
                assert_eq!(build(source, 0), "up");
                assert!(mc_last_error().is_null());
                mc_expr_free(source);
            })
        })
        .collect();
    for worker in workers {
        worker.join().unwrap();
    }
}

#[test]
fn repeated_branch_creation_and_release_preserves_retained_owner() {
    unsafe {
        let source = make("metric", "up", "", &[]);
        for i in 0..10_000 {
            let derived = make("=", "job", &i.to_string(), &[source]);
            assert_eq!(build(derived, 0), format!("up{{job=\"{i}\"}}"));
            mc_expr_free(derived);
        }
        assert_eq!(build(source, 0), "up");
        mc_expr_free(source);
    }
}
