//! Persistent selectors. Adding a matcher shares the existing chain and name.
use super::{identifier, quote_len, valid_name, Result};
use std::sync::Arc;

#[derive(Clone, Debug)]
pub(super) struct Selector {
    pub name: Arc<str>,
    pub matchers: Option<Arc<Matcher>>,
}

#[derive(Debug)]
pub(super) struct Matcher {
    pub previous: Option<Arc<Matcher>>,
    pub label: Box<str>,
    pub op: &'static str,
    pub value: Box<str>,
    pub bytes: usize,
    pub count: usize,
    pub excludes_empty: bool,
}

impl Selector {
    pub fn new(name: &str) -> Self {
        Self {
            name: name.into(),
            matchers: None,
        }
    }

    pub fn with_matcher(&self, label: &str, op: &str, value: &str) -> Result<Self> {
        if !valid_name(label) {
            return Err("invalid label name".into());
        }
        let op = match op {
            "=" => "=",
            "!=" => "!=",
            "=~" => "=~",
            "!~" => "!~",
            _ => return Err("invalid matcher operator".into()),
        };
        let own_excludes_empty = if self.name.is_empty() {
            match op {
                "=" => !value.is_empty(),
                "!=" => value.is_empty(),
                "=~" | "!~" => {
                    let re = regex::Regex::new(&unquote_re2(value))
                        .map_err(|e| format!("invalid selector regex: {e}"))?;
                    re.is_match("") == (op == "!~")
                }
                _ => unreachable!(),
            }
        } else {
            true
        };
        let excludes_empty =
            own_excludes_empty || self.matchers.as_ref().is_some_and(|m| m.excludes_empty);
        let bytes = (if identifier(label, false) {
            label.len()
        } else {
            quote_len(label)
        })
        .saturating_add(op.len())
        .saturating_add(quote_len(value));
        let (bytes, count) = match &self.matchers {
            Some(previous) => (
                bytes.saturating_add(1).saturating_add(previous.bytes),
                previous.count.saturating_add(1),
            ),
            None => (bytes, 1),
        };
        Ok(Self {
            name: self.name.clone(),
            matchers: Some(Arc::new(Matcher {
                previous: self.matchers.clone(),
                label: label.into(),
                op,
                value: value.into(),
                bytes,
                count,
                excludes_empty,
            })),
        })
    }

    pub fn prom_valid(&self) -> bool {
        !self.name.is_empty() || self.matchers.as_ref().is_some_and(|m| m.excludes_empty)
    }

    pub fn body_bytes(&self) -> usize {
        let metric = if self.name.is_empty() {
            0
        } else {
            9usize.saturating_add(quote_len(&self.name))
        };
        metric
            .saturating_add(self.matchers.as_ref().map_or(0, |m| m.bytes))
            .saturating_add(usize::from(metric > 0 && self.matchers.is_some()))
    }

    pub fn output_bytes(&self) -> usize {
        let matcher_bytes = self.matchers.as_ref().map_or(0, |m| m.bytes);
        if !self.name.is_empty() && identifier(&self.name, true) {
            self.name.len().saturating_add(if self.matchers.is_some() {
                matcher_bytes.saturating_add(2)
            } else {
                0
            })
        } else {
            let metric = if self.name.is_empty() {
                0
            } else {
                9usize.saturating_add(quote_len(&self.name))
            };
            metric
                .saturating_add(matcher_bytes)
                .saturating_add(2)
                .saturating_add(usize::from(metric != 0 && self.matchers.is_some()))
        }
    }
}

// Go/RE2 supports \Q...\E, which Rust's regex parser does not. Translate only
// that quoting form for the empty-value check; preserve the user's actual RE2
// pattern in the emitted query. Escaped backslashes never open a quoted block.
fn unquote_re2(pattern: &str) -> String {
    let mut result = String::with_capacity(pattern.len());
    let mut chars = pattern.chars();
    while let Some(c) = chars.next() {
        if c != '\\' {
            result.push(c);
            continue;
        }
        match chars.next() {
            Some('Q') => {
                let mut literal = String::new();
                while let Some(c) = chars.next() {
                    if c == '\\' {
                        match chars.next() {
                            Some('E') => break,
                            Some(next) => {
                                literal.push(c);
                                literal.push(next);
                            }
                            None => literal.push(c),
                        }
                    } else {
                        literal.push(c);
                    }
                }
                result.push_str(&regex::escape(&literal));
            }
            Some(c) => {
                result.push('\\');
                result.push(c);
            }
            None => result.push('\\'),
        }
    }
    result
}

impl Drop for Matcher {
    fn drop(&mut self) {
        // Only dismantle nodes whose last owner is being released. Shared nodes
        // are never modified, and concurrent releases cannot lose a last owner.
        let mut next = self.previous.take();
        while let Some(arc) = next {
            match Arc::into_inner(arc) {
                Some(mut matcher) => next = matcher.previous.take(),
                None => break,
            }
        }
    }
}
