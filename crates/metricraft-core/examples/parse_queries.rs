//! Test-only batch bridge for pinned upstream conformance (hex UTF-8 lines).
use metricraft_core::expression::{BuildOptions, Expr, Mode, ParseOptions};
use std::io::{self, BufRead};

fn hex(text: &str) -> String {
    use std::fmt::Write;
    let mut output = String::with_capacity(text.len() * 2);
    for byte in text.bytes() {
        write!(output, "{byte:02x}").unwrap();
    }
    output
}

fn main() {
    let utf8_names = std::env::args().any(|arg| arg == "--unquoted-utf8-names");
    let mode = if std::env::args().any(|arg| arg == "--metricsql") {
        Mode::MetricsQl
    } else {
        Mode::PromQl
    };
    let options = ParseOptions {
        build: BuildOptions {
            experimental_functions: true,
            syntax_features: 14 | if utf8_names { 16 } else { 0 },
            ..Default::default()
        },
        ..Default::default()
    };
    for line in io::stdin().lock().lines() {
        let line = line.unwrap();
        let bytes = (0..line.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&line[i..i + 2], 16).unwrap())
            .collect();
        let input = String::from_utf8(bytes).unwrap();
        match Expr::parse_with_options(&input, mode, options) {
            Ok(expr) => {
                let text = expr.build_with_options(mode, options.build).unwrap();
                let reparsed = Expr::parse_with_options(&text, mode, options).unwrap();
                assert_eq!(
                    reparsed.build_with_options(mode, options.build).unwrap(),
                    text
                );
                println!("ok\t{}", hex(&text));
            }
            Err(error) => println!(
                "err\t{:?}\t{}\t{}\t{}",
                error.kind,
                error.start,
                error.end,
                hex(&error.message)
            ),
        }
    }
}
