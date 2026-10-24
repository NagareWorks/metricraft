"""Build Chinese reference data without translating names, signatures or examples."""
import copy
import api_contracts as en
from api_purposes_zh import PURPOSES
from api_parameters_zh import TEXT as PARAMETER_TEXT

TEXT = {english: PURPOSES[name] for name, english in en.PURPOSES.items() if name in PURPOSES}
CLIENT = {
    "__init__": "从显式配置或已注册实例创建客户端，使用上下文管理器释放传输资源。",
    "query": "向配置的 Prometheus 或 VictoriaMetrics 后端执行即时查询。",
    "query_range": "从 start 到 end 按请求的 step 重复求值。",
    "series": "通过后端元数据 API 列出匹配序列的标签集。",
    "labels": "列出标签名，可选使用选择器与时间范围限制。",
    "label_values": "列出某标签的已知值，可选使用选择器与时间范围限制。",
    "insert": "向 VictoriaMetrics 写入端点发送样本。PrometheusConfig 会抛出 NotImplementedError。",
    "health": "检查后端健康端点，返回是否可访问且健康。",
    "close": "只释放一次自有传输资源；需要异步清理时使用 aclose()。",
    "aclose": "等待异步清理并释放同步传输。",
    "closed": "客户端是否已关闭；关闭后拒绝后续请求。",
    "client": "访问当前同步 HTTP 传输。",
    "async_client": "访问当前异步 HTTP 传输。",
    "get_connection_info": "返回当前后端连接设置的浅拷贝。",
    "select_base_url": "返回查询基础 URL，适用时包含集群租户路径。",
    "insert_base_url": "返回 VictoriaMetrics 写入基础 URL，不支持 Prometheus。",
    "storage_base_url": "适用时返回配置的存储基础 URL。",
}
CONFIG = {
    "__init__": "创建后端连接设置。配置对象可变，不适用表达式的不可变保证。",
    "db_type": "返回此后端的 DBType 标识。",
    "http_options": "返回保存的 HttpClientOptions 对象。",
    "http_options_dict": "将 HTTP 选项导出为字典，用于配置传输。",
    "set_http_options": "替换当前配置对象的 HTTP 选项。",
    "update_http_options": "将 HTTP 选项合并到当前配置，保留未指定的设置。",
    "get_connection_info": "返回解析后的后端连接设置与 HTTP 选项。",
    "get_insert_url_base": "返回写入基础 URL。PrometheusConfig 没有 VictoriaMetrics 导入端点，因此抛出 NotImplementedError。",
    "get_query_url_base": "返回包含部署或租户前缀的查询基础 URL，客户端负责添加具体端点。",
    "validate": "检查必要的端点与设置，配置无效时抛出 ValueError。",
    "ensure": "将 None、映射或已有选项规范化为 HttpClientOptions。",
    "from_mapping": "从映射创建 HTTP 选项，规范化别名，并将未知传输键保留在 extras 中。",
    "merge": "返回应用覆盖后的新 HTTP 选项。请求头和 extras 按键合并，非 None 字段替换旧值。",
    "to_dict": "将已配置的 HTTP 设置和 extras 导出为字典。",
}
for name, translation in CLIENT.items():
    TEXT[en.CLIENT[name]] = translation
    TEXT[en.CLIENT[name] + " Await this asynchronous variant."] = translation + " 此异步版本需要 await。"
TEXT.update({en.CONFIG[name]: translation for name, translation in CONFIG.items()})
TEXT["Create frozen transport options. Header/extras dictionaries are copied; freezing does not recursively freeze their contents."] = "创建冻结的传输选项。请求头与 extras 字典会复制，冻结不会递归冻结字典内容。"
TEXT["Request methods can raise MCHTTPError, TimeoutError, ConnectionError or parameter-validation errors. Use with/async with for cleanup."] = "请求方法可能抛出 MCHTTPError、TimeoutError、ConnectionError 或参数校验错误。使用 with/async with 清理资源。"
TEXT["Configuration and transport validation are separate from query validation."] = "配置与传输验证独立于查询验证。"
TEXT["QueryBuilder — a new immutable expression sharing unchanged native subtrees. The receiver is unchanged; no data is queried."] = "QueryBuilder：共享未变化原生子树的新不可变表达式。接收表达式不变，不查询数据。"
for name, translation in {
    "build": "str：已验证的查询文本，可保存或用于客户端请求。",
    "validate": "str：成功时为空，否则为原生验证消息；无效 Python 参数仍可能抛出异常。",
    "analyze": "dict：图计数与启发建议，不是服务器执行计划。",
    "to_debug_json": "str：描述唯一原生节点及其关系的 JSON。",
    "debug": "str：与 to_debug_json() 相同的 JSON 图。",
    "debug_positions": "str：包含查询文本与 UTF-8 字节范围的 JSON，不是 Python 字符偏移。",
    "visualize_positions": "str：已核对的源码与范围 JSON，不创建图片或浏览器窗口。",
    "__init__": "QueryBuilder：无状态工厂；构建前先创建 from_* 表达式。",
}.items():
    TEXT[en.RETURNS[name]] = translation
for name, translation in {
    "by": "对未分组聚合只调用一次 by() 或 without()。需要两种形式时，从同一聚合分别派生。两种方言都允许不分组。",
    "without": "对未分组聚合只调用一次 by() 或 without()。两种方言都允许不分组。",
    "range": "不传参数时默认为 '5m'。对于已经计算的 PromQL 表达式，请使用 subquery()。",
    "subquery": "PromQL 要求显式的正窗口，MetricsQL 可以省略。时长表达式形式需要启用对应功能。",
    "rollup": "建议使用 rollup(window='5m', result='avg')，也接受兼容形式 rollup('avg', '5m')。window/duration 与 result/func 分别是互斥别名。",
    "function": "字符串是字面量。表达式请用 Q.from_metric('up')；function('rate', 'up[5m]') 不会把参数解析为查询。",
    "from_scalar": "原生标量使用 f64，超出 IEEE-754 精确整数范围的 Python 整数可能被舍入。",
    "histogram_quantile": "传统 Prometheus 桶在聚合时需要保留 le 标签。原生直方图支持与插值由后端决定。",
    "anchored": "需要 features=('promql-extended-range-selectors',) 及对应服务器支持。可用窗口函数包括 rate、increase、delta、changes、resets。",
    "smoothed": "需要 features=('promql-extended-range-selectors',) 及对应服务器支持。可用窗口函数包括 rate、increase、delta。",
    "fill": "需要 features=('promql-binop-fill-modifiers',) 及对应服务器支持。",
}.items():
    TEXT[en.NOTES[name]] = translation


def translate(text, mapping=TEXT):
    if not text:
        return text
    if text not in mapping:
        raise ValueError(f"Missing Chinese API translation: {text}")
    return mapping[text]


def localize(api):
    result = copy.deepcopy(api)
    for cls in result:
        for method in cls["methods"]:
            method["purpose"] = translate(method["purpose"])
            method["notes"] = translate(method["notes"])
            if cls["name"] == "QueryBuilder":
                method["returns"] = translate(method["returns"])
            else:
                method["returns"] = {"HTTP transport": "HTTP 传输", "Async HTTP transport": "异步 HTTP 传输"}.get(method["returns"], method["returns"])
            for parameter in method["parameters"]:
                parameter["description"] = translate(parameter["description"], PARAMETER_TEXT)
                parameter["type"] = parameter["type"].replace("keyword arguments", "关键字参数").replace("by keyword", "按关键字传入").replace("not accepted", "不接受")
    return result
