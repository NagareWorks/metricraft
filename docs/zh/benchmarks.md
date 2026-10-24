# 性能测量

<a id="unified-suite"></a>

## 统一套件

本地与 [Benchmarks Action](../../.github/workflows/benchmarks.yml) 使用相同入口：

```sh
python scripts/run_benchmarks.py --output /path/outside/checkout/new-run --memory-seconds 180
```

运行器构建 release 原生库并显式选择它，随后执行：

- 等价选择器、速率与聚合形状的纯 Rust 和 Python/ctypes 计时。
- 当前 SDK 在 1、8、32 个标签下的构建、渲染与共享选择器复用。
- 合成错误率、直方图分位数和 16 条查询的可配置仪表盘负载。
- 原生分配统计、Python 所有者保留，以及并发构建、报错和释放探针。

报告必须写入仓库外的新目录或空目录。`CARGO_TARGET_DIR` 可复用已有构建目录，否则构建放在报告旁。`--iterations`、`--rounds` 控制计时采样，`--memory-seconds`、`--workers` 控制并发压力；默认分别为 200 次、五轮、60 秒和四个工作线程。计时比较不包含内存跟踪。

Action 在相关 PR、开发或发布分支推送，以及手动触发时运行，环境为 Linux/Windows 与 Python 3.12。它发布 Job Summary 和保留 30 天的 `metricraft-benchmarks-<os>` 产物。报告包含环境、源码和二进制标识、阶段测量、内存采样与子进程日志。检查失败会使任务失败，并保留部分报告。生成测量结果不提交、不打包。计时回退需要审阅，共享运行器噪声不作为确定性性能门槛；所有权、输入不可变与分配释放断言失败则会直接使任务失败。

合成负载替代无法取得的原始应用轨迹，用于本地验收。它们不包含 HTTP I/O，不代表应用端到端延迟或后端结果等价性。

<a id="individual-timing-probes"></a>

## 单独计时探针

`python_timings.py` 测量当前 Rust 支撑的 Python 外观层，使用选择器、速率和聚合负载，分别测量构建加释放、重复渲染、构建加渲染加释放，以及从带 1、8、32 个标签的共享选择器派生分支。不包含 HTTP I/O。

```sh
cargo build --release --workspace --locked
# Set METRICRAFT_NATIVE_LIB to that release build's metricraft_ffi library.
python benchmarks/python_timings.py --iterations 300 --rounds 5 --output /path/to/timings.json
```

GC 保持开启。每项结果记录各轮每操作耗时的中位数、最小值、最大值，Python/平台信息，原生库哈希，修订号与源码哈希（包括新文件）。验证也保持开启。统一套件另外报告等价纯 Rust 形状，便于观察 Python 外观层和 FFI 开销。比较时应核对修订号、机器与负载配置。

这些是本地微基准，不是应用加速比或延迟保证。原始应用火焰图不可用，应把合成负载作为可复现代理，并在有条件时收集实际应用轨迹。优化批处理、arena 或缓存前，分别测量纯 Rust 和 Python/FFI，同时考虑宽树、深树、复用、并发、分配与释放。

严格函数式要求仍然适用：性能提升不能依赖修改共享查询、跳过验证或泄漏原生节点。

<a id="memory"></a>

## 内存

```sh
cargo run -p metricraft-core --release --example memory_profile --locked
python benchmarks/python_memory.py --branches 2000 --batches 10 --output /path/to/memory.json
python benchmarks/threaded_memory.py --seconds 180 --workers 4 --output /path/to/threaded-memory.json
```

原生探针在独立进程中，通过带统计功能的系统分配器计算请求的分配字节数，检查共享与独立构建、保留版本、重复构建和释放、深链与指数展开拒绝。每个场景结束后都断言活跃分配量回到基线，并作为 `cargo test --workspace` 的一部分自动运行。

Python 探针使用真实 release 库、弱引用、`tracemalloc` 与进程内存（Windows 私有/工作集字节或 Linux RSS）。采样覆盖选择器、label-copy、WITH 分支及每次调用的字符串所有者。原生探针检查共享大选择器的 10,000 个标签或模板分支，并释放深度 100,000 的 WITH 链。

这些探针由同一个统一基准 Action 运行。Python 采样包含测量记录与分配器缓存，不等于原生分配计数；对象释放后 RSS 不一定回到初始值。参见[内存行为与测量结果](memory.md)。
