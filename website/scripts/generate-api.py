"""Extract public Python signatures without importing the SDK or native library."""
import ast
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "python/metricraft/src/metricraft"


def main():
    classes = {}
    for path in sorted(SOURCE.rglob("*.py")):
        if "_legacy" in path.parts:
            continue
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
                if item.name.startswith("_") and item.name != "__init__":
                    continue
                decorators = [ast.unparse(d) for d in item.decorator_list]
                if any(d.endswith((".setter", ".deleter")) for d in decorators):
                    continue
                args = copy.deepcopy(item.args)
                if args.args and args.args[0].arg in ("self", "cls"):
                    args.args.pop(0)
                signature = f"{item.name}({ast.unparse(args)})"
                if item.returns:
                    signature += " -> " + ast.unparse(item.returns)
                doc = ast.get_docstring(item) or ""
                result[item.name] = {
                    "name": item.name,
                    "signature": signature,
                    "doc": doc,
                    "group": path.stem.replace("_", " ").strip().title(),
                    "source": path.relative_to(ROOT).as_posix(),
                    "line": item.lineno,
                    "badges": [d for d in decorators if d in (
                        "vm_only", "prom_only", "prom_experimental", "classmethod", "property")]
                    + (["async"] if isinstance(item, ast.AsyncFunctionDef) else []),
                }
            elif isinstance(item, ast.Assign) and isinstance(item.value, ast.Name):
                for target in item.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith("_") and item.value.id in result:
                        entry = dict(result[item.value.id])
                        entry.update(name=target.id, signature=entry["signature"].replace(item.value.id, target.id, 1),
                                     doc=f"Alias of {item.value.id}().", line=item.lineno)
                        result[target.id] = entry
        return result

    output = []
    for name in ("QueryBuilder", "DatabaseClient", "PrometheusConfig", "VMSingleConfig", "VMClusterConfig", "HttpClientOptions"):
        node, path = classes[name]
        entries = methods(name)
        # The dataclass constructor is synthesized by Python, so document its declared fields.
        if name == "HttpClientOptions":
            fields = [n for n in node.body if isinstance(n, ast.AnnAssign)]
            signature = name + "(" + ", ".join(
                ast.unparse(n.target) + ": " + ast.unparse(n.annotation)
                + (" = " + ast.unparse(n.value) if n.value else "") for n in fields) + ")"
            entries["__init__"] = dict(name="__init__", signature=signature, doc="Constructor fields declared by the frozen dataclass.",
                                       group="Configuration", source=path.relative_to(ROOT).as_posix(), line=node.lineno, badges=[])
        output.append({"name": name, "methods": sorted(entries.values(), key=lambda m: (m["group"], m["name"]))})
    destination = ROOT / "website/.generated/api.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {sum(len(c['methods']) for c in output)} public API entries from Python source.")


if __name__ == "__main__":
    main()
