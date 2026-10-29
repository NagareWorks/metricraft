"""Native parser witnesses checked by the pinned promtool, outside unit tests."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
FLAGS = "--enable-feature=promql-experimental-functions,promql-duration-expr,promql-extended-range-selectors,promql-binop-fill-modifiers"
DEFERRED = {"extension_duration_expression", "extension_duration_subquery", "extension_duration_offset"}
POSITIVE = [
    'sum by(on)(up)', 'a + on(group_left) b', 'sum by("on")(up)',
    'sum by(bool,atan2,by,offset)(up)',
    r'up{job="\uFFFD"}', r'up{job="\xef\xbf\xbd"}', r'{"\uFFFD"}',
    r'"\uFFFD"', 'up # \ufffd\n', '0x12E+2', '0x_E+2', '0xEE1',
    'sum by(foo:bar)(up)', 'sum without(:zone)(up)', 'a + on(foo:bar) group_left(:zone) b',
    'sum by("NaN","Inf","without")(up)', 'a / on("Inf") group_left("without") b',
    'rate(up[5m] offset 1h smoothed)', 'rate(up[5m] @ 0 anchored)',
    'rate(up[5m] offset 1h @ 0 smoothed)', 'up offset 1h smoothed',
    'rate(up[5m] @ start() smoothed)', 'rate(up[5m] @ end() anchored)',
    'rate(up[5m] offset 1h @ start() smoothed)',
    'rate(up[5m] @ end() offset 1h anchored)',
    'up > bool on() 0', 'a + ignoring() 1', '1 + on() group_left(job) a',
    '1 > bool ignoring() 2', '1 + ignoring() group_right(job) a',
    r'up{job=~`[a]\Q[x]\E`}', r'up{job=~`[^]]\Qa\E`}',
    r'up{job=~`[[:alpha:]]\Qa\E`}',
    r'up{job=~`\Q\\E()`}', r'up{job=~`\Q\\\E[ab]`}',
    r'up{job=~`(?<job_1>a)`}', r'up{job=~`\p{LC}+`}',
    'sum(rate(up{job="api"}[5m])) by (job,)', 'a / on(job) group_left(zone) b',
    'up @ start() offset -1h', 'up[1h:] @ end()', 'up[0x10]', 'up[010]',
    'up @ 010', 'up @ 0x10', 'up @ 1h', 'up offset 0w', 'up offset +1h',
    'up # comment\r + other', 'up{job="a\rb"}', 'up{job=`a\rb`}',
    r'{"温度","job-name"="a\"b\n",zone!~`ap.*`}',
    r'up{job="\xC3\xA9\u4e2d\U0001F600\101"}',
    r'label_replace(up, "host", "$1", "instance", `([^:]+):.*`)',
    'with', ':', ':metric:name', 'vector(-Inf)', 'vector(NaN)',
    'a + fill(-1) b', 'a + fill(+1) b', 'a + fill(NaN) b', 'a + fill_left',
    '{"up","other"}', '{bool="x"}', '{NaN="x"}',
    'sum by () (up)', 'SUM(up)', 'a + on() group_left b',
    '08', '1_000', '0xE+2', '0x_A', '1_2.3_4', '0_7', '0_8', '0s0ms',
    r'up{job=~`\p{L}+`}', r'up{job=~`\Qapi.+\E`}', r'up{job=~`\141`}',
]
NEGATIVE = [
    'up{job="\ufffd"}', '"\ufffd"', 'up{job=`\ufffd`}',
    '0x_1e', '0x1_e', '0x1_EF', '0x1E+2', '0x1E-2', '0x1E', '0xEE',
    r'{job=~`a+\Q\E?`}',
    'up{foo:bar="x"}', '{job!~"a{00}"}',
    'info(up,({}))', 'info(up,({job="x"}))', 'sum by(without)(up)',
    r'up{job="\x+1"}', r'up{job="\u+123"}', r'up{job="\U+0000041"}',
    r'up{job=~`a++`}', r'up{job=~`a**`}', r'up{job=~`a?*`}', r'up{job=~`a{2}*`}',
    r'up{job=~`(?<é>.)`}', r'up{job=~`(?P<a.b>.)`}',
    r'up{job=~`[\Qa\E]`}', r'up{job=~`[]\Qa\E]`}',
    r'up{job=~`[^]\Qa\E]`}', r'up{job=~`[[:alpha:]\Qa\E]`}',
    r'up{job=~`\Q\\E(`}', r'up{job=~`\Q\\\E(?x)a`}', r'{job=~`\Q\\E*`}',
    'up > bool on(job) 0', 'up + on() fill(0) 1',
    '', 'up trailing', 'rate(up[5m]', 'up{job=api}', 'rate(up)', '{}',
    '{job=~".*"}', r'up{job=~"(?=a)"}', r'up{job="bad\q"}', 'up + bool other',
    '1 > 2', 'sum by(job)(up) without(zone)', 'unknown(up)', 'RATE(up[5m])',
    'up + on(job) on(zone) other', 'up * group_left(zone) other', 'abs(up,)',
    'up offset 1h offset 2h', 'up @ 1 @ 2', '(up)[5m]', '(up + x)[5m]',
    'up{"another"}', 'up{__name__="other"}', 'up{__name__=~"a.*"}',
    '0xFFFFFFFFFFFFFFFF', '1__000', '1e999', '0x', 'up @ 1e20', 'up[1000y]',
    '(up) offset 1h', '(up) @ 0', '(up) smoothed', 'up offset 1h[5m]',
    'a + fill((1)) b', 'a + fill_left(0) fill_left(1) b', 'sum by(NaN)(up)',
    r'up{job=~"(?x)ab"}', r'up{job=~"a{1001}"}', r'up{job=~`\1`}',
    r'up{job=~`\u0061`}', 'up[]', 'up[:]', r'up{job="\ud800"}', 'up\v+other',
]
UNSUPPORTED = [
    r'up{job=~`\Q\E`}', r'up{job=~`\Q`}', r'{job!~`a+\Q\E?`}',
    r'up{job=~`a*\Q\E*`}', r'up{job=~`a+\Q\E??`}',
    '{job=~"a{00}"}', 'up{job=~"a{01}"}', 'up{job=~"a{0,01}"}',
    'up{job=~"a{01,2}"}', 'up{job=~"a{00,}"}', 'up{job=~"a{00,01}"}',
    'up{job=~"a{01}*"}',
    'up[+1]', 'up offset NaN', r'up{job=~`\12`}',
    r'up{job=~`(?ii)a`}', r'up{job=~`(?P<x>a)(?P<x>b)`}',
    'up[(step())]', 'up[1+1]', 'up[5m:step()]', 'up offset (1h*2)',
    'up offset 0[5m]', 'up smoothed[5m]', 'sum by(job,job)(up)',
    r'up{job="\xff"}', r'up{job=~"[a&&b]"}', r'up{job=~`\p{Greek}`}',
]


def native(texts):
    """Hex framing also covers embedded newlines and non-ASCII string data."""
    target = Path(os.environ.get("CARGO_TARGET_DIR", ROOT / "target")).resolve()
    subprocess.run(["cargo", "build", "-p", "metricraft-core", "--example", "parse_queries", "--locked"], cwd=ROOT, check=True)
    binary = target / "debug/examples" / ("parse_queries.exe" if os.name == "nt" else "parse_queries")
    process = subprocess.run([str(binary)], input="".join(text.encode().hex() + "\n" for text in texts), text=True, capture_output=True)
    if process.returncode:
        raise AssertionError("native parser bridge failed:\n" + process.stderr)
    rows = [line.split("\t") for line in process.stdout.splitlines()]
    if len(rows) != len(texts):
        raise AssertionError("native parser response count differs")
    return [(row[0], row[1] if row[0] == "err" else None, bytes.fromhex(row[-1]).decode()) for row in rows]


def check_rules(texts, path, valid):
    path.write_text(json.dumps({"groups": [{"name": "parser", "rules": [
        {"record": "parser_" + str(i), "expr": text} for i, text in enumerate(texts)
    ]}]}, ensure_ascii=False), encoding="utf-8")
    process = subprocess.run(["promtool", FLAGS, "check", "rules", "--lint=none", str(path)], capture_output=True, text=True, encoding="utf-8")
    if (process.returncode == 0) != valid:
        context = repr(texts) if len(texts) < 5 else str(len(texts)) + " queries"
        raise AssertionError("promtool acceptance differs: " + context + "\n" + process.stdout + process.stderr)


def check(generated, directory):
    originals = [(name, text) for name, text, mode in generated if mode == "promql"]
    all_texts = [text for _, text in originals] + POSITIVE + NEGATIVE + UNSUPPORTED
    results = native(all_texts)
    accepted, deferred = [], set()
    for (name, text), (status, kind, value) in zip(originals, results):
        if name in DEFERRED:
            assert (status, kind) == ("err", "Unsupported"), (name, value)
            deferred.add(name)
        else:
            assert status == "ok", (name, text, kind, value)
            accepted.append(value)
    assert deferred == DEFERRED
    index = len(originals)
    for text, (status, _, value) in zip(POSITIVE, results[index:]):
        assert status == "ok", (text, value)
        accepted.extend([text, value])
    index += len(POSITIVE)
    for i, (text, (status, _, value)) in enumerate(zip(NEGATIVE, results[index:])):
        assert status == "err", (text, value)
        check_rules([text], directory / ("invalid-" + str(i) + ".json"), False)
    index += len(NEGATIVE)
    for text, (status, kind, value) in zip(UNSUPPORTED, results[index:]):
        assert (status, kind) == ("err", "Unsupported"), (text, value)
    check_rules(accepted + UNSUPPORTED, directory / "parsed-rules.json", True)
    check_results(directory)
    print("Native PromQL parsing: {} generated roundtrips, {} explicit duration gaps, {} extra valid, {} invalid, {} unsupported witnesses.".format(len(originals) - len(deferred), len(deferred), len(POSITIVE), len(NEGATIVE), len(UNSUPPORTED)))


def check_results(directory):
    samples = lambda labels, value: [{"labels": labels, "value": value}]
    cases = [
        ("vector(1 + 2 * 3)", samples("{}", 7)),
        ("vector(-2 ^ 2)", samples("{}", -4)),
        ("vector((-2) ^ 2)", samples("{}", 4)),
        ("vector(2 ^ 3 ^ 2)", samples("{}", 512)),
        ("vector(010 + 08 + 0xE + 1_000)", samples("{}", 1030)),
        ("vector(1 < bool 2)", samples("{}", 1)),
        ("vector(1 < bool on() 2)", samples("{}", 1)),
        ("sum(requests_total) + ignoring() group_left(job) 1", samples("{}", 1801)),
        ('sum by(job)(rate(requests_total{instance=~"a|b"}[5m])) > 2', samples('{job="api"}', 3)),
        ('sum without(instance)(rate(requests_total[5m]))', samples('{job="api"}', 3)),
        ('sum by(job)(rate(requests_total[5m])) / on(job) group_left(team) quota', samples('{job="api",team="core"}', 1)),
        ('requests_total{instance="a"} @ 120 offset 60s', samples('requests_total{job="api",instance="a"}', 60)),
        ('max_over_time((sum(rate(requests_total[2m])))[5m:1m])', samples("{}", 3)),
        ('sum by(job)(rate(requests_total[5m])) > 200', []),
    ]
    normalized = native([text for text, _ in cases])
    checks = []
    for (text, expected), (status, _, rendered) in zip(cases, normalized):
        assert status == "ok", (text, rendered)
        for query in (text, rendered):
            checks.append({"expr": query, "eval_time": "10m", "exp_samples": expected})
    path = directory / "parser-evaluation.json"
    path.write_text(json.dumps({"evaluation_interval": "1m", "tests": [{
        "interval": "1m", "input_series": [
            {"series": 'requests_total{job="api",instance="a"}', "values": "0+60x10"},
            {"series": 'requests_total{job="api",instance="b"}', "values": "0+120x10"},
            {"series": 'quota{job="api",team="core"}', "values": "3+0x10"},
        ], "promql_expr_test": checks,
    }]}), encoding="utf-8")
    subprocess.run(["promtool", FLAGS, "test", "rules", str(path)], check=True)
    print("Prometheus evaluated {} original/parsed query pairs against fixed samples.".format(len(cases)))


def check_extended_results(client, start, report, compare):
    # promtool 3.15.0's test-rules engine does not inherit extended-range flags.
    # Evaluate these pairs on the already running, explicitly enabled server.
    inputs = [
        ('smoothed', 'sum(rate(mc_requests_total{job="api"}[5m] offset 1m smoothed))'),
        ('anchored', 'sum(rate(mc_requests_total{job="api"}[5m] @ ' + str(start + 600) + ' anchored))'),
        ('smoothed_start', 'sum(rate(mc_requests_total{job="api"}[5m] @ start() smoothed))'),
        ('anchored_end', 'sum(rate(mc_requests_total{job="api"}[5m] @ end() offset 1m anchored))'),
    ]
    for (name, source), (status, _, text) in zip(inputs, native([text for _, text in inputs])):
        assert status == "ok", (source, text)
        row = {"mode": "promql", "name": "parser_" + name, "source": source, "query": text,
               "expected": [({}, 15)], "status": "failed"}
        report["cases"].append(row)
        for key, query in (("original", source), ("actual", text)):
            result = client.query(query, time=start + 600)
            row[key] = result.data
            compare(result, row["expected"], start + 600)
        row["status"] = "passed"
