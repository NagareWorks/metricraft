#![no_main]
use libfuzzer_sys::fuzz_target;

#[path = "../../crates/metricraft-core/tests/support/compositions.rs"]
mod compositions;

fuzz_target!(|data: &[u8]| {
    compositions::exercise(data);
});
