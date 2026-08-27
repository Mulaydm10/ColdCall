"""ColdCall — the project's Python payload.

**This package is deliberately empty of domain logic.** It previously contained cold-chain
stability maths written against a mission that was *inferred* from the supplied tech stack
rather than agreed as the thesis. That inference was cleared on 2026-08-27 so it could not
bias the real idea — see ``ADR-0006``. Restore instructions are in that ADR.

What survives, and why: this package is uploaded into a Daytona sandbox and executed there
against a stock Python, so whatever lands here must import with nothing but the standard
library. Anything needing httpx/pandas belongs in the ``data`` extra, not here. That constraint
is a property of the platform, not of any particular idea, so it outlives the reset.
"""

__all__: list[str] = []
__version__ = "0.1.0"
