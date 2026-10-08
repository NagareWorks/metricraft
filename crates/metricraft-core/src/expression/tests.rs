use super::*;

fn metric() -> Expr {
    Expr::apply("metric", "up", "", &[]).unwrap()
}

#[test]
fn transformations_share_children_without_mutation() {
    let base = metric();
    let filtered = Expr::apply("=", "job", "api", std::slice::from_ref(&base)).unwrap();
    let (Kind::Selector(original), Kind::Selector(derived)) = (&base.0.kind, &filtered.0.kind)
    else {
        panic!("expected selectors")
    };
    assert!(Arc::ptr_eq(&original.name, &derived.name));
    assert_eq!(base.build(Mode::PromQl).unwrap(), "up");
    drop(base);
    assert_eq!(filtered.build(Mode::PromQl).unwrap(), "up{job=\"api\"}");
    let branch = Expr::apply("=", "env", "prod", std::slice::from_ref(&filtered)).unwrap();
    let (Kind::Selector(original), Kind::Selector(derived)) = (&filtered.0.kind, &branch.0.kind)
    else {
        panic!("expected selectors")
    };
    assert!(Arc::ptr_eq(
        original.matchers.as_ref().unwrap(),
        derived
            .matchers
            .as_ref()
            .unwrap()
            .previous
            .as_ref()
            .unwrap()
    ));
}

#[test]
fn label_branches_share_sources_and_release_the_last_owner() {
    let base = metric();
    let weak = Arc::downgrade(&base.0);
    let src = Expr::apply("string", "job", "", &[]).unwrap();
    let dst = Expr::apply("string", "service", "", &[]).unwrap();
    let branches: Vec<_> = ["label_copy", "label_move"]
        .into_iter()
        .map(|name| {
            Expr::apply("call", name, "", &[base.clone(), src.clone(), dst.clone()]).unwrap()
        })
        .collect();
    for branch in &branches {
        let Kind::Call(_, args) = &branch.0.kind else {
            panic!("expected call")
        };
        assert!(Arc::ptr_eq(&base.0, &args[0].0));
        assert!(Arc::ptr_eq(&src.0, &args[1].0));
        assert!(Arc::ptr_eq(&dst.0, &args[2].0));
    }
    assert_eq!(base.build(Mode::PromQl).unwrap(), "up");
    drop(base);
    assert!(weak.upgrade().is_some());
    drop(branches);
    assert!(weak.upgrade().is_none());
}

#[test]
fn nested_capabilities_are_checked_at_build() {
    let vm = Expr::apply("default", "", "", &[metric(), metric()]).unwrap();
    let root = Expr::apply("sum", "", "", &[vm]).unwrap();
    assert!(root.build(Mode::PromQl).is_err());
    assert_eq!(
        root.build(Mode::MetricsQl).unwrap(),
        "sum ((up default up))"
    );
}

#[test]
fn releasing_a_selector_reclaims_its_root_without_invalidating_branches() {
    let base = metric();
    let filtered = Expr::apply("=", "job", "api", std::slice::from_ref(&base)).unwrap();
    let other = Expr::apply("=", "job", "worker", std::slice::from_ref(&base)).unwrap();
    let base_weak = Arc::downgrade(&base.0);
    let filtered_weak = Arc::downgrade(&filtered.0);
    drop(base);
    drop(filtered);
    assert!(filtered_weak.upgrade().is_none());
    // A selector branch shares matcher/name payloads, not the old root node.
    assert!(base_weak.upgrade().is_none());
    assert_eq!(other.build(Mode::PromQl).unwrap(), "up{job=\"worker\"}");
    drop(other);
    assert!(base_weak.upgrade().is_none());
}

#[test]
fn expression_owners_can_move_between_threads_without_a_registry() {
    let base = metric();
    let workers: Vec<_> = (0..8)
        .map(|i| {
            let base = base.clone();
            std::thread::spawn(move || {
                Expr::apply("=", "worker", &i.to_string(), &[base])
                    .unwrap()
                    .build(Mode::PromQl)
                    .unwrap()
            })
        })
        .collect();
    for (i, worker) in workers.into_iter().enumerate() {
        assert_eq!(worker.join().unwrap(), format!("up{{worker=\"{i}\"}}"));
    }
    assert_eq!(base.build(Mode::PromQl).unwrap(), "up");
}

#[test]
fn concurrent_last_owners_release_a_deep_shared_dag() {
    let base = metric();
    let weak_base = Arc::downgrade(&base.0);
    let mut root = base;
    for _ in 0..10_000 {
        root = Expr::apply("+", "", "", &[root.clone(), root]).unwrap();
    }
    let weak_root = Arc::downgrade(&root.0);
    let barrier = Arc::new(std::sync::Barrier::new(8));
    let roots = vec![root; 8];
    let workers: Vec<_> = roots
        .into_iter()
        .map(|root| {
            let barrier = barrier.clone();
            std::thread::spawn(move || {
                barrier.wait();
                drop(root);
            })
        })
        .collect();
    for worker in workers {
        worker.join().unwrap();
    }
    assert!(weak_root.upgrade().is_none());
    assert!(weak_base.upgrade().is_none());
}

#[test]
fn syntax_fields_cannot_be_raw_query_fragments() {
    assert!(Expr::apply("metric", "up\ndown", "", &[]).is_err());
    assert!(Expr::apply("range", "5m] or up", "", &[metric()]).is_err());
    assert!(Expr::apply("made_up_function", "", "", &[metric()]).is_err());
    let implicit = Expr::apply("rate", "", "", &[metric()]).unwrap();
    assert!(implicit.build(Mode::PromQl).is_err());
    assert_eq!(implicit.build(Mode::MetricsQl).unwrap(), "rate(up)");
    assert!(classic_duration("1h30m5s"));
    assert!(classic_duration("1ms"));
    assert!(!classic_duration("5m1h"));
    assert!(!classic_duration("0s"));
}
