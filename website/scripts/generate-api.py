"""Extract real signatures; require editorial documentation for every parameter."""
import ast
import copy
import json
from pathlib import Path
from api_contracts import contract
from api_parameters import parameter

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "python/metricraft/src/metricraft"
CATEGORIES = {"Expression": "construction", "Query Builder": "construction", "Selectors": "selectors",
    "Aggregation": "aggregation", "Operators": "operators", "Temporal": "time", "Rollups": "rollups",
    "Extended Rollups": "metricsql-rollups", "Functions": "functions", "Labels": "labels",
    "Transforms": "transforms", "Templates": "templates", "Diagnostics": "diagnostics"}


def parameters(args):
    positional = args.posonlyargs + args.args
    defaults = [None] * (len(positional) - len(args.defaults)) + args.defaults
    result = [(p, d, "") for p, d in zip(positional, defaults)]
    if args.vararg:
        result.append((args.vararg, None, "*"))
    result.extend((p, d, "") for p, d in zip(args.kwonlyargs, args.kw_defaults))
    if args.kwarg:
        result.append((args.kwarg, None, "**"))
    return [dict(name=p.arg, display=prefix + p.arg, default=ast.unparse(d) if d else None)
            for p, d, prefix in result]


def main():
    classes = {}
    for path in sorted(SOURCE.rglob("*.py")):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.ClassDef):
                classes[node.name] = (node, path)

    def methods(name):
        node, path = classes[name]
        result = {}
        for base in reversed(node.bases):
            if isinstance(base, ast.Name) and base.id in classes:
                result.update(methods(base.id))
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decorators = [ast.unparse(d) for d in item.decorator_list]
                if any(d.endswith((".setter", ".deleter")) for d in decorators):
                    continue
                args = copy.deepcopy(item.args)
                if args.args and args.args[0].arg in ("self", "cls"):
                    args.args.pop(0)
                signature = f"{item.name}({ast.unparse(args)})"
                returns = ast.unparse(item.returns) if item.returns else ""
                if returns:
                    signature += " -> " + returns
                result[item.name] = dict(name=item.name, signature=signature, parameters=parameters(args),
                    return_type=returns, group=path.stem.replace("_", " ").strip().title(),
                    source=path.relative_to(ROOT).as_posix(), line=item.lineno,
                    badges=[d for d in decorators if d in ("vm_only", "prom_only", "prom_experimental", "classmethod", "property")]
                    + (["async"] if isinstance(item, ast.AsyncFunctionDef) else []))
            elif isinstance(item, ast.Assign) and isinstance(item.value, ast.Name):
                for target in item.targets:
                    if isinstance(target, ast.Name) and item.value.id in result:
                        entry = copy.deepcopy(result[item.value.id])
                        entry.update(name=target.id, signature=entry["signature"].replace(item.value.id, target.id, 1), alias=item.value.id, line=item.lineno)
                        result[target.id] = entry
        return result

    output = []
    for name in ("QueryBuilder", "DatabaseClient", "PrometheusConfig", "VMSingleConfig", "VMClusterConfig", "HttpClientOptions"):
        node, path = classes[name]
        entries = {k: v for k, v in methods(name).items() if not k.startswith("_") or k == "__init__"}
        if name == "HttpClientOptions":
            fields = [n for n in node.body if isinstance(n, ast.AnnAssign)]
            def default(n):
                return "{}" if isinstance(n.value, ast.Call) else ast.unparse(n.value) if n.value else None
            signature = name + "(" + ", ".join(ast.unparse(n.target) + ": " + ast.unparse(n.annotation)
                + (" = " + default(n) if default(n) is not None else "") for n in fields) + ")"
            entries["__init__"] = dict(name="__init__", signature=signature, return_type=name,
                parameters=[dict(name=n.target.id, display=n.target.id, default=default(n)) for n in fields],
                group="Configuration", source=path.relative_to(ROOT).as_posix(), line=node.lineno, badges=[])
        for entry in entries.values():
            key = entry["name"]
            editorial = dict(entry)
            if "alias" in entry and not entry["alias"].startswith("_"):
                editorial["name"] = entry["alias"]
            try:
                purpose, returns, notes, example = contract(name, editorial)
                entry.update(purpose=purpose, returns=returns, notes=notes, example=example)
                for p in entry["parameters"]:
                    p["type"], p["description"] = parameter(name, editorial["name"], p["name"])
            except KeyError as exc:
                raise SystemExit(f"Missing editorial contract: {name}.{key} / {exc}") from exc
            entry["category"] = CATEGORIES[entry["group"]] if name == "QueryBuilder" else "client" if name == "DatabaseClient" else "configuration"
            entry["id"] = f"api-{name.lower()}-{key}"
        output.append({"name": name, "methods": sorted(entries.values(), key=lambda m: m["name"])})
    destination = ROOT / "website/.generated/api.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Documented {sum(len(c['methods']) for c in output)} API entries; every parameter has an editorial contract.")


if __name__ == "__main__":
    main()
