//! Pure Rust counterpart of compare_immutable.py; all times include validation.
use metricraft_core::expression::{Expr, Mode};
use std::{hint::black_box, time::Instant};

fn construct(labels: usize) -> Expr {
    let mut query = Expr::apply("metric", "http_requests_total", "", &[]).unwrap();
    for index in 0..labels {
        query = Expr::apply(
            "=",
            &format!("label_{index}"),
            &format!("value_{index}"),
            &[query],
        )
        .unwrap();
    }
    query = Expr::apply("range", "5m", "", &[query]).unwrap();
    query = Expr::apply("rate", "", "", &[query]).unwrap();
    query = Expr::apply("sum", "", "", &[query]).unwrap();
    let label = Expr::apply("string", "job", "", &[]).unwrap();
    Expr::apply("by", "", "", &[query, label]).unwrap()
}

fn measure(iterations: usize, rounds: usize, mut run: impl FnMut()) -> f64 {
    for _ in 0..20 {
        run();
    }
    let mut samples = Vec::new();
    for _ in 0..rounds {
        let started = Instant::now();
        for _ in 0..iterations {
            run();
        }
        samples.push(started.elapsed().as_secs_f64() * 1_000_000.0 / iterations as f64);
    }
    samples.sort_by(f64::total_cmp);
    samples[rounds / 2]
}

fn main() {
    let args: Vec<_> = std::env::args().collect();
    let iterations = args.get(1).map_or(1000, |v| v.parse().unwrap());
    let rounds = args.get(2).map_or(5, |v| v.parse().unwrap());
    assert!(iterations > 0 && rounds > 0);
    println!("{{");
    for (index, labels) in [1, 8, 32].into_iter().enumerate() {
        let existing = construct(labels);
        let construct_us = measure(iterations, rounds, || {
            black_box(construct(labels));
        });
        let render_us = measure(iterations, rounds, || {
            black_box(existing.build(Mode::MetricsQl).unwrap());
        });
        let total_us = measure(iterations, rounds, || {
            black_box(construct(labels).build(Mode::MetricsQl).unwrap());
        });
        if index > 0 {
            println!(",");
        }
        print!("\"{labels}_labels\":{{\"construct_and_release_us\":{construct_us},\"render_existing_us\":{render_us},\"construct_render_release_us\":{total_us}}}");
    }
    println!("\n}}");
}
