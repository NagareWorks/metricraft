# 参与贡献

MetriCraft 将 Rust 核心、C ABI、Python 绑定和 VictoriaMetrics 客户端维护在同一个仓库中。文档、示例说明和贡献指南同时提供英文与中文，代码和 API 名称保持一致。

<a id="set-up"></a>

## 配置环境

开发需要 Python 3.11+ 和 Rust 工具链。包元数据仍声明支持 Python 3.8+，明确调整声明之前，改动必须保持兼容。请使用独立虚拟环境，避免可编辑开发安装替换其他应用使用的已发布软件包。在仓库根目录执行：

```sh
python -m venv .venv
```

Windows PowerShell 使用 `.venv\Scripts\Activate.ps1` 激活，Linux/macOS 使用 `source .venv/bin/activate`，然后执行：

```sh
python -m pip install -e ".[dev]"
python scripts/dev.py build
```

构建产物需要放在仓库外时，先设置 `CARGO_TARGET_DIR`。`METRICRAFT_NATIVE_LIB` 可指向显式共享库。仅导入客户端必须在没有任何原生库时也能工作。

<a id="architecture-rules"></a>

## 架构规则

- 通过一个构建器和一棵不可变 Rust AST 支持 PromQL 与 MetricsQL。
- 保持转换纯粹，共享不可变子表达式；绝不修改调用方仍可保留或复用的表达式。
- 查询语义、验证和渲染放在 `metricraft-core`。C ABI 关注转换、错误和所有权，Python 提供链式外观。
- MetricsQL 专有方法标记 `@vm_only`，PromQL 专有方法标记 `@prom_only`，并在 Rust 节点中编码对应限制。按所选构建模式检查嵌套节点。共享操作存在方言专有形式时，只限制对应形式。
- 将字符串视为数据，不作为语法；不添加隐式原始表达式回退。
- 客户端 I/O 与构建保持独立。存储、界面、授权和应用读入查询文本的验证不属于 SDK。

已支持操作与职责边界见[架构](architecture.md)。查询语言范围保持为 PromQL 与 MetricsQL。

<a id="validate-changes"></a>

## 验证改动

```sh
cargo fmt --all -- --check
python scripts/dev.py rust
python scripts/dev.py query
python scripts/dev.py client
python scripts/dev.py smoke
python scripts/dev.py tests
python scripts/dev.py conformance
```

`query` 运行不可变表达式、字面量、方言、修饰符及仅客户端导入的工作区约定测试。`client` 运行模拟 HTTP 测试，`tests` 运行当前完整 Python SDK 测试集。API 约定使用 Rust 构建器可执行样例，并覆盖直接构造客户端和命名配置。`check` 组合 Rust、完整 Python 套件和离线示例，测试命令默认不生成覆盖率或字节码文件。

`conformance` 还需要 PATH 中存在 Go 1.24.2+ 与 `promtool`。CI 固定 Go 1.25.3、Prometheus 3.15.0 和 MetricsQL v0.87.4；MetricsQL 模块只用于测试。这是上游解析器语法检查，不验证查询执行或完整语言覆盖。Go 缓存与临时规则文件默认位于 `CARGO_TARGET_DIR` 的父目录，可用 `GOCACHE`/`GOMODCACHE` 覆盖。

CI 还会通过 SDK 客户端，对隔离的 Prometheus 3.15.0 与 VictoriaMetrics 1.153.0 运行合成测试集，检查值、标签、时间戳，包括保存后读出的文本、同步/异步调用和范围求值。本地复现见[后端结果验证](backend-validation.md)。失败会阻止 conformance 和发布检查；生成报告保存在 Actions 产物，不进入库或单元测试集。

独立[兼容性工作流](../../.github/workflows/compatibility.yml) 发现官方 PromQL/MetricsQL 能力，发布 Job Summary 和 `metricraft-upstream-compatibility` 产物，其中包含 `matrix.md`、`matrix.json`、已验证上游源码快照和运行日志。报告、清单和比较快照都是生成输出，不提交。该工作流独立于单元测试和固定版本发布解析器测试集。

本地先构建原生 SDK，再运行 `python scripts/compatibility/check.py --output /path/outside/checkout/compatibility`。需要 curl、Go 和 promtool 3.15.0。`--offline` 复用输出目录中已验证的源码快照。检测漂移时，下载先前产物并传入 `--compare /download/matrix.json --check`；仓库不维护基线快照。签名缺失、主题未覆盖和解析器拒绝会失败；后端语义、规范化格式和未发布新增功能明确分类。`sampled` 只表示所列样例通过解析，不代表完整语言或语义支持。网络或提取失败不会静默使用过期数据。

行为变更应增加有针对性的回归测试。性能改动应将构建、渲染与 HTTP I/O 分开测量，记录修订号、构建模式和负载，不能仅因使用 Rust 就推断加速。

原生 wheel 发布要求包含原生库并通过安装包测试。在仓库根目录运行 `python -m build` 构建发行包。Python 元数据与 Rust 工作区并列，使源码归档可独立构建。C ABI 独立于 CPython，因此 wheel 使用带平台标签的 `py3-none`。`pyproject.toml` 中包版本显式维护，发布 tag 必须完全匹配。

构建后运行 `python scripts/check_python_package.py <dist>`，验证已安装 SDK 的无源码导入、无原生代码使用路径。加上 `--require-bundled-native` 验证包内 Rust 构建器；加上 `--typing` 用 mypy 检查安装包消费者约定（该检查需要 Python 3.11+）。检查在仓库之外运行，覆盖链式返回类型、装饰方法、运算符、客户端与错误参数。

wheel 和 sdist 必须包含 `py.typed` 与内联注解。类型 CI 使用 mypy 和 Pyright 检查构建后的 Linux wheel。所有原生 wheel 任务都对已安装的软件包运行三个可下载示例，不回退到源码或外部原生路径。

构建 wheel 后，也可单独检查类型：

```sh
python scripts/check_python_typing.py /path/to/metricraft.whl
```

安装 `pyright` 与 Node.js 后加 `--pyright`，与 CI 一致。公共构建器注解应完整，包含别名与特殊方法。Python 类型描述参数形式和返回值，表达式种类、方言限制、功能开关和值范围仍由 Rust 校验。

<a id="documentation-website"></a>

## 文档网站

英文 Markdown 位于 `docs/`，中文位于 `docs/zh/`，均由 `website/` 中的自定义 Astro 网站直接读取。使用 Node.js 24+、Python 3.11+，在 `website/` 运行 `npm ci`、`npm run check`、`npm run build`。构建从源码生成双语 API 参考，建立按语言区分的本地搜索索引，并检查链接、章节锚点与资源。CI 将这些检查纳入 `required-checks`。

中英文页面使用相同章节锚点，切换语言时保留当前位置。新增页面与 API 说明时，应同步维护两种语言。预览与维护方法见[网站指南](../../website/README.md)。

<a id="github-actions"></a>

## GitHub Actions

具有写权限的维护者，以及已有提交或 PR 合入的贡献者，其 CI 自动运行。fork 工作流策略应设为 **Require approval for first-time contributors**。没有先前合入贡献的用户，其工作流需由有写权限的维护者审阅并批准；仅再开一个 PR 不会取消该要求。

`release` 环境单独保护包发布。管理员应将审批人限制为当前有写权限的维护者；添加协作者不会自动添加发布审批人。

`Benchmarks` 在 Linux/Windows 的相关 PR、分支推送与手动运行中使用 `python scripts/run_benchmarks.py --output <external-directory>`。先测纯 Rust 和当前 Python/ctypes 外观，再运行合成应用负载和内存/生命周期探针。计时供审阅，正确性或释放检查失败会使任务失败。复现及产物细节见[基准指南](benchmarks.md)。

`Native robustness` 在 Linux 使用 AddressSanitizer/泄漏检测运行 Rust 测试，随后运行有时限的 libFuzzer。它独立于计时，在相关 PR 或手动触发时运行；确定性组合种子也进入普通 Rust 回归测试。共享验证器检查输入不可变性、缓存大小、构建限制和释放路径，不证明后端语义。日志、语料和崩溃输入作为 Actions 产物上传。复现命令见[工作流](../../.github/workflows/robustness.yml)；生成语料和构建输出应放在仓库外。配置好工作流并不等于已执行验证。

`CI` 在开发/发布分支推送、PR 与手动触发时运行，检查工作流语法、Rust 格式，测试 Python 3.8–3.13，并运行固定 PromQL/MetricsQL 解析器测试集。分支保护的必需状态应设为 `required-checks`，所需任务失败、取消或跳过都会阻止成功。

可复用 `Packages` 工作流测试 Rust 核心和 ABI，为 Linux x86_64、Windows x86_64、macOS Intel、macOS Apple Silicon 构建 wheel。Linux 在 manylinux_2_28 中构建并执行 `auditwheel repair`。每个 wheel 包含一个原生库及其源码 SHA；验证平台元数据、RECORD 哈希、仅客户端使用和不回退源码的原生查询构建。所有 wheel 都含原生库并带平台标签。

产物名为 `metricraft-dist-<platform>` 与 `metricraft-dist-sdist`，保留 14 天。sdist 包含 Python SDK、Rust 源码和 Cargo 锁文件。CI 在仓库之外用新的原生构建目录重新构建、安装它。源码安装需要 Rust 和平台 C 链接器，工具链缺失会使安装失败，而不是安装无法使用的构建器。

`Release` 针对选定提交复用完整 CI，然后直接发布已测试产物，不重新构建。推送 `v*` tag 后，通过版本与源码检查才会发布。手动触发默认只构建；发布时需选择已有版本 tag 并设置 `publish`。PyPI Trusted Publishing 配置使用 `NagareWorks/metricraft`、`release.yml`、`release` 环境；发布使用 GitHub OIDC，不用长期 PyPI token。常规 CI 只读且不需要发布凭据。

发布后四个平台都会从公共 PyPI 下载 wheel，比较其 SHA-256 与已测试产物，并再次运行隔离安装检查。上传成功本身不代表发布完成。

<a id="submit-a-change"></a>

## 提交改动

创建范围明确的分支与 PR。合入 `main` 要求审查讨论已解决、`required-checks` 成功。有写权限的维护者可以合入自己的 PR，不要求独立批准审查。优先 squash，也可 rebase；`main` 禁止 merge commit、强推和删除分支。

描述问题、修改后行为、兼容性影响和已运行检查。避免无关格式改动。API 变化时同步更新示例，README 保持简洁。提交主题应具体，例如 `fix(query): preserve shared selectors`。

除非明确另有说明，提交给项目的贡献与项目一样按 [Apache 2.0](../../LICENSE) 授权，不要求额外 CLA。贡献者通过 GitHub 历史署名。示例与测试数据中不要包含凭据、私有部署地址或公司专属配置。
