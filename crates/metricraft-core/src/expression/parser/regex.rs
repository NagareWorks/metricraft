//! Validate the supported RE2 subset without rewriting the stored matcher.
use super::ParseErrorKind::{self, Unsupported, Validation};
use regex_syntax::ast::{self, Ast};
type Result = std::result::Result<(), (ParseErrorKind, &'static str)>;

pub(super) fn validate(pattern: &str) -> Result {
    let mut chars = pattern.chars().peekable();
    let mut quoted = false;
    let mut in_class = false;
    // A leading ] (also after ^) is literal; POSIX [:...:] has its own closing ].
    // 0 = after [, 1 = after [^, 2 = after a class atom.
    let mut class_start = 0;
    let mut posix_class = false;
    while let Some(c) = chars.next() {
        if quoted {
            if c == '\\' && chars.peek() == Some(&'E') {
                chars.next();
                quoted = false;
            }
            continue;
        }
        if c != '\\' {
            match c {
                '[' if !in_class => {
                    in_class = true;
                    class_start = 0;
                }
                '[' if in_class && chars.peek() == Some(&':') => {
                    posix_class = true;
                    class_start = 2;
                }
                ':' if posix_class && chars.peek() == Some(&']') => {
                    chars.next();
                    posix_class = false;
                }
                '^' if in_class && class_start == 0 => class_start = 1,
                ']' if in_class && !posix_class && class_start == 2 => in_class = false,
                _ if in_class => class_start = 2,
                _ => {}
            }
            continue;
        }
        match chars.next() {
            Some('Q') if in_class => {
                return Err((
                    Validation,
                    "RE2 quoting is not allowed inside character classes",
                ))
            }
            Some('Q') => {
                let mut tail = chars.clone();
                if chars.peek().is_none() || (tail.next() == Some('\\') && tail.next() == Some('E'))
                {
                    return Err((Unsupported, "empty RE2 quoted blocks can change repetition binding and are not supported"));
                }
                quoted = true;
            }
            Some('1'..='7') if !chars.peek().is_some_and(|c| matches!(c, '0'..='7')) => {
                return Err((Validation, "RE2 does not support backreferences"))
            }
            _ => {}
        }
        if in_class {
            class_start = 2;
        }
    }
    let translated = super::super::selector::unquote_re2(pattern);
    let tree = ast::parse::Parser::new().parse(&translated).map_err(|_| {
        (
            Unsupported,
            "matcher regex is outside the supported RE2 subset",
        )
    })?;
    check(&tree, &translated, 1)?;
    regex::Regex::new(&translated).map_err(|_| {
        (
            Unsupported,
            "matcher regex exceeds supported syntax or compilation limits",
        )
    })?;
    Ok(())
}

fn check(tree: &Ast, source: &str, repetitions: u32) -> Result {
    match tree {
        Ast::Flags(value) => flags(&value.flags)?,
        Ast::Group(group) => {
            if let ast::GroupKind::CaptureName { name, .. } = &group.kind {
                if !name
                    .name
                    .bytes()
                    .all(|c| c.is_ascii_alphanumeric() || c == b'_')
                {
                    return Err((
                        Validation,
                        "RE2 capture names only accept ASCII letters, digits and underscores",
                    ));
                }
            }
            if let Some(value) = group.flags() {
                flags(value)?;
            }
            check(&group.ast, source, repetitions)?;
        }
        Ast::Repetition(rep) => {
            use ast::{RepetitionKind::Range, RepetitionRange::*};
            if matches!(rep.op.kind, Range(_)) {
                let text = &source[rep.op.span.start.offset..rep.op.span.end.offset];
                if text.split(['{', ',', '}', '?']).any(|part| {
                    part.len() > 1
                        && part.starts_with('0')
                        && part.bytes().all(|c| c.is_ascii_digit())
                }) {
                    return Err((Unsupported, "RE2 treats leading-zero repetition counts as literals; these patterns are not supported"));
                }
            }
            let count = match rep.op.kind {
                Range(Exactly(n) | AtLeast(n) | Bounded(_, n)) => n,
                _ => 1,
            };
            let count = repetitions.saturating_mul(count.max(1));
            if count > 1000 {
                return Err((Validation, "RE2 repeat count exceeds 1000"));
            }
            check(&rep.ast, source, count)?;
            if matches!(*rep.ast, Ast::Repetition(_)) {
                return Err((
                    Validation,
                    "RE2 does not allow consecutive repetition operators",
                ));
            }
        }
        Ast::Concat(value) => {
            for child in &value.asts {
                check(child, source, repetitions)?;
            }
        }
        Ast::Alternation(value) => {
            for child in &value.asts {
                check(child, source, repetitions)?;
            }
        }
        Ast::Literal(value) => literal(value)?,
        Ast::ClassUnicode(value) => unicode(value)?,
        Ast::ClassBracketed(value) => match &value.kind {
            ast::ClassSet::Item(item) => class(item)?,
            _ => {
                return Err((
                    Unsupported,
                    "ambiguous bracketed regex classes are not supported",
                ))
            }
        },
        Ast::Assertion(value) => {
            use ast::AssertionKind::*;
            if !matches!(
                value.kind,
                StartLine | EndLine | StartText | EndText | WordBoundary | NotWordBoundary
            ) {
                return Err((
                    Unsupported,
                    "regex word boundary extension is not supported",
                ));
            }
        }
        _ => {}
    }
    Ok(())
}

fn flags(value: &ast::Flags) -> Result {
    use ast::{Flag::*, FlagsItemKind::*};
    if value
        .items
        .iter()
        .any(|item| matches!(item.kind, Flag(Unicode | CRLF | IgnoreWhitespace)))
    {
        return Err((Validation, "RE2 only supports i, m, s and U flags"));
    }
    Ok(())
}

fn literal(value: &ast::Literal) -> Result {
    use ast::{HexLiteralKind::*, LiteralKind::*};
    if matches!(
        value.kind,
        HexFixed(UnicodeShort | UnicodeLong) | HexBrace(UnicodeShort | UnicodeLong)
    ) {
        return Err((Validation, "RE2 Unicode escapes use \\x{...}"));
    }
    Ok(())
}

fn unicode(value: &ast::ClassUnicode) -> Result {
    use ast::ClassUnicodeKind::*;
    let name = match &value.kind {
        OneLetter(c) => c.to_string(),
        Named(name) => name.clone(),
        _ => String::new(),
    };
    if ![
        "C", "Cc", "Cf", "Co", "Cs", "L", "LC", "Ll", "Lm", "Lo", "Lt", "Lu", "M", "Mc", "Me",
        "Mn", "N", "Nd", "Nl", "No", "P", "Pc", "Pd", "Pe", "Pf", "Pi", "Po", "Ps", "S", "Sc",
        "Sk", "Sm", "So", "Z", "Zl", "Zp", "Zs",
    ]
    .contains(&name.as_str())
    {
        return Err((
            Unsupported,
            "Unicode regex properties beyond general categories are not supported yet",
        ));
    }
    Ok(())
}

fn class(item: &ast::ClassSetItem) -> Result {
    use ast::ClassSetItem::*;
    match item {
        Literal(value) => literal(value)?,
        Range(value) => {
            literal(&value.start)?;
            literal(&value.end)?;
        }
        Unicode(value) => unicode(value)?,
        Union(value) => {
            for child in &value.items {
                class(child)?;
            }
        }
        Bracketed(_) => {
            return Err((
                Unsupported,
                "nested bracketed regex classes are not supported",
            ))
        }
        _ => {}
    }
    Ok(())
}
