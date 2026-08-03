"""Regenerate and verify repository checksum inventories portably."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]

TEXT_INVENTORIES = (
    "results/production_confirmatory/SHA256SUMS.txt",
    "results/production_corrected_end_to_end/SHA256SUMS.txt",
    "results/sensitivity_analyses/SHA256SUMS.txt",
)
JSON_INVENTORIES = (
    "results/h1_depth_weighting/comparison/artifact_checksums.json",
    "results/h2_replication_v1/_pipeline_output_stage1/SHA256SUMS_stage1_output.json",
)
# These preserve historical/external identities and are verified, never rewritten.
IMMUTABLE_INVENTORIES = (
    "results/superseded_pooled/SHA256SUMS.txt",
    "verification/input_checksums.sha256",
)
TEXT_SUFFIXES = {
    ".py", ".tex", ".bib", ".md", ".txt", ".json", ".yaml", ".yml",
    ".csv", ".tsv", ".toml", ".sha256",
}


def digest(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def normalize_path(value: str) -> str:
    return PurePosixPath(value.replace("\\", "/").removeprefix("./")).as_posix()


def text_entries(inventory: Path) -> dict[str, str]:
    entries = {}
    for line in inventory.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        checksum, name = line.split(maxsplit=1)
        entries[normalize_path(name.lstrip("*"))] = checksum
    return entries


def json_entries(inventory: Path) -> dict[str, str]:
    return {normalize_path(k): v for k, v in json.loads(inventory.read_text(encoding="utf-8")).items()}


def resolve(inventory: Path, name: str) -> Path:
    if name.startswith(("results/", "paper/", "verification/", "qnn_snr/", "scripts/")):
        return ROOT / name
    return inventory.parent / name


def current(entries: dict[str, str], inventory: Path) -> dict[str, str]:
    output = {}
    for name in sorted(entries):
        path = resolve(inventory, name)
        if not path.is_file():
            raise FileNotFoundError(f"{inventory.relative_to(ROOT)} references missing {name}")
        output[name] = digest(path)
    return output


def write_text_inventory(path: Path, entries: dict[str, str]) -> None:
    body = "".join(f"{value} *./{name}\n" for name, value in sorted(entries.items()))
    path.write_text(body, encoding="utf-8", newline="\n")


def write_json_inventory(path: Path, entries: dict[str, str]) -> None:
    path.write_text(json.dumps(dict(sorted(entries.items())), indent=2) + "\n", encoding="utf-8", newline="\n")


def verify_final_submission() -> list[str]:
    errors = []
    out = ROOT / "results/final_submission_v1"
    for name, expected in text_entries(out / "checksums.sha256").items():
        path = out / name
        if not path.is_file() or digest(path) != expected:
            errors.append(f"final_submission_v1 checksum mismatch: {name}")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    for item in manifest["component_references"]:
        path = ROOT / normalize_path(item["path"])
        if not path.is_file() or digest(path) != item["sha256"]:
            errors.append(f"component-reference mismatch: {item['path']}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    for relative in TEXT_INVENTORIES:
        path = ROOT / relative
        old = text_entries(path)
        new = current(old, path)
        if args.check and old != new:
            errors.append(f"stale active inventory: {relative}")
        elif not args.check:
            write_text_inventory(path, new)
    for relative in JSON_INVENTORIES:
        path = ROOT / relative
        old = json_entries(path)
        new = current(old, path)
        if args.check and old != new:
            errors.append(f"stale active inventory: {relative}")
        elif not args.check:
            write_json_inventory(path, new)
    for relative in IMMUTABLE_INVENTORIES:
        print(f"Preserved immutable historical/external inventory without rewriting: {relative}")
    errors.extend(verify_final_submission())
    if errors:
        print("\n".join(errors))
        return 1
    print("All active and immutable checksum inventories verify.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
