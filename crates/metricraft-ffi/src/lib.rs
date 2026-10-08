//! C ABI for owned immutable expressions. The mutable prototype ABI is retired.

mod errors;
pub mod expression;

pub use errors::McError;
use std::ffi::CString;
use std::os::raw::c_char;

/// Binding contract version, independent of the package release version.
/// Changes to required binding symbols, pointers or ownership increment this.
#[no_mangle]
pub extern "C" fn mc_abi_version() -> u32 {
    4
}

/// Free text returned by mc_expr_build. A null pointer is a no-op.
///
/// # Safety
/// A non-null pointer must be a live allocation returned by this library and
/// must be released exactly once.
#[no_mangle]
pub unsafe extern "C" fn mc_string_free(ptr: *mut c_char) {
    if !ptr.is_null() {
        drop(CString::from_raw(ptr));
    }
}

/// Copy the calling thread's last failure. The caller owns the returned error.
/// A successful constructor or build clears the thread's failure.
#[no_mangle]
pub extern "C" fn mc_last_error() -> *mut McError {
    errors::last_error()
}

/// Free an error returned by mc_last_error. A null pointer is a no-op.
///
/// # Safety
/// A non-null pointer must be a live error returned by this library and must be
/// released exactly once.
#[no_mangle]
pub unsafe extern "C" fn mc_error_free(err: *mut McError) {
    errors::free_error(err);
}
