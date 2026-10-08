"""Failure contracts for the backend semantic oracle, independent of servers."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_backend_results import compare
from metricraft import MetricsQueryResult


class BackendOracleTests(unittest.TestCase):
    def result(self, labels=None, value="12", timestamp=600, **kwargs):
        return MetricsQueryResult("success", {"resultType": "vector", "result": [
            {"metric": {"job": "api"} if labels is None else labels,
             "value": [timestamp, value]}]}, **kwargs)

    def test_accepts_only_expected_values_labels_and_timestamps(self):
        expected = [({"job": "api"}, 12)]
        compare(self.result(), expected, 600)
        for result in (self.result(value="13"), self.result(value="NaN"),
                       self.result(labels={}), self.result(timestamp=601),
                       self.result(_is_partial=True)):
            with self.subTest(result=result), self.assertRaises(AssertionError):
                compare(result, expected, 600)

    def test_rejects_duplicate_or_missing_series(self):
        result = self.result()
        duplicate = MetricsQueryResult("success", {"resultType": "vector", "result": result.result * 2})
        with self.assertRaisesRegex(AssertionError, "duplicate"):
            compare(duplicate, [({"job": "api"}, 12)], 600)
        with self.assertRaisesRegex(AssertionError, "label sets"):
            compare(result, [({"job": "api"}, 12), ({"job": "worker"}, 2)], 600)


if __name__ == "__main__":
    unittest.main()
