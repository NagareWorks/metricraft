//! Literal ranges, subqueries and time modifiers. Computed durations are explicit gaps.
use super::super::{Extra, Kind};
use super::{Expr, ParseErrorKind as Error, Parser, Result, Value};

impl Parser<'_> {
    pub(super) fn postfix(
        &mut self,
        start: usize,
        mut expr: Expr,
        mut grouped: bool,
    ) -> Result<Expr> {
        loop {
            if grouped
                && (self.is("offset") || self.is("@") || self.is("anchored") || self.is("smoothed"))
            {
                return Err(self.error(
                    Error::Syntax,
                    "time modifier cannot follow a parenthesized expression",
                ));
            }
            if self.eat("[") {
                let window = self.duration()?;
                if self.eat(":") {
                    let step = if self.is("]") {
                        String::new()
                    } else {
                        self.duration()?
                    };
                    self.duration_end("]")?;
                    expr = self.apply(start, "subquery", &window, &step, &[expr])?;
                } else {
                    self.duration_end("]")?;
                    if grouped {
                        return Err(self.error(
                            Error::Syntax,
                            "range selector must directly follow a metric selector",
                        ));
                    }
                    if matches!(&expr.0.kind, Kind::Offset(_, value) if value.parse::<f64>() == Ok(0.0))
                        || matches!(&expr.0.kind, Kind::Extra(Extra::Suffix(_, _)))
                    {
                        return Err(self.error(Error::Unsupported, "time modifiers before a range are not supported; place them after the range"));
                    }
                    expr = self.apply(start, "range", &window, "", &[expr])?;
                }
                grouped = false;
            } else if self.eat("offset") {
                let negative = self.eat("-");
                if !negative {
                    self.eat("+");
                }
                let duration = self.duration()?;
                let duration = if negative {
                    format!("-{duration}")
                } else {
                    duration
                };
                expr = self.apply(start, "offset", &duration, "", &[expr])?;
            } else if self.eat("@") {
                let value = if self.is("start") || self.is("end") {
                    let value = self.current().text().to_ascii_lowercase();
                    self.index += 1;
                    self.expect("(")?;
                    self.expect(")")?;
                    value
                } else {
                    let value = self.signed_number()?;
                    if !value.is_finite() || value.abs() >= 9_223_372_036_854_775_808.0 {
                        return Err(self.error(Error::Validation, "timestamp out of bounds"));
                    }
                    value.to_string()
                };
                expr = self.apply(start, "at", &value, "", &[expr])?;
            } else if self.is("anchored") || self.is("smoothed") {
                let op = self.current().text().to_ascii_lowercase();
                self.index += 1;
                expr = self.suffix(start, expr, &op)?;
            } else {
                break;
            }
        }
        Ok(expr)
    }

    fn duration(&mut self) -> Result<String> {
        if self.is("nan") {
            return Err(self.error(
                Error::Unsupported,
                "non-finite durations cannot be represented by the AST",
            ));
        }
        let Value::Number(text) = self.current().value else {
            return Err(self.error(
                if self.is("(")
                    || self.is("+")
                    || self.is("-")
                    || self.is("step")
                    || self.is("range")
                    || self.is("min_of")
                    || self.is("max_of")
                {
                    Error::Unsupported
                } else {
                    Error::Syntax
                },
                "expected a literal duration; computed duration parsing is not implemented yet",
            ));
        };
        let value =
            super::numbers::number(text).map_err(|message| self.error(Error::Syntax, message))?;
        if !value.is_finite() || value > 9_223_372_036.854_776 {
            return Err(self.error(Error::Validation, "duration out of range"));
        }
        let text = if super::super::classic_duration(text) {
            text.to_owned()
        } else {
            value.to_string()
        };
        self.index += 1;
        Ok(text)
    }

    fn suffix(&mut self, start: usize, expr: Expr, op: &str) -> Result<Expr> {
        // offset and @ decorate the same selector in PromQL regardless of order.
        // There can be at most one of each before this suffix.
        match &expr.0.kind {
            Kind::Offset(child, value) | Kind::At(child, value) => {
                let wrapper = if matches!(expr.0.kind, Kind::Offset(..)) {
                    "offset"
                } else {
                    "at"
                };
                let inner = self.suffix(start, child.clone(), op)?;
                let value = if wrapper == "at" {
                    value.strip_suffix("()").unwrap_or(value)
                } else {
                    value
                };
                self.apply(start, wrapper, value, "", &[inner])
            }
            _ => self.apply(start, op, "", "", &[expr]),
        }
    }

    fn duration_end(&mut self, end: &str) -> Result<()> {
        if matches!(self.current().text(), "+" | "-" | "*" | "/" | "%" | "^") {
            return Err(self.error(
                Error::Unsupported,
                "computed duration parsing is not implemented yet",
            ));
        }
        self.expect(end)
    }
}
