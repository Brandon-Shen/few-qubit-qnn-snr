"""Task D: re-run the replicate-count (R) pilot calibration for depth=1 cells
specifically, with max_R raised from the confirmatory config's 200 to 500, to see
whether the non-convergence documented in results/production_confirmatory/pilot_replicate_selection.json
(4/8 representative cells, all depth=1) resolves at a higher ceiling.

Does not touch results/production_confirmatory/pilot_replicate_selection.json or any confirmatory output --
writes only to verification/. Uses the same select_replicate_count() the pipeline's
`pilot-replicates` CLI command calls, restricted to the depth=1 subset of the
confirmatory config's prespecified representative_cells (A12) with max_R raised.

Run standalone from the repo root:
    python verification/r_calibration_depth1_check.py

Writes: verification/pilot_replicate_selection_depth1_maxR500.json
"""
from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path

from qnn_snr.config import load_config
from qnn_snr.pilot import select_replicate_count

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "confirmatory.yaml"
NEW_MAX_R = 500


def main():
    cfg = load_config(CONFIG_PATH)
    depth1_cells = [c for c in cfg.pilot.replicate_count.representative_cells if c["depth"] == 1]
    print(f"depth=1 representative cells (from configs/confirmatory.yaml, A12): {depth1_cells}")

    new_replicate_pilot = replace(cfg.pilot.replicate_count, max_R=NEW_MAX_R,
                                   representative_cells=depth1_cells)
    new_pilot = replace(cfg.pilot, replicate_count=new_replicate_pilot)
    new_cfg = replace(cfg, pilot=new_pilot)

    t0 = time.time()
    out = select_replicate_count(new_cfg, mode="finite_shot_end_to_end")
    dt = time.time() - t0
    print(f"wall clock: {dt:.2f}s")

    out["wall_clock_seconds"] = dt
    out["max_R_used"] = NEW_MAX_R
    out["cells_checked"] = depth1_cells

    out_path = Path(__file__).parent / "pilot_replicate_selection_depth1_maxR500.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")

    for cell in out["per_cell"]:
        last = cell["history"][-1]
        print(f"config={cell['configuration_id']} depth={cell['depth']} budget={cell['budget']}: "
              f"selected_R={cell['selected_R']}  last_R={last['R']} "
              f"mean_hw={last['mean_halfwidth']:.6f} snr_hw={last['snr_halfwidth']:.4f}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
