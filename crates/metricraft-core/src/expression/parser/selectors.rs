//! Selector values remain decoded data; no query fragments cross into the AST.
use super::{Expr, Mode, ParseErrorKind as Error, Parser, Result, Value};

impl Parser<'_> {
    fn label(&mut self, grouping: bool) -> Result<String> {
        let extended = self.mode == Mode::PromQl
            && self.options.build.syntax_features & super::names::FEATURE != 0;
        let value = match &self.current().value {
            Value::Word(value) if super::names::valid(value, grouping && !extended, extended) => {
                (*value).to_owned()
            }
            Value::String(value) => {
                if self.mode == Mode::MetricsQl {
                    let raw = &self.source[self.current().start + 1..self.current().end - 1];
                    if raw.contains('\\') || !super::names::valid(raw, true, false) {
                        return Err(self.error(
                            Error::Unsupported,
                            "MetricsQL extended/escaped quoted identifiers are not implemented yet",
                        ));
                    }
                }
                value.clone()
            }
            _ => return Err(self.error(Error::Syntax, "expected a label name")),
        };
        self.index += 1;
        Ok(value)
    }

    pub(super) fn labels(&mut self) -> Result<Vec<Expr>> {
        self.expect("(")?;
        let mut result = Vec::new();
        let mut seen = std::collections::HashSet::new();
        while !self.eat(")") {
            let start = self.current().start;
            if self.mode == Mode::PromQl && (self.is("inf") || self.is("nan") || self.is("without"))
            {
                return Err(self.error(
                    Error::Syntax,
                    "reserved token cannot be an unquoted grouping label",
                ));
            }
            let name = self.label(true)?;
            if !seen.insert(name.clone()) {
                return Err(self.error(
                    Error::Unsupported,
                    "duplicate grouping labels are not supported by the AST",
                ));
            }
            result.push(self.apply(start, "string", &name, "", &[])?);
            if !self.eat(",") {
                self.expect(")")?;
                break;
            }
        }
        Ok(result)
    }

    pub(super) fn selector(&mut self, start: usize, metric: &str) -> Result<Expr> {
        let mut selector = self.apply(
            start,
            if metric.is_empty() {
                "selector"
            } else {
                "metric"
            },
            metric,
            "",
            &[],
        )?;
        if !self.eat("{") {
            return Ok(selector);
        }
        let mut exact_name = std::borrow::Cow::Borrowed(metric);
        while !self.eat("}") {
            let quoted = matches!(self.current().value, Value::String(_));
            let label = self.label(false)?;
            if quoted && (self.is(",") || self.is("}")) {
                if self.mode == Mode::PromQl && !metric.is_empty() {
                    return Err(self.error(Error::Syntax, "duplicate metric name"));
                }
                self.check_metric_name(&mut exact_name, &label)?;
                selector = self.apply(start, "=", "__name__", &label, &[selector])?;
            } else {
                if self.mode == Mode::PromQl && label == "__name__" && !metric.is_empty() {
                    return Err(self.error(Error::Validation, "metric name must not be set twice"));
                }
                let op = self.current().text().to_owned();
                if !matches!(op.as_str(), "=" | "!=" | "=~" | "!~") {
                    return Err(self.error(Error::Syntax, "expected a label matcher"));
                }
                self.index += 1;
                let Value::String(value) = &self.current().value else {
                    return Err(self.error(Error::Syntax, "expected a quoted matcher value"));
                };
                let value = value.clone();
                if label == "__name__" && op == "=" {
                    self.check_metric_name(&mut exact_name, &value)?;
                }
                if matches!(op.as_str(), "=~" | "!~") {
                    self.charge(value.len().saturating_mul(32))?;
                    super::regex::validate(&value)
                        .map_err(|(kind, message)| self.error(kind, message))?;
                }
                self.index += 1;
                selector = self.apply(start, &op, &label, &value, &[selector])?;
            }
            if self.mode == Mode::MetricsQl && (self.is("or") || self.is("+")) {
                return Err(self.error(
                    Error::Unsupported,
                    "MetricsQL selector alternatives and computed strings are not implemented yet",
                ));
            }
            if !self.eat(",") {
                self.expect("}")?;
                break;
            }
        }
        Ok(selector)
    }

    fn check_metric_name(
        &self,
        previous: &mut std::borrow::Cow<'_, str>,
        value: &str,
    ) -> Result<()> {
        if self.mode == Mode::MetricsQl {
            // Upstream treats an empty earlier name as unset, but rejects a
            // different name (including empty) after a nonempty exact name.
            if !previous.is_empty() && previous.as_ref() != value {
                return Err(self.error(Error::Validation, "conflicting exact metric names"));
            }
            if previous.is_empty() {
                *previous = std::borrow::Cow::Owned(value.to_owned());
            }
        }
        Ok(())
    }
}
