//! MetricsQL differences around the shared expression grammar.
//!
//! Keep unsupported syntax explicit until it has upstream semantic witnesses;
//! in particular, PromQL duration expressions must not be reused here.
use super::{Expr, ParseError, ParseErrorKind as Error, Parser, Result, Value};

impl Parser<'_> {
    pub(super) fn vm_rollup_start(&self) -> bool {
        self.is("[") || self.is("offset") || self.is("@")
    }

    pub(super) fn vm_number(&self, start: usize, text: &str) -> Result<f64> {
        // Decimal/octal numbers share the upstream base-0-then-float behavior.
        // Duration scalars and size multipliers need MetricsQL's own lowering.
        if text
            .bytes()
            .any(|c| c.is_ascii_alphabetic() && c != b'e' && c != b'E')
            && !text.eq_ignore_ascii_case("inf")
            && !text.eq_ignore_ascii_case("nan")
        {
            return Err(ParseError::kind(
                Error::Unsupported,
                start,
                start + text.len(),
                "MetricsQL duration scalars and numeric suffixes are not implemented yet",
            ));
        }
        if text
            .split_once(['e', 'E'])
            .is_some_and(|(_, exponent)| exponent.contains('_'))
        {
            return Err(ParseError::new(
                start,
                start + text.len(),
                "numeric separators are not allowed in MetricsQL exponents",
            ));
        }
        let value = super::numbers::number(text)
            .map_err(|message| ParseError::new(start, start + text.len(), message))?;
        // Upstream selects base-0 only when the *original* second byte is a
        // digit. 0_10 is decimal ten; 010 and 01_0 are octal eight.
        if text.starts_with("0_") {
            return text.replace('_', "").parse::<f64>().map_err(|_| {
                ParseError::new(start, start + text.len(), "invalid decimal literal")
            });
        }
        Ok(value)
    }

    pub(super) fn vm_postfix(&mut self, start: usize, mut expr: Expr) -> Result<Expr> {
        if self.eat("[") {
            let window = if self.is(":") {
                String::new()
            } else {
                self.vm_duration(false)?
            };
            if self.eat(":") {
                let step = if self.is("]") {
                    String::new()
                } else {
                    self.vm_duration(false)?
                };
                self.expect("]")?;
                expr = self.apply(start, "subquery", &window, &step, &[expr])?;
            } else {
                self.expect("]")?;
                expr = self.apply(start, "range", &window, "", &[expr])?;
            }
        }
        // One rollup tail: [window:step], optional @, offset, optional @.
        // Repetition or reordered brackets remain trailing syntax errors.
        if self.eat("@") {
            expr = self.vm_at(start, expr)?;
        }
        if self.eat("offset") {
            let negative = self.eat("-");
            let duration = self.vm_duration(true)?;
            let duration = if negative {
                format!("-{duration}")
            } else {
                duration
            };
            expr = self.apply(start, "offset", &duration, "", &[expr])?;
        }
        if self.eat("@") {
            expr = self.vm_at(start, expr)?;
        }
        Ok(expr)
    }

    fn vm_duration(&mut self, zero: bool) -> Result<String> {
        let Value::Number(text) = &self.current().value else {
            return Err(self.error(
                Error::Unsupported,
                "expected a literal MetricsQL duration; computed windows are not supported",
            ));
        };
        let text = (*text).to_owned();
        // Lowercase fractional/step durations can remain literal metadata. The
        // backend retains responsibility for millisecond truncation and steps.
        // Uppercase M means a numeric multiplier, so never lowercase blindly.
        if text.bytes().any(|c| c.is_ascii_uppercase()) || text.contains('_') {
            return Err(self.error(
                Error::Unsupported,
                "uppercase or separated MetricsQL durations are not implemented yet",
            ));
        }
        // The unitless number `.5` is valid, but each unit-bearing duration
        // component needs an integer part: `.5m` and `1h.5m` are not VM tokens.
        if text.parse::<f64>().is_err()
            && text
                .bytes()
                .enumerate()
                .any(|(i, c)| c == b'.' && (i == 0 || !text.as_bytes()[i - 1].is_ascii_digit()))
        {
            return Err(self.error(
                Error::Syntax,
                "MetricsQL duration components require a digit before the decimal point",
            ));
        }
        super::super::literals::duration(&text, zero)
            .map_err(|message| self.error(Error::Validation, message))?;
        self.index += 1;
        // Adjacent signed duration parts are a single MetricsQL literal, not
        // sample arithmetic (e.g. `offset 1h-5m`). Do not reinterpret them.
        if self.is("-") && self.tokens[self.index - 1].end == self.current().start
            && self.tokens.get(self.index + 1).is_some_and(|t| {
                matches!(t.value, Value::Number(s) if s.bytes().any(|c| matches!(c, b'm' | b's' | b'h' | b'd' | b'w' | b'y' | b'i')))
            })
        {
            return Err(self.error(Error::Unsupported, "signed compound MetricsQL durations are not implemented yet"));
        }
        Ok(text)
    }

    fn vm_at(&mut self, start: usize, expr: Expr) -> Result<Expr> {
        let value = if self.is("start") || self.is("end") {
            let value = self.current().text().to_ascii_lowercase();
            self.index += 1;
            self.expect("(")?;
            self.expect(")")?;
            value
        } else {
            if self.is("(") || matches!(self.current().value, Value::Word(_)) {
                return Err(self.error(
                    Error::Unsupported,
                    "MetricsQL computed @ timestamps are not implemented yet",
                ));
            }
            let signed = self.is("+") || self.is("-");
            let value = self.signed_number()?;
            if signed && self.vm_rollup_start() {
                // In VM a sign consumes a full single expression, including
                // its rollup tail. That tail belongs inside the @ expression.
                return Err(self.error(
                    Error::Unsupported,
                    "rollups inside signed MetricsQL @ timestamps are not implemented yet",
                ));
            }
            value.to_string()
        };
        self.apply(start, "at", &value, "", &[expr])
    }
}
