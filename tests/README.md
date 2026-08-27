> **LOCKED governing file.** Do not edit in place. See `GOVERNANCE.md`.

# tests/

**There is no runnable test baseline yet, and that is expected — do not fake one.** The stack
is explicitly undecided (`design/decisions/ADR-0002-stack-selection.md`, `Q-0002`), so there is
nothing here to configure a test runner around. This directory exists as a placeholder so the
convention is visible before there's anything to test.

**Binding requirement:** whoever resolves `ADR-0002` must land a green smoke test (one trivial
passing test, proving the chosen toolchain's test runner actually works end-to-end) in the same
change that adds the stack's toolchain config and fills in `CLAUDE.md`'s "Canonical commands"
section. A scaffold whose test command fails on first invocation trains everyone to bypass it —
don't let that happen here even once.

Once a stack exists, this README should be updated (still LOCKED — route the edit through the
Main Agent per `GOVERNANCE.md`) to state the actual test conventions: directory layout, marker
conventions, how to run the fast subset vs. the full suite.
