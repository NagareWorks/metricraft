//! Label function signatures and label-name/pair validation.
use super::super::valid_name;
use super::{Expr, Kind, Result, Signature, Type};

pub(super) fn signature(name: &str) -> Option<Signature> {
    use Type::*;
    Some(match name {
        "alias" => (&[Instant, String], 2, 2, Instant, true),
        "label_replace" => (&[Instant, String], 5, 5, Instant, false),
        "label_join" => (&[Instant, String], 3, usize::MAX, Instant, false),
        "sort_by_label" | "sort_by_label_desc" => {
            (&[Instant, String], 1, usize::MAX, Instant, false)
        }
        "label_set" | "label_del" | "label_keep" => {
            (&[Instant, String], 1, usize::MAX, Instant, true)
        }
        "label_lowercase"
        | "label_uppercase"
        | "sort_by_label_numeric"
        | "sort_by_label_numeric_desc" => (&[Instant, String], 2, usize::MAX, Instant, true),
        "label_copy" | "label_move" => (&[Instant, String], 1, usize::MAX, Instant, true),
        "label_map" => (&[Instant, String], 2, usize::MAX, Instant, true),
        "label_match" | "label_mismatch" => (&[Instant, String], 3, 3, Instant, true),
        "label_transform" => (&[Instant, String], 4, 4, Instant, true),
        "label_value" => (&[Instant, String], 2, 2, Instant, true),
        "labels_equal" => (&[Instant, String], 3, usize::MAX, Instant, true),
        "label_graphite_group" => (&[Instant, Scalar], 2, usize::MAX, Instant, true),
        "drop_common_labels" => (&[Instant], 1, usize::MAX, Instant, true),
        _ => return None,
    })
}

// Called only after arity and expression types have been checked.
pub(super) fn validate(name: &str, args: &[Expr]) -> Result<()> {
    let label = |index: usize| -> Result<()> {
        if matches!(&args[index].0.kind, Kind::String(value) if !valid_name(value)) {
            return Err("invalid label name".into());
        }
        Ok(())
    };
    match name {
        "label_replace" => {
            label(1)?;
            label(3)?;
        }
        "label_join" => {
            label(1)?;
            for i in 3..args.len() {
                label(i)?;
            }
        }
        "label_copy" | "label_move" => {
            if args.len() % 2 != 1 {
                return Err(format!("{name} requires source/destination label pairs"));
            }
            for i in 1..args.len() {
                label(i)?;
            }
        }
        "label_map" => {
            if !args.len().is_multiple_of(2) {
                return Err("label_map requires source/destination value pairs".into());
            }
            label(1)?;
        }
        "label_match" | "label_mismatch" | "label_transform" | "label_value" => label(1)?,
        "count_values_over_time" => label(0)?,
        "histogram_quantile" if args.len() == 3 => label(2)?,
        "histogram_share" if args.len() == 3 => label(2)?,
        "label_del"
        | "label_keep"
        | "label_lowercase"
        | "label_uppercase"
        | "labels_equal"
        | "sort_by_label"
        | "sort_by_label_desc"
        | "sort_by_label_numeric"
        | "sort_by_label_numeric_desc" => {
            for i in 1..args.len() {
                label(i)?;
            }
        }
        "label_set" => {
            if args.len() % 2 != 1 {
                return Err("label_set requires label/value pairs".into());
            }
            for i in (1..args.len()).step_by(2) {
                label(i)?;
            }
        }
        _ => {}
    }
    Ok(())
}
