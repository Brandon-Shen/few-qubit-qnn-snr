# Referenced-figure font audit

Status: **pass for all referenced figure PDFs**. Poppler 25.07.0 `pdffonts` reports no `Type 3` row after regeneration.

The TeX sources reference six unique vector PDFs. All are Matplotlib outputs. `paper/scripts/plot_style.py` is the shared style module for Figures 0 and 1; Figures 12 and 16 have self-contained renderers; Figures 13 and 14 use the existing `figures()` renderer in `scripts/run_h1_depth_weighting.py` with already-frozen CSV sources. No renderer reads `results/superseded/` or `results/superseded_pooled/`.

| Figure path | Generator | Command | Before fonts | After fonts | Type 3 after | SHA-256 before | SHA-256 after |
|---|---|---|---|---|---|---|---|
| `paper/figures/fig16_architecture.pdf` | `paper/scripts/make_fig16_architecture.py` | `python paper/scripts/make_fig16_architecture.py` | CID TrueType | CID TrueType | No | `a46d8068dc0ee220ed5fd2c12692d1731aa1cb447523aff51283a12b4aa24e55` | `a46d8068dc0ee220ed5fd2c12692d1731aa1cb447523aff51283a12b4aa24e55` |
| `paper/figures/fig13_h1_depth.pdf` | `scripts/run_h1_depth_weighting.py::figures` | render-only Python invocation recorded below | Type 3 | CID TrueType | No | `8403f4d3d6b18a3f91c249f0a5eed44988eb4a0fc466852fdc8d85c4287998a0` | `a2153cba375dec7cb013cdf0abb93e0c8f51e4e68f7608dc8f55451214f6a769` |
| `paper/figures/fig14_h1_weighting.pdf` | `scripts/run_h1_depth_weighting.py::figures` | render-only Python invocation recorded below | Type 3 | CID TrueType | No | `40c590a409909a740cd085fdaf258bdc58862c59c39312d99384b1f2e1aeb5e3` | `3bce90e577750449e092d17085b90485f6b7138a440a5a14dd94057364ece675` |
| `paper/figures/fig0_el_primary.pdf` | `paper/scripts/make_fig0_el_primary.py` | `python paper/scripts/make_fig0_el_primary.py` | CID TrueType | CID TrueType | No | `05007ea46bfdb20d83abce3d1d579187b519c82e551738b1eada45b1df63180a` | `929faf1642a7234f7cb16a59352711585a68e965172589bf1ddf37c1ba1aade7` |
| `paper/figures/fig1_confirmatory_forest.pdf` | `paper/scripts/make_fig1_forest.py` | `python paper/scripts/make_fig1_forest.py` | CID TrueType | CID TrueType | No | `f7042e8b4d19c236f677376d1015d738dafae62e11537ee80519c432e58d6b59` | `ba3136b6fa0e16d6ba4daf70278ff1534edb617bc24503b721451b26ee2d0fef` |
| `paper/figures/fig12_j_conditional.pdf` | `paper/scripts/make_fig12_j_conditional.py` | `python paper/scripts/make_fig12_j_conditional.py` | Type 3 | CID TrueType | No | `5fe0ee6ae54dffde5de673523431506841c12b5fc6bf7f6255dabc3940c06341` | `0ceb356621295ddc601e76f384c60fa5ccae7dac0f950adca02b8e52067f8351` |

Render-only invocation for Figures 13 and 14:

```text
from pathlib import Path
import pandas as pd
from scripts.run_h1_depth_weighting import figures
comp = Path('results/h1_depth_weighting/comparison')
figures(pd.read_csv(comp/'figure_a_depth_source.csv'),
        pd.read_csv(comp/'figure_b_weighting_source.csv'), comp)
```

The resulting `figure_a_depth.pdf` and `figure_b_weighting.pdf` were copied to the manuscript's deterministic filenames `fig13_h1_depth.pdf` and `fig14_h1_weighting.pdf`.

## Content and dimension checks

- `pdfinfo` reports identical before/after page counts and page sizes for all six PDFs.
- Normalized `pdftotext -layout` content is identical before/after for every figure. Figures 13 and 14 differ only in whitespace placement in raw extraction, caused by the change from Type 3 glyphs to Unicode-mapped CID TrueType fonts.
- The frozen Figure 0 source checksum remains `d0db4812d881108a7d5d03705ccb2ee8a9fab5bab71f1fc05546a968dba0797d`; its independent recomputation still gives `I=1.0340744657849426` and `J=1.2417603765323095`.
- Visual inspection of all six regenerated previews found no missing glyph, clipping, hidden datum, changed label, changed mathematical notation, altered axis/limit, rasterization, or loss of grayscale distinguishability.
- The backed-up input PDFs are under `verification/figure_font_audit/before/`; `before_checksums.sha256` records their hashes.

## Final article PDFs

Not rebuilt or rechecked in this task, per the user's follow-up instruction that TeX compilation was unnecessary. Existing PDFs under `paper/output/` predate this figure replacement and must not be described as rebuilt artifacts.
