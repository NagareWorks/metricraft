#![no_main]
use libfuzzer_sys::fuzz_target;

#[path = "../../crates/metricraft-core/tests/support/parsing.rs"]
mod parsing;

fuzz_target!(|data: &[u8]| {
    parsing::exercise(data);
});
