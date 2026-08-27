"""The green-baseline test required by ADR-0002, plus the sandbox-payload contract.

This file used to carry a guard asserting the package exported *nothing* — the tripwire from
ADR-0006, which cleared an inferred mission so it could not bias the real thesis. The thesis
has since arrived and the domain logic is deliberate, so that guard has done its job and is
retired here, exactly as its own docstring instructed.

What replaces it is the constraint that outlives the reset: whatever this package grows into,
it is uploaded into a Daytona sandbox and must import against a stock interpreter.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

#: Everything the sandbox driver and the agent are allowed to depend on.
EXPECTED_EXPORTS = {
    "DESTROY",
    "QUARANTINE_RETEST",
    "RELEASE",
    "CrossCheck",
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
}


@pytest.mark.smoke
def test_package_imports_and_exposes_the_documented_surface():
    import coldcall

    assert set(coldcall.__all__) == EXPECTED_EXPORTS
    assert coldcall.__version__
    for name in coldcall.__all__:
        assert hasattr(coldcall, name), f"{name} is exported but missing"


@pytest.mark.smoke
def test_package_imports_against_a_stock_interpreter():
    """The real constraint, checked the only way that proves it: a subprocess with no venv
    site-packages on the path beyond this package's own source tree.

    ``-I`` isolates the interpreter (no user site, no PYTHONPATH, no cwd injection), so the
    only importable third-party code is whatever we put on sys.path explicitly. If anyone
    adds an httpx or pandas import to src/coldcall, this fails here rather than at 2 a.m.
    inside a sandbox during the demo.
    """
    src = Path(__file__).resolve().parent.parent / "src"
    probe = (
        f"import sys; sys.path.insert(0, {str(src)!r});"
        "import coldcall;"
        "from coldcall.disposition import disposition, DispositionPolicy;"
        "from coldcall.mkt import Reading;"
        "from coldcall.plot import excursion_svg;"
        "from coldcall import cli;"
        "r = disposition([Reading(22.0, 60.0)], 20.0, 25.0, DispositionPolicy(6.0));"
        "print(r.verdict)"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", probe],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, (
        "the sandbox payload does not import against a stock interpreter:\n"
        f"{completed.stderr}"
    )
    assert completed.stdout.strip() == "release"
