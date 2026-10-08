//! Lexically scoped MetricsQL WITH values and functions. All names are validated.
use super::render::Part;
use super::{Expr, Kind, Mode, Result, Type};

#[derive(Debug)]
pub(super) enum Template {
    Reference(String, Vec<Expr>, bool),
    Definition(Vec<String>, Expr),
    With(Vec<(String, Expr)>, Expr),
}

pub(super) enum Scope<'a> {
    Bindings(&'a [(String, Expr)]),
    Parameters(&'a [String]),
}

fn symbol(name: &str) -> bool {
    let mut chars = name.chars();
    chars.next().is_some_and(|c| c.is_alphabetic() || c == '_')
        && chars.all(|c| c.is_alphanumeric() || c == '_')
        && !matches!(
            name,
            "with" | "WITH" | "on" | "ignoring" | "bool" | "group_left" | "group_right"
        )
}

impl Template {
    pub fn children(&self) -> Vec<&Expr> {
        match self {
            Self::Reference(_, args, _) => args.iter().collect(),
            Self::Definition(_, body) => vec![body],
            Self::With(bindings, body) => bindings.iter().map(|(_, v)| v).chain([body]).collect(),
        }
    }
    pub fn detach(self, out: &mut Vec<Expr>) {
        match self {
            Self::Reference(_, args, _) => out.extend(args),
            Self::Definition(_, body) => out.push(body),
            Self::With(bindings, body) => {
                out.extend(bindings.into_iter().map(|(_, v)| v));
                out.push(body);
            }
        }
    }
    pub fn parts<'a>(&'a self, emit: &mut impl FnMut(Part<'a>)) {
        use Part::*;
        match self {
            Self::Reference(name, args, called) => {
                emit(Text(name));
                if *called {
                    emit(Text("("));
                    for (i, arg) in args.iter().enumerate() {
                        if i > 0 {
                            emit(Text(", "));
                        }
                        emit(Child(arg));
                    }
                    emit(Text(")"));
                }
            }
            Self::Definition(_, body) => emit(Child(body)),
            Self::With(bindings, body) => {
                emit(Text("WITH ("));
                for (i, (name, value)) in bindings.iter().enumerate() {
                    if i > 0 {
                        emit(Text(", "));
                    }
                    emit(Text(name));
                    emit(Bindings(&bindings[..i]));
                    if let Kind::Template(Self::Definition(params, definition)) = &value.0.kind {
                        emit(Text("("));
                        for (j, param) in params.iter().enumerate() {
                            if j > 0 {
                                emit(Text(", "));
                            }
                            emit(Text(param));
                        }
                        emit(Text(") = "));
                        emit(Parameters(params));
                        emit(Child(definition));
                        emit(EndScope);
                    } else {
                        emit(Text(" = "));
                        emit(Child(value));
                    }
                    emit(EndScope);
                }
                emit(Text(") ("));
                emit(Bindings(bindings));
                emit(Child(body));
                emit(EndScope);
                emit(Text(")"));
            }
        }
    }
    pub fn check(&self, ty: Type, scopes: &[Scope<'_>]) -> Result<()> {
        match self {
            Self::Definition(..) => {
                return Err("template definitions can only appear as WITH bindings".into())
            }
            Self::Reference(name, args, called) => {
                for scope in scopes.iter().rev() {
                    match scope {
                        Scope::Parameters(params) if params.contains(name) && !called => {
                            return Ok(())
                        }
                        Scope::Bindings(bindings) => {
                            if let Some((_, value)) =
                                bindings.iter().rev().find(|(key, _)| key == name)
                            {
                                let (arity, function) =
                                    if let Kind::Template(Self::Definition(p, _)) = &value.0.kind {
                                        (p.len(), true)
                                    } else {
                                        (0, false)
                                    };
                                if arity != args.len() || function != *called {
                                    return Err(format!("invalid template call {name:?}"));
                                }
                                if (ty == Type::String) != (value.0.ty == Type::String) {
                                    return Err(format!(
                                        "reference {name:?} has the wrong declared type"
                                    ));
                                }
                                return Ok(());
                            }
                        }
                        _ => {}
                    }
                }
                return Err(format!("unbound template reference {name:?}"));
            }
            _ => {}
        }
        Ok(())
    }
}

pub(super) fn apply(op: &str, name: &str, kind: &str, args: &[Expr]) -> Result<Expr> {
    let string = |value: &Expr| -> Result<String> {
        let Kind::String(s) = &value.0.kind else {
            return Err("template names must be literal strings".into());
        };
        if !symbol(s) {
            return Err("invalid template symbol".into());
        }
        Ok(s.clone())
    };
    let (template, ty) = match op {
        "reference" | "template_call" => {
            if !symbol(name) || op == "reference" && !args.is_empty() {
                return Err("invalid reference".into());
            }
            let ty = match kind {
                "scalar" => Type::Scalar,
                "string" => Type::String,
                "instant" => Type::Instant,
                "range" => Type::Range,
                _ => return Err("invalid reference type".into()),
            };
            (
                Template::Reference(name.into(), args.to_vec(), op == "template_call"),
                ty,
            )
        }
        "template" => {
            let Some(body) = args.last() else {
                return Err("template needs a body".into());
            };
            let params = args[..args.len() - 1]
                .iter()
                .map(string)
                .collect::<Result<Vec<_>>>()?;
            if params
                .iter()
                .enumerate()
                .any(|(i, p)| params[..i].contains(p))
            {
                return Err("duplicate template parameter".into());
            }
            (Template::Definition(params, body.clone()), body.0.ty)
        }
        "with" if !args.is_empty() && args.len() % 2 == 1 => {
            let mut bindings = Vec::new();
            for pair in args[1..].chunks_exact(2) {
                let key = string(&pair[0])?;
                if bindings.iter().any(|(name, _)| name == &key) {
                    return Err("duplicate WITH binding".into());
                }
                bindings.push((key, pair[1].clone()));
            }
            if bindings.is_empty() {
                return Err("WITH needs at least one binding".into());
            }
            (Template::With(bindings, args[0].clone()), args[0].0.ty)
        }
        _ => return Err("invalid template arguments".into()),
    };
    Ok(Expr::new(
        Kind::Template(template),
        ty,
        Some(Mode::MetricsQl),
    ))
}
