"""ColdCall — deterministic cold-chain stability and disposition math.

This package is intentionally dependency-free: it is uploaded into a Daytona sandbox and
executed there against a stock Python, so it must import with nothing but the standard
library. Anything needing httpx/pandas belongs in the ``data`` extra, not here.

Two layers, deliberately separate:

* :mod:`coldcall.mkt` — the primitives. Mean kinetic temperature, excursion accounting, and
  a conservative release/review/quarantine stability budget.
* :mod:`coldcall.disposition` — the decision a quality director signs: release,
  quarantine-and-retest, or destroy, with the policy inputs recorded alongside the verdict.

:mod:`coldcall.crosscheck` recomputes the verdict by deliberately different numerical means
and refuses to let a bundle be presented when the two disagree. :mod:`coldcall.weather` answers
why the load warmed, which the arithmetic cannot. :mod:`coldcall.plot` renders the evidence
chart (stdlib SVG, no matplotlib) and :mod:`coldcall.cli` is the sandbox entry point the agent
invokes.
"""

from coldcall.crosscheck import CrossCheck, cross_check
from coldcall.disposition import (
    DESTROY,
    QUARANTINE_RETEST,
    RELEASE,
    Disposition,
    DispositionPolicy,
    disposition,
    potency_estimate_pct,
)
from coldcall.mkt import (
    ExcursionSummary,
    Reading,
    StabilityBudget,
    excursion_summary,
    mean_kinetic_temperature,
    stability_budget,
)
from coldcall.plot import excursion_svg

__all__ = [
    "DESTROY",
    "CrossCheck",
    "QUARANTINE_RETEST",
    "RELEASE",
    "Disposition",
    "DispositionPolicy",
    "ExcursionSummary",
    "Reading",
    "StabilityBudget",
    "cross_check",
    "disposition",
    "excursion_summary",
    "excursion_svg",
    "mean_kinetic_temperature",
    "potency_estimate_pct",
    "stability_budget",
]
__version__ = "0.2.0"
