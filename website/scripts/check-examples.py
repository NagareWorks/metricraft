"""Execute offline API/category examples using the installed development SDK."""
import json
from pathlib import Path
import re
from metricraft import QueryBuilder as Q

ROOT = Path(__file__).resolve().parents[2]
api = json.loads((ROOT / "website/.generated/api.json").read_text(encoding="utf-8"))
count = 0
for cls in api:
    for method in cls["methods"]:
        if method["example"]:
            eval(method["example"], {"Q": Q})
            count += 1
for path in (ROOT / "docs/reference").glob("*.md"):
    if path.stem == "client":
        continue  # Explicit network example; covered by backend integration checks.
    for snippet in re.findall(r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S):
        exec(snippet, {})
        count += 1
print(f"Executed {count} offline API examples.")
