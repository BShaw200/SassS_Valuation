from __future__ import annotations

from typing import Any, Iterable

DISCLAIMER = (
    "This tool provides an approximate private-market SaaS valuation based on user inputs and generalized "
    "valuation logic. It is not a formal valuation, fairness opinion, tax opinion, or investment "
    "recommendation. Actual transaction values may differ materially based on market conditions, buyer type, "
    "deal structure, diligence findings, and negotiated terms."
)


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def safe_add(left: float | None, right: float) -> float:
    return (left or 0.0) + right


def pct(value: float) -> str:
    return f"{value:.1f}%"


def multiple(value: float) -> str:
    return f"{value:.2f}x ARR"


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"{sign}${abs_value/1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"{sign}${abs_value/1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"{sign}${abs_value/1_000:.1f}K"
    return f"{sign}${abs_value:,.0f}"


def average(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def normalize_score(value: float) -> int:
    return int(round(clamp(value, 0, 100)))


def get_field(inputs: dict[str, Any], field: str, default: float = 0.0) -> float:
    return float(inputs.get(field, default))
