//! Ranges, subqueries and time modifiers backed by the shared expression graph.
use super::super::{Extra, Kind};
use super::{Expr, ParseErrorKind as Error, Parser, Result};

impl Parser<'_> {
    pub(super) fn postfix(
        &mut self,
        start: usize,
        mut expr: Expr,
        mut grouped: bool,
        depth: usize,
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
                let window = self.duration(0, depth + 1)?;
                if self.eat(":") {
                    let step = if self.is("]") {
                        None
                    } else {
                        Some(self.duration(0, depth + 1)?)
                    };
                    self.expect("]")?;
                    if let Some(literal) = window.literal() {
                        if step.as_ref().is_none_or(|s| s.literal().is_some()) {
                            let step = step.as_ref().and_then(|s| s.literal()).unwrap_or("");
                            expr = self.apply(start, "subquery", literal, step, &[expr])?;
                            grouped = false;
                            continue;
                        }
                    }
                    let mut args = vec![expr, window.into_expr(self)?];
                    if let Some(step) = step {
                        args.push(step.into_expr(self)?);
                    }
                    expr = self.apply(start, "subquery_expr", "", "", &args)?;
                } else {
                    self.expect("]")?;
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
                    expr = if let Some(literal) = window.literal() {
                        self.apply(start, "range", literal, "", &[expr])?
                    } else {
                        let window = window.into_expr(self)?;
                        self.apply(start, "range_expr", "", "", &[expr, window])?
                    };
                }
                grouped = false;
            } else if self.eat("offset") {
                let duration = self.offset_duration(depth + 1)?;
                expr = if let Some(literal) = duration.literal() {
                    self.apply(start, "offset", literal, "", &[expr])?
                } else {
                    let duration = duration.into_expr(self)?;
                    self.apply(start, "offset_expr", "", "", &[expr, duration])?
                };
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
            Kind::Extra(Extra::Offset(child, value)) => {
                let inner = self.suffix(start, child.clone(), op)?;
                self.apply(start, "offset_expr", "", "", &[inner, value.clone()])
            }
            _ => self.apply(start, op, "", "", &[expr]),
        }
    }
}
