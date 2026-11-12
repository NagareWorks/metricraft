//! The restricted arithmetic grammar used inside ranges, subqueries and offsets.
use super::super::Kind;
use super::{Expr, ParseErrorKind as Error, Parser, Result, Value};

pub(super) enum Duration {
    Literal {
        value: f64,
        text: String,
        start: usize,
    },
    Computed(Expr),
}

impl Duration {
    pub fn literal(&self) -> Option<&str> {
        match self {
            Self::Literal { text, .. } => Some(text),
            Self::Computed(_) => None,
        }
    }

    pub fn into_expr(self, parser: &mut Parser<'_>) -> Result<Expr> {
        match self {
            Self::Literal { value, start, .. } => {
                parser.apply(start, "number", &value.to_string(), "", &[])
            }
            Self::Computed(expr) => Ok(expr),
        }
    }
}

impl Parser<'_> {
    pub(super) fn offset_duration(&mut self, depth: usize) -> Result<Duration> {
        // The upstream grammar reduces bare numbers/functions immediately, but
        // a leading parenthesis selects duration_expr and consumes its arithmetic.
        // A single sign followed by a literal, function or parentheses is also
        // atomic. Repeated signs use the general duration-expression alternative.
        let computed = self.is("(")
            || (self.is("+") || self.is("-"))
                && matches!(self.tokens[self.index + 1].text(), "+" | "-");
        self.duration(if computed { 0 } else { 7 }, depth)
    }

    pub(super) fn duration(&mut self, minimum: u8, depth: usize) -> Result<Duration> {
        if depth >= self.options.max_depth {
            return Err(self.error(Error::Limit, "parse depth limit exceeded"));
        }
        let start = self.current().start;
        let mut left = self.duration_atom(minimum, depth)?;
        loop {
            let op = self.current().text();
            let power = match op {
                "+" | "-" => 4,
                "*" | "/" | "%" => 5,
                "^" => 6,
                _ => break,
            };
            if power < minimum {
                break;
            }
            let op = op.to_owned();
            self.index += 1;
            let right = self.duration(if op == "^" { power } else { power + 1 }, depth + 1)?;
            let args = [left.into_expr(self)?, right.into_expr(self)?];
            left = Duration::Computed(self.apply(start, &op, "", "", &args)?);
        }
        Ok(left)
    }

    fn duration_atom(&mut self, minimum: u8, depth: usize) -> Result<Duration> {
        let start = self.current().start;
        if self.eat("-") || self.eat("+") {
            let negative = self.tokens[self.index - 1].text() == "-";
            // Unparenthesized offsets stop at the first operand, even before ^.
            let value = self.duration(minimum.max(6), depth + 1)?;
            if !negative {
                return Ok(value);
            }
            return match value {
                Duration::Literal { value, text, .. } => Ok(Duration::Literal {
                    value: -value,
                    text: text
                        .strip_prefix('-')
                        .map(str::to_owned)
                        .unwrap_or_else(|| format!("-{text}")),
                    start,
                }),
                Duration::Computed(expr) => Ok(Duration::Computed(self.apply(
                    start,
                    "negate",
                    "",
                    "",
                    &[expr],
                )?)),
            };
        }
        if self.eat("(") {
            let value = self.duration(0, depth + 1)?.into_expr(self)?;
            self.expect(")")?;
            // Prometheus distinguishes (0) from the literal 0: the former is
            // evaluated at query time. Preserve that distinction without growing
            // parentheses on each parse/render cycle.
            return Ok(Duration::Computed(
                if matches!(value.0.kind, Kind::Number(_)) {
                    self.apply(start, "parenthesize", "", "", &[value])?
                } else {
                    value
                },
            ));
        }
        let name = self.current().text().to_ascii_lowercase();
        if matches!(name.as_str(), "step" | "range" | "min_of" | "max_of") {
            self.index += 1;
            self.expect("(")?;
            let args = if matches!(name.as_str(), "min_of" | "max_of") {
                let left = self.duration(0, depth + 1)?.into_expr(self)?;
                self.expect(",")?;
                vec![left, self.duration(0, depth + 1)?.into_expr(self)?]
            } else {
                Vec::new()
            };
            self.expect(")")?;
            return Ok(Duration::Computed(
                self.apply(start, "call", &name, "", &args)?,
            ));
        }
        if self.is("nan") {
            return Err(self.error(
                Error::Unsupported,
                "non-finite durations cannot be represented by the AST",
            ));
        }
        let Value::Number(text) = self.current().value else {
            return Err(self.error(Error::Syntax, "expected a duration operand"));
        };
        let value =
            super::numbers::number(text).map_err(|message| self.error(Error::Syntax, message))?;
        if !value.is_finite() || value > 9_223_372_036.854_776 {
            return Err(self.error(Error::Validation, "duration out of range"));
        }
        let literal = if super::super::classic_duration(text) {
            text.to_owned()
        } else {
            value.to_string()
        };
        self.index += 1;
        Ok(Duration::Literal {
            value,
            text: literal,
            start,
        })
    }
}
