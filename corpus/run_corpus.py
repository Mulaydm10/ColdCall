"""Run the deterministic disposition over every fetched corpus dataset.

For each ``corpus/datasets/<slug>/config.json`` whose data has been fetched and adapted, this
invokes ``python -m coldcall.cli`` **as a subprocess** per leg — the exact entry point the
sandbox runs, so the benchmark exercises what ships, not a lookalike import path — then
compares each verdict against the dataset's ``expected.json`` regression pins and writes
``corpus/results.json`` plus the human-readable ``corpus/RESULTS.md``.

Exit codes: 0 when every computed leg matches its pin (NEW legs do not fail), 1 when any leg
drifted from its pin, errored, or tripped the cross-check (the CLI's own exit 3 — two
implementations of a regulated calculation disagreeing is never ignorable).

Stdlib only, like everything else on the compute path.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = REPO_ROOT / "corpus" / "datasets"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_leg(
    leg_path: Path, profile_path: Path, policy: dict[str, Any], leg_id: str
) -> dict[str, Any]:
    """Score one leg through the CLI and return a result row.

    The row always carries ``status``: ``ok`` (verdict computed, cross-check agreed),
    ``crosscheck_disagreement`` (exit 3 — the verdict cannot be trusted), or ``error``
    (bad input or a crash; stderr is preserved because that is the actionable part).
    """
    cmd = [
        sys.executable,
        "-m",
        "coldcall.cli",
        "--telemetry",
        str(leg_path),
        "--product",
        str(profile_path),
        "--allowed-excursion-hours",
        str(policy["allowed_excursion_hours"]),
        "--retest-at-pct",
        str(policy.get("retest_at_pct", 50.0)),
        "--destroy-at-pct",
        str(policy.get("destroy_at_pct", 100.0)),
        "--shipment-id",
        leg_id,
    ]
    if policy.get("no_freeze_rule"):
        cmd.append("--no-freeze-rule")

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
    )

    row: dict[str, Any] = {"leg_id": leg_id, "exit_code": proc.returncode}
    if proc.returncode in (0, 3):
        try:
            document = json.loads(proc.stdout)
        except json.JSONDecodeError:
            row["status"] = "error"
            row["detail"] = f"unparseable CLI stdout: {proc.stdout[:200]!r}"
            return row
        excursion = document.get("excursion") or {}
        row["verdict"] = document.get("verdict")
        row["mkt_c"] = document.get("mkt_c")
        row["budget_consumed_pct"] = document.get("budget_consumed_pct")
        row["excursion_minutes"] = excursion.get("minutes_out_of_range")
        row["max_c"] = excursion.get("max_c")
        row["min_c"] = excursion.get("min_c")
        row["crosscheck_agrees"] = (document.get("cross_check") or {}).get("agrees")
        row["status"] = "ok" if proc.returncode == 0 else "crosscheck_disagreement"
    else:
        row["status"] = "error"
        row["detail"] = proc.stderr.strip()[:500]
    return row


def run_dataset(dataset_dir: Path) -> dict[str, Any] | None:
    """Run every leg of one dataset. Returns None when its data is not fetched yet."""
    config = _load_json(dataset_dir / "config.json")
    data_dir = REPO_ROOT / config["data_dir"]
    manifest_path = data_dir / "manifest.json"
    if not manifest_path.exists():
        print(
            f"  SKIP {config['slug']}: no {manifest_path.relative_to(REPO_ROOT)} — run "
            f"corpus/datasets/{config['slug']}/fetch.sh then adapt.py",
            file=sys.stderr,
        )
        return None

    manifest = _load_json(manifest_path)
    profile_path = REPO_ROOT / config["profile"]
    expected_path = dataset_dir / "expected.json"
    expected: dict[str, Any] = (
        _load_json(expected_path).get("legs", {}) if expected_path.exists() else {}
    )

    rows: list[dict[str, Any]] = []
    for leg in manifest["legs"]:
        row = _run_leg(data_dir / leg["file"], profile_path, config["policy"], leg["id"])
        row["n_readings"] = leg.get("n")
        pin = expected.get(leg["id"])
        if row["status"] != "ok":
            row["check"] = "FAIL"
        elif pin is None:
            row["check"] = "NEW"
        elif pin.get("verdict") == row.get("verdict"):
            row["check"] = "PASS"
        else:
            row["check"] = "DRIFT"
            row["pinned"] = pin.get("verdict")
        rows.append(row)
        print(
            f"  {row['check']:<5} {leg['id']:<40} {row.get('verdict') or row['status']}",
            flush=True,
        )

    return {"slug": config["slug"], "title": config.get("title", config["slug"]), "legs": rows}


def _markdown(results: list[dict[str, Any]], generated_at: str) -> str:
    lines = [
        "# Corpus results (generated — do not edit)",
        "",
        f"Generated by `corpus/run_corpus.py` at {generated_at}. Verdicts are regression",
        "pins, not ground truth — see `corpus/README.md`.",
        "",
    ]
    for dataset in results:
        counts: dict[str, int] = {}
        for row in dataset["legs"]:
            counts[row["check"]] = counts.get(row["check"], 0) + 1
        summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
        lines += [f"## {dataset['title']} (`{dataset['slug']}`) — {summary}", ""]
        lines += [
            "| leg | n | verdict | MKT °C | budget % | excursion min | check |",
            "|---|---:|---|---:|---:|---:|---|",
        ]
        for row in dataset["legs"]:
            if row["status"] == "error":
                lines.append(
                    f"| `{row['leg_id']}` | {row.get('n_readings', '')} | "
                    f"error: {row.get('detail', '')[:80]} | | | | {row['check']} |"
                )
                continue
            lines.append(
                f"| `{row['leg_id']}` | {row.get('n_readings', '')} "
                f"| `{row['verdict']}` | {row['mkt_c']} | {row['budget_consumed_pct']} "
                f"| {row['excursion_minutes']} | {row['check']} |"
            )
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python corpus/run_corpus.py")
    parser.add_argument("--only", help="run a single dataset slug")
    parser.add_argument(
        "--no-write", action="store_true", help="print results but do not touch RESULTS.md"
    )
    args = parser.parse_args(argv)

    dataset_dirs = sorted(
        d for d in DATASETS_DIR.iterdir() if (d / "config.json").exists()
    )
    if args.only:
        dataset_dirs = [d for d in dataset_dirs if d.name == args.only]
        if not dataset_dirs:
            print(f"no dataset named {args.only!r} under corpus/datasets/", file=sys.stderr)
            return 2

    results = []
    for dataset_dir in dataset_dirs:
        print(f"{dataset_dir.name}:", flush=True)
        outcome = run_dataset(dataset_dir)
        if outcome is not None:
            results.append(outcome)

    if not results:
        print("nothing ran — no dataset has fetched data", file=sys.stderr)
        return 2

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not args.no_write:
        (REPO_ROOT / "corpus" / "results.json").write_text(
            json.dumps({"generated_at": generated_at, "datasets": results}, indent=2) + "\n",
            encoding="utf-8",
        )
        (REPO_ROOT / "corpus" / "RESULTS.md").write_text(
            _markdown(results, generated_at), encoding="utf-8"
        )

    failed = [
        row
        for dataset in results
        for row in dataset["legs"]
        if row["check"] in ("FAIL", "DRIFT")
    ]
    total = sum(len(dataset["legs"]) for dataset in results)
    print(f"\n{total} legs across {len(results)} datasets — {len(failed)} FAIL/DRIFT")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
