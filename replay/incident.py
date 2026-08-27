"""Run one incident end to end against a live TrueForge, including the approval gate.

This is the demo driver. It opens the session that becomes the incident record, streams the
turn, makes the subagent fan-out visible as it happens, and — the part that matters — halts on
``tool.approval_required`` and puts the decision in a human's hands.

Three things it deliberately does not do
----------------------------------------
* **It does not auto-approve by default.** ``--auto allow`` exists for unattended smoke runs
  and prints a loud banner when used, because a gate that approves itself is not a gate.
* **It does not compute anything.** Every number it displays came from the sandbox.
* **It does not hide a failure.** If a turn errors, the error is the output.

Schema notes, verified against the live ``/api/v1/openapi.json`` rather than the build spec,
which is wrong on both counts:

* a session body is ``{"agent": {"spec": …}}``, not ``{"agent": …}``;
* approval resumes carry ``{"status": "allow"}`` / ``{"status": "deny", "reason": …}`` and must
  never be mixed with ``user.message`` items in the same turn.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE_URL = "http://localhost:8790/api/v1"
PUBLIC_REPO = "https://github.com/Mulaydm10/ColdCall"

# ANSI, degraded to nothing when piped — this output is read on camera.
_BOLD, _DIM, _RED, _GREEN, _YELLOW, _CYAN, _OFF = (
    ("\033[1m", "\033[2m", "\033[31m", "\033[32m", "\033[33m", "\033[36m", "\033[0m")
    if sys.stdout.isatty()
    else ("", "", "", "", "", "", "")
)


def _request(method: str, url: str, body: dict[str, Any] | None = None, timeout: float = 60.0):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"content-type": "application/json"} if data else {}
    return urllib.request.urlopen(
        urllib.request.Request(url, data=data, headers=headers, method=method), timeout=timeout
    )


def _get_json(url: str) -> dict[str, Any]:
    with _request("GET", url) as response:
        return json.loads(response.read().decode("utf-8") or "{}")


def _post_json(url: str, body: dict[str, Any]) -> dict[str, Any]:
    with _request("POST", url, body) as response:
        return json.loads(response.read().decode("utf-8") or "{}")


def _stream(url: str, body: dict[str, Any], timeout: float) -> Iterator[dict[str, Any]]:
    """Yield decoded SSE ``data:`` payloads from a streaming turn."""
    with _request("POST", url, body, timeout=timeout) as response:
        for raw in response:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                yield json.loads(payload)
            except json.JSONDecodeError:
                continue


def configured_servers(base_url: str) -> set[str]:
    try:
        return {s.get("name") for s in _get_json(f"{base_url}/mcp-servers").get("data", [])}
    except (urllib.error.URLError, json.JSONDecodeError):
        return set()


def build_spec(manifest_path: Path, base_url: str) -> dict[str, Any]:
    """Load the manifest and drop MCP servers this harness does not actually have.

    Session creation validates the whole spec up front, so referencing a connector that was
    never configured fails the session rather than degrading. Dropping them here — loudly —
    means a deferred Supabase login stops the *actions*, which is honest, instead of stopping
    the agent from starting at all, which just looks broken.
    """
    spec = json.loads(manifest_path.read_text(encoding="utf-8"))
    spec.pop("$comment", None)
    available = configured_servers(base_url)
    wanted = spec.get("mcp_servers", [])
    kept = [s for s in wanted if s.get("name") in available]
    dropped = [s.get("name") for s in wanted if s.get("name") not in available]
    if dropped:
        print(
            f"{_YELLOW}  note: {', '.join(dropped)} not configured on this harness — "
            f"attaching {len(kept)} of {len(wanted)} connectors{_OFF}"
        )
    spec["mcp_servers"] = kept
    return spec


def excursion_message(payload: dict[str, Any], readings: list[dict[str, Any]]) -> str:
    """The webhook a temperature logger would post, plus what the sandbox needs to act on it.

    The readings travel in the payload rather than being read from a database because the
    incident store is local SQLite and the sandbox is a remote microVM. That is also how a
    real excursion webhook works — the logger posts its window. When the Supabase connector is
    authorised, this becomes a database read and the payload carries only the identifiers.
    """
    return f"""EXCURSION ALERT. Open an incident and work it per the `coldchain-sop` skill.

{json.dumps(payload, indent=2)}

## Getting the disposition module into your sandbox

The deterministic module is open source. In the sandbox, run:

    git clone --depth 1 {PUBLIC_REPO} /work/coldcall

Then write the readings below to `/work/leg.json` and run, from `/work/coldcall`:

    PYTHONPATH=src python -m coldcall.cli \\
      --telemetry /work/leg.json \\
      --product data/product_profile.json \\
      --allowed-excursion-hours 6 \\
      --shipment-id {payload.get('shipment_id', '')} --lot-id {payload.get('lot_id', '')} \\
      --svg-out /work/excursion.svg --json-out /work/verdict.json

Report its JSON verbatim. Do not restate the verdict in your own words and do not round it.
If it fails to run, that is the finding — report the error rather than estimating.

## Telemetry for this shipment ({len(readings)} readings, real recorded data, replayed)

```json
{json.dumps(readings)}
```
"""


def _thread_label(event: dict[str, Any]) -> str:
    """`main` for the orchestrator, a short id for a strand."""
    thread = str(event.get("thread_id", ""))
    return "main" if thread == "main" else thread[:8]


def render(event: dict[str, Any]) -> None:
    """Print a turn event the way a viewer needs to see it.

    Event names are the ones the running harness actually emits, read off a live turn's
    ``/events`` rather than from the build spec: the model's own output arrives as
    ``model.message`` carrying either ``content`` or ``tool_calls``, and results come back as
    ``tool.response``. There is no ``message.delta``.
    """
    kind = event.get("type", "")
    where = _thread_label(event)

    if kind == "thread.created":
        print(f"{_CYAN}  ├─ strand started {where}{_OFF}")
    elif kind == "thread.done":
        print(f"{_CYAN}  └─ strand finished {where}{_OFF}")
    elif kind == "sandbox.created":
        print(f"{_DIM}     sandbox ready{_OFF}")
    elif kind == "model.message":
        for call in event.get("tool_calls") or []:
            fn = call.get("function", {})
            name = fn.get("name", "?")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            # `intent` is the harness's own one-line rationale for the call. It is the single
            # most useful thing on screen during a demo, so it leads.
            intent = args.get("intent") or args.get("command") or ""
            suffix = f" {_DIM}{str(intent)[:90]}{_OFF}" if intent else ""
            print(f"{_DIM}     [{where}]{_OFF} → {name}{suffix}")
        content = event.get("content")
        if isinstance(content, str) and content.strip():
            print(f"\n{content.strip()}\n")
        elif isinstance(content, list):
            for part in content:
                text = part.get("text") if isinstance(part, dict) else None
                if text and text.strip():
                    print(f"\n{text.strip()}\n")
    elif kind == "tool.response":
        content = str(event.get("content", ""))
        if '"error"' in content or "failed" in content.lower():
            print(f"{_RED}     [{where}] tool error: {content[:300]}{_OFF}")
    elif kind == "turn.error" or event.get("error"):
        print(f"{_RED}  turn error: {json.dumps(event)[:400]}{_OFF}")


def approval_banner(event: dict[str, Any]) -> None:
    calls = event.get("tool_calls", [])
    print(f"\n{_BOLD}{_YELLOW}{'═' * 72}{_OFF}")
    print(f"{_BOLD}{_YELLOW}  HELD FOR APPROVAL — irreversible action{_OFF}")
    print(f"{_BOLD}{_YELLOW}{'═' * 72}{_OFF}")
    for call in calls:
        name = call.get("name") or call.get("tool_name") or "?"
        args = call.get("arguments") or call.get("args") or {}
        rendered = json.dumps(args, indent=2) if isinstance(args, dict) else str(args)
        print(f"\n  {_BOLD}{name}{_OFF}")
        for line in rendered.splitlines()[:24]:
            print(f"    {_DIM}{line}{_OFF}")
    print(f"\n{_BOLD}{_YELLOW}{'─' * 72}{_OFF}")


def decide(auto: str | None) -> tuple[str, str]:
    if auto == "allow":
        print(f"{_RED}  --auto allow: approving without a human. NOT the demo path.{_OFF}")
        return "allow", ""
    if auto == "deny":
        print(f"{_YELLOW}  --auto deny: denying automatically.{_OFF}")
        return "deny", "automated deny (--auto deny)"
    while True:
        answer = input(f"  {_BOLD}allow / deny ?{_OFF} ").strip().lower()
        if answer in ("a", "allow"):
            return "allow", ""
        if answer in ("d", "deny"):
            return "deny", input("  reason: ").strip() or "denied by the operator"
        print("  please answer 'allow' or 'deny'.")


def run(base_url: str, spec: dict[str, Any], message: str, auto: str | None, timeout: float) -> int:
    session = _post_json(f"{base_url}/sessions", {"agent": {"spec": spec}}).get("data", {})
    session_id = session.get("id")
    if not session_id:
        print(f"{_RED}session created but carried no id{_OFF}", file=sys.stderr)
        return 1

    print(f"\n{_BOLD}incident session {session_id}{_OFF}")
    print(f"{_DIM}  the session IS the incident record — watch it at "
          f"{base_url.rsplit('/api/', 1)[0]}{_OFF}\n")

    body: dict[str, Any] = {
        "stream": True,
        "input": [{"type": "user.message", "content": message}],
    }
    turn_id = ""

    while True:
        pending: dict[str, Any] | None = None
        try:
            for event in _stream(f"{base_url}/sessions/{session_id}/turns", body, timeout):
                if event.get("type") == "turn.created":
                    turn_id = event.get("id", turn_id) or turn_id
                if event.get("type") == "tool.approval_required":
                    pending = event
                    approval_banner(event)
                    break
                render(event)
        except urllib.error.HTTPError as exc:
            print(f"{_RED}turn failed: HTTP {exc.code} {exc.read().decode()[:400]}{_OFF}")
            return 1
        except urllib.error.URLError as exc:
            print(f"{_RED}could not reach the harness: {exc}{_OFF}")
            return 1

        if pending is None:
            print(f"\n{_GREEN}turn complete — session {session_id}{_OFF}")
            return 0

        status, reason = decide(auto)
        approval: dict[str, Any] = {"status": status}
        if status == "deny" and reason:
            approval["reason"] = reason

        # Every pending call in the thread is resolved with the same decision. Approving some
        # and denying others in one gesture would leave the agent half-authorised, which is a
        # worse state than either answer.
        body = {
            "stream": True,
            "previous_turn_id": turn_id,
            "input": [
                {
                    "type": "user.tool_approval",
                    "thread_id": pending.get("thread_id", ""),
                    "tool_call_id": call.get("id") or call.get("tool_call_id", ""),
                    "approval": approval,
                }
                for call in pending.get("tool_calls", [])
            ],
        }
        colour = _GREEN if status == "allow" else _YELLOW
        print(f"{colour}  → {status.upper()}{_OFF}\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python replay/incident.py",
        description="Run one cold-chain incident end to end against a live TrueForge.",
    )
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p.add_argument("--manifest", type=Path, default=REPO_ROOT / "agents/coldcall.agent.json")
    p.add_argument("--leg", type=Path, default=REPO_ROOT / "data/samples/selected_leg.json")
    p.add_argument("--shipment-id", default="VCC-118")
    p.add_argument("--lot-id", default="A2231")
    p.add_argument(
        "--auto",
        choices=["allow", "deny"],
        help="answer the approval gate automatically. For unattended smoke runs only — the "
        "gate is the demo, and a gate that approves itself is not one.",
    )
    p.add_argument("--timeout", type=float, default=900.0)
    args = p.parse_args(argv)

    base_url = args.base_url.rstrip("/")
    readings = json.loads(args.leg.read_text(encoding="utf-8"))
    out_of_range = [r for r in readings if float(r["temp_c"]) > 25.0]
    payload = {
        "event": "temperature_excursion",
        "shipment_id": args.shipment_id,
        "lot_id": args.lot_id,
        "product_id": "AMOXICILLIN-500",
        "labelled_range_c": [20.0, 25.0],
        "excursion_permitted_range_c": [15.0, 30.0],
        "readings_in_window": len(readings),
        "readings_out_of_labelled_range": len(out_of_range),
        "peak_temp_c": max((float(r["temp_c"]) for r in readings), default=None),
        "telemetry_provenance": (
            "real recorded shipment leg from Zenodo 10.5281/zenodo.7907515, replayed — "
            "NOT live telemetry. See replay/SHIPMENT.md."
        ),
    }

    try:
        spec = build_spec(args.manifest, base_url)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"could not load the agent manifest: {exc}", file=sys.stderr)
        return 2

    return run(base_url, spec, excursion_message(payload, readings), args.auto, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
