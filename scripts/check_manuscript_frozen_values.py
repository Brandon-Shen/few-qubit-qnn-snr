"""Check manuscript-ready values against the frozen numerical source of truth."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "paper/sn-article.tex"
SUPP = ROOT / "paper/supplemental.tex"
UPLOAD_MAIN = ROOT / "submission_package/main.tex"
UPLOAD_SUPP = ROOT / "submission_package/ESM_1.tex"
OUT = ROOT / "verification/manuscript_value_check.json"
TEXT_SUFFIXES = {
    ".py", ".tex", ".bib", ".md", ".txt", ".json", ".yaml", ".yml",
    ".csv", ".tsv", ".toml", ".sha256",
}

REQUIRED_MAIN = {
    "H1 estimate": "0.004043", "H1 SE": "0.001081", "H1 Holm": "0.000739",
    "H1 bootstrap low": "0.000473", "H1 bootstrap high": "0.007535",
    "H2 estimate": "0.014338", "H2 Holm": "0.015963", "H2 bootstrap low": "-0.016240",
    "H3 estimate": "-0.011615", "H3 Holm": "0.047875", "H3 bootstrap high": "0.009563",
    "H4 estimate": "-0.010179", "H4 Holm": "0.057658", "H4 bootstrap high": "0.005863",
    "seed H1": "0.007726", "H1 equal depth": "0.002374", "H1 observation weighted": "0.004043",
    "H3 L0": "-0.000958", "H3 L1": "-0.022273", "H3 conditional": "0.006978",
    "J original R0": "1.241760", "J original R1": "1.126633",
    "J seed R0": "1.163219", "J seed R1": "1.242137",
    "task rows": "4,000", "resource rows": "320", "zero variance join": "1,833", "job difference": "27.08",
}
PROHIBITED_MAIN = {
    "0.004346": "superseded direct-0/1 H1", "0.024996": "superseded direct-0/1 H2",
    "p_{\\mathrm{Holm}}=0.115": "superseded H4 Holm value",
    "No residual-shortcut interaction is supported": "obsolete residual-absence claim",
    "No interaction involving the residual": "obsolete residual-absence claim",
    "J_{EL}=": "ambiguous unconditioned J notation", "final energy": "task metric called final",
    "final fidelity": "task metric called final",
}

def sha(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()

def main(output: Path = OUT) -> dict:
    text = MAIN.read_text(encoding="utf-8")
    supp = SUPP.read_text(encoding="utf-8")
    missing = {label: token for label, token in REQUIRED_MAIN.items() if token not in text}
    prohibited = {token: reason for token, reason in PROHIBITED_MAIN.items() if token in text}
    ambiguous_j = bool(re.search(r"J_\{EL\}(?!\\mid)", text))
    availability_tokens = (
        "results/final\\_submission\\_v1/manifest.json",
        "submission-numerical-results-freeze-v1",
        "MANUSCRIPT\\_COMMIT.txt",
        "results/superseded/",
    )
    availability_errors = [token for token in availability_tokens if token not in text]
    synchronization_errors = []
    if MAIN.read_bytes() != UPLOAD_MAIN.read_bytes():
        synchronization_errors.append("main manuscript upload copy")
    if SUPP.read_bytes() != UPLOAD_SUPP.read_bytes():
        synchronization_errors.append("supplement upload copy")

    manifest = json.loads((ROOT / "results/final_submission_v1/manifest.json").read_text())
    hash_errors = []
    for ref in manifest["component_references"]:
        path = ROOT / ref["path"]
        if not path.exists() or sha(path) != ref["sha256"]:
            hash_errors.append(ref["path"])

    fig0 = pd.read_csv(ROOT / "paper/figure_data/fig0_el_primary_source.csv")
    figure_errors = []
    if set(fig0.metric) != {"I_EL_given_R0", "J_EL_given_R0"}:
        figure_errors.append("Figure 0 conditional metric names")
    j = pd.read_csv(ROOT / "results/jel_conditional/summary.csv")
    if len(j) != 4 or j.completed.min() != 2000 or j.failed.max() != 0:
        figure_errors.append("conditional J frozen rows/counts")

    abstract = text.split("\\abstract{", 1)[1].split("}\n\n\\keywords", 1)[0]
    abstract_plain = re.sub(r"\\[A-Za-z]+|[{}$]", " ", abstract)
    abstract_words = len(re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", abstract_plain))
    result = {
        "status": "pass" if not (missing or prohibited or ambiguous_j or hash_errors or figure_errors or availability_errors or synchronization_errors) and 150 <= abstract_words <= 250 else "fail",
        "authoritative_manifest": "results/final_submission_v1/manifest.json",
        "main_source": str(MAIN.relative_to(ROOT)).replace("\\", "/"),
        "supplement_source": str(SUPP.relative_to(ROOT)).replace("\\", "/"),
        "abstract_word_count": abstract_words,
        "required_values_checked": len(REQUIRED_MAIN), "missing_required": missing,
        "prohibited_matches": prohibited, "ambiguous_unconditioned_j": ambiguous_j,
        "manifest_hash_errors": hash_errors, "figure_source_errors": figure_errors,
        "availability_errors": availability_errors,
        "synchronization_errors": synchronization_errors,
        "supplement_contains_explicit_historical_audit": "Historical correction and audit record" in supp,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    result = main(args.output)
    print(json.dumps(result, indent=2))
    raise SystemExit(result["status"] != "pass")
