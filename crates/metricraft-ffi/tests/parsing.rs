use metricraft_ffi::expression::{mc_expr_build, mc_expr_build_with_options, mc_expr_free};
use metricraft_ffi::parsing::{mc_expr_parse, McParseErrorInfo, McParseOptions};
use metricraft_ffi::{mc_abi_version, mc_error_free, mc_last_error, mc_string_free};
use std::{ffi::CStr, ptr};

unsafe fn message() -> String {
    let error = mc_last_error();
    assert!(!error.is_null());
    let text = CStr::from_ptr((*error).message)
        .to_str()
        .unwrap()
        .to_owned();
    mc_error_free(error);
    text
}

#[test]
fn computed_durations_reuse_the_existing_abi_and_feature_bit() {
    unsafe {
        let source = b"up[range():step()] offset (1h*2)";
        let mut info = McParseErrorInfo::default();
        assert!(mc_expr_parse(source.as_ptr(), source.len(), 0, ptr::null(), &mut info).is_null());
        assert_eq!(info.kind, 2);
        let options = McParseOptions {
            flags: 2,
            ..McParseOptions::default()
        };
        let expr = mc_expr_parse(source.as_ptr(), source.len(), 0, &options, &mut info);
        assert!(!expr.is_null(), "{}", message());
        assert_eq!(info.kind, 0);
        let output = mc_expr_build_with_options(expr, 0, 0, 0, 2);
        assert!(!output.is_null(), "{}", message());
        assert_eq!(
            CStr::from_ptr(output).to_str().unwrap(),
            "(up)[range():step()] offset ((3600 * 2))"
        );
        mc_string_free(output);
        mc_expr_free(expr);
    }
}

#[test]
fn counted_source_is_owned_after_parse_and_nul_is_not_a_terminator() {
    unsafe {
        assert_eq!(mc_abi_version(), 4);
        let mut source = b"sum(up)".to_vec();
        let expr = mc_expr_parse(
            source.as_ptr(),
            source.len(),
            0,
            ptr::null(),
            ptr::null_mut(),
        );
        assert!(!expr.is_null(), "{}", message());
        source.fill(0);
        drop(source);
        let output = mc_expr_build(expr, 0);
        assert_eq!(CStr::from_ptr(output).to_str().unwrap(), "sum (up)");
        mc_string_free(output);
        mc_expr_free(expr);

        let text = b"up\0 + other";
        let mut info = McParseErrorInfo::default();
        assert!(mc_expr_parse(text.as_ptr(), text.len(), 0, ptr::null(), &mut info).is_null());
        assert_eq!((info.kind, info.start, info.end), (1, 2, 3));
        assert!(message().contains("unexpected character"));

        let text = b"up{job=\"a\0b\"}";
        let expr = mc_expr_parse(text.as_ptr(), text.len(), 0, ptr::null(), &mut info);
        assert!(!expr.is_null(), "{}", message());
        assert_eq!((info.kind, info.start, info.end), (0, 0, 0));
        assert!(mc_last_error().is_null());
        let output = mc_expr_build(expr, 0);
        assert_eq!(
            CStr::from_ptr(output).to_str().unwrap(),
            r#"up{job="a\u0000b"}"#
        );
        mc_string_free(output);
        mc_expr_free(expr);
    }
}

#[test]
fn parse_errors_have_byte_spans_and_owned_legacy_messages() {
    unsafe {
        let source = "{\"温度\"} + @";
        let mut info = McParseErrorInfo::default();
        assert!(mc_expr_parse(source.as_ptr(), source.len(), 0, ptr::null(), &mut info).is_null());
        assert_eq!(info.kind, 1);
        assert_eq!((info.start, info.end), (source.len() - 1, source.len()));
        let snapshot = mc_last_error();
        assert!(!snapshot.is_null());
        let expr = mc_expr_parse(b"up".as_ptr(), 2, 0, ptr::null(), &mut info);
        assert!(!expr.is_null());
        assert!(mc_last_error().is_null());
        assert_eq!(info.kind, 0);
        assert!(CStr::from_ptr((*snapshot).message)
            .to_str()
            .unwrap()
            .contains("bytes"));
        mc_error_free(snapshot);
        mc_expr_free(expr);
    }
}

#[test]
fn parse_arguments_limits_and_dialect_fail_without_partial_handles() {
    unsafe {
        let mut info = McParseErrorInfo::default();
        assert!(mc_expr_parse(ptr::null(), 1, 0, ptr::null(), &mut info).is_null());
        assert!(message().contains("source buffer"));
        assert_eq!(info.kind, 0);
        assert!(mc_expr_parse(ptr::null(), 0, 0, ptr::null(), &mut info).is_null());
        assert_eq!(info.kind, 1);
        assert!(mc_expr_parse([255u8].as_ptr(), 1, 0, ptr::null(), &mut info).is_null());
        assert!(message().contains("UTF-8"));
        assert_eq!(info.kind, 0);
        assert!(mc_expr_parse(b"up".as_ptr(), 2, 99, ptr::null(), &mut info).is_null());
        assert!(message().contains("query mode"));
        let source = b"WITH (x = up) x";
        assert!(mc_expr_parse(source.as_ptr(), source.len(), 1, ptr::null(), &mut info).is_null());
        assert_eq!(info.kind, 4);
        assert!(message().contains("MetricsQL WITH"));
        for options in [
            McParseOptions {
                max_input_bytes: 1,
                ..Default::default()
            },
            McParseOptions {
                max_depth: 129,
                ..Default::default()
            },
        ] {
            assert!(mc_expr_parse(b"up".as_ptr(), 2, 0, &options, &mut info).is_null());
            assert_eq!(info.kind, 5);
        }
        let options = McParseOptions {
            flags: 32,
            ..Default::default()
        };
        assert!(mc_expr_parse(b"up".as_ptr(), 2, 0, &options, &mut info).is_null());
        assert_eq!(info.kind, 0);
        assert!(message().contains("option flags"));
    }
}

#[test]
fn parsing_errors_are_per_call_and_thread_local() {
    let workers: Vec<_> = (0..8)
        .map(|i| {
            std::thread::spawn(move || unsafe {
                let source = format!("up + {}@", " ".repeat(i));
                let mut info = McParseErrorInfo::default();
                assert!(
                    mc_expr_parse(source.as_ptr(), source.len(), 0, ptr::null(), &mut info)
                        .is_null()
                );
                assert_eq!(info.start, source.len() - 1);
                assert!(message().contains(&format!("bytes {}..", source.len() - 1)));
            })
        })
        .collect();
    for worker in workers {
        worker.join().unwrap();
    }
}

#[test]
fn metricsql_uses_the_existing_counted_entrypoint_and_owns_its_source() {
    unsafe {
        let mut source = b"sum(rate(up)) > 10".to_vec();
        let mut info = McParseErrorInfo::default();
        let expr = mc_expr_parse(source.as_ptr(), source.len(), 1, ptr::null(), &mut info);
        assert!(!expr.is_null(), "{}", message());
        assert_eq!(info.kind, 0);
        source.fill(0);
        drop(source);
        let output = mc_expr_build(expr, 1);
        assert!(!output.is_null(), "{}", message());
        assert_eq!(
            CStr::from_ptr(output).to_str().unwrap(),
            "(sum (rate(up)) > 10)"
        );
        mc_string_free(output);
        assert!(mc_expr_build(expr, 0).is_null());
        assert!(message().contains("MetricsQL"));
        mc_expr_free(expr);
    }
}
