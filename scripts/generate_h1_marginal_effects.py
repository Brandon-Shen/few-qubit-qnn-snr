"""Generate model-derived H1 marginal predictions and contrasts."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from patsy import build_design_matrices
from scipy.stats import norm

from qnn_snr.stats.factor_coding import H1_CENTERED_FORMULA, add_centered_factors
from qnn_snr.stats.models import build_h1_dataset, fit_mixed_model

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "h1_marginal_effects"
DEPTH_WEIGHTS = {1: 0.0625, 2: 0.1250, 3: 0.1875, 4: 0.2500, 6: 0.3750}
Z = norm.ppf(0.975)


def fmt(x: float) -> str:
    return f"{x:.6f}"


def main() -> None:
    if not np.isclose(sum(DEPTH_WEIGHTS.values()), 1.0):
        raise AssertionError("depth weights do not sum to one")
    exact = pd.read_parquet(ROOT / "results/production_confirmatory/raw/exact.parquet")
    data = add_centered_factors(build_h1_dataset(exact))
    fit = fit_mixed_model(H1_CENTERED_FORMULA, data, "a")
    if fit.error or not fit.converged:
        raise RuntimeError(f"adopted H1 fit failed: {fit.error}")
    result = fit.raw_result
    names = list(result.fe_params.index)
    beta = result.fe_params.to_numpy(float)
    cov = result.cov_params().loc[names, names].to_numpy(float)
    depth_z = data[["depth", "depth_z"]].drop_duplicates().set_index("depth")["depth_z"].to_dict()

    predictions, vectors = [], {}
    for L in (0, 1):
        for E in (0, 1):
            grid = pd.DataFrame([
                {"E": E, "L": L, "R": R, "depth": D, "depth_z": depth_z[D],
                 "weight": 0.5 * DEPTH_WEIGHTS[D]}
                for R in (0, 1) for D in DEPTH_WEIGHTS
            ])
            grid = add_centered_factors(grid)
            X = np.asarray(build_design_matrices([result.model.data.design_info], grid)[0], float)
            x = grid["weight"].to_numpy() @ X
            if list(result.model.exog_names) != names:
                raise AssertionError("fixed-effect design ordering mismatch")
            mu = float(x @ beta); se = float(np.sqrt(x @ cov @ x)); lo, hi = mu-Z*se, mu+Z*se
            key = f"E{E}_L{L}"; vectors[key] = x
            predictions.append({
                "E": E, "L": L,
                "objective": "Global infidelity" if L == 0 else "TFIM energy",
                "cnot_schedule": "Baseline" if E == 0 else "Pair-restricted",
                "mu_asinh": mu, "se_asinh": se, "ci_lo_asinh": lo, "ci_hi_asinh": hi,
                "sinh_adjusted_mean": float(np.sinh(mu)),
                "sinh_ci_lo": float(np.sinh(lo)), "sinh_ci_hi": float(np.sinh(hi)),
            })

    specs = [
        ("restricted_minus_baseline_L0", "Pair-restricted minus baseline at global infidelity",
         [(1, "E1_L0"), (-1, "E0_L0")]),
        ("restricted_minus_baseline_L1", "Pair-restricted minus baseline at TFIM energy",
         [(1, "E1_L1"), (-1, "E0_L1")]),
        ("difference_in_schedule_effects_H1", "Difference in schedule effects, H1",
         [(1, "E1_L1"), (-1, "E0_L1"), (-1, "E1_L0"), (1, "E0_L0")]),
    ]
    contrasts = []
    pred_by_key = {f"E{r['E']}_L{r['L']}": r for r in predictions}
    for cid, label, terms in specs:
        c = sum(sign * vectors[key] for sign, key in terms)
        est = float(c @ beta); se = float(np.sqrt(c @ cov @ c))
        # Difference(s) between sinh-transformed adjusted modeled locations.
        orig = sum(sign * np.sinh(float(vectors[key] @ beta)) for sign, key in terms)
        grad = sum(sign * np.cosh(float(vectors[key] @ beta)) * vectors[key] for sign, key in terms)
        orig_se = float(np.sqrt(grad @ cov @ grad))
        contrasts.append({
            "contrast_id": cid, "contrast": label,
            "estimate_asinh": est, "se_asinh": se, "ci_lo_asinh": est-Z*se, "ci_hi_asinh": est+Z*se,
            "difference_sinh_adjusted": float(orig), "delta_se": orig_se,
            "delta_ci_lo": float(orig-Z*orig_se), "delta_ci_hi": float(orig+Z*orig_se),
        })

    h1 = contrasts[-1]
    h1_name = "E_c:L_c"
    expected_est = float(result.fe_params[h1_name])
    expected_se = float(np.sqrt(result.cov_params().loc[h1_name, h1_name]))
    if not (np.isclose(h1["estimate_asinh"], expected_est, atol=1e-12) and
            np.isclose(h1["se_asinh"], expected_se, atol=1e-12)):
        raise AssertionError("marginal difference-in-differences does not reproduce centered H1")

    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(predictions).to_csv(OUT / "h1_marginal_effects.csv", index=False)
    pd.DataFrame(contrasts).to_csv(OUT / "h1_marginal_contrasts.csv", index=False)
    payload = {
        "model_formula": H1_CENTERED_FORMULA, "random_effects_for_predictions": 0,
        "residual_weights": {"0": 0.5, "1": 0.5}, "depth_weights": DEPTH_WEIGHTS,
        "predictions": predictions, "contrasts": contrasts,
        "h1_reproduction": {"coefficient": h1_name, "fit_estimate": expected_est,
                            "fit_se": expected_se, "absolute_estimate_error": abs(h1["estimate_asinh"]-expected_est),
                            "absolute_se_error": abs(h1["se_asinh"]-expected_se)},
    }
    (OUT / "h1_marginal_effects.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [r"\begin{table*}[t]", r"\centering", r"\small",
             r"\caption{Model-adjusted H1 marginal predictions and contrasts. Predictions average equally over residual status and use the adopted parameter/observation weights over $D=1,2,3,4,6$. Random effects are set to zero. Original-scale entries are $\sinh$ transforms of adjusted means on the $\operatorname{asinh}(|g_{\mathrm{exact}}|)$ scale and are not arithmetic means of raw gradient magnitudes. The difference in objective-specific schedule effects equals the adopted centered H1 estimand.}",
             r"\label{tab:h1-marginal-effects}", r"\begin{tabularx}{\textwidth}{@{}llXX@{}}", r"\toprule",
             r"\multicolumn{4}{l}{\textbf{Panel A---Adjusted marginal predictions}}\\",
             r"Objective & CNOT schedule & Adjusted $\operatorname{asinh}(|g_{\mathrm{exact}}|)$ (95\% CI) & $\sinh$ of adjusted mean (transformed 95\% CI)\\", r"\midrule"]
    for p in predictions:
        lines.append(f"{p['objective']} & {p['cnot_schedule']} & {fmt(p['mu_asinh'])} [{fmt(p['ci_lo_asinh'])}, {fmt(p['ci_hi_asinh'])}] & {fmt(p['sinh_adjusted_mean'])} [{fmt(p['sinh_ci_lo'])}, {fmt(p['sinh_ci_hi'])}]\\\\")
    lines += [r"\midrule", r"\multicolumn{4}{l}{\textbf{Panel B---Marginal contrasts}}\\",
              r"\multicolumn{2}{p{0.30\textwidth}}{Contrast} & Difference on asinh scale (95\% CI) & Difference between $\sinh$-transformed adjusted values (delta-method 95\% CI)\\", r"\midrule"]
    for c in contrasts:
        lines.append(f"\\multicolumn{{2}}{{p{{0.30\\textwidth}}}}{{{c['contrast']}}} & {fmt(c['estimate_asinh'])} [{fmt(c['ci_lo_asinh'])}, {fmt(c['ci_hi_asinh'])}] & {fmt(c['difference_sinh_adjusted'])} [{fmt(c['delta_ci_lo'])}, {fmt(c['delta_ci_hi'])}]\\\\")
    lines += [r"\bottomrule", r"\end{tabularx}", r"\end{table*}", ""]
    (OUT / "h1_marginal_effects_table.tex").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(payload["h1_reproduction"], indent=2))


if __name__ == "__main__":
    main()
