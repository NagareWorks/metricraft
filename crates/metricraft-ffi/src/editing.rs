//! Additive ABI-4 traversal and persistent edits of the native shared graph.
use crate::errors::boundary;
use metricraft_core::expression::{BuildLimits, BuildOptions, Expr, Mode};
use std::{ffi::CString, os::raw::c_char, ptr};

/// Fixed layout; null options and zero budgets select native defaults.
#[repr(C)]
#[derive(Clone, Copy, Default)]
pub struct McBuildOptions {
    pub max_output_bytes: usize,
    pub max_expanded_nodes: usize,
    pub flags: u32,
}

unsafe fn path<'a>(data: *const usize, len: usize) -> Result<&'a [usize], String> {
    if len > 1024 || (len != 0 && data.is_null()) {
        return Err("invalid AST path: expected at most 1024 child indexes".into());
    }
    Ok(if len == 0 {
        &[]
    } else {
        std::slice::from_raw_parts(data, len)
    })
}

/// Read kind 0 = node kind, 1 = value type. Free the owned string with mc_string_free.
/// # Safety
/// expr must be null or a live expression pointer for this call.
#[no_mangle]
pub unsafe extern "C" fn mc_expr_node_info(expr: *const Expr, kind: u32) -> *mut c_char {
    boundary(|| {
        let expr = expr.as_ref().ok_or("null expression")?;
        let text = match kind {
            0 => expr.node_kind(),
            1 => expr.value_type(),
            _ => return Err("invalid node information kind".into()),
        };
        Ok(CString::new(text)
            .map_err(|_| "interior NUL in node information")?
            .into_raw())
    })
    .unwrap_or(ptr::null_mut())
}

/// Return child count, or -1 on error. Null output with zero capacity queries size.
/// Otherwise writes one owning handle per child, each freed with mc_expr_free.
/// Capacity errors leave output untouched; successful writes affect only count slots.
/// # Safety
/// expr must be live for this call. Non-null output must point to capacity writable,
/// aligned pointer slots, and must not alias expr. Never free expr during the call.
#[no_mangle]
pub unsafe extern "C" fn mc_expr_children(
    expr: *const Expr,
    output: *mut *mut Expr,
    capacity: usize,
) -> isize {
    boundary(|| {
        let expr = expr.as_ref().ok_or("null expression")?;
        let children = expr.children();
        let len = children.len();
        if output.is_null() && capacity == 0 {
            return Ok(len as isize);
        }
        if output.is_null() || capacity < len {
            return Err("insufficient AST child output capacity".into());
        }
        // Finish allocations before transferring any handles to the caller.
        let owners: Vec<_> = children.into_iter().map(Box::new).collect();
        for (i, owner) in owners.into_iter().enumerate() {
            output.add(i).write(Box::into_raw(owner));
        }
        Ok(len as isize)
    })
    .unwrap_or(-1)
}

/// Read an occurrence; empty path shares the root. The result owns its handle.
/// # Safety
/// expr must be live. For nonzero len, indexes must point to len readable usize
/// values for the call. Null indexes are allowed for an empty path.
#[no_mangle]
pub unsafe extern "C" fn mc_expr_at_path(
    expr: *const Expr,
    indexes: *const usize,
    len: usize,
) -> *mut Expr {
    boundary(|| {
        let expr = expr.as_ref().ok_or("null expression")?;
        Ok(Box::into_raw(Box::new(expr.at_path(path(indexes, len)?)?)))
    })
    .unwrap_or(ptr::null_mut())
}

/// Pointer identity of shared nodes (not semantic equality). Returns 0/1, or -1 on error.
/// # Safety
/// Both pointers must be null or live expression owners for this call.
#[no_mangle]
pub unsafe extern "C" fn mc_expr_shares_node(expr: *const Expr, other: *const Expr) -> i32 {
    boundary(|| {
        let expr = expr.as_ref().ok_or("null expression")?;
        let other = other.as_ref().ok_or("null other expression")?;
        Ok(i32::from(expr.shares_node(other)))
    })
    .unwrap_or(-1)
}

/// Replace one occurrence, sharing unaffected nodes and validating the resulting root.
/// Mode: 0 PromQL, 1 MetricsQL. Flags match mc_expr_build_with_options.
/// Returns an owner freed with mc_expr_free, or null with mc_last_error on failure.
/// # Safety
/// expr/replacement must stay live for this call. Nonzero len requires len readable
/// usize indexes. Non-null options must point to an aligned McBuildOptions instance.
#[no_mangle]
pub unsafe extern "C" fn mc_expr_replace_at(
    expr: *const Expr,
    indexes: *const usize,
    len: usize,
    replacement: *const Expr,
    mode: u32,
    options: *const McBuildOptions,
) -> *mut Expr {
    boundary(|| {
        let expr = expr.as_ref().ok_or("null expression")?;
        let replacement = replacement.as_ref().ok_or("null replacement")?;
        let path = path(indexes, len)?;
        let mode = match mode {
            0 => Mode::PromQl,
            1 => Mode::MetricsQl,
            _ => return Err("invalid query mode".into()),
        };
        let input = options.as_ref().copied().unwrap_or_default();
        if input.flags & !15 != 0 {
            return Err("unknown build option flags".into());
        }
        let defaults = BuildLimits::default();
        let budget = |value, default| if value == 0 { default } else { value };
        let options = BuildOptions {
            limits: BuildLimits {
                max_output_bytes: budget(input.max_output_bytes, defaults.max_output_bytes),
                max_expanded_nodes: budget(input.max_expanded_nodes, defaults.max_expanded_nodes),
            },
            experimental_functions: input.flags & 1 != 0,
            syntax_features: input.flags & 14,
        };
        Ok(Box::into_raw(Box::new(expr.replace_at(
            path,
            replacement,
            mode,
            options,
        )?)))
    })
    .unwrap_or(ptr::null_mut())
}
