"""Axis formatter factories for ReportKit analytical charts."""
from __future__ import annotations

from matplotlib.ticker import FuncFormatter


def percent_formatter(decimals: int = 0, *, scale: float = 100.0) -> FuncFormatter:
    """Format fractional values as percentages using ``scale``."""
    return FuncFormatter(lambda x, _: f"{x * scale:.{decimals}f}%")


def bps_formatter(decimals: int = 0) -> FuncFormatter:
    """Format fractional values as basis points."""
    return FuncFormatter(lambda x, _: f"{x * 10000:.{decimals}f} bp")


def number_formatter(decimals: int = 1) -> FuncFormatter:
    """Format numbers with thousands separators and fixed precision."""
    return FuncFormatter(lambda x, _: f"{x:,.{decimals}f}")


def integer_formatter() -> FuncFormatter:
    """Format values as whole numbers with thousands separators."""
    return FuncFormatter(lambda x, _: f"{x:,.0f}")


def currency_formatter(symbol: str = "$", decimals: int = 0) -> FuncFormatter:
    """Format numbers with a currency symbol and fixed precision."""
    return FuncFormatter(lambda x, _: f"{symbol}{x:,.{decimals}f}")


def multiple_formatter(decimals: int = 1) -> FuncFormatter:
    """Format values as multiples with a multiplication sign."""
    return FuncFormatter(lambda x, _: f"{x:.{decimals}f}×")


__all__ = [
    "bps_formatter", "currency_formatter", "integer_formatter", "multiple_formatter",
    "number_formatter", "percent_formatter",
]
