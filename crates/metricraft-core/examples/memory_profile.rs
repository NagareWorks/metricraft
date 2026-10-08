//! Requested native allocation bytes, not RSS or allocator-reserved memory.
//! Run in a fresh process: cargo run -p metricraft-core --release --example memory_profile
use metricraft_core::{Expr, Mode};
use std::alloc::{GlobalAlloc, Layout, System};
use std::hint::black_box;
use std::sync::atomic::{AtomicUsize, Ordering::Relaxed};

struct CountingAllocator;
static LIVE: AtomicUsize = AtomicUsize::new(0);
static PEAK: AtomicUsize = AtomicUsize::new(0);

fn allocated(bytes: usize) {
    let live = LIVE.fetch_add(bytes, Relaxed) + bytes;
    PEAK.fetch_max(live, Relaxed);
}

unsafe impl GlobalAlloc for CountingAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let ptr = System.alloc(layout);
        if !ptr.is_null() {
            allocated(layout.size());
        }
        ptr
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        let ptr = System.alloc_zeroed(layout);
        if !ptr.is_null() {
            allocated(layout.size());
        }
        ptr
    }
    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        System.dealloc(ptr, layout);
        LIVE.fetch_sub(layout.size(), Relaxed);
    }
    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, size: usize) -> *mut u8 {
        let result = System.realloc(ptr, layout, size);
        if !result.is_null() {
            LIVE.fetch_sub(layout.size(), Relaxed);
            allocated(size);
        }
        result
    }
}

#[global_allocator]
static ALLOCATOR: CountingAllocator = CountingAllocator;

fn selector(labels: usize) -> Expr {
    let mut q = Expr::apply("metric", "requests_total", "", &[]).unwrap();
    let value = "x".repeat(128);
    for i in 0..labels {
        q = Expr::apply("=", &format!("label_{i}"), &value, &[q]).unwrap();
    }
    q
}

fn scenario(name: &str, run: impl FnOnce(usize) -> usize) -> usize {
    let baseline = LIVE.load(Relaxed);
    PEAK.store(baseline, Relaxed);
    let retained = run(baseline);
    let remaining = LIVE.load(Relaxed) as isize - baseline as isize;
    let peak = PEAK.load(Relaxed) - baseline;
    println!("{name}: retained_bytes={retained} peak_bytes={peak} after_drop_bytes={remaining}");
    assert_eq!(remaining, 0, "native allocations remained after {name}");
    retained
}

pub fn main() {
    // Initialize stdout before recording allocation baselines.
    println!("Native requested allocation bytes; all retained roots are released per case.");
    let shared = scenario("shared_filter_branches_512", |baseline| {
        let base = selector(256);
        let roots: Vec<_> = (0..512)
            .map(|i| {
                Expr::apply("=", "instance", &i.to_string(), std::slice::from_ref(&base)).unwrap()
            })
            .collect();
        black_box(&roots);
        LIVE.load(Relaxed) - baseline
    });
    let independent = scenario("independent_filter_branches_512", |baseline| {
        let roots: Vec<_> = (0..512)
            .map(|i| Expr::apply("=", "instance", &i.to_string(), &[selector(256)]).unwrap())
            .collect();
        black_box(&roots);
        LIVE.load(Relaxed) - baseline
    });
    let label_branches = scenario("shared_label_branches_10000", |baseline| {
        let base = selector(256);
        let source = Expr::apply("string", "label_0", "", &[]).unwrap();
        let destination = Expr::apply("string", "copied", "", &[]).unwrap();
        let roots: Vec<_> = (0..10_000)
            .map(|_| {
                Expr::apply(
                    "call",
                    "label_copy",
                    "",
                    &[base.clone(), source.clone(), destination.clone()],
                )
                .unwrap()
            })
            .collect();
        black_box(&roots);
        LIVE.load(Relaxed) - baseline
    });
    assert!(
        label_branches < 8 * 1024 * 1024,
        "label branches copied their source tree"
    );
    let templates = scenario("shared_template_branches_10000", |baseline| {
        let base = selector(256);
        let key = Expr::apply("string", "x", "", &[]).unwrap();
        let reference = Expr::apply("reference", "x", "instant", &[]).unwrap();
        let roots: Vec<_> = (0..10_000)
            .map(|_| {
                Expr::apply(
                    "with",
                    "",
                    "",
                    &[reference.clone(), key.clone(), base.clone()],
                )
                .unwrap()
            })
            .collect();
        black_box(&roots);
        black_box(roots[0].build(Mode::MetricsQl).unwrap());
        LIVE.load(Relaxed) - baseline
    });
    assert!(
        templates < 8 * 1024 * 1024,
        "templates copied their binding tree"
    );
    scenario("deep_template_chain_100000", |baseline| {
        let mut root = selector(0);
        let key = Expr::apply("string", "x", "", &[]).unwrap();
        let value = Expr::apply("number", "1", "", &[]).unwrap();
        for _ in 0..100_000 {
            root = Expr::apply("with", "", "", &[root, key.clone(), value.clone()]).unwrap();
        }
        assert!(root.build(Mode::MetricsQl).is_err());
        black_box(&root);
        LIVE.load(Relaxed) - baseline
    });
    assert!(
        shared < independent / 8,
        "branching appears to copy the shared selector"
    );
    let mut small = 0;
    for count in [1_000, 10_000] {
        let retained = scenario(&format!("shared_filter_branches_{count}"), |baseline| {
            let base = selector(256);
            let roots: Vec<_> = (0..count)
                .map(|i| {
                    Expr::apply("=", "instance", &i.to_string(), std::slice::from_ref(&base))
                        .unwrap()
                })
                .collect();
            black_box(&roots);
            LIVE.load(Relaxed) - baseline
        });
        if count == 1_000 {
            small = retained;
        } else {
            assert!(
                retained < small * 12,
                "branch allocation growth is superlinear"
            );
        }
    }
    scenario("retained_versions_1000", |baseline| {
        let mut roots = vec![selector(0)];
        for i in 0..1_000 {
            let next = Expr::apply(
                "=",
                "instance",
                &i.to_string(),
                std::slice::from_ref(roots.last().unwrap()),
            )
            .unwrap();
            roots.push(next);
        }
        black_box(&roots);
        LIVE.load(Relaxed) - baseline
    });
    scenario("create_build_drop_10000", |baseline| {
        let base = selector(32);
        for _ in 0..10_000 {
            let branch = Expr::apply("=", "job", "api", std::slice::from_ref(&base)).unwrap();
            black_box(branch.build(Mode::PromQl).unwrap());
        }
        LIVE.load(Relaxed) - baseline
    });

    scenario("deep_chain_100000", |baseline| {
        let mut root = selector(0);
        for _ in 0..100_000 {
            root = Expr::apply("abs", "", "", &[root]).unwrap();
        }
        let limits = metricraft_core::expression::BuildLimits {
            max_output_bytes: 1024 * 1024,
            max_expanded_nodes: 100_001,
        };
        black_box(root.build_with_limits(Mode::PromQl, limits).unwrap());
        LIVE.load(Relaxed) - baseline
    });
    scenario("shared_dag_2pow60_rejected", |baseline| {
        let mut root = selector(0);
        for _ in 0..60 {
            root = Expr::apply("+", "", "", &[root.clone(), root]).unwrap();
        }
        assert!(root
            .build(Mode::PromQl)
            .unwrap_err()
            .contains("max_output_bytes"));
        LIVE.load(Relaxed) - baseline
    });
    scenario("shared_dag_diagnostics_1000", |baseline| {
        let mut root = selector(32);
        for _ in 0..60 {
            root = Expr::apply("+", "", "", &[root.clone(), root]).unwrap();
        }
        for _ in 0..1_000 {
            black_box(root.inspect(false, 1024 * 1024, 10_000).unwrap());
            assert!(root.inspect(false, 10, 10_000).is_err());
        }
        LIVE.load(Relaxed) - baseline
    });
    scenario("shared_selector_or_2pow256_rejected", |baseline| {
        let base = selector(256);
        let mut root = base.clone();
        for _ in 0..256 {
            root = Expr::apply("selector_or", "", "", &[root.clone(), root]).unwrap();
        }
        let filtered = Expr::apply("=", "job", "api", &[root]).unwrap();
        assert!(filtered
            .build(Mode::MetricsQl)
            .unwrap_err()
            .contains("max_output_bytes"));
        let retained = LIVE.load(Relaxed) - baseline;
        assert!(
            retained < 1024 * 1024,
            "selector alternatives were expanded before build"
        );
        retained
    });
}
