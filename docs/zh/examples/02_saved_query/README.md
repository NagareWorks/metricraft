# 保存查询文本，稍后执行

示例应用构建查询字符串，通过 SQLite 写入并读出，再将字符串交给客户端。SQLite 代码属于应用，SDK 不提供持久化 API；YAML、XML 或其他数据库也可以承担相同职责。

在应用虚拟环境中安装已发布的软件包：

```sh
python -m pip install metricraft
```

将[完整示例](../../../examples/02_saved_query/main.py)保存为 `main.py`，运行 `python main.py`。匹配平台的 wheel 已包含原生库，不需要构建 Rust。如果已有仓库，也可以在根目录运行 `python docs/examples/02_saved_query/main.py`。支持的平台与 uv 用法见[安装指南](../../getting-started.md)。

默认使用内存数据库和注入的离线 HTTP 传输。要保留应用数据库，并查询真实的单机 VictoriaMetrics：

```sh
python main.py --database queries.sqlite --url http://localhost:8428
```

端点由应用提供，示例不包含部署或仪表盘。`DatabaseClient` 直接接受读出的字符串，不解析、转义或清理它。`build()` 返回文本时，安全构建的边界就已结束；后续编辑、存储完整性和访问控制由应用负责。

只需要客户端时，构造 `DatabaseClient(VMSingleConfig(url))` 并调用 `client.query(loaded_text)` 即可，不需要导入构建器或加载原生库。
