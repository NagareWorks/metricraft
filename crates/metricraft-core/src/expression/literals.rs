//! Numeric and duration data parsing. Query text never enters this boundary.
use super::{Expr, Kind, Mode, Result, Type};

// Called during the existing iterative render walk, not a second tree traversal.
pub(super) fn validate_duration_node(expr: &Expr) -> Result<()> {
    let allowed = match &expr.0.kind {
        Kind::Number(n) => n.is_finite(),
        Kind::Parenthesized(_) | Kind::Unary(_, _) => true,
        Kind::Binary(b) => {
            matches!(b.op.as_str(), "+" | "-" | "*" | "/" | "%" | "^")
                && !(matches!(b.op.as_str(), "/" | "%")
                    && matches!(b.rhs.0.kind, Kind::Number(0.0)))
        }
        Kind::Call(name, _) => matches!(name.as_str(), "step" | "range" | "min_of" | "max_of"),
        _ => false,
    };
    if allowed {
        Ok(())
    } else {
        Err("duration expressions only accept finite numbers, arithmetic, step(), range(), min_of() and max_of()".into())
    }
}

pub(super) fn duration(text: &str, zero: bool) -> Result<(f64, f64)> {
    if let Ok(n) = text.parse::<f64>() {
        if n.is_finite() && (n > 0.0 || zero && n == 0.0) {
            return Ok((n, 0.0));
        }
        return Err("invalid duration".into());
    }
    let mut rest = text;
    let (mut seconds, mut steps) = (0.0, 0.0);
    while !rest.is_empty() {
        let count = rest
            .bytes()
            .take_while(|c| c.is_ascii_digit() || *c == b'.')
            .count();
        if count == 0 {
            return Err("invalid duration".into());
        }
        let number = rest[..count]
            .parse::<f64>()
            .map_err(|_| "invalid duration")?;
        rest = &rest[count..];
        let (unit, factor) = if rest.starts_with("ms") {
            ("ms", 0.001)
        } else {
            match rest.as_bytes().first() {
                Some(b's') => ("s", 1.0),
                Some(b'm') => ("m", 60.0),
                Some(b'h') => ("h", 3600.0),
                Some(b'd') => ("d", 86400.0),
                Some(b'w') => ("w", 604800.0),
                Some(b'y') => ("y", 31536000.0),
                Some(b'i') => ("i", 0.0),
                _ => return Err("invalid duration unit".into()),
            }
        };
        if unit == "i" {
            steps += number;
        } else {
            seconds += number * factor;
        }
        rest = &rest[unit.len()..];
    }
    if !seconds.is_finite() || !steps.is_finite() || (!zero && seconds + steps <= 0.0) {
        return Err("invalid positive duration".into());
    }
    Ok((seconds, steps))
}

pub(super) fn mode(text: &str, zero: bool) -> Result<Option<Mode>> {
    duration(text, zero)?;
    Ok(
        if super::classic_duration(text)
            || text.parse::<f64>().is_ok()
            || zero && matches!(text, "0s" | "0m" | "0h" | "0ms")
        {
            None
        } else {
            Some(Mode::MetricsQl)
        },
    )
}

pub(super) fn duration_expr(text: &str) -> Result<Expr> {
    let (seconds, steps) = duration(text, true)?;
    let number = |n| Expr::new(Kind::Number(n), Type::Scalar, None);
    if steps == 0.0 {
        return Ok(number(seconds));
    }
    let scaled = Expr::apply("*", "", "", &[Expr::call("step", &[])?, number(steps)])?;
    if seconds == 0.0 {
        Ok(scaled)
    } else {
        Expr::apply("+", "", "", &[scaled, number(seconds)])
    }
}

pub(super) fn numeric(text: &str) -> Result<Expr> {
    let clean = text.replace('_', "");
    for (suffix, factor) in [
        ("Ki", 1024.0),
        ("Mi", 1048576.0),
        ("Gi", 1073741824.0),
        ("Ti", 1099511627776.0),
        ("K", 1e3),
        ("M", 1e6),
        ("G", 1e9),
        ("T", 1e12),
    ] {
        if let Some(prefix) = clean.strip_suffix(suffix) {
            let n = prefix
                .parse::<f64>()
                .map_err(|_| "invalid numeric literal")?
                * factor;
            if !n.is_finite() {
                return Err("numeric literal overflow".into());
            }
            return Ok(Expr::new(Kind::Number(n), Type::Scalar, None));
        }
    }
    Expr::apply("number", &clean, "", &[])
}
