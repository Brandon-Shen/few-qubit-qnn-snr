"""Freeze report/provenance for the completed H1 depth/weighting run."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from qnn_snr.stats.h1_depth_weighting import DEPTHS, sha256

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/h1_depth_weighting"
VERIFY = ROOT / "verification"
PLAN_COMMIT = "d528566acb2488380b5efd42d91b9e81fc739aaf"
IMPLEMENTATION_COMMIT = "d9a5ce0e499ebc74bb352c969dc50a61246ade6c"
MATERIALITY_SE = 0.0010812660


def read(label: str, name: str) -> pd.DataFrame:
    return pd.read_csv(BASE / label / name)


def row_dict(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.to_json(orient="records"))


def main() -> None:
    original = read("original", "depth_contrasts.csv")
    seed = read("independent_seed", "depth_contrasts.csv")
    ow = read("original", "weighted_summaries.csv")
    sw = read("independent_seed", "weighted_summaries.csv")
    depth_diff = read("comparison", "depth_comparisons.csv")
    weighted_diff = read("comparison", "weighted_comparisons.csv")
    pooled = read("comparison", "adopted_pooled.csv")
    pooled_diff = read("comparison", "adopted_pooled_difference.csv")
    om = json.loads((BASE / "original/moderation_tests.json").read_text())
    sm = json.loads((BASE / "independent_seed/moderation_tests.json").read_text())

    positive_both = int(((original.estimate > 0) & (seed.estimate > 0)).sum())
    depth_class = "retained at all depths" if positive_both == 5 else (
        "retained at most depths" if positive_both >= 3 else ("mixed depth pattern" if positive_both >= 1 else "not retained"))
    ranges = {"original": float(ow.estimate.max()-ow.estimate.min()),
              "independent_seed": float(sw.estimate.max()-sw.estimate.min())}
    all_weight_signs_positive = bool((ow.estimate > 0).all() and (sw.estimate > 0).all())
    weighting_class = ("direction changes under weighting" if not all_weight_signs_positive else
                        "same direction but magnitude weighting-sensitive" if max(ranges.values()) > MATERIALITY_SE else
                        "materially insensitive to weighting")
    fractions = depth_diff.set_index("depth").absolute_contribution_fraction
    max_depth = int(fractions.idxmax())
    shallow_fraction = float(fractions.loc[[1, 2]].sum())
    localization = (f"difference concentrated at D={max_depth}" if fractions.max() >= .5 else
                    "difference concentrated at shallow depths D=1-2" if shallow_fraction >= .6 else
                    "no clear localization")
    obs_orig = ow.set_index("estimand").loc["observation_weighted"]
    obs_seed = sw.set_index("estimand").loc["observation_weighted"]
    equal_orig = ow.set_index("estimand").loc["equal_depth"]
    equal_seed = sw.set_index("estimand").loc["equal_depth"]
    parameter_identical = bool(np.allclose(
        ow.query("estimand == 'observation_weighted'").filter(like="weight_").to_numpy(),
        ow.query("estimand == 'parameter_weighted'").filter(like="weight_").to_numpy(), atol=0, rtol=0))
    pooled_matches_obs = {
        "original": bool(np.isclose(pooled.query("dataset=='original'").estimate.iloc[0], obs_orig.estimate, atol=1e-14)),
        "independent_seed": bool(np.isclose(pooled.query("dataset=='independent_seed'").estimate.iloc[0], obs_seed.estimate, atol=1e-14)),
    }
    result = {
        "status": "completed post-primary exploratory/robustness analysis",
        "plan_commit": PLAN_COMMIT, "implementation_commit": IMPLEMENTATION_COMMIT,
        "results_freeze_commit": None, "provenance_commit": None,
        "depth_specific": {"original": row_dict(original), "independent_seed": row_dict(seed)},
        "weighted": {"original": row_dict(ow), "independent_seed": row_dict(sw)},
        "comparisons": {"depth": row_dict(depth_diff), "weighted": row_dict(weighted_diff),
                        "adopted_pooled": row_dict(pooled_diff)},
        "moderation": {"original": om, "independent_seed": sm},
        "classifications": {"positive_direction_retained_in_both_n_depths": positive_both,
                            "depth_direction": depth_class, "weighting": weighting_class,
                            "weighting_ranges": ranges, "localization": localization,
                            "largest_absolute_contribution_depth": max_depth,
                            "largest_absolute_contribution_fraction": float(fractions.max()),
                            "shallow_D1_D2_absolute_contribution_fraction": shallow_fraction,
                            "frozen_overall": "direction retained but magnitude uncertain"},
        "weight_identity": {"observation_equals_parameter": parameter_identical,
                            "weights": {str(d): float(x) for d, x in zip(DEPTHS, [.0625,.125,.1875,.25,.375])}},
        "pooled_relation": {"point_estimate_equals_observation_weighted": pooled_matches_obs,
                            "note": "Point estimates coincide in this balanced design; SEs differ slightly because the categorical and adopted pooled models estimate different fixed-effect/covariance structures."},
        "recommended_manuscript_language": [
            "In a post-primary categorical-depth robustness analysis, the centered E×L interaction was positive in both seed datasets at D=3, 4, and 6, whereas the original estimates at D=1 and D=2 were negative and imprecise and the independent-seed estimates were positive and imprecise.",
            "Equal-depth averaging reduced the interaction relative to observation/parameter weighting in both datasets, but did not change its point-estimate sign; observation and matched-parameter weights were identical because row counts were balanced apart from the planned depth-dependent parameter count.",
            "The seed-minus-original difference was largest and distinguishable from zero at D=6, but under the prospectively frozen contribution rule the pooled magnitude difference had no clear single-depth or shallow-depth localization.",
            "Model-based inference detected depth moderation in the original dataset but the initialization-clustered robust test did not; neither test detected moderation in the independent-seed dataset, so moderation evidence was covariance-sensitive.",
            "These post-primary results retain the overall description 'direction retained but magnitude uncertain,' while adding that depthwise direction agreed at three of five depths and magnitude was weighting-sensitive."
        ],
        "caveats": ["Depth contrasts and weighted summaries are post-primary exploratory results.",
                    "Wald intervals are unadjusted; Holm-adjusted p-values are supplied separately within each dataset.",
                    "The original model-based and cluster-robust moderation tests disagree.",
                    "No equivalence claim is made from a difference interval containing zero."],
    }
    (VERIFY / "h1_depth_weighting_results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    def depth_lines(frame):
        return "\n".join(f"- D={int(r.depth)}: {r.estimate:.6f} (SE {r.se:.6f}; 95% CI [{r.ci_lo:.6f}, {r.ci_hi:.6f}]; raw p={r.p_raw:.4g}; within-dataset Holm p={r.p_holm_within_dataset:.4g})" for r in frame.itertuples())
    report = f"""# H1 depth heterogeneity and weighting results

**Status:** completed post-primary exploratory/robustness analysis under plan `{PLAN_COMMIT}`. The raw datasets were fit separately. These results are not part of, and do not alter, the original H1--H4 Holm family.

## Depth-specific centered E×L contrasts

Original data:

{depth_lines(original)}

Independent-seed data:

{depth_lines(seed)}

The point-estimate direction is positive in both datasets at 3 of 5 depths (D=3, 4, and 6), giving the frozen category **{depth_class}**. At D=1 and D=2, the original point estimates are negative and imprecise while the independent-seed estimates are positive and imprecise. Thus “direction retained at all depths” is not justified.

## Weighting and adopted pooled estimands

- Original equal-depth: {equal_orig.estimate:.6f} (95% CI [{equal_orig.ci_lo:.6f}, {equal_orig.ci_hi:.6f}]).
- Independent-seed equal-depth: {equal_seed.estimate:.6f} (95% CI [{equal_seed.ci_lo:.6f}, {equal_seed.ci_hi:.6f}]).
- Original observation/parameter weighted: {obs_orig.estimate:.6f} (95% CI [{obs_orig.ci_lo:.6f}, {obs_orig.ci_hi:.6f}]).
- Independent-seed observation/parameter weighted: {obs_seed.estimate:.6f} (95% CI [{obs_seed.ci_lo:.6f}, {obs_seed.ci_hi:.6f}]).
- Frozen adopted pooled: original {pooled.query("dataset=='original'").estimate.iloc[0]:.6f}; independent seed {pooled.query("dataset=='independent_seed'").estimate.iloc[0]:.6f}.

Observation and matched-parameter weights are identical: `(0.0625, 0.125, 0.1875, 0.25, 0.375)` for D=1/2/3/4/6. The categorical observation-weighted point estimates equal the adopted pooled estimates to numerical precision in this balanced design. Their SEs differ slightly because the categorical and adopted pooled models estimate different fixed-effect/covariance structures. Relative to the frozen materiality unit of one original-H1 SE, both datasets are **{weighting_class}**; no weighting changes the point-estimate sign.

## Original-versus-independent-seed differences

The equal-depth difference is {weighted_diff.query("estimand=='equal_depth'").difference_seed_minus_original.iloc[0]:.6f} (95% CI [{weighted_diff.query("estimand=='equal_depth'").difference_ci_lo.iloc[0]:.6f}, {weighted_diff.query("estimand=='equal_depth'").difference_ci_hi.iloc[0]:.6f}]). The observation/parameter-weighted difference is {weighted_diff.query("estimand=='observation_weighted'").difference_seed_minus_original.iloc[0]:.6f} (95% CI [{weighted_diff.query("estimand=='observation_weighted'").difference_ci_lo.iloc[0]:.6f}, {weighted_diff.query("estimand=='observation_weighted'").difference_ci_hi.iloc[0]:.6f}]). The frozen adopted-pooled difference is {pooled_diff.difference_seed_minus_original.iloc[0]:.6f} (95% CI [{pooled_diff.difference_ci_lo.iloc[0]:.6f}, {pooled_diff.difference_ci_hi.iloc[0]:.6f}]).

D=6 supplies the largest absolute observation-weighted contribution ({fractions.loc[6]:.1%}) and its difference interval excludes zero, but it does not reach the frozen 50% single-depth threshold; D=1--2 together supply only {shallow_fraction:.1%}. The frozen localization result is therefore **{localization}**.

## Moderation tests

- Original: mixed-model Wald χ²(4)={om['mixed_model']['statistic']:.3f}, p={om['mixed_model']['p_value']:.4g}; initialization-clustered robust χ²(4)={om['cluster_robust_ols']['statistic']:.3f}, p={om['cluster_robust_ols']['p_value']:.4g}.
- Independent seed: mixed-model Wald χ²(4)={sm['mixed_model']['statistic']:.3f}, p={sm['mixed_model']['p_value']:.4g}; initialization-clustered robust χ²(4)={sm['cluster_robust_ols']['statistic']:.3f}, p={sm['cluster_robust_ols']['p_value']:.4g}.

Mixed-model and robust point contrasts agree to machine precision, but their covariance-based moderation conclusions disagree for the original dataset. Both fail to reject moderation homogeneity for the independent-seed dataset. Evidence for original-data moderation is therefore covariance-sensitive.

## Frozen interpretation

The overall classification **direction retained but magnitude uncertain** remains appropriate. A more precise restrained description is: **the pooled positive direction is retained, depthwise positive direction agrees at three of five depths, magnitude is weighting-sensitive, and the cross-seed magnitude difference has no clear localization under the prospectively frozen rule**.

## Exact recommended future manuscript language

1. “In a post-primary categorical-depth robustness analysis, the centered E×L interaction was positive in both seed datasets at D=3, 4, and 6, whereas the original estimates at D=1 and D=2 were negative and imprecise and the independent-seed estimates were positive and imprecise.”
2. “Equal-depth averaging reduced the interaction relative to observation/parameter weighting in both datasets, but did not change its point-estimate sign; observation and matched-parameter weights were identical because row counts were balanced apart from the planned depth-dependent parameter count.”
3. “The seed-minus-original difference was largest and distinguishable from zero at D=6, but under the prospectively frozen contribution rule the pooled magnitude difference had no clear single-depth or shallow-depth localization.”
4. “Model-based inference detected depth moderation in the original dataset but the initialization-clustered robust test did not; neither test detected moderation in the independent-seed dataset, so moderation evidence was covariance-sensitive.”
5. “These post-primary results retain the overall description ‘direction retained but magnitude uncertain,’ while adding that depthwise direction agreed at three of five depths and magnitude was weighting-sensitive.”

No manuscript file was edited. Machine-readable contrasts, covariance matrices, comparisons, validation, figures, and caveats are under `results/h1_depth_weighting/`.
"""
    (VERIFY / "h1_depth_weighting_results.md").write_text(report, encoding="utf-8")

    files = sorted(p for p in BASE.rglob("*") if p.is_file() and p.name != "artifact_checksums.json")
    checksums = {str(p.relative_to(ROOT)).replace("\\", "/"): sha256(p) for p in files}
    (BASE / "comparison/artifact_checksums.json").write_text(json.dumps(checksums, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
