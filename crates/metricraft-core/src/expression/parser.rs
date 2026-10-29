//! Query text enters the builder's existing immutable graph, never a raw node.
mod expressions;
mod lexer;
mod numbers;
mod regex;
mod selectors;
mod time;

use super::{BuildOptions, Expr, Mode};
use lexer::{Token, Value};
use std::fmt;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[non_exhaustive]
pub enum ParseErrorKind {
    /// Invalid tokens, delimiters, or grammar.
    Syntax,
    /// The parsed shape violates a type, value, or enabled-feature constraint.
    Validation,
    /// A recognized expression requires a different query dialect.
    Dialect,
    /// This parser or the shared AST cannot yet represent the construct.
    Unsupported,
    /// A configured resource budget was exceeded or is invalid.
    Limit,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ParseError {
    pub kind: ParseErrorKind,
    /// UTF-8 byte offsets in the original input, end exclusive.
    pub start: usize,
    pub end: usize,
    pub message: String,
}

impl ParseError {
    fn new(start: usize, end: usize, message: impl Into<String>) -> Self {
        Self::kind(ParseErrorKind::Syntax, start, end, message)
    }
    fn kind(kind: ParseErrorKind, start: usize, end: usize, message: impl Into<String>) -> Self {
        Self {
            kind,
            start,
            end,
            message: message.into(),
        }
    }
}
impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} at bytes {}..{}", self.message, self.start, self.end)
    }
}
impl std::error::Error for ParseError {}

#[derive(Clone, Copy, Debug)]
pub struct ParseOptions {
    /// Maximum UTF-8 input bytes; default 1 MiB, must be nonzero.
    pub max_input_bytes: usize,
    /// Maximum lexical tokens, excluding EOF; default 100,000, must be nonzero.
    pub max_tokens: usize,
    /// Recursive grammar depth, in 1..=128; AST rendering itself is iterative.
    pub max_depth: usize,
    /// Conservative construction/validation work units, not a time limit.
    pub max_work: usize,
    /// Output/node budgets and explicit Prometheus experimental-feature flags.
    pub build: BuildOptions,
}
impl Default for ParseOptions {
    fn default() -> Self {
        Self {
            max_input_bytes: 1024 * 1024,
            max_tokens: 100_000,
            max_depth: 64,
            max_work: 1_000_000,
            build: BuildOptions::default(),
        }
    }
}

impl Expr {
    /// Parse PromQL into the same graph used by builders and `replace_at`.
    /// MetricsQL parsing and computed duration syntax are not implemented yet.
    /// Formatting/comments are discarded; no raw-expression fallback is used.
    /// See `docs/query-parsing.md` for the supported subset and other limitations.
    pub fn parse(source: &str, mode: Mode) -> Result<Self> {
        Self::parse_with_options(source, mode, ParseOptions::default())
    }

    pub fn parse_with_options(source: &str, mode: Mode, options: ParseOptions) -> Result<Self> {
        if options.max_input_bytes == 0
            || options.max_tokens == 0
            || options.max_work == 0
            || !(1..=128).contains(&options.max_depth)
        {
            return Err(ParseError::kind(
                ParseErrorKind::Limit,
                0,
                0,
                "invalid parse limits (depth must be 1..128)",
            ));
        }
        if source.len() > options.max_input_bytes {
            return Err(ParseError::kind(
                ParseErrorKind::Limit,
                0,
                0,
                "input byte limit exceeded",
            ));
        }
        if mode != Mode::PromQl {
            return Err(ParseError::kind(
                ParseErrorKind::Unsupported,
                0,
                source.len(),
                "MetricsQL parsing is not implemented yet",
            ));
        }
        let mut parser = Parser {
            tokens: lexer::lex(source, options.max_tokens)?,
            index: 0,
            options,
            work: 0,
        };
        let expr = parser.expression(0, 0)?;
        if !matches!(parser.current().value, Value::End) {
            return Err(parser.error(ParseErrorKind::Syntax, "unexpected trailing input"));
        }
        expr.build_with_options(mode, options.build)
            .map_err(|message| {
                ParseError::kind(ParseErrorKind::Validation, 0, source.len(), message)
            })?;
        Ok(expr)
    }
}

type Result<T> = std::result::Result<T, ParseError>;
struct Parser<'a> {
    tokens: Vec<Token<'a>>,
    index: usize,
    options: ParseOptions,
    work: usize,
}

impl Parser<'_> {
    fn current(&self) -> &Token<'_> {
        &self.tokens[self.index]
    }
    fn error(&self, kind: ParseErrorKind, message: impl Into<String>) -> ParseError {
        ParseError::kind(kind, self.current().start, self.current().end, message)
    }
    fn is(&self, text: &str) -> bool {
        self.current().text().eq_ignore_ascii_case(text)
    }
    fn eat(&mut self, text: &str) -> bool {
        if self.is(text) {
            self.index += 1;
            true
        } else {
            false
        }
    }
    fn expect(&mut self, text: &str) -> Result<()> {
        if self.eat(text) {
            Ok(())
        } else {
            Err(self.error(ParseErrorKind::Syntax, format!("expected {text:?}")))
        }
    }
    fn charge(&mut self, amount: usize) -> Result<()> {
        self.work = self.work.saturating_add(amount);
        if self.work > self.options.max_work {
            Err(self.error(ParseErrorKind::Limit, "parse work limit exceeded"))
        } else {
            Ok(())
        }
    }
    fn apply(&mut self, start: usize, op: &str, a: &str, b: &str, args: &[Expr]) -> Result<Expr> {
        self.charge(
            1usize
                .saturating_add(a.len())
                .saturating_add(b.len())
                .saturating_add(args.len()),
        )?;
        // Existing builder label validation checks duplicates pairwise.
        if matches!(
            op,
            "by" | "without" | "on" | "ignoring" | "group_left" | "group_right"
        ) {
            let bytes = args
                .iter()
                .skip(1)
                .map(|a| a.complexity().output_bytes)
                .fold(0usize, usize::saturating_add);
            self.charge(args.len().saturating_mul(bytes))?;
        }
        let end = self.tokens[self.index.saturating_sub(1)].end.max(start);
        let expr = Expr::apply(op, a, b, args)
            .map_err(|message| ParseError::kind(ParseErrorKind::Validation, start, end, message))?;
        if expr.0.required_mode == Some(Mode::MetricsQl) {
            return Err(ParseError::kind(
                ParseErrorKind::Dialect,
                start,
                end,
                "expression requires MetricsQL",
            ));
        }
        let complexity = expr.complexity();
        if complexity.expanded_nodes > self.options.build.limits.max_expanded_nodes
            || complexity.output_bytes > self.options.build.limits.max_output_bytes
        {
            return Err(ParseError::kind(
                ParseErrorKind::Limit,
                start,
                end,
                "parsed expression exceeds build limits",
            ));
        }
        Ok(expr)
    }
}
