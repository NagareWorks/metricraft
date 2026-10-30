//! Additive ABI-4 parsing entry point. Existing expression/error ownership is reused.
use crate::errors::boundary;
use metricraft_core::expression::{
    BuildLimits, BuildOptions, Expr, Mode, ParseError, ParseErrorKind, ParseOptions,
};
use std::ptr;

/// Fixed-layout parsing options. Null options or zero fields select native defaults.
/// Flags match mc_expr_build_with_options; no experimental features are implicit.
#[repr(C)]
#[derive(Clone, Copy, Default)]
pub struct McParseOptions {
    pub max_input_bytes: usize,
    pub max_tokens: usize,
    pub max_depth: usize,
    pub max_work: usize,
    pub max_output_bytes: usize,
    pub max_expanded_nodes: usize,
    pub flags: u32,
}

/// Optional caller-owned output; no allocation and no free function is required.
/// kind: 0 = no parser error, 1 syntax, 2 validation, 3 dialect, 4 unsupported,
/// 5 limit, 6 other. start..end are end-exclusive UTF-8 byte offsets.
/// The owned error message remains available through mc_last_error/mc_error_free.
#[repr(C)]
#[derive(Clone, Copy, Default)]
pub struct McParseErrorInfo {
    pub kind: u32,
    pub start: usize,
    pub end: usize,
}

/// Parse a counted UTF-8 buffer into an owning immutable expression handle.
/// Mode: 0 PromQL, 1 MetricsQL (currently explicitly unsupported). Return null on
/// failure. Release success with mc_expr_free. Input is borrowed only for this call.
/// Interior NUL bytes are parsed, never treated as a source terminator.
/// error_info is zeroed on entry; ABI argument/panic failures use mc_last_error
/// without a parser kind. Success clears the calling thread's last error.
///
/// # Safety
/// Non-null source must reference source_len readable bytes for this call; null
/// is allowed only for zero length. Non-null options/error_info must reference
/// aligned instances of their declared types. Output must not alias the inputs.
#[no_mangle]
pub unsafe extern "C" fn mc_expr_parse(
    source: *const u8,
    source_len: usize,
    mode: u32,
    options: *const McParseOptions,
    error_info: *mut McParseErrorInfo,
) -> *mut Expr {
    if !error_info.is_null() {
        error_info.write(McParseErrorInfo::default());
    }
    boundary(|| {
        let mode = match mode {
            0 => Mode::PromQl,
            1 => Mode::MetricsQl,
            _ => return Err("invalid query mode".into()),
        };
        let input = options.as_ref().copied().unwrap_or_default();
        if input.flags & !15 != 0 {
            return Err("unknown build option flags".into());
        }
        let defaults = ParseOptions::default();
        let budget = |value, default| if value == 0 { default } else { value };
        let options = ParseOptions {
            max_input_bytes: budget(input.max_input_bytes, defaults.max_input_bytes),
            max_tokens: budget(input.max_tokens, defaults.max_tokens),
            max_depth: budget(input.max_depth, defaults.max_depth),
            max_work: budget(input.max_work, defaults.max_work),
            build: BuildOptions {
                limits: BuildLimits {
                    max_output_bytes: budget(
                        input.max_output_bytes,
                        defaults.build.limits.max_output_bytes,
                    ),
                    max_expanded_nodes: budget(
                        input.max_expanded_nodes,
                        defaults.build.limits.max_expanded_nodes,
                    ),
                },
                experimental_functions: input.flags & 1 != 0,
                syntax_features: input.flags & 14,
            },
        };
        if source_len > isize::MAX as usize || (source.is_null() && source_len != 0) {
            return Err("invalid source buffer".into());
        }
        // Enforce the input budget before scanning or decoding the caller's buffer.
        let parsed = if source_len > options.max_input_bytes {
            Err(ParseError {
                kind: ParseErrorKind::Limit,
                start: 0,
                end: 0,
                message: "input byte limit exceeded".into(),
            })
        } else {
            let bytes = if source_len == 0 {
                &[]
            } else {
                std::slice::from_raw_parts(source, source_len)
            };
            let text = std::str::from_utf8(bytes).map_err(|_| "invalid UTF-8 source")?;
            Expr::parse_with_options(text, mode, options)
        };
        let expr = parsed.map_err(|error| {
            if !error_info.is_null() {
                error_info.write(McParseErrorInfo {
                    kind: match error.kind {
                        ParseErrorKind::Syntax => 1,
                        ParseErrorKind::Validation => 2,
                        ParseErrorKind::Dialect => 3,
                        ParseErrorKind::Unsupported => 4,
                        ParseErrorKind::Limit => 5,
                        _ => 6,
                    },
                    start: error.start,
                    end: error.end,
                });
            }
            error.to_string()
        })?;
        Ok(Box::into_raw(Box::new(expr)))
    })
    .unwrap_or(ptr::null_mut())
}
