//! Pure unary/binary operations and mutually exclusive matching modifiers.
use super::{comparison, labels, set_operator, Binary, Expr, Kind, Mode, Result, Type};
use std::sync::Arc;

pub(super) fn is_name(op: &str) -> bool {
    matches!(
        op,
        "parenthesize"
            | "between"
            | "negate"
            | "positive"
            | "+"
            | "-"
            | "*"
            | "/"
            | "%"
            | "^"
            | "atan2"
            | "default"
            | "if"
            | "ifnot"
            | "=="
            | "!="
            | ">"
            | "<"
            | ">="
            | "<="
            | "and"
            | "or"
            | "unless"
            | "</"
            | ">/"
            | "bool"
            | "on"
            | "ignoring"
            | "group_left"
            | "group_right"
            | "group_left_all"
            | "group_right_all"
            | "fill"
            | "fill_left"
            | "fill_right"
    )
}

pub(super) fn apply(op: &str, a: &str, args: &[Expr]) -> Result<Expr> {
    let arity = |n| {
        if args.len() == n {
            Ok(())
        } else {
            Err(format!("{op} expects {n} expressions"))
        }
    };
    match op {
        "parenthesize" => {
            arity(1)?;
            Ok(Expr::new(
                Kind::Parenthesized(args[0].clone()),
                args[0].0.ty,
                None,
            ))
        }
        "between" => {
            arity(3)?;
            let (Kind::Number(minimum), Kind::Number(maximum)) = (&args[1].0.kind, &args[2].0.kind)
            else {
                return Err("between requires literal numeric bounds".into());
            };
            if args[0].0.ty != Type::Instant
                || !minimum.is_finite()
                || !maximum.is_finite()
                || minimum > maximum
            {
                return Err("between requires an instant vector and minimum <= maximum".into());
            }
            let lower = Expr::apply(">=", "", "", &args[..2])?;
            Expr::apply("<=", "", "", &[lower, args[2].clone()])
        }
        "negate" | "positive" => {
            arity(1)?;
            if !matches!(args[0].0.ty, Type::Scalar | Type::Instant | Type::Range) {
                return Err("unary operands must be scalar or instant vector".into());
            }
            Ok(Expr::new(
                Kind::Unary(
                    if op == "negate" { "-" } else { "+" }.into(),
                    args[0].clone(),
                ),
                if args[0].0.ty == Type::Range {
                    Type::Instant
                } else {
                    args[0].0.ty
                },
                if args[0].0.ty == Type::Range {
                    Some(Mode::MetricsQl)
                } else {
                    None
                },
            ))
        }
        "+" if args.len() == 2 && args.iter().all(|a| a.0.ty == Type::String) => Ok(Expr::new(
            Kind::Binary(Binary {
                op: "+".into(),
                lhs: args[0].clone(),
                rhs: args[1].clone(),
                return_bool: false,
                matching: None,
                grouping: None,
                extra: None,
            }),
            Type::String,
            Some(Mode::MetricsQl),
        )),
        "+" | "-" | "*" | "/" | "%" | "^" | "atan2" | "default" | "if" | "ifnot" | "==" | "!="
        | ">" | "<" | ">=" | "<=" | "and" | "or" | "unless" | "</" | ">/" => {
            arity(2)?;
            let tuple_match = matches!(op, "==" | "!=")
                && matches!(&args[1].0.kind, Kind::Tuple(v) if v.iter().all(|x| x.0.ty==Type::Scalar));
            if args.iter().enumerate().any(|(i, e)| {
                !(matches!(e.0.ty, Type::Scalar | Type::Instant | Type::Range)
                    || i == 1 && tuple_match)
            }) {
                return Err("binary operands must be scalar or instant vector".into());
            }
            let vm_only = matches!(op, "default" | "if" | "ifnot")
                || tuple_match
                || args.iter().any(|e| e.0.ty == Type::Range)
                || set_operator(op) && args.iter().any(|e| e.0.ty != Type::Instant);
            let prom_only = matches!(op, "</" | ">/");
            if prom_only && (args[0].0.ty != Type::Instant || vm_only) {
                return Err("histogram trim requires a vector on the left".into());
            }
            let ty = if args.iter().all(|e| e.0.ty == Type::Scalar) {
                Type::Scalar
            } else {
                Type::Instant
            };
            Ok(Expr::new(
                Kind::Binary(Binary {
                    op: op.into(),
                    lhs: args[0].clone(),
                    rhs: args[1].clone(),
                    return_bool: false,
                    matching: None,
                    grouping: None,
                    extra: None,
                }),
                ty,
                if vm_only {
                    Some(Mode::MetricsQl)
                } else if prom_only {
                    Some(Mode::PromQl)
                } else {
                    None
                },
            ))
        }
        "bool" | "on" | "ignoring" | "group_left" | "group_right" | "group_left_all"
        | "group_right_all" | "fill" | "fill_left" | "fill_right" => {
            if args.is_empty() {
                return Err("binary modifier requires an expression".into());
            }
            let Kind::Binary(binary) = &args[0].0.kind else {
                return Err("modifier requires a binary expression".into());
            };
            let mut binary = binary.clone();
            let all = matches!(op, "group_left_all" | "group_right_all");
            let fill = matches!(op, "fill" | "fill_left" | "fill_right");
            let mut required = args[0].0.required_mode;
            if all || fill {
                let mode = if all { Mode::MetricsQl } else { Mode::PromQl };
                if required.is_some_and(|m| m != mode) {
                    return Err("conflicting dialect modifiers".into());
                }
                required = Some(mode);
            }
            if op == "bool" {
                arity(1)?;
                if !comparison(&binary.op) {
                    return Err("bool requires a comparison".into());
                }
                binary.return_bool = true;
            } else {
                if binary.lhs.0.ty != Type::Instant || binary.rhs.0.ty != Type::Instant {
                    if required == Some(Mode::PromQl)
                        || !matches!(binary.lhs.0.ty, Type::Scalar | Type::Instant | Type::Range)
                        || !matches!(binary.rhs.0.ty, Type::Scalar | Type::Instant | Type::Range)
                    {
                        return Err("vector matching requires two instant vectors".into());
                    }
                    required = Some(Mode::MetricsQl);
                }
                if fill {
                    arity(2)?;
                    if set_operator(&binary.op) {
                        return Err("fill is not supported on set operators".into());
                    }
                    let Kind::Number(n) = args[1].0.kind else {
                        return Err("fill value must be a numeric literal".into());
                    };
                    let mut extra = binary.extra.as_deref().cloned().unwrap_or_default();
                    if op != "fill_right" {
                        if extra.fill_left.is_some() {
                            return Err("left fill is already set".into());
                        }
                        extra.fill_left = Some(n);
                    }
                    if op != "fill_left" {
                        if extra.fill_right.is_some() {
                            return Err("right fill is already set".into());
                        }
                        extra.fill_right = Some(n);
                    }
                    binary.extra = Some(Arc::new(extra));
                    return Ok(Expr::new(Kind::Binary(binary), args[0].0.ty, required));
                }
                let labels = if all {
                    arity(1)?;
                    vec!["*".into()]
                } else {
                    labels(&args[1..])?
                };
                if matches!(op, "on" | "ignoring") {
                    if binary.matching.is_some() {
                        return Err("vector matching is already set".into());
                    }
                    binary.matching = Some(Arc::new((op.into(), labels)));
                } else {
                    if set_operator(&binary.op)
                        || matches!(binary.op.as_str(), "default" | "if" | "ifnot")
                    {
                        return Err("grouping requires arithmetic or comparison".into());
                    }
                    if binary.grouping.is_some() {
                        return Err("grouping is already set".into());
                    }
                    binary.grouping = Some(Arc::new((op.trim_end_matches("_all").into(), labels)));
                    if all {
                        let mut extra = binary.extra.as_deref().cloned().unwrap_or_default();
                        extra.copy_all = true;
                        if !a.is_empty() {
                            extra.prefix = Some(a.into());
                        }
                        binary.extra = Some(Arc::new(extra));
                    }
                }
                if let (Some((name, matching)), Some((_, grouping))) =
                    (binary.matching.as_deref(), binary.grouping.as_deref())
                {
                    if name == "on" && matching.iter().any(|x| grouping.contains(x)) {
                        return Err("on and group labels must not overlap".into());
                    }
                }
            }
            Ok(Expr::new(Kind::Binary(binary), args[0].0.ty, required))
        }
        _ => Err(format!("unknown operator {op}")),
    }
}
