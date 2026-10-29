use metricraft_core::expression::{
    BuildLimits, BuildOptions, Expr, Mode, ParseErrorKind, ParseOptions,
};

pub fn exercise(data: &[u8]) {
    let Ok(source) = std::str::from_utf8(data) else {
        return;
    };
    let options = ParseOptions {
        max_input_bytes: 16_384,
        max_tokens: 4096,
        max_depth: 32,
        max_work: 200_000,
        build: BuildOptions {
            limits: BuildLimits {
                max_output_bytes: 131_072,
                max_expanded_nodes: 4096,
            },
            experimental_functions: true,
            syntax_features: 14,
        },
    };
    match Expr::parse_with_options(source, Mode::PromQl, options) {
        Ok(expr) => {
            let output = expr
                .build_with_options(Mode::PromQl, options.build)
                .unwrap();
            let expanded = ParseOptions {
                max_input_bytes: 131_072,
                max_tokens: 32_768,
                max_depth: 128,
                max_work: 1_000_000,
                ..options
            };
            match Expr::parse_with_options(&output, Mode::PromQl, expanded) {
                Ok(again) => assert_eq!(
                    again
                        .build_with_options(Mode::PromQl, options.build)
                        .unwrap(),
                    output
                ),
                // Canonical parentheses may exceed recursion limits for a long flat input.
                Err(error) => assert_eq!(
                    error.kind,
                    ParseErrorKind::Limit,
                    "{source:?} -> {output:?}: {error}"
                ),
            }
            let unchanged = expr
                .replace_at(&[], &expr, Mode::PromQl, options.build)
                .unwrap();
            assert!(unchanged.shares_node(&expr));
        }
        Err(error) => {
            assert!(error.start <= error.end && error.end <= source.len());
            assert!(source.is_char_boundary(error.start) && source.is_char_boundary(error.end));
        }
    }
}
