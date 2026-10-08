//! Structured syntax extensions; no field is interpreted as a raw query fragment.
use super::{Expr, Kind, Mode, Result, Type};

#[derive(Debug)]
pub(super) enum Extra {
    Selectors(Vec<Expr>, usize, usize), // branches, expanded alternatives, empty alternatives
    Matcher(Expr, String, &'static str, Expr, usize),
    Range(Expr, Expr),
    Subquery(Expr, Expr, Option<Expr>),
    At(Expr, Expr),
    Offset(Expr, Expr),
    Suffix(Expr, &'static str),
    Limit(Expr, usize),
}

impl Extra {
    pub fn name(&self) -> &'static str {
        match self {
            Self::Selectors(..) => "selector_alternatives",
            Self::Matcher(..) => "computed_matcher",
            Self::Range(..) => "range_expression",
            Self::Subquery(..) => "subquery_expression",
            Self::At(..) => "at_expression",
            Self::Offset(..) => "offset_expression",
            Self::Suffix(_, name) => name,
            Self::Limit(..) => "aggregate_limit",
        }
    }
    pub fn children(&self) -> Vec<&Expr> {
        match self {
            Self::Selectors(args, ..) => args.iter().collect(),
            Self::Matcher(source, _, _, value, _) => vec![source, value],
            Self::Range(a, b) | Self::At(a, b) | Self::Offset(a, b) => vec![a, b],
            Self::Subquery(a, b, c) => {
                let mut v = vec![a, b];
                v.extend(c.as_ref());
                v
            }
            Self::Suffix(a, _) | Self::Limit(a, _) => vec![a],
        }
    }
    pub fn detach(self, out: &mut Vec<Expr>) {
        match self {
            Self::Selectors(args, ..) => out.extend(args),
            Self::Matcher(source, _, _, value, _) => out.extend([source, value]),
            Self::Range(a, b) | Self::At(a, b) | Self::Offset(a, b) => out.extend([a, b]),
            Self::Subquery(a, b, c) => {
                out.extend([a, b]);
                out.extend(c);
            }
            Self::Suffix(a, _) | Self::Limit(a, _) => out.push(a),
        }
    }
    pub fn parts<'a>(&'a self, emit: &mut impl FnMut(super::render::Part<'a>)) {
        use super::render::Part::*;
        match self {
            Self::Selectors(..) => {
                emit(Text("{"));
                self.matcher_parts(emit);
                emit(Text("}"));
            }
            Self::Matcher(..) => {
                emit(Text("{"));
                self.matcher_parts(emit);
                emit(Text("}"));
            }
            Self::Range(a, b) => {
                emit(Child(a));
                emit(Text("["));
                emit(DurationChild(b));
                emit(Text("]"));
            }
            Self::Subquery(a, b, c) => {
                emit(Text("("));
                emit(Child(a));
                // Prometheus 3.15's duration lexer requires a numeric token
                // before the colon, even when the window is just range().
                emit(Text(")[(0 + "));
                emit(DurationChild(b));
                emit(Text("):"));
                if let Some(c) = c {
                    emit(DurationChild(c));
                }
                emit(Text("]"));
            }
            Self::At(a, b) | Self::Offset(a, b) => {
                emit(Child(a));
                emit(Text(if matches!(self, Self::At(..)) {
                    " @ ("
                } else {
                    " offset ("
                }));
                emit(if matches!(self, Self::Offset(..)) {
                    DurationChild(b)
                } else {
                    Child(b)
                });
                emit(Text(")"));
            }
            Self::Suffix(a, name) => {
                emit(Child(a));
                emit(Text(" "));
                emit(Text(name));
            }
            Self::Limit(a, n) => {
                emit(Child(a));
                emit(Text(" limit "));
                emit(Number(*n as f64));
            }
        }
    }
    pub fn feature(&self) -> u32 {
        match self {
            Self::Range(..) | Self::Subquery(..) | Self::Offset(..) => 2,
            Self::Suffix(..) => 4,
            _ => 0,
        }
    }

    pub fn matcher_parts<'a>(&'a self, emit: &mut impl FnMut(super::render::Part<'a>)) {
        use super::render::Part::*;
        match self {
            Self::Selectors(args, ..) => {
                for (i, arg) in args.iter().enumerate() {
                    if i > 0 {
                        emit(Text(" or "));
                    }
                    emit(SelectorInside(arg));
                }
            }
            Self::Matcher(source, ..) => {
                emit(SelectorFilter(self));
                emit(SelectorInside(source));
                emit(EndSelectorFilter);
            }
            _ => unreachable!(),
        }
    }

    pub fn filter_parts<'a>(&'a self, emit: &mut impl FnMut(super::render::Part<'a>)) {
        use super::render::Part::*;
        let Self::Matcher(_, label, op, value, _) = self else {
            unreachable!()
        };
        emit(if super::identifier(label, false) {
            Text(label)
        } else {
            Quoted(label)
        });
        emit(Text(op));
        emit(SelectorValue(value));
    }
}

// Counts are cached on selector extension roots so shared OR composition and
// adding a common filter never traverse or materialize expanded alternatives.
pub(super) fn selector_counts(expr: &Expr) -> Option<(usize, usize)> {
    match &expr.0.kind {
        Kind::Selector(s) => Some((1, usize::from(s.name.is_empty() && s.matchers.is_none()))),
        Kind::Extra(Extra::Selectors(_, count, empty)) => Some((*count, *empty)),
        Kind::Extra(Extra::Matcher(_, _, _, _, count)) => Some((*count, 0)),
        _ => None,
    }
}

pub(super) fn matcher(label: &str, op: &str, args: &[Expr]) -> Result<Expr> {
    if !super::valid_name(label)
        || args.len() != 2
        || args[1].0.ty != Type::String
        || selector_counts(&args[0]).is_none()
    {
        return Err("computed matcher requires a selector, label and string expression".into());
    }
    let op = match op {
        "=" => "=",
        "!=" => "!=",
        "=~" => "=~",
        "!~" => "!~",
        _ => return Err("invalid matcher operator".into()),
    };
    Ok(Expr::new(
        Kind::Extra(Extra::Matcher(
            args[0].clone(),
            label.into(),
            op,
            args[1].clone(),
            selector_counts(&args[0]).unwrap().0,
        )),
        Type::Instant,
        Some(Mode::MetricsQl),
    ))
}

pub(super) fn apply(op: &str, args: &[Expr]) -> Result<Expr> {
    let Some(source) = args.first() else {
        return Err(format!("{op} requires a source"));
    };
    if matches!(op, "at_expr" | "offset_expr")
        && source.has_time_modifier(if op == "at_expr" { "at" } else { "offset" })
    {
        return Err("time modifier is already set".into());
    }
    let scalar = |i: usize| -> Result<Expr> {
        let value = args
            .get(i)
            .ok_or_else(|| format!("{op} requires a duration/timestamp"))?;
        if value.0.ty != Type::Scalar {
            return Err("duration/timestamp must be scalar".into());
        }
        if let Kind::Number(n) = value.0.kind {
            if !n.is_finite() || matches!(op, "range_expr" | "subquery_expr") && n <= 0.0 {
                return Err(
                    "duration/timestamp must be finite; range windows and steps must be positive"
                        .into(),
                );
            }
        }
        Ok(value.clone())
    };
    let (kind, ty, mode) = match op {
        "selector_or" if args.len() >= 2 => {
            let (mut count, mut empty) = (0usize, 0usize);
            for arg in args {
                let (alternatives, empty_alternatives) =
                    selector_counts(arg).ok_or("selector alternatives require selectors")?;
                count = count.saturating_add(alternatives);
                empty = empty.saturating_add(empty_alternatives);
            }
            (
                Extra::Selectors(args.to_vec(), count, empty),
                Type::Instant,
                Mode::MetricsQl,
            )
        }
        "range_expr" if args.len() == 2 && matches!(source.0.kind, Kind::Selector(_)) => (
            Extra::Range(source.clone(), scalar(1)?),
            Type::Range,
            Mode::PromQl,
        ),
        "subquery_expr" if (2..=3).contains(&args.len()) && source.0.ty == Type::Instant => (
            Extra::Subquery(
                source.clone(),
                scalar(1)?,
                if args.len() == 3 {
                    Some(scalar(2)?)
                } else {
                    None
                },
            ),
            Type::Range,
            Mode::PromQl,
        ),
        "at_expr" if args.len() == 2 && matches!(source.0.ty, Type::Instant | Type::Range) => (
            Extra::At(source.clone(), scalar(1)?),
            source.0.ty,
            Mode::MetricsQl,
        ),
        "offset_expr" if args.len() == 2 && source.time_target() => (
            Extra::Offset(source.clone(), scalar(1)?),
            source.0.ty,
            Mode::PromQl,
        ),
        "anchored" | "smoothed"
            if args.len() == 1
                && (matches!(
                    source.0.kind,
                    Kind::Range(..) | Kind::Extra(Extra::Range(..))
                ) || op == "smoothed" && matches!(source.0.kind, Kind::Selector(_))) =>
        {
            (
                Extra::Suffix(
                    source.clone(),
                    if op == "anchored" {
                        "anchored"
                    } else {
                        "smoothed"
                    },
                ),
                source.0.ty,
                Mode::PromQl,
            )
        }
        "aggregate_limit" if args.len() == 2 && matches!(source.0.kind, Kind::Aggregate(..)) => {
            let Kind::Number(n) = scalar(1)?.0.kind else {
                return Err("limit must be an integer literal".into());
            };
            if !n.is_finite() || n < 0.0 || n.fract() != 0.0 || n > u32::MAX as f64 {
                return Err("limit must be an unsigned 32-bit integer".into());
            }
            (
                Extra::Limit(source.clone(), n as usize),
                Type::Instant,
                Mode::MetricsQl,
            )
        }
        _ => return Err(format!("invalid source or argument count for {op}")),
    };
    Ok(Expr::new(Kind::Extra(kind), ty, Some(mode)))
}
