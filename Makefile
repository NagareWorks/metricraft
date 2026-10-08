TARGET ?=

.PHONY: check fmt lint test ffi-header

check:
	cargo check --workspace $(if $(TARGET),--target $(TARGET),)

fmt:
	cargo fmt --all

lint:
	cargo clippy --workspace --all-targets -- -D warnings

test:
	cargo test --workspace $(if $(TARGET),--target $(TARGET),)

ffi-header:
	cbindgen --config cbindgen.toml --crate metricraft-ffi --output target/metricraft.h
