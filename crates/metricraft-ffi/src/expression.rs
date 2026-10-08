//! Owning opaque pointers for immutable expressions; no global expression registry.
use crate::errors::boundary;
use metricraft_core::expression::{BuildLimits, BuildOptions, Expr, Mode};
use std::{
    ffi::{CStr, CString},
    os::raw::c_char,
    ptr,
};

/// Read-only diagnostics: kind 0 = shared graph, 1 = analysis, 2 = rendered spans.
/// Zero budgets select 1 MiB output and 10,000 work items. Only spans expand nodes.
/// Mode/flags have the same meaning as mc_expr_build_with_options.
///
/// # Safety
/// The expression pointer must stay live for the call. Free text with mc_string_free.
#[no_mangle]
pub unsafe extern "C" fn mc_expr_inspect(
    expr: *const Expr,
    kind: u32,
    mode: u32,
    max_output_bytes: usize,
    max_items: usize,
    flags: u32,
) -> *mut c_char {
    boundary(|| {
        let expr = expr.as_ref().ok_or("null expression")?;
        if flags & !15 != 0 {
            return Err("unknown build option flags".into());
        }
        let mode = match mode {
            0 => Mode::PromQl,
            1 => Mode::MetricsQl,
            _ => return Err("invalid query mode".into()),
        };
        let max_bytes = if max_output_bytes == 0 {
            1024 * 1024
        } else {
            max_output_bytes
        };
        let max_items = if max_items == 0 { 10_000 } else { max_items };
        let text = match kind {
            0 | 1 => expr.inspect(kind == 1, max_bytes, max_items)?,
            2 => expr.positions(
                mode,
                BuildOptions {
                    limits: BuildLimits {
                        max_output_bytes: max_bytes,
                        max_expanded_nodes: max_items,
                    },
                    experimental_functions: flags & 1 != 0,
                    syntax_features: flags & 14,
                },
            )?,
            _ => return Err("invalid diagnostic kind".into()),
        };
        CString::new(text)
            .map(CString::into_raw)
            .map_err(|_| "interior NUL in output".into())
    })
    .unwrap_or(ptr::null_mut())
}

unsafe fn text<'a>(p: *const c_char) -> Result<&'a str, String> {
    if p.is_null() {
        return Err("null text argument".into());
    }
    CStr::from_ptr(p)
        .to_str()
        .map_err(|_| "invalid UTF-8".into())
}
/// Construct a validated expression, or return null with a thread-local error.
///
/// # Safety
/// Arguments must be valid C strings and live expression pointers. Child pointers
/// are borrowed for this call; the returned expression owns shared Rust children.
#[no_mangle]
pub unsafe extern "C" fn mc_expr_new(
    op: *const c_char,
    a: *const c_char,
    b: *const c_char,
    children: *const *const Expr,
    count: usize,
) -> *mut Expr {
    boundary(|| {
        if count > 1024 || (count != 0 && children.is_null()) {
            return Err("invalid child array".into());
        }
        let children = if count == 0 {
            &[][..]
        } else {
            std::slice::from_raw_parts(children, count)
        };
        let mut args = Vec::with_capacity(count);
        for child in children {
            if child.is_null() {
                return Err("null child".into());
            }
            args.push((**child).clone());
        }
        let expr = Expr::apply(text(op)?, text(a)?, text(b)?, &args)?;
        Ok(Box::into_raw(Box::new(expr)))
    })
    .unwrap_or(ptr::null_mut())
}
/// Release an owning expression pointer. A null pointer is a no-op.
///
/// # Safety
/// Release exactly once. The expression must not be used afterwards, and must
/// not be borrowed by another concurrent call while it is being released.
#[no_mangle]
pub unsafe extern "C" fn mc_expr_free(expr: *mut Expr) {
    if !expr.is_null() {
        drop(Box::from_raw(expr));
    }
}
/// 0 = PromQL, 1 = MetricsQL. Return text is owned; free with mc_string_free.
/// Returns null on failure, available through mc_last_error.
///
/// # Safety
/// A non-null expression pointer must stay live for the duration of the call.
#[no_mangle]
pub unsafe extern "C" fn mc_expr_build(expr: *const Expr, mode: u32) -> *mut c_char {
    mc_expr_build_with_limits(expr, mode, 0, 0)
}

/// Build with explicit expansion budgets. A zero budget selects that field's default.
/// Defaults: 1 MiB UTF-8 output and 100,000 expanded nodes (including matchers).
///
/// # Safety
/// The expression pointer must remain valid for this call, as for mc_expr_build.
#[no_mangle]
pub unsafe extern "C" fn mc_expr_build_with_limits(
    expr: *const Expr,
    mode: u32,
    max_output_bytes: usize,
    max_expanded_nodes: usize,
) -> *mut c_char {
    mc_expr_build_with_options(expr, mode, max_output_bytes, max_expanded_nodes, 0)
}

/// Build flags: 0 experimental functions, 1 duration expressions, 2 extended ranges, 3 binary fill.
///
/// # Safety
/// The expression pointer must remain valid for this call, as for mc_expr_build.
#[no_mangle]
pub unsafe extern "C" fn mc_expr_build_with_options(
    expr: *const Expr,
    mode: u32,
    max_output_bytes: usize,
    max_expanded_nodes: usize,
    flags: u32,
) -> *mut c_char {
    boundary(|| {
        if flags & !15 != 0 {
            return Err("unknown build option flags".into());
        }
        let expr = expr.as_ref().ok_or("null expression")?;
        let mode = match mode {
            0 => Mode::PromQl,
            1 => Mode::MetricsQl,
            _ => return Err("invalid query mode".into()),
        };
        let defaults = BuildLimits::default();
        let limits = BuildLimits {
            max_output_bytes: if max_output_bytes == 0 {
                defaults.max_output_bytes
            } else {
                max_output_bytes
            },
            max_expanded_nodes: if max_expanded_nodes == 0 {
                defaults.max_expanded_nodes
            } else {
                max_expanded_nodes
            },
        };
        CString::new(expr.build_with_options(
            mode,
            BuildOptions {
                limits,
                experimental_functions: flags & 1 != 0,
                syntax_features: flags & 14,
            },
        )?)
        .map(CString::into_raw)
        .map_err(|_| "interior NUL in output".into())
    })
    .unwrap_or(ptr::null_mut())
}
