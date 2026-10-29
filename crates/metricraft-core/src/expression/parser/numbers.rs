//! PromQL literal rules, deliberately separate from MetricsQL numeric suffixes.
use super::{ParseErrorKind as Error, Parser, Result, Value};

// Prometheus 3.15 treats e/E at scan boundaries as exponents even in hex.
// In particular, 0xE+2 is a sum, while 0x1E+2 is one invalid numeric token.
pub(super) fn hex_end(
    source: &str,
    start: usize,
) -> std::result::Result<usize, (usize, &'static str)> {
    let bytes = source.as_bytes();
    let mut pos = start + 2;
    let mut exponent = false;
    if bytes.get(pos) == Some(&b'_') {
        pos += 1;
    }
    if bytes.get(pos).is_some_and(u8::is_ascii_hexdigit) {
        pos += 1;
    }
    while let Some(&c) = bytes.get(pos) {
        match c {
            b'.' => return Err((pos + 1, "fractional hexadecimal literals are not allowed")),
            b'e' | b'E' | b'_' => {
                if c != b'_' {
                    if exponent {
                        return Err((pos + 1, "repeated exponent in hexadecimal literal"));
                    }
                    exponent = true;
                }
                pos += 1;
                if c != b'_' && bytes.get(pos).is_some_and(|c| matches!(c, b'+' | b'-')) {
                    pos += 1;
                }
                if bytes
                    .get(pos)
                    .is_none_or(|c| matches!(c, b'.' | b'_' | b'e' | b'E'))
                {
                    return Err((pos, "invalid hexadecimal numeric separator or exponent"));
                }
            }
            c if c.is_ascii_hexdigit() => {
                while bytes.get(pos).is_some_and(u8::is_ascii_hexdigit) {
                    pos += 1;
                }
            }
            c if c.is_ascii_alphanumeric() => return Err((pos + 1, "invalid hexadecimal digit")),
            _ => break,
        }
    }
    Ok(pos)
}

pub(super) fn number(text: &str) -> std::result::Result<f64, &'static str> {
    if text.eq_ignore_ascii_case("inf") {
        return Ok(f64::INFINITY);
    }
    if text.eq_ignore_ascii_case("nan") {
        return Ok(f64::NAN);
    }
    let hex = text.starts_with("0x") || text.starts_with("0X");
    for (i, byte) in text.bytes().enumerate() {
        if byte == b'_' {
            let digit = |b: u8| {
                if hex {
                    b.is_ascii_hexdigit()
                } else {
                    b.is_ascii_digit()
                }
            };
            if !(i == 2 && hex || i > 0 && digit(text.as_bytes()[i - 1]))
                || !text.as_bytes().get(i + 1).is_some_and(|b| digit(*b))
            {
                return Err("invalid numeric separator");
            }
        }
    }
    let clean = text.replace('_', "");
    if hex {
        return i64::from_str_radix(&clean[2..], 16)
            .map(|v| v as f64)
            .map_err(|_| "invalid hexadecimal integer");
    }
    // Prometheus tries signed base-0 integers first, then decimal floating point.
    if clean.starts_with('0') && clean.len() > 1 && clean.bytes().all(|b| b.is_ascii_digit()) {
        if let Ok(value) = i64::from_str_radix(&clean, 8) {
            return Ok(value as f64);
        }
    }
    if let Ok(value) = clean.parse::<f64>() {
        return if value.is_finite() {
            Ok(value)
        } else {
            Err("numeric literal overflow")
        };
    }
    if text.contains('_') {
        return Err("numeric separators are not allowed in durations");
    }
    duration(text)
}

fn duration(text: &str) -> std::result::Result<f64, &'static str> {
    let mut rest = text;
    let mut previous = 8;
    let mut milliseconds = 0u64;
    while !rest.is_empty() {
        let count = rest.bytes().take_while(|c| c.is_ascii_digit()).count();
        let amount = rest[..count]
            .parse::<u64>()
            .map_err(|_| "invalid duration literal")?;
        rest = &rest[count..];
        let (unit, rank, factor) = if rest.starts_with("ms") {
            ("ms", 1, 1)
        } else {
            match rest.as_bytes().first() {
                Some(b'y') => ("y", 7, 31_536_000_000),
                Some(b'w') => ("w", 6, 604_800_000),
                Some(b'd') => ("d", 5, 86_400_000),
                Some(b'h') => ("h", 4, 3_600_000),
                Some(b'm') => ("m", 3, 60_000),
                Some(b's') => ("s", 2, 1000),
                _ => return Err("invalid numeric or duration literal"),
            }
        };
        if rank >= previous {
            return Err("duration units must be unique and descending");
        }
        previous = rank;
        rest = &rest[unit.len()..];
        milliseconds = amount
            .checked_mul(factor)
            .and_then(|v| milliseconds.checked_add(v))
            .ok_or("duration overflow")?;
    }
    if previous == 8 || milliseconds > (i64::MAX as u64 / 1_000_000) {
        return Err("duration out of range");
    }
    Ok(milliseconds as f64 / 1000.0)
}

impl Parser<'_> {
    pub(super) fn signed_number(&mut self) -> Result<f64> {
        let negative = self.eat("-");
        if !negative {
            self.eat("+");
        }
        let text = self.current().text();
        if !matches!(self.current().value, Value::Number(_))
            && !text.eq_ignore_ascii_case("inf")
            && !text.eq_ignore_ascii_case("nan")
        {
            return Err(self.error(Error::Syntax, "expected a numeric or duration literal"));
        }
        let value = number(text).map_err(|message| self.error(Error::Syntax, message))?;
        self.index += 1;
        Ok(if negative { -value } else { value })
    }
}
