"""Native MetricsQL parser witnesses against pinned upstream syntax and values."""
import json
import subprocess

from parsing import ROOT, native

POSITIVE = [
    'sum by(job)(rate(requests_total{status=~"5.."})) > 100',
    'rate(up)', 'increase(up)', 'abs(up,)', 'sum(up,) by(job,)',
    'avg_over_time((a + b)[5m])', 'up[5m:2i]', 'up[:1m]', 'up[:]',
    'up[.5]', 'up[1.5m]', 'up[2m1h]', 'up[1h1h]', 'up[010]',
    'rate(up[0.5m])', 'up offset .5', 'up offset 0.5m',
    'up offset -1h @ end()', 'up @ start() offset 1h', '(up) offset 1h',
    'up @ +1', 'up offset 0', 'up offset 1h - 5',
    '(up @ 100) offset 1h', '(up offset 1h) @ 100', '(up offset 1h) offset 2h',
    '+p offset 0[5m]', '-p offset 0[5m]', '(-p)[5m]',
    '-p offset 1h offset 2h', '-p offset 1h @ 100 @ 200', '(p @ 100)[5m]',
    'a default b if c or d', 'a ifnot b and c', '1 > 2',
    'a + on(job) group_left(zone) b',
    'histogram_quantiles("phi", .5, .9, rate(bucket[5m]))',
    'label_set(up, "team", "core")', 'union(a,b)',
    'sum by(NaN,without)(up)', 'sum by("job")(up)',
    '{}', '{job=~".*"}', 'up{__name__=~"u.*"}', '{"up", job="api"}',
    'up # comment\r + ignored', 'up # comment\n + other',
    'up{job=`a\rb`}', 'up{job="a\rb"}', 'up{job="中"}',
    r'up{job="a\"b\\c\n"}', r'label_replace(up, "dst", "$1", "src", `(.*)`) ',
    '010 + 08 + 0_10 + 01_0 + 1_000 + .5e2', 'vector(NaN)', 'vector(-Inf)',
]
# Exercise both enclosing RHS precedence and unary zero-subtraction lowering.
ARITHMETIC = [
    '{}{}{}'.format(left, op, right)
    for left in ('-2', '--2', '(-2)', '2^-2', '+-2')
    for op in ('*', '/', '%', '^')
    for right in ('3', '-3', '3^2')
]
POSITIVE += ['vector(' + text + ')' for text in ARITHMETIC]
# Keyword-shaped metric names must survive normalization as data, including
# case-insensitive modifiers and the prefix position after a join modifier.
POSITIVE += [
    template.format(name=name)
    for word in ('bool', 'on', 'ignoring', 'group_left', 'group_right',
                 'prefix', 'fill', 'fill_left', 'fill_right')
    for name in (word, word.upper())
    for template in ('a + ({name})', 'a + ({name}{{job="api"}} offset 1m)',
                     'a + on(job) group_left(zone) ({name})')
]
# Aggregate names are metrics when disambiguated by parentheses, a matcher or
# an offset; the emitted query must not reinterpret a following word operator.
AGGREGATE_METRICS = ('sum', 'avg', 'count', 'topk', 'count_values', 'quantiles',
                     'topk_avg', 'bottomk_median', 'outliers_mad', 'zscore')
POSITIVE += [
    template.format(name=name)
    for word in AGGREGATE_METRICS
    for name in (word, word.upper())
    for template in ('({name}) or up', '{name}{{job="api"}} or up',
                     '{name} offset 1h or up')
]
POSITIVE += [
    'up{"up"}', '{"up","up"}', 'up{__name__="up"}',
    '{__name__="",__name__="up"}', 'up{__name__=~"down",__name__!="up"}',
    'limit_ratio or up', 'LIMIT_RATIO and up',
    'RATE(up[5m])', 'RaTe(up)', 'LaBeL_SeT(UP, "label", "MiXeD")',
    'HISTOGRAM_QUANTILES("phi", .5, .9, RATE(bucket[5m]))',
]
SET_OPERATORS = ('and', 'or', 'unless', 'default', 'if', 'ifnot')
FILL_NAMES = tuple(name for word in ('fill', 'fill_left', 'fill_right')
                   for name in (word, word.upper()))
POSITIVE += ['up {} ({})'.format(op, name) for op in SET_OPERATORS for name in FILL_NAMES]
NEGATIVE = [
    '', 'up + @', 'up{job=api}', 'abs(up', 'a + bool b',
    'up @ 1 @ 2', 'up offset 1h[5m]', 'up[5m][1m]', 'up offset +1h',
    'a + fill(+1) b', '1e1_0', 'up[1+2]', 'up[step()]',
    'up{job="bad\\q"}', 'a + on(job) on(zone) b',
    '-a*b[5m][1m]', '+a*b[5m][1m]', '-a*b offset 1h offset 2h',
    'rate(up[.5m])', 'up offset .5m', 'up[1h.5m]', 'up[1h:.5m]',
    'up{__name__="down"}', '{__name__="up",__name__="down"}',
    '{"up",__name__="down"}', '{__name__="up","down"}', 'up{"down"}',
    '{__name__="up",__name__=""}',
]
NEGATIVE += [name + ' or up' for word in AGGREGATE_METRICS for name in (word, word.upper())]
NEGATIVE += ['up {} {} {}'.format(op, matching, name)
             for op in SET_OPERATORS for name in FILL_NAMES for matching in ('', 'on(job)')]
NEGATIVE += ['up {} on(job) group_left(zone) {}'.format(op, name)
             for op in ('+', '*', '==') for name in ('prefix', 'PREFIX')]
UNSUPPORTED = [
    'WITH (x = up) x', 'up{job="api" or job="worker"}',
    'a + fill_left(0) fill_right(-1) b',
    'up{job="a"+"b"}', 'abs(up) keep_metric_names', 'sum(up) limit 1',
    'up offset 1h-5m', 'up @ (end()-1)', '1m', '1MiB', '0x1E+2',
    '温度', 'foo.bar', r'up{"job\u0041"="x"}', 'up[$__interval]',
    'up @ +1700000000 offset 1h', 'up @ -1 offset 1h', 'up @ +1[5m]',
    'a + on(job) group_left() prefix "src_" b',
    'a + on(job) group_right() PREFIX "src_" b',
]


def oracle(texts, env):
    result = subprocess.run(
        ['go', 'run', '-mod=readonly', '.', '-json'],
        cwd=ROOT / 'tests/conformance/metricsql', env=env,
        input=json.dumps(texts), text=True, encoding='utf-8',
        capture_output=True, check=True,
    )
    rows = json.loads(result.stdout)
    assert len(rows) == len(texts), 'upstream parser response count differs'
    return rows


def check(env):
    sources = POSITIVE + NEGATIVE + UNSUPPORTED
    upstream = oracle(sources, env)
    results = native(sources, mode='metricsql')
    normalized = []
    failures = []
    for index, (source, reference, result) in enumerate(zip(sources, upstream, results)):
        status, kind, value = result
        if index < len(POSITIVE):
            if not (reference['ok'] and status == 'ok'):
                failures.append((source, reference, result))
                continue
            normalized.append(value)
        elif index < len(POSITIVE) + len(NEGATIVE):
            if not (not reference['ok'] and status == 'err'):
                failures.append((source, reference, result))
        else:
            if not (reference['ok'] and (status, kind) == ('err', 'Unsupported')):
                failures.append((source, reference, result))
    for source, result in zip(normalized, oracle(normalized, env)):
        if not result['ok']:
            failures.append((source, result))
    assert not failures, failures
    print('Native MetricsQL parsing: {} valid roundtrips, {} invalid, {} unsupported witnesses.'.format(
        len(POSITIVE), len(NEGATIVE), len(UNSUPPORTED)))


def check_results(client, start, report, compare):
    """Real VM evaluation: original and normalized text plus fixed-value cases."""
    from metricraft import QueryBuilder as Q
    cases = [
        ('sum by(job)(rate(mc_requests_total))', [({'job': 'api'}, 15), ({'job': 'worker'}, 3)]),
        ('mc_missing default sum(mc_temperature)', [({}, 40)]),
        ('sum(mc_temperature) if mc_missing', []),
        ('sum(mc_temperature) ifnot mc_missing', [({}, 40)]),
        ('sum(mc_temperature offset 2m)', [({}, 34)]),
        ('sum(mc_temperature @ {})'.format(start + 7 * 60), [({}, 31)]),
        ('sum((mc_temperature @ {}) offset 2m)'.format(start + 7 * 60), [({}, 31)]),
        ('sum((mc_temperature offset 1m) offset 1m)', [({}, 34)]),
        ('sum(mc_temperature{job=~"a.*"}) > 25', [({}, 30)]),
        ('vector(1 > 2)', []),
        ('vector(-2^2)', [({}, -4)]),
        ('vector(2^-2*3)', [({}, .75)]),
        ('vector(2^-2^2)', [({}, .0625)]),
        ('vector(010 + 08 + 1_000)', [({}, 1016)]),
        ('vector(0_10 + 01_0)', [({}, 18)]),
    ]
    cases += [('vector(' + text + ')', None) for text in ARITHMETIC]
    for source, expected in cases:
        text = Q.parse(source, 'metricsql').build('metricsql')
        # The fixture grid is one minute. Pin implicit subquery resolution too;
        # VM's default five-minute step makes nested rollups align elsewhere.
        row = {'mode': 'metricsql', 'name': 'parsed_' + source, 'query': text,
               'original': source, 'step': '60s', 'expected': expected, 'status': 'failed'}
        report['cases'].append(row)
        before = client.query(source, time=start + 600, step='60s')
        after = client.query(text, time=start + 600, step='60s')
        row.update(original_actual=before.data, actual=after.data)
        if expected is not None:
            compare(before, expected, start + 600)
            compare(after, expected, start + 600)
        assert before.is_success and after.is_success, (source, before, after)
        assert before.data == after.data, (source, text, before.data, after.data)
        row['status'] = 'passed'
