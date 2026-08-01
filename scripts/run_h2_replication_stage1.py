"""H2 robustness/replication package, Phase 6: Stage 1 replication runner.

Orchestrates the existing, already-tested `qnn_snr` CLI (not a bespoke
reimplementation of the generation/fitting logic) against
configs/h2_replication_v1_stage1.yaml -- a new seed namespace
(seed_root=3872531887), the identical design shape as production
(8 configs x 5 depths x 4 budgets x 50 inits), R_rep=30 (matching
production exactly), end-to-end mode only.

Steps run: generate-exact -> generate-shots(end_to_end) -> validate ->
aggregate -> fit -> report. Bootstrap is deliberately NOT run here (see
configs/h2_replication_v1_stage1.yaml's comment: at the measured cost for
this dataset size, even n=30 is a separate ~72-minute step) -- run
scripts/run_h2_replication_stage1_bootstrap.py afterward for that.

Idempotent: `qnn_snr`'s own generate-exact/generate-shots steps already
skip regeneration if output exists (matching production's convention);
this wrapper additionally records per-step wall-clock, exit code, and
output-file hashes to a step log, and never proceeds past a failed step
silently.

Run from the repo root: python scripts/run_h2_replication_stage1.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "h2_replication_v1_stage1.yaml"
RESULTS_DIR = REPO_ROOT / "results" / "h2_replication_v1" / "_pipeline_output_stage1"
LOG_PATH = REPO_ROOT / "results" / "h2_replication_v1" / "stage1_execution_log.json"

STEPS = [
    ["generate-exact", "--config", str(CONFIG_PATH)],
    ["generate-shots", "--config", str(CONFIG_PATH), "--mode", "finite_shot_end_to_end"],
    ["validate", "--config", str(CONFIG_PATH)],
    ["aggregate", "--config", str(CONFIG_PATH), "--pointwise-bootstrap-iterations", "20"],
    ["fit", "--config", str(CONFIG_PATH)],
    ["report", "--config", str(CONFIG_PATH)],
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_log() -> list[dict]:
    if LOG_PATH.exists():
        return json.loads(LOG_PATH.read_text())
    return []


def save_log(entries: list[dict]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(entries, indent=2, default=str), encoding="utf-8")


def main() -> None:
    entries = load_log()
    completed_steps = {e["step_name"] for e in entries if e["exit_code"] == 0}

    for step_args in STEPS:
        step_name = step_args[0]
        if step_name in completed_steps:
            print(f"[{step_name}] already completed successfully (per {LOG_PATH.name}), skipping")
            continue

        print(f"[{step_name}] starting: python -m qnn_snr {' '.join(step_args)}", flush=True)
        t0 = time.time()
        proc = subprocess.run(
            [sys.executable, "-m", "qnn_snr", *step_args],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        dt = time.time() - t0
        entry = {
            "step_name": step_name, "args": step_args, "exit_code": proc.returncode,
            "wallclock_s": dt, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:],
        }
        entries.append(entry)
        save_log(entries)

        print(f"[{step_name}] exit_code={proc.returncode} wallclock_s={dt:.1f}", flush=True)
        if proc.returncode != 0:
            print(f"[{step_name}] FAILED. stderr tail:\n{proc.stderr[-2000:]}", flush=True)
            print("Stopping: a failed step is never silently skipped past.", flush=True)
            sys.exit(1)

    # --- Hash every output file produced ---
    output_hashes = {}
    if RESULTS_DIR.exists():
        for p in sorted(RESULTS_DIR.rglob("*")):
            if p.is_file():
                output_hashes[str(p.relative_to(RESULTS_DIR))] = sha256_of(p)
    (RESULTS_DIR / "SHA256SUMS_stage1_output.json").write_text(
        json.dumps(output_hashes, indent=2), encoding="utf-8"
    )

    print(f"\nStage 1 (generate+fit+report) complete. {len(entries)} step(s) logged to {LOG_PATH}.")
    print(f"Output hashes written to {RESULTS_DIR / 'SHA256SUMS_stage1_output.json'} "
          f"({len(output_hashes)} files).")


if __name__ == "__main__":
    main()
