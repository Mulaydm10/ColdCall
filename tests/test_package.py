"""The green-baseline test required by ADR-0002.

The suite that used to live here tested cold-chain stability maths written against an inferred
mission, and was removed with it (ADR-0006). This file keeps `uv run pytest` — a canonical
command in CLAUDE.md — green and meaningful in the meantime: it proves the toolchain resolves
the project-local venv, puts `src/` on the path, and imports the package that gets uploaded
into the sandbox.

Delete this file once the real thesis brings real tests.
"""

import pytest


@pytest.mark.smoke
def test_package_imports_with_stdlib_only():
    """The sandbox payload must import against a stock interpreter."""
    import coldcall

    assert coldcall.__version__ == "0.1.0"


@pytest.mark.smoke
def test_package_carries_no_inferred_domain_logic():
    """Guard the reset: nothing mission-shaped should reappear here by accident.

    This is not busywork. The point of ADR-0006 is that domain logic must follow the thesis,
    not precede it. If someone re-adds an export before VISION.md is real, this fails and asks
    them to write the ADR first.
    """
    import coldcall

    assert coldcall.__all__ == []
