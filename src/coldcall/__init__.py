"""ColdCall — deterministic cold-chain stability math.

This package is intentionally dependency-free: it is uploaded into a Daytona sandbox and
executed there against a stock Python, so it must import with nothing but the standard
library. Anything needing httpx/pandas belongs in the ``data`` extra, not here.
"""

from coldcall.mkt import (
    ExcursionSummary,
    Reading,
    StabilityBudget,
    excursion_summary,
    mean_kinetic_temperature,
    stability_budget,
)

__all__ = [
    "ExcursionSummary",
    "Reading",
    "StabilityBudget",
    "excursion_summary",
    "mean_kinetic_temperature",
    "stability_budget",
]
__version__ = "0.1.0"
