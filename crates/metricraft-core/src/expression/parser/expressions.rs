//! Precedence, function calls, aggregations and vector matching.
use super::super::{aggregation, Type};
use super::{Expr, Mode, ParseErrorKind as Error, Parser, Result, Value};

impl Parser<'_> {
    pub(super) fn expression(&mut self, minimum: i8, depth: usize) -> Result<Expr> {
        self.expression_tail(minimum, depth).map(|(expr, _)| expr)
    }

    fn expression_tail(&mut self, minimum: i8, depth: usize) -> Result<(Expr, bool)> {
        if depth >= self.options.max_depth {
            return Err(self.error(Error::Limit, "parse depth limit exceeded"));
        }
        let start = self.current().start;
        let grouped = self.is("(");
        let atom = self.atom(minimum, depth)?;
        let mut left = self.postfix(start, atom, grouped, depth)?;
        let mut consumed_binary = false;
        loop {
            let op = self.current().text().to_ascii_lowercase();
            let power = match op.as_str() {
                "default" if self.mode == Mode::MetricsQl => -1,
                "if" | "ifnot" if self.mode == Mode::MetricsQl => 0,
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
            consumed_binary = true;
            self.index += 1;
            let modifiers = self.modifiers(&op)?;
            let right = self.expression(if op == "^" { power } else { power + 1 }, depth + 1)?;
            // Prometheus discards empty vector matching (including its grouping)
            // when either operand is scalar. Fill modifiers still require vectors.
            let ignore_matching = self.mode == Mode::PromQl
                && (left.0.ty == Type::Scalar || right.0.ty == Type::Scalar)
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
        Ok((left, consumed_binary))
    }

    fn atom(&mut self, minimum: i8, depth: usize) -> Result<Expr> {
        let start = self.current().start;
        if self.eat("-") || self.eat("+") {
            let negative = self.tokens[self.index - 1].text() == "-";
            // MetricsQL lowers unary minus to zero subtraction before balancing
            // operators. Respect the enclosing RHS precedence as well.
            let power = if self.mode == Mode::MetricsQl {
                minimum.max(5)
            } else {
                6
            };
            let (value, consumed_binary) = self.expression_tail(power, depth + 1)?;
            if self.mode == Mode::MetricsQl && consumed_binary && self.vm_rollup_start() {
                // Balancing a unary minus may consume following arithmetic,
                // but a leftover postfix belongs to its original RHS. It must
                // not attach to the entire newly negated product.
                return Err(self.error(Error::Syntax, "unexpected rollup after a binary operand"));
            }
            if !negative && self.mode == Mode::MetricsQl {
                // Upstream removes unary plus before balancing binary nodes.
                return Ok(value);
            }
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
            let value = self.expression(-1, depth + 1)?;
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
                if self.mode == Mode::MetricsQl && keyword == "with" && self.is("(") {
                    return Err(self.error(
                        Error::Unsupported,
                        "MetricsQL WITH parsing is not implemented yet",
                    ));
                }
                if matches!(keyword.as_str(), "inf" | "nan") {
                    return self.apply(start, "number", &keyword, "", &[]);
                }
                if self.mode == Mode::PromQl
                    && matches!(
                        keyword.as_str(),
                        "bool" | "on" | "ignoring" | "group_left" | "group_right" | "atan2"
                    )
                {
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
                if self.mode == Mode::MetricsQl
                    && aggregation::is_name(&keyword)
                    && keyword != "limit_ratio" // PromQL-only aggregate; an ordinary VM metric.
                    && matches!(self.current().value, Value::Word(_))
                    && !self.is("offset")
                {
                    // VM reads an aggregate name followed by an identifier as
                    // an aggregation, even when that identifier is `or`/`and`.
                    return Err(self.error(Error::Syntax, "expected an aggregation modifier"));
                }
                if self.is("(") {
                    let mut args =
                        self.arguments(depth, self.mode == Mode::PromQl && name == "info")?;
                    if self.mode == Mode::PromQl && name == "histogram_quantiles" && args.len() >= 2
                    {
                        let vector = args.remove(0);
                        args.push(vector);
                        return self.apply(start, "histogram_quantiles_auto", "", "", &args);
                    }
                    let function = if self.mode == Mode::MetricsQl {
                        &keyword
                    } else {
                        &name
                    };
                    return self.apply(start, "call", function, "", &args);
                }
                if !super::names::valid(
                    &name,
                    true,
                    self.mode == Mode::PromQl
                        && self.options.build.syntax_features & super::names::FEATURE != 0,
                ) {
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
        if self.mode == Mode::MetricsQl {
            let value = self.vm_number(start, text)?;
            return self.apply(start, "number", &value.to_string(), "", &[]);
        }
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
            let value = self.expression(-1, depth + 1)?;
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
                if self.mode == Mode::MetricsQl {
                    self.index += 1;
                    break;
                }
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

    fn modifiers(&mut self, operator: &str) -> Result<Vec<(String, Vec<Expr>)>> {
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
                if self.mode == Mode::MetricsQl && self.is("prefix") {
                    return Err(self.error(
                        Error::Unsupported,
                        "MetricsQL join prefixes are not implemented yet",
                    ));
                }
            }
        }
        if self.mode == Mode::MetricsQl
            && matches!(
                operator,
                "and" | "or" | "unless" | "default" | "if" | "ifnot"
            )
            && (self.is("fill") || self.is("fill_left") || self.is("fill_right"))
        {
            // VM reserves these after set operators even without `(`. A
            // parenthesized metric operand remains unambiguous and legal.
            return Err(self.error(Error::Syntax, "fill modifiers cannot follow set operators"));
        }
        while (self.is("fill") || self.is("fill_left") || self.is("fill_right"))
            && self
                .tokens
                .get(self.index + 1)
                .is_some_and(|t| t.text() == "(")
        {
            if self.mode == Mode::MetricsQl {
                return Err(self.error(
                    Error::Unsupported,
                    "MetricsQL fill modifiers are not yet supported by the shared AST",
                ));
            }
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
