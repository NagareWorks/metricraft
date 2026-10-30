use metricraft_core::{Expr, Mode};
use metricraft_ffi::editing::*;
use metricraft_ffi::expression::{mc_expr_build, mc_expr_free};
use metricraft_ffi::{mc_error_free, mc_last_error, mc_string_free};
use std::{ffi::CStr, ptr};

unsafe fn render(expr: *const Expr) -> String {
    let text = mc_expr_build(expr, 0);
    assert!(!text.is_null());
    let result = CStr::from_ptr(text).to_str().unwrap().to_owned();
    mc_string_free(text);
    result
}

#[test]
fn handles_survive_their_inputs_and_share_untouched_nodes() {
    unsafe {
        let query = Box::into_raw(Box::new(Expr::parse("up > 10", Mode::PromQl).unwrap()));
        let threshold = Box::into_raw(Box::new(Expr::parse("20", Mode::PromQl).unwrap()));
        let edited = mc_expr_replace_at(query, [1].as_ptr(), 1, threshold, 0, ptr::null());
        assert!(!edited.is_null());
        assert_eq!(mc_expr_children(query, ptr::null_mut(), 0), 2);
        let mut children = [ptr::null_mut(); 2];
        assert_eq!(mc_expr_children(query, children.as_mut_ptr(), 2), 2);
        let unchanged = mc_expr_at_path(edited, [0].as_ptr(), 1);
        assert_eq!(mc_expr_shares_node(unchanged, children[0]), 1);
        let same = mc_expr_replace_at(query, [1].as_ptr(), 1, children[1], 0, ptr::null());
        assert_eq!(mc_expr_shares_node(query, same), 1);
        let changed = mc_expr_at_path(edited, [1].as_ptr(), 1);
        assert_eq!(mc_expr_shares_node(threshold, changed), 1);
        assert_eq!(mc_expr_shares_node(query, edited), 0);
        mc_expr_free(query);
        mc_expr_free(threshold);
        assert_eq!(render(same), "(up > 10)");
        assert_eq!(render(edited), "(up > 20)");
        assert_eq!(render(children[0]), "up");
        for owner in [edited, same, unchanged, changed, children[0], children[1]] {
            mc_expr_free(owner);
        }
    }
}

#[test]
fn invalid_arguments_leave_child_output_untouched_and_errors_recover() {
    unsafe {
        let query = Expr::parse("up + down", Mode::PromQl).unwrap();
        let mut output = [ptr::null_mut(); 1];
        assert_eq!(mc_expr_children(&query, output.as_mut_ptr(), 1), -1);
        assert!(output[0].is_null());
        assert_eq!(mc_expr_children(&query, ptr::null_mut(), 1), -1);
        assert_eq!(mc_expr_children(ptr::null(), ptr::null_mut(), 0), -1);
        assert!(mc_expr_at_path(&query, ptr::null(), 1).is_null());
        assert!(mc_expr_at_path(&query, ptr::null(), 1025).is_null());
        assert!(mc_expr_at_path(&query, [2].as_ptr(), 1).is_null());
        assert_eq!(mc_expr_shares_node(&query, ptr::null()), -1);
        assert!(mc_expr_node_info(&query, 2).is_null());
        assert!(mc_expr_node_info(ptr::null(), 0).is_null());
        let error = mc_last_error();
        assert!(!error.is_null());
        let root = mc_expr_at_path(&query, ptr::null(), 0);
        assert_eq!(mc_expr_shares_node(&query, root), 1);
        assert!(mc_last_error().is_null());
        assert!(!(*error).message.is_null());
        mc_error_free(error);
        for (kind, expected) in [(0, "binary"), (1, "instant")] {
            let info = mc_expr_node_info(root, kind);
            assert_eq!(CStr::from_ptr(info).to_str().unwrap(), expected);
            mc_string_free(info);
        }
        mc_expr_free(root);
    }
}

#[test]
fn edit_rejections_do_not_mutate_inputs_or_skip_final_root_validation() {
    unsafe {
        let query = Expr::parse("up + 1", Mode::PromQl).unwrap();
        let vector = Expr::parse("down", Mode::PromQl).unwrap();
        assert!(mc_expr_replace_at(&query, [1].as_ptr(), 1, &vector, 0, ptr::null()).is_null());
        assert!(mc_expr_replace_at(&query, ptr::null(), 0, &vector, 99, ptr::null()).is_null());
        assert!(mc_expr_replace_at(&query, ptr::null(), 0, ptr::null(), 0, ptr::null()).is_null());
        for options in [
            McBuildOptions {
                max_output_bytes: 1,
                ..Default::default()
            },
            McBuildOptions {
                max_expanded_nodes: 1,
                ..Default::default()
            },
            McBuildOptions {
                flags: 16,
                ..Default::default()
            },
        ] {
            assert!(mc_expr_replace_at(&query, ptr::null(), 0, &query, 0, &options).is_null());
        }
        assert_eq!(render(&query), "(up + 1)");
    }
}
