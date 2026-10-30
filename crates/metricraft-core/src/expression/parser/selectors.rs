//! Selector values remain decoded data; no query fragments cross into the AST.
use super::{Expr, ParseErrorKind as Error, Parser, Result, Value};

impl Parser<'_> {
    fn label(&mut self, grouping: bool) -> Result<String> {
        let value = match &self.current().value {
            Value::Word(value)
                if if grouping {
                    grouping_label(value)
                } else {
                    super::super::identifier(value, false)
                } =>
            {
                (*value).to_owned()
            }
            Value::String(value) => value.clone(),
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
            if self.is("inf") || self.is("nan") || self.is("without") {
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
        while !self.eat("}") {
            let quoted = matches!(self.current().value, Value::String(_));
            let label = self.label(false)?;
            if quoted && (self.is(",") || self.is("}")) {
                if !metric.is_empty() {
                    return Err(self.error(Error::Syntax, "duplicate metric name"));
                }
                selector = self.apply(start, "=", "__name__", &label, &[selector])?;
            } else {
                if label == "__name__" && !metric.is_empty() {
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
                if matches!(op.as_str(), "=~" | "!~") {
                    self.charge(value.len().saturating_mul(32))?;
                    super::regex::validate(&value)
                        .map_err(|(kind, message)| self.error(kind, message))?;
                }
                self.index += 1;
                selector = self.apply(start, &op, &label, &value, &[selector])?;
            }
            if !self.eat(",") {
                self.expect("}")?;
                break;
            }
        }
        Ok(selector)
    }
}

fn grouping_label(value: &str) -> bool {
    let mut bytes = value.bytes();
    bytes
        .next()
        .is_some_and(|c| c.is_ascii_alphabetic() || matches!(c, b'_' | b':'))
        && bytes.all(|c| c.is_ascii_alphanumeric() || matches!(c, b'_' | b':'))
}
