"""Regression tests for the H2 replication seed namespace (Phase 5/8):
the replication seed_root must not overlap with any existing seed_root in
the repo, and must produce different derive_seed() outputs than production
for a broad sample of (stream, ids) tuples.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import qnn_snr
from qnn_snr.config import load_config
from qnn_snr.seeds import derive_seed

REPO_ROOT = Path(qnn_snr.__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "configs"

REPLICATION_SEED_ROOT = 3872531887


def test_replication_seed_root_matches_documented_derivation():
    expected = int.from_bytes(hashlib.sha256(b"h2_independent_replication_v1").digest()[:4], "big")
    assert expected == REPLICATION_SEED_ROOT


def test_replication_seed_root_differs_from_all_known_config_roots():
    """Check against the pre-existing production/dev/smoke configs
    specifically (not a glob over configs/*.yaml, which would trivially
    include the replication's own config and always pass)."""
    known_roots = set()
    for name in ("confirmatory.yaml", "dev.yaml", "smoke.yaml"):
        cfg = load_config(CONFIG_DIR / name)
        known_roots.add(cfg.seed_root)
    assert REPLICATION_SEED_ROOT not in known_roots, (
        f"replication seed_root collides with an existing config root: {known_roots}"
    )


@pytest.mark.parametrize("stream", ["init_theta", "init_classical", "shots"])
def test_derive_seed_differs_between_production_and_replication_roots(stream):
    production_root = 20260726
    # Sample a spread of (init_id, depth, config_id, mode, budget, replicate_id)-shaped
    # id tuples matching the call sites in qnn_snr/replicate.py.
    sample_ids_variants = [
        (0, 1), (0, 6), (49, 1), (49, 6),
        (0, 1, 1, "finite_shot_end_to_end", 250, 0),
        (0, 1, 1, "finite_shot_end_to_end", 250, 29),
        (49, 6, 8, "finite_shot_end_to_end", 2000, 29),
    ]
    collisions = 0
    for ids in sample_ids_variants:
        prod_seed = derive_seed(production_root, stream, *ids)
        repl_seed = derive_seed(REPLICATION_SEED_ROOT, stream, *ids)
        if prod_seed == repl_seed:
            collisions += 1
    assert collisions == 0, (
        f"{collisions} seed collision(s) found between production and replication "
        f"roots for stream={stream!r} -- replication would not be independent"
    )


def test_stage1_config_uses_replication_seed_root():
    stage1_path = CONFIG_DIR / "h2_replication_v1_stage1.yaml"
    if not stage1_path.exists():
        pytest.skip("Stage 1 config not yet created")
    cfg = load_config(stage1_path)
    assert cfg.seed_root == REPLICATION_SEED_ROOT


def test_stage1_config_does_not_write_into_original_confirmatory_results_dir():
    stage1_path = CONFIG_DIR / "h2_replication_v1_stage1.yaml"
    if not stage1_path.exists():
        pytest.skip("Stage 1 config not yet created")
    cfg = load_config(stage1_path)
    assert "production_confirmatory" not in cfg.output.results_dir
    assert cfg.output.results_dir != "results"
