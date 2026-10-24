# 结构化语言扩展

在应用虚拟环境中安装已发布的软件包：

```sh
python -m pip install metricraft
```

将[完整示例](../../../examples/03_language_extensions/main.py)保存为 `main.py`，运行 `python main.py`。如果已有仓库，在根目录运行 `python docs/examples/03_language_extensions/main.py`。匹配平台的 wheel 已包含原生库，无需构建 Rust 或启动服务器。支持的平台与 uv 用法见[安装指南](../../getting-started.md)。

示例展示共享过滤条件、MetricsQL 选择器分支、相对区间窗口、聚合限制、具有作用域的函数与字符串绑定，最后展示 Prometheus 时长表达式。

`reference()` 创建有类型的符号，它在对应 `.with_()` 作用域内才有效。所有绑定值都是表达式或经过转义的字面量。示例会输出查询字符串，应用可将其保存在自己的配置或数据库中。

版本基线与功能开关见[语言支持](../../language-support.md)。
