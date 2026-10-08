// A standalone process keeps allocator accounting free of test-harness allocations.
#[path = "../examples/memory_profile.rs"]
mod profile;

fn main() {
    profile::main();
}
