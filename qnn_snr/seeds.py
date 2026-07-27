"""Deterministic, collision-resistant seed derivation.

Separate seed streams for initialization, shot sampling, optimization, and
bootstrap (Section 22), each derived from `seed_root` plus a stream name and
an arbitrary tuple of integer/string ids via SHA-256, so re-running the same
config always reproduces bit-identical seeds without any shared mutable RNG
state between call sites.
"""
from __future__ import annotations

import hashlib


def derive_seed(seed_root: int, stream: str, *ids) -> int:
    payload = f"{seed_root}|{stream}|" + "|".join(str(i) for i in ids)
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2 ** 31 - 1)
