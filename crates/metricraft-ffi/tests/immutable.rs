use metricraft_ffi::expression::{mc_expr_build, mc_expr_free, mc_expr_new};
use metricraft_ffi::mc_string_free;
use std::{ffi::CStr, ptr};

#[test]
fn owned_children_outlive_their_ffi_owners() {
    unsafe {
        let metric = mc_expr_new(
            c"metric".as_ptr(),
            c"up".as_ptr(),
            c"".as_ptr(),
            ptr::null(),
            0,
        );
        assert!(!metric.is_null());
        let children = [metric as *const _];
        let sum = mc_expr_new(
            c"sum".as_ptr(),
            c"".as_ptr(),
            c"".as_ptr(),
            children.as_ptr(),
            1,
        );
        assert!(!sum.is_null());
        mc_expr_free(metric);
        let text = mc_expr_build(sum, 0);
        assert!(!text.is_null());
        assert_eq!(CStr::from_ptr(text).to_str().unwrap(), "sum (up)");
        mc_string_free(text);
        mc_expr_free(sum);
    }
}
