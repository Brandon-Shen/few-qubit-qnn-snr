"""Best-effort structural check for sn-article.tex.
pdflatex compilation (no LaTeX toolchain is available in this environment --
see verification/paper_accuracy_check.md / the session's final report for why
this is a stand-in, not a real compile). Checks:
  - \\begin{X}/\\end{X} balance
  - brace balance (ignoring braces inside verbatim-like contexts is not
    attempted; this codebase's main.tex has none)
  - every \\label is unique
  - every \\ref/\\Cref target has a matching \\label
  - every \\includegraphics file exists on disk

\\input{...} directives are expanded (recursively) before any check runs,
matching what a real LaTeX compile would see, so labels/refs defined in an
\\input-ed file (e.g. a generated table) resolve correctly.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

MAIN_TEX = Path(__file__).resolve().parents[1] / "sn-article.tex"
PAPER_DIR = MAIN_TEX.parent


def expand_inputs(text: str, base_dir: Path, seen: frozenset[Path] = frozenset()) -> str:
    def replace(match: re.Match) -> str:
        rel = match.group(1)
        path = base_dir / rel
        if not path.suffix:
            path = path.with_suffix(".tex")
        if not path.exists() or path in seen:
            return match.group(0)  # leave as-is; MISSING GRAPHIC-style checks aren't done for \input
        included = path.read_text(encoding="utf-8")
        return expand_inputs(included, path.parent, seen | {path})

    return re.sub(r"\\input\{([^}]+)\}", replace, text)


def check():
    text = MAIN_TEX.read_text(encoding="utf-8")
    text = expand_inputs(text, PAPER_DIR)
    problems = []

    begins = re.findall(r"\\begin\{([^}]+)\}", text)
    ends = re.findall(r"\\end\{([^}]+)\}", text)
    bc, ec = Counter(begins), Counter(ends)
    for env in set(bc) | set(ec):
        if bc[env] != ec[env]:
            problems.append(f"ENV MISMATCH: \\begin{{{env}}} x{bc[env]} vs \\end{{{env}}} x{ec[env]}")

    depth = 0
    for i, ch in enumerate(text):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                line = text[:i].count("\n") + 1
                problems.append(f"UNMATCHED CLOSING BRACE at line {line}")
                depth = 0
    if depth != 0:
        problems.append(f"BRACE IMBALANCE at EOF: depth={depth}")

    labels = re.findall(r"\\label\{([^}]+)\}", text)
    label_counts = Counter(labels)
    for lbl, n in label_counts.items():
        if n > 1:
            problems.append(f"DUPLICATE LABEL: {lbl} defined {n} times")

    refs = re.findall(r"\\(?:ref|Cref|cref)\{([^}]+)\}", text)
    for r in refs:
        if r not in label_counts:
            problems.append(f"UNDEFINED REF: {r}")

    includes = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text)
    for inc in includes:
        p = PAPER_DIR / inc
        if not p.exists():
            problems.append(f"MISSING GRAPHIC: {inc} (looked in {p})")

    if problems:
        print(f"{len(problems)} PROBLEM(S) FOUND:")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    else:
        print(f"OK: {len(begins)} environments balanced, {len(labels)} unique labels, "
              f"{len(refs)} refs all resolve, {len(includes)} includegraphics all found.")


if __name__ == "__main__":
    check()
