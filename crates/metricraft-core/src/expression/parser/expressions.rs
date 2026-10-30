//! Precedence, function calls, aggregations and vector matching.
use super::super::{aggregation, Type};
use super::{Expr, ParseErrorKind as Error, Parser, Result, Value};

impl Parser<'_> {
    pub(super) fn expression(&mut self, minimum: u8, depth: usize) -> Result<Expr> {
        if depth >= self.options.max_depth {
            return Err(self.error(Error::Limit, "parse depth limit exceeded"));
        }
        let start = self.current().start;
        let grouped = self.is("(");
        let atom = self.atom(depth)?;
        let mut left = self.postfix(start, atom, grouped)?;
        loop {
            let op = self.current().text().to_ascii_lowercase();
            let power = match op.as_str() {
                "or" => 1,
                "and" | "unless" => 2,
                "==" | "!=" | ">" | "<" | ">=" | "<=" => 3,
                "</" | ">/" => 3,
                "+" | "-" => 4,
                "*" | "/" | "%" | "atan2" => 5,
                "^" => 6,
                _ => break,
            };
            if power < minimum {
                break;
            }
            self.index += 1;
            let modifiers = self.modifiers()?;
            let right = self.expression(if op == "^" { power } else { power + 1 }, depth + 1)?;
            // Prometheus discards empty vector matching (including its grouping)
            // when either operand is scalar. Fill modifiers still require vectors.
            let ignore_matching = (left.0.ty == Type::Scalar || right.0.ty == Type::Scalar)
                && modifiers.iter().any(|(name, args)| {
                    matches!(name.as_str(), "on" | "ignoring") && args.is_empty()
                });
            left = self.apply(start, &op, "", "", &[left, right])?;
            for (name, mut args) in modifiers {
                if ignore_matching
                    && matches!(
                        name.as_str(),
                        "on" | "ignoring" | "group_left" | "group_right"
                    )
                {
                    continue;
                }
                args.insert(0, left);
                left = self.apply(start, &name, "", "", &args)?;
            }
        }
        Ok(left)
    }

    fn atom(&mut self, depth: usize) -> Result<Expr> {
        let start = self.current().start;
        if self.eat("-") || self.eat("+") {
            let negative = self.tokens[self.index - 1].text() == "-";
            let value = self.expression(6, depth + 1)?;
            return self.apply(
                start,
                if negative { "negate" } else { "positive" },
                "",
                "",
                &[value],
            );
        }
        if self.is("{") {
            return self.selector(start, "");
        }
        if self.eat("(") {
            let value = self.expression(0, depth + 1)?;
            self.expect(")")?;
            return Ok(value);
        }
        match &self.current().value {
            Value::String(value) => {
                let value = value.clone();
                self.index += 1;
                self.apply(start, "string", &value, "", &[])
            }
            Value::Number(value) => {
                let value = (*value).to_owned();
                self.index += 1;
                self.number(start, &value)
            }
            Value::Word(word) => {
                let name = (*word).to_owned();
                let keyword = name.to_ascii_lowercase();
                self.index += 1;
                if matches!(keyword.as_str(), "inf" | "nan") {
                    return self.apply(start, "number", &keyword, "", &[]);
                }
                if matches!(
                    keyword.as_str(),
                    "bool" | "on" | "ignoring" | "group_left" | "group_right" | "atan2"
                ) {
                    return Err(super::ParseError::kind(
                        Error::Syntax,
                        start,
                        start + name.len(),
                        "keyword cannot be an unquoted metric name",
                    ));
                }
                if aggregation::is_name(&keyword)
                    && (self.is("(") || self.is("by") || self.is("without"))
                {
                    let grouping = self.grouping()?;
                    let args = self.arguments(depth, false)?;
                    let expr = self.apply(start, &keyword, "", "", &args)?;
                    let after = self.grouping()?;
                    if grouping.is_some() && after.is_some() {
                        return Err(self.error(Error::Syntax, "duplicate aggregation grouping"));
                    }
                    return if let Some((op, mut args)) = grouping.or(after) {
                        args.insert(0, expr);
                        self.apply(start, &op, "", "", &args)
                    } else {
                        Ok(expr)
                    };
                }
                if self.is("(") {
                    let mut args = self.arguments(depth, name == "info")?;
                    if name == "histogram_quantiles" && args.len() >= 2 {
                        let vector = args.remove(0);
                        args.push(vector);
                        return self.apply(start, "histogram_quantiles_auto", "", "", &args);
                    }
                    return self.apply(start, "call", &name, "", &args);
                }
                if !name
                    .bytes()
                    .all(|c| c.is_ascii_alphanumeric() || matches!(c, b'_' | b':'))
                {
                    return Err(super::ParseError::kind(
                        Error::Syntax,
                        start,
                        start + name.len(),
                        "invalid unquoted metric name",
                    ));
                }
                self.selector(start, &name)
            }
            _ => Err(self.error(Error::Syntax, "expected an expression")),
        }
    }

    pub(super) fn number(&mut self, start: usize, text: &str) -> Result<Expr> {
        let value = super::numbers::number(text)
            .map_err(|message| super::ParseError::new(start, start + text.len(), message))?;
        self.apply(start, "number", &value.to_string(), "", &[])
    }

    fn arguments(&mut self, depth: usize, info: bool) -> Result<Vec<Expr>> {
        self.expect("(")?;
        let mut args = Vec::new();
        if self.eat(")") {
            return Ok(args);
        }
        loop {
            let start = self.current().start;
            let preserve_group = info && args.len() == 1 && self.is("(");
            let value = self.expression(0, depth + 1)?;
            // info's second argument must be a direct selector, not a grouped one.
            // Keep that syntactic distinction until the builder validates the call.
            args.push(if preserve_group {
                self.apply(start, "parenthesize", "", "", &[value])?
            } else {
                value
            });
            if !self.eat(",") {
                self.expect(")")?;
                break;
            }
            if self.is(")") {
                return Err(self.error(Error::Syntax, "trailing comma in function arguments"));
            }
        }
        Ok(args)
    }

    fn grouping(&mut self) -> Result<Option<(String, Vec<Expr>)>> {
        if self.is("by") || self.is("without") {
            let op = self.current().text().to_ascii_lowercase();
            self.index += 1;
            Ok(Some((op, self.labels()?)))
        } else {
            Ok(None)
        }
    }

    fn modifiers(&mut self) -> Result<Vec<(String, Vec<Expr>)>> {
        let mut result = Vec::new();
        if self.eat("bool") {
            result.push(("bool".into(), vec![]));
        }
        if self.is("on") || self.is("ignoring") {
            let op = self.current().text().to_ascii_lowercase();
            self.index += 1;
            result.push((op, self.labels()?));
            if self.is("group_left") || self.is("group_right") {
                let op = self.current().text().to_ascii_lowercase();
                self.index += 1;
                let args = if self.is("(") { self.labels()? } else { vec![] };
                result.push((op, args));
            }
        }
        while (self.is("fill") || self.is("fill_left") || self.is("fill_right"))
            && self
                .tokens
                .get(self.index + 1)
                .is_some_and(|t| t.text() == "(")
        {
            let op = self.current().text().to_ascii_lowercase();
            self.index += 1;
            self.expect("(")?;
            let start = self.current().start;
            let value = self.signed_number()?;
            self.expect(")")?;
            result.push((
                op,
                vec![self.apply(start, "number", &value.to_string(), "", &[])?],
            ));
        }
        Ok(result)
    }
}
