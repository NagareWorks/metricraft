# 构建第一条查询

MetriCraft 是用于构建 PromQL、MetricsQL 并查询 Prometheus 或 VictoriaMetrics 的 Python SDK。Rust 管理不可变表达式树，Python 提供链式 API 和独立的 HTTP 客户端。

<a id="install-from-pypi"></a>

## 从 PyPI 安装

需要 Python 3.8 或更新版本。推荐使用 [uv](https://docs.astral.sh/uv/) 管理项目依赖和环境。在已有 uv 项目中执行以下命令；如果是新项目，先运行 `uv init`：

```sh
uv add metricraft
```

也可以使用 pip。先在应用目录中创建虚拟环境：

```sh
python -m venv .venv
```

Windows PowerShell 中运行 `.venv\Scripts\Activate.ps1` 激活环境；Linux/macOS 中运行 `source .venv/bin/activate`，然后安装：

```sh
python -m pip install metricraft
```

回归测试覆盖启用 GIL 的 CPython 3.8–3.15。Python 3.14 和 3.15 还会在所有提供预编译包的平台上执行独立的 wheel 安装验证。

匹配平台的 wheel 已包含 Rust 核心，使用时不需要安装 Rust、Cargo、编译器，也不需要克隆本仓库。使用 uv 时，将下文的 `python` 命令换成 `uv run python`。

<a id="precompiled-platforms"></a>

### 预编译平台

| 系统 | Python 架构 | 最低运行要求 |
| --- | --- | --- |
| Windows | x86_64（64 位） | 运行 64 位 Python 的 Windows |
| Linux | x86_64 | glibc 2.28 或更新版本 |
| macOS | x86_64（Intel） | macOS 11 或更新版本 |
| macOS | arm64（Apple Silicon） | macOS 11 或更新版本 |

wheel 必须与当前 Python 解释器的平台和架构匹配。目前没有 Linux ARM64、Alpine/musl 和 32 位 Windows 的预编译 wheel。源码安装需要 Rust 和平台 C 链接器，具体见[源码环境配置](contributing.md#set-up)。

如果只接受预编译 wheel、不希望触发源码构建：

```sh
python -m pip install --only-binary=:all: metricraft
```

如果 pip 提示找不到匹配的发行包，请检查 Python 版本、架构和软件包索引。镜像站可能尚未同步发布内容，必要时加上 `--index-url https://pypi.org/simple` 重试。

<a id="free-threaded-cpython"></a>

### 自由线程 CPython

CPython 3.14t 和 3.15t 会在关闭 GIL 时执行测试，包括 wheel 安装验证。它们使用相同的平台 wheel：打包的 Rust 库采用 C ABI，不链接 CPython 扩展 ABI。自由线程从 [Python 3.14](https://peps.python.org/pep-0779/) 起成为官方正式支持的可选构建。

自由线程解释器也可以启用 GIL，因此需要检查实际运行模式：

```sh
python -c "import sys, sysconfig; print(sysconfig.get_config_var('Py_GIL_DISABLED'), sys._is_gil_enabled())"
```

自由线程执行时应输出 `1 False`。不可变查询表达式可以在线程间共享。客户端应在使用前完成配置，等待未完成请求结束后再关闭；共享客户端时，自定义传输也需要支持线程安全。并发关闭客户端会确保每个自有传输只释放一次，但不会让用户回调或可变配置自动变得线程安全。

<a id="compose-a-query"></a>

## 组合查询

```python
from metricraft import QueryBuilder as Q

requests = Q.from_metric("http_requests_total").where_eq("job", "api")
rate = requests.rate("5m").sum().by("job")
text = rate.build("promql")

assert text == 'sum by (job) (rate(http_requests_total{job="api"}[5m]))'
assert requests.build("promql") == 'http_requests_total{job="api"}'
print(text)
```

将代码保存为 `first_query.py`，运行 `python first_query.py`。这个示例完全离线，输出 `sum by (job) (rate(http_requests_total{job="api"}[5m]))`。

第二个断言说明：派生出 `rate` 后，`requests` 仍然不变。任何表达式都可以作为新分支的起点反复使用。

在构建时选择 `"promql"` 或 `"metricsql"`。默认是 `"metricsql"`；显式指定方言，便于将保存的查询与目标后端对应起来。不受所选方言支持的形式会报错，嵌套表达式也会检查。

<a id="execute-with-the-client"></a>

## 通过客户端执行

下面的示例需要一个可访问的 Prometheus 服务。它与离线构建示例不同，返回结果取决于服务中的数据。

```python
from metricraft import DatabaseClient, PrometheusConfig

with DatabaseClient(PrometheusConfig("http://localhost:9090")) as client:
    result = client.query(text)
    print(result.is_success)
```

客户端也接受从应用存储中读取的查询字符串。只使用字符串查询时，不需要加载原生构建库。使用上下文管理器关闭传输资源；异步调用使用 `async with`。

<a id="check-which-package-is-loaded"></a>

## 检查实际加载的安装包

如果以前的开发安装仍在加载本地源码，可以先检查：

```sh
python -m pip show metricraft
python -c "import metricraft; print(metricraft.__file__)"
```

输出中的 `Editable project location` 表示当前安装指向源码。要在同一个环境中将它替换成已发布的 wheel：

```sh
python -m pip install --force-reinstall --only-binary=:all: --index-url https://pypi.org/simple metricraft
```

替换安装包后，重启已经运行的 Python 进程或 notebook 内核。发布的 wheel 会加载自身携带的原生库。如果开发时设置的 `METRICRAFT_NATIVE_LIB` 指向旧库或不存在的文件，请移除该覆盖设置。源码开发安装应放在单独的虚拟环境中。

<a id="where-to-go-next"></a>

## 接下来阅读

- [构建查询](building-queries.md)：过滤、分组和向量匹配。
- [查询后端](client-guide.md)：连接配置与异步调用。
- [从界面选项构建查询](examples/01_configurable_query/README.md)：离线应用示例。
- [语言支持](language-support.md)：版本基线与功能开关。
