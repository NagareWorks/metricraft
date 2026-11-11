//! PromQL's opt-in unquoted names use Unicode category L, not Alphabetic.
use unicode_properties::{GeneralCategoryGroup, UnicodeGeneralCategory};

pub(super) const FEATURE: u32 = 16;

pub(super) fn start(c: char, extended: bool) -> bool {
    if c.is_ascii() {
        return c.is_ascii_alphabetic() || c == '_';
    }
    extended && c.general_category_group() == GeneralCategoryGroup::Letter
}

pub(super) fn continuation(c: char, extended: bool) -> bool {
    start(c, extended) || c.is_ascii_digit() || extended && c == '.'
}

pub(super) fn valid(value: &str, colon: bool, extended: bool) -> bool {
    let mut chars = value.chars();
    chars
        .next()
        .is_some_and(|c| start(c, extended) || colon && c == ':')
        && chars.all(|c| continuation(c, extended) || colon && c == ':')
}
