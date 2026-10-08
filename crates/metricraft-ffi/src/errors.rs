use std::cell::RefCell;
use std::ffi::CString;
use std::os::raw::{c_char, c_uint};
use std::panic::{catch_unwind, AssertUnwindSafe};

const ERR_INVALID_ARGUMENT: c_uint = 1;
const ERR_INTERNAL: c_uint = 2;

#[repr(C)]
pub struct McError {
    pub code: c_uint,
    pub message: *mut c_char,
}

thread_local! {
    // The Windows GNU std TLS expansion is also linted; the user initializer is const.
    #[allow(clippy::missing_const_for_thread_local)]
    static LAST_ERROR: RefCell<Option<(c_uint, String)>> = const { RefCell::new(None) };
}

fn set_error(code: c_uint, msg: impl Into<String>) {
    LAST_ERROR.with(|cell| {
        *cell.borrow_mut() = Some((code, msg.into()));
    });
}

fn clear_error() {
    LAST_ERROR.with(|cell| {
        *cell.borrow_mut() = None;
    });
}

/// Keep recoverable Rust panics inside the ABI. Invalid C pointers, allocation
/// aborts and stack overflow remain outside this contract.
pub fn boundary<T>(call: impl FnOnce() -> Result<T, String>) -> Option<T> {
    clear_error();
    match catch_unwind(AssertUnwindSafe(call)) {
        Ok(Ok(value)) => Some(value),
        Ok(Err(message)) => {
            set_error(ERR_INVALID_ARGUMENT, message);
            None
        }
        Err(_) => {
            set_error(ERR_INTERNAL, "internal query engine failure");
            None
        }
    }
}

pub fn last_error() -> *mut McError {
    LAST_ERROR.with(|cell| {
        if let Some((code, msg)) = cell.borrow().as_ref() {
            if let Ok(cmsg) = CString::new(msg.as_str()) {
                let err = McError {
                    code: *code,
                    message: cmsg.into_raw(),
                };
                return Box::into_raw(Box::new(err));
            }
        }
        std::ptr::null_mut()
    })
}

pub unsafe fn free_error(err: *mut McError) {
    if err.is_null() {
        return;
    }
    unsafe {
        let boxed = Box::from_raw(err);
        if !boxed.message.is_null() {
            let _ = CString::from_raw(boxed.message);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn panic_is_reported_and_the_thread_can_recover() {
        let value: Option<()> = boundary(|| panic!("injected engine failure"));
        assert!(value.is_none());
        unsafe {
            let error = last_error();
            assert!(!error.is_null());
            assert_eq!((*error).code, ERR_INTERNAL);
            free_error(error);
        }
        assert_eq!(boundary(|| Ok(42)), Some(42));
        assert!(last_error().is_null());
    }
}
