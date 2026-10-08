"""
Operator enumerations for PromQL/MetricsQL.

This module contains all operator-related enumerations moved from AST modules
and enhanced with additional functionality.
"""

from metricraft._legacy.enums.base import OperationEnum, FunctionEnum


class BinaryOperator(OperationEnum):
    """Binary operators supported in MetricsQL/PromQL."""
    # Arithmetic operators
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    MOD = "%"
    POW = "^"

    # Comparison operators
    EQ = "=="
    NE = "!="
    GT = ">"
    LT = "<"
    GE = ">="
    LE = "<="

    # Logical operators
    AND = "and"
    OR = "or"
    UNLESS = "unless"

    # Set operators
    GROUP_LEFT = "group_left"
    GROUP_RIGHT = "group_right"

    # MetricsQL-specific operators
    DEFAULT = "default"

    @property
    def operation_name(self) -> str:
        """Get a human-readable name for this operation for error messages."""
        operation_names = {
            self.ADD: "addition",
            self.SUB: "subtraction",
            self.MUL: "multiplication",
            self.DIV: "division",
            self.MOD: "modulo",
            self.POW: "exponentiation",
            self.GT: "greater than comparison",
            self.LT: "less than comparison",
            self.GE: "greater than or equal comparison",
            self.LE: "less than or equal comparison",
            self.EQ: "equality comparison",
            self.NE: "inequality comparison",
            self.AND: "AND operation",
            self.OR: "OR operation",
            self.UNLESS: "UNLESS operation",
            self.GROUP_LEFT: "group_left operation",
            self.GROUP_RIGHT: "group_right operation",
            self.DEFAULT: "default operation"
        }
        return operation_names.get(self, f"{self.value} operation")

    @property
    def is_arithmetic(self) -> bool:
        """Check if this operator is an arithmetic operator."""
        return self in {
            self.ADD,
            self.SUB,
            self.MUL,
            self.DIV,
            self.MOD,
            self.POW}

    @property
    def is_comparison(self) -> bool:
        """Check if this operator is a comparison operator."""
        return self in {self.EQ, self.NE, self.GT, self.LT, self.GE, self.LE}

    @property
    def is_logical(self) -> bool:
        """Check if this operator is a logical operator."""
        return self in {self.AND, self.OR, self.UNLESS}

    @property
    def is_set_operator(self) -> bool:
        """Check if this operator is a set operator."""
        return self in {self.GROUP_LEFT, self.GROUP_RIGHT}


class UnaryOperator(OperationEnum):
    """Unary operators supported in MetricsQL/PromQL."""
    PLUS = "+"
    MINUS = "-"

    @property
    def operation_name(self) -> str:
        """Get human-readable operation name."""
        return f"unary {self.value}"


class AggregationOperator(FunctionEnum):
    """Aggregation operators supported in MetricsQL/PromQL."""
    # Standard PromQL aggregations
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    AVG = "avg"
    GROUP = "group"
    STDDEV = "stddev"
    STDVAR = "stdvar"
    COUNT = "count"
    COUNT_VALUES = "count_values"
    BOTTOMK = "bottomk"
    TOPK = "topk"
    QUANTILE = "quantile"

    # MetricsQL specific aggregations
    MEDIAN = "median"
    MAD = "mad"
    MODE = "mode"
    ANY = "any"
    GEOMEAN = "geomean"
    HISTOGRAM_QUANTILE = "histogram_quantile"
    LIMITK = "limitk"
    DISTINCT = "distinct"
    OUTLIERS_MAD = "outliers_mad"
    OUTLIERS_IQR = "outliers_iqr"

    @property
    def is_standard_promql(self) -> bool:
        """Check if this aggregation is part of standard PromQL."""
        standard = {
            self.SUM, self.MIN, self.MAX, self.AVG, self.GROUP,
            self.STDDEV, self.STDVAR, self.COUNT, self.COUNT_VALUES,
            self.BOTTOMK, self.TOPK, self.QUANTILE
        }
        return self in standard

    @property
    def requires_parameter(self) -> bool:
        """Check if this aggregation requires a parameter (like k for topk)."""
        return self in {
            self.BOTTOMK, self.TOPK, self.QUANTILE, self.COUNT_VALUES,
            self.LIMITK, self.OUTLIERS_MAD, self.OUTLIERS_IQR
        }

    @property
    def is_metricsql_extension(self) -> bool:
        """Check if this aggregation is a MetricsQL extension."""
        return not self.is_standard_promql


class MatchType(OperationEnum):
    """Types of label matching operators."""
    EQUAL = "="  # Exact match
    NOT_EQUAL = "!="  # Not equal
    REGEX_MATCH = "=~"  # Regex match
    REGEX_NOT_MATCH = "!~"  # Regex not match

    @property
    def is_regex(self) -> bool:
        """Check if this match type uses regex."""
        return self in {self.REGEX_MATCH, self.REGEX_NOT_MATCH}

    @property
    def operation_name(self) -> str:
        """Get a human-readable name for this match operation."""
        names = {
            self.EQUAL: "exact match",
            self.NOT_EQUAL: "not equal match",
            self.REGEX_MATCH: "regex match",
            self.REGEX_NOT_MATCH: "regex not match"
        }
        return names.get(self, f"label matching ({self.value})")

    @property
    def is_negated(self) -> bool:
        """Check if this match type is negated."""
        return self in {self.NOT_EQUAL, self.REGEX_NOT_MATCH}
