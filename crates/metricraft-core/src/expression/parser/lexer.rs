//! Bounded UTF-8 lexer. Tokens borrow source text; only decoded strings allocate.
use super::{ParseError, ParseErrorKind};

#[derive(Debug)]
pub(super) enum Value<'a> {
    Word(&'a str),
    Number(&'a str),
    String(String),
    Symbol(&'a str),
    End,
}

#[derive(Debug)]
pub(super) struct Token<'a> {
    pub value: Value<'a>,
    pub start: usize,
    pub end: usize,
}

impl Token<'_> {
    pub fn text(&self) -> &str {
        match &self.value {
            Value::Word(s) | Value::Number(s) | Value::Symbol(s) => s,
            _ => "",
        }
    }
}

pub(super) fn lex(source: &str, limit: usize) -> Result<Vec<Token<'_>>, ParseError> {
    let mut tokens = Vec::new();
    let mut pos = 0;
    let mut brackets = 0usize;
    while pos < source.len() {
        let c = source[pos..].chars().next().unwrap();
        if matches!(c, ' ' | '\t' | '\n' | '\r') {
            pos += 1;
            continue;
        }
        if c == '#' {
            pos += source[pos..]
                .find(['\n', '\r'])
                .unwrap_or(source.len() - pos);
            continue;
        }
        if tokens.len() >= limit {
            return Err(ParseError::kind(
                ParseErrorKind::Limit,
                pos,
                pos,
                "token limit exceeded",
            ));
        }
        let start = pos;
        let value = if matches!(c, '"' | '\'' | '`') {
            let (value, end) = string(source, pos, c)?;
            pos = end;
            Value::String(value)
        } else if c.is_ascii_digit()
            || c == '.'
                && source
                    .as_bytes()
                    .get(pos + 1)
                    .is_some_and(u8::is_ascii_digit)
        {
            if source[pos..].starts_with("0x") || source[pos..].starts_with("0X") {
                pos = super::numbers::hex_end(source, pos)
                    .map_err(|(end, message)| ParseError::new(start, end, message))?;
            } else {
                pos += 1;
                while pos < source.len() {
                    let b = source.as_bytes()[pos];
                    if b.is_ascii_alphanumeric()
                        || matches!(b, b'.' | b'_')
                        || matches!(b, b'+' | b'-')
                            && matches!(source.as_bytes()[pos - 1], b'e' | b'E')
                    {
                        pos += 1;
                    } else {
                        break;
                    }
                }
            }
            Value::Number(&source[start..pos])
        } else if c.is_alphabetic() || c == '_' || c == ':' && brackets == 0 {
            pos += c.len_utf8();
            while let Some(c) = source[pos..].chars().next() {
                if c.is_alphanumeric() || c == '_' || c == ':' && brackets == 0 {
                    pos += c.len_utf8();
                } else {
                    break;
                }
            }
            Value::Word(&source[start..pos])
        } else {
            let two = source.get(pos..pos + 2).unwrap_or("");
            if matches!(two, "==" | "!=" | "=~" | "!~" | ">=" | "<=" | "</" | ">/") {
                pos += 2;
            } else if "{}()[],:@+-*/%^=<>".contains(c) {
                if c == '[' {
                    brackets += 1;
                }
                if c == ']' {
                    brackets = brackets.saturating_sub(1);
                }
                pos += 1;
            } else {
                return Err(ParseError::new(
                    start,
                    start + c.len_utf8(),
                    "unexpected character",
                ));
            }
            Value::Symbol(&source[start..pos])
        };
        tokens.push(Token {
            value,
            start,
            end: pos,
        });
    }
    tokens.push(Token {
        value: Value::End,
        start: pos,
        end: pos,
    });
    Ok(tokens)
}

fn string(source: &str, start: usize, quote: char) -> Result<(String, usize), ParseError> {
    let mut bytes = Vec::new();
    let mut pos = start + 1;
    let error = |end, message| ParseError::new(start, end, message);
    while pos < source.len() {
        let c = source[pos..].chars().next().unwrap();
        pos += c.len_utf8();
        if c == '\u{fffd}' {
            return Err(error(
                pos,
                "literal replacement character is rejected by PromQL; use a Unicode escape",
            ));
        }
        if c == quote {
            return String::from_utf8(bytes)
                .map(|value| (value, pos))
                .map_err(|_| {
                    ParseError::kind(
                        ParseErrorKind::Unsupported,
                        start,
                        pos,
                        "non-UTF-8 string bytes cannot be represented by the AST",
                    )
                });
        }
        if c != '\\' || quote == '`' {
            if quote != '`' && c == '\n' {
                return Err(error(pos, "newline in quoted string"));
            }
            bytes.extend_from_slice(c.encode_utf8(&mut [0; 4]).as_bytes());
            continue;
        }
        let escape = source[pos..]
            .chars()
            .next()
            .ok_or_else(|| error(pos, "unterminated escape"))?;
        pos += escape.len_utf8();
        let decoded = match escape {
            'a' => Some(7),
            'b' => Some(8),
            'f' => Some(12),
            'n' => Some(10),
            'r' => Some(13),
            't' => Some(9),
            'v' => Some(11),
            '\\' => Some(b'\\'),
            q if q == quote => Some(q as u8),
            _ => None,
        };
        if let Some(byte) = decoded {
            bytes.push(byte);
            continue;
        }
        let (width, radix, begin) = match escape {
            'x' => (2, 16, pos),
            'u' => (4, 16, pos),
            'U' => (8, 16, pos),
            '0'..='7' => (3, 8, pos - 1),
            _ => return Err(error(pos, "invalid string escape")),
        };
        let end = begin + width;
        let digits = source
            .get(begin..end)
            .ok_or_else(|| error(pos, "incomplete string escape"))?;
        if !digits.bytes().all(|byte| {
            if radix == 16 {
                byte.is_ascii_hexdigit()
            } else {
                matches!(byte, b'0'..=b'7')
            }
        }) {
            return Err(error(end, "invalid string escape digits"));
        }
        let n =
            u32::from_str_radix(digits, radix).map_err(|_| error(end, "invalid string escape"))?;
        pos = end;
        if matches!(escape, 'u' | 'U') {
            let c = char::from_u32(n).ok_or_else(|| error(end, "invalid Unicode scalar"))?;
            bytes.extend_from_slice(c.encode_utf8(&mut [0; 4]).as_bytes());
        } else {
            bytes.push(u8::try_from(n).map_err(|_| error(end, "byte escape exceeds 255"))?);
        }
    }
    Err(error(pos, "unterminated string"))
}
