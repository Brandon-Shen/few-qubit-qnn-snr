"""Command-line interface (Section 21).

python -m qnn_snr validate --config configs/confirmatory.yaml
python -m qnn_snr generate-exact --config configs/confirmatory.yaml
python -m qnn_snr generate-shots --config configs/confirmatory.yaml --mode finite_shot_end_to_end
python -m qnn_snr aggregate --config configs/confirmatory.yaml
python -m qnn_snr fit --config configs/confirmatory.yaml
python -m qnn_snr bootstrap --config configs/confirmatory.yaml --iterations 2000
python -m qnn_snr report --config configs/confirmatory.yaml
python -m qnn_snr run-all --config configs/smoke.yaml
python -m qnn_snr pilot-replicates --config configs/confirmatory.yaml
python -m qnn_snr pilot-initializations --config configs/confirmatory.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from qnn_snr.budget import enumerate_jobs
from qnn_snr.config import ExperimentConfig, config_hash, load_config
from qnn_snr.figures import generate_all_figures
from qnn_snr.manifest import build_manifest, get_git_commit, now_iso, write_manifest
from qnn_snr.pilot import select_initialization_count, select_replicate_count
from qnn_snr.replicate import generate_exact_rows, generate_shot_rows
from qnn_snr.report import write_assumptions_snapshot, write_results_summary, write_statistical_methods
from qnn_snr.schema import read_tidy_dataset, write_tidy_dataset
from qnn_snr.stats.bootstrap import confirmatory_bootstrap_ci, run_h1_bootstrap, run_h2h4_bootstrap
from qnn_snr.stats.descriptive import configuration_summaries, physics_summary_rows, resource_accounting_table
from qnn_snr.stats.exploratory import build_exploratory_table
from qnn_snr.stats.holm import build_confirmatory_table
from qnn_snr.stats.interactions import compute_interaction_indices
from qnn_snr.stats.models import CONFIRMATORY_MODE, fit_h1_model, fit_h2h4_model, fit_sensitivity_model
from qnn_snr.stats.pointwise import pointwise_statistics, zero_variance_confirmatory_cells
from qnn_snr.validate import validate_dataset

SHOT_MODES = ("finite_shot_conditional", "finite_shot_end_to_end")


def _results_dir(cfg: ExperimentConfig) -> Path:
    return Path(cfg.output.results_dir)


def _raw_dir(cfg: ExperimentConfig) -> Path:
    return _results_dir(cfg) / "raw"


def _load_raw(cfg: ExperimentConfig) -> pd.DataFrame:
    parts = [read_tidy_dataset(p) for p in sorted(_raw_dir(cfg).glob("*.parquet"))]
    if not parts:
        print("No raw data found under results/raw -- run generate-exact/generate-shots first.", file=sys.stderr)
        sys.exit(1)
    return pd.concat(parts, ignore_index=True)


def _append_manifest_step(cfg: ExperimentConfig, step: str, **extra):
    path = _results_dir(cfg) / "run_manifest.json"
    if path.exists():
        manifest = json.loads(path.read_text(encoding="utf-8"))
    else:
        manifest = build_manifest(cfg, start_time=now_iso())
    manifest.setdefault("steps_run", []).append({"step": step, "time": now_iso(), **extra})
    manifest["end_time"] = now_iso()
    manifest["config_hash"] = config_hash(cfg)
    write_manifest(_results_dir(cfg), manifest)


def cmd_validate(args):
    cfg = load_config(args.config)
    df = _load_raw(cfg)
    report = validate_dataset(df, cfg)
    out_path = _results_dir(cfg) / "data_validation_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _append_manifest_step(cfg, "validate", passed=report["passed"], n_errors=len(report["errors"]))
    print(json.dumps({"passed": report["passed"], "errors": report["errors"][:20]}, indent=2))
    if not report["passed"]:
        sys.exit(1)


def cmd_generate_exact(args):
    cfg = load_config(args.config)
    out_path = _raw_dir(cfg) / "exact.parquet"
    if out_path.exists() and not args.overwrite:
        print(f"{out_path} already exists; pass --overwrite to regenerate (resume support).")
        return
    n_cells = len(cfg.circuit.depths) * cfg.design.n_initializations * len(cfg.design.configurations)
    print(f"Estimated exact-mode rows: ~{n_cells * cfg.task.n_qubits * 3} "
          f"({n_cells} (depth,init,config) cells, up to {cfg.task.n_qubits} params/block)")
    rows = generate_exact_rows(cfg, git_commit=get_git_commit())
    write_tidy_dataset(rows, out_path)
    _append_manifest_step(cfg, "generate-exact", n_rows=len(rows))
    print(f"wrote {len(rows)} rows to {out_path}")


def cmd_generate_shots(args):
    cfg = load_config(args.config)
    out_path = _raw_dir(cfg) / f"{args.mode}.parquet"
    if out_path.exists() and not args.overwrite:
        print(f"{out_path} already exists; pass --overwrite to regenerate (resume support).")
        return
    n_replicates = (len(cfg.circuit.depths) * cfg.design.n_initializations * len(cfg.design.configurations)
                     * len(cfg.budget.values) * cfg.design.replicates)
    print(f"Estimated finite-shot replicate computations: {n_replicates} "
          f"(mode={args.mode}; each computation runs O(depth) block re-evaluations)")
    rows = generate_shot_rows(cfg, args.mode, git_commit=get_git_commit())
    write_tidy_dataset(rows, out_path)
    _append_manifest_step(cfg, f"generate-shots:{args.mode}", n_rows=len(rows))
    print(f"wrote {len(rows)} rows to {out_path}")


def cmd_aggregate(args):
    cfg = load_config(args.config)
    df = _load_raw(cfg)
    shot_df = df[df["analysis_mode"].isin(SHOT_MODES)]
    pw = pointwise_statistics(shot_df, bootstrap_iterations=args.pointwise_bootstrap_iterations)
    out_path = _results_dir(cfg) / "pointwise_gradient_statistics.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pw.to_parquet(out_path, index=False)
    _append_manifest_step(cfg, "aggregate", n_cells=len(pw))
    print(f"wrote {len(pw)} pointwise cells to {out_path}")


def cmd_fit(args):
    cfg = load_config(args.config)
    mode = getattr(args, "mode", CONFIRMATORY_MODE)
    is_confirmatory = mode == CONFIRMATORY_MODE
    df = _load_raw(cfg)
    exact_df = df[df["analysis_mode"] == "statevector_exact"]
    pw_path = _results_dir(cfg) / "pointwise_gradient_statistics.parquet"
    pw_all = pd.read_parquet(pw_path) if pw_path.exists() else pointwise_statistics(df[df["analysis_mode"].isin(SHOT_MODES)])
    pw = pw_all[pw_all["analysis_mode"] == mode]  # single-mode slice -- fit_h2h4_model refuses mixed-mode input

    zero_var = zero_variance_confirmatory_cells(pw)
    if len(zero_var) > 0:
        print(f"WARNING: {len(zero_var)} {mode} cells have exactly zero replicate "
              f"variance (Section 9) -- see pointwise_gradient_statistics.parquet's zero_variance_flag "
              f"column; no variance-floor policy is prespecified, so these cells are flagged but the "
              f"model still fits on the remaining finite-SNR cells.", file=sys.stderr)

    h2h4 = fit_h2h4_model(pw)
    fit_sensitivity_model(pw)  # sensitivity model run for completeness; not part of confirmatory outputs

    results_dir = _results_dir(cfg)
    results_dir.mkdir(parents=True, exist_ok=True)

    if not is_confirmatory:
        # Diagnostic-mode fit (e.g. finite_shot_conditional). Per the paper's Methods,
        # only CONFIRMATORY_MODE is confirmatory -- this path never touches the
        # confirmatory_hypotheses.csv/holm_adjustment.csv/snr_model_coefficients.csv
        # files so a diagnostic run can never silently overwrite the confirmatory record.
        print(f"NOTE: --mode={mode!r} is a diagnostic fit, not the confirmatory analysis "
              f"(confirmatory mode is {CONFIRMATORY_MODE!r}). Writing to "
              f"snr_model_coefficients_diagnostic_{mode}.csv only -- no confirmatory files "
              f"touched. See verification/conditional_vs_endtoend_comparison.md.", file=sys.stderr)
        pd.DataFrame([{"coefficient": k, "estimate": v, "se": h2h4.bse.get(k, float("nan"))}
                      for k, v in h2h4.params.items()]).to_csv(
            results_dir / f"snr_model_coefficients_diagnostic_{mode}.csv", index=False)
        _append_manifest_step(cfg, f"fit-diagnostic:{mode}", h2h4_converged=h2h4.converged,
                               n_zero_variance_cells=len(zero_var))
        print(f"diagnostic {mode} SNR-model coefficients written to "
              f"snr_model_coefficients_diagnostic_{mode}.csv")
        return

    h1 = fit_h1_model(exact_df)
    pd.DataFrame([{"coefficient": k, "estimate": v, "se": h1.bse.get(k, float("nan"))}
                  for k, v in h1.params.items()]).to_csv(results_dir / "exact_model_coefficients.csv", index=False)
    pd.DataFrame([{"coefficient": k, "estimate": v, "se": h2h4.bse.get(k, float("nan"))}
                  for k, v in h2h4.params.items()]).to_csv(results_dir / "snr_model_coefficients.csv", index=False)

    confirmatory = build_confirmatory_table(h1, h2h4, alpha=cfg.stats.alpha_family_wise)
    confirmatory.to_csv(results_dir / "confirmatory_hypotheses.csv", index=False)
    confirmatory[["hypothesis", "coefficient_label", "p_unadjusted", "p_holm", "reject_after_holm",
                  "family_wise_alpha"]].to_csv(results_dir / "holm_adjustment.csv", index=False)

    _append_manifest_step(cfg, "fit", h1_converged=h1.converged, h2h4_converged=h2h4.converged,
                           n_zero_variance_cells=len(zero_var))
    print(confirmatory[["hypothesis", "coefficient_label", "estimate", "p_unadjusted", "p_holm",
                         "reject_after_holm"]].to_string(index=False))


def cmd_bootstrap(args):
    cfg = load_config(args.config)
    n_iter = args.iterations or cfg.bootstrap_iterations()
    df = _load_raw(cfg)
    exact_df = df[df["analysis_mode"] == "statevector_exact"]
    shot_df = df[df["analysis_mode"] == CONFIRMATORY_MODE]  # confirmatory bootstrap: end-to-end mode only
    results_dir = _results_dir(cfg)

    h1_boot = run_h1_bootstrap(exact_df, n_iter, cfg.stats.bootstrap.seed, cfg.stats.bootstrap.min_success_fraction,
                                checkpoint_path=results_dir / "_checkpoints" / "h1_boot.parquet")
    h2h4_boot = run_h2h4_bootstrap(shot_df, n_iter, cfg.stats.bootstrap.seed + 1,
                                    cfg.stats.bootstrap.min_success_fraction,
                                    checkpoint_path=results_dir / "_checkpoints" / "h2h4_boot.parquet")

    combined = pd.concat([
        h1_boot.coefficients.assign(hypothesis_family="exact_signal") if not h1_boot.coefficients.empty else pd.DataFrame(),
        h2h4_boot.coefficients.assign(hypothesis_family="estimator_snr") if not h2h4_boot.coefficients.empty else pd.DataFrame(),
    ], ignore_index=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(results_dir / "bootstrap_coefficients.parquet", index=False)

    diagnostics = {
        "h1": {"n_requested": h1_boot.n_requested, "n_successful": h1_boot.n_successful,
               "success_fraction_met": h1_boot.success_fraction_met, "failed_iterations": h1_boot.failed_iterations},
        "h2h4": {"n_requested": h2h4_boot.n_requested, "n_successful": h2h4_boot.n_successful,
                 "success_fraction_met": h2h4_boot.success_fraction_met, "failed_iterations": h2h4_boot.failed_iterations},
    }
    (results_dir / "bootstrap_diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")

    ci = confirmatory_bootstrap_ci(h1_boot, h2h4_boot)
    conf_path = results_dir / "confirmatory_hypotheses.csv"
    if conf_path.exists():
        conf = pd.read_csv(conf_path)
        for hyp, (lo, hi) in ci.items():
            conf.loc[conf["hypothesis"] == hyp, "bootstrap_ci_lo"] = lo
            conf.loc[conf["hypothesis"] == hyp, "bootstrap_ci_hi"] = hi
        conf.to_csv(conf_path, index=False)

    _append_manifest_step(cfg, "bootstrap", iterations=n_iter, diagnostics=diagnostics)
    if not h1_boot.success_fraction_met or not h2h4_boot.success_fraction_met:
        print("WARNING: bootstrap min_success_fraction not met; see bootstrap_diagnostics.json", file=sys.stderr)
    print(json.dumps(diagnostics, indent=2))


def cmd_report(args):
    cfg = load_config(args.config)
    results_dir = _results_dir(cfg)
    df = _load_raw(cfg)
    exact_df = df[df["analysis_mode"] == "statevector_exact"]
    shot_df = df[df["analysis_mode"].isin(SHOT_MODES)]
    pw_path = results_dir / "pointwise_gradient_statistics.parquet"
    pw = pd.read_parquet(pw_path) if pw_path.exists() else pointwise_statistics(shot_df)

    physics_df = pd.DataFrame(physics_summary_rows(cfg))
    resource_table = resource_accounting_table(shot_df)
    summaries = configuration_summaries(pw, exact_df, physics_df, resource_table)
    summaries.to_csv(results_dir / "configuration_summaries.csv", index=False)
    resource_table.to_csv(results_dir / "resource_accounting.csv", index=False)

    interactions = compute_interaction_indices(pw, exact_df)
    interactions.to_csv(results_dir / "interaction_indices.csv", index=False)

    h2h4 = fit_h2h4_model(pw[pw["analysis_mode"] == CONFIRMATORY_MODE])
    conf_path = results_dir / "confirmatory_hypotheses.csv"
    if conf_path.exists():
        confirmatory = pd.read_csv(conf_path)
    else:
        h1 = fit_h1_model(exact_df)
        confirmatory = build_confirmatory_table(h1, h2h4, alpha=cfg.stats.alpha_family_wise)
        confirmatory.to_csv(conf_path, index=False)

    exploratory = build_exploratory_table(h2h4, summaries)
    exploratory.to_csv(results_dir / "exploratory_results.csv", index=False)

    write_assumptions_snapshot(results_dir)
    write_statistical_methods(results_dir)
    write_results_summary(results_dir, confirmatory, interactions, summaries, exploratory, cfg)

    bootstrap_path = results_dir / "bootstrap_coefficients.parquet"
    bootstrap_df = pd.read_parquet(bootstrap_path) if bootstrap_path.exists() else None

    generate_all_figures(results_dir / "figures", confirmatory_table=confirmatory, pointwise_df=pw,
                          exact_df=exact_df, configuration_summaries=summaries, resource_table=resource_table,
                          bootstrap_coef_df=bootstrap_df, physics_df=physics_df)
    _append_manifest_step(cfg, "report")
    print(f"report written to {results_dir}")


def cmd_run_all(args):
    cfg = load_config(args.config)
    manifest = build_manifest(cfg, start_time=now_iso())
    write_manifest(_results_dir(cfg), manifest)

    cmd_generate_exact(args)
    for mode in cfg.gradient.modes:
        if mode in SHOT_MODES:
            shot_args = argparse.Namespace(config=args.config, mode=mode, overwrite=args.overwrite)
            cmd_generate_shots(shot_args)

    validate_args = argparse.Namespace(config=args.config)
    cmd_validate(validate_args)

    agg_args = argparse.Namespace(config=args.config, pointwise_bootstrap_iterations=args.pointwise_bootstrap_iterations)
    cmd_aggregate(agg_args)

    fit_args = argparse.Namespace(config=args.config)
    cmd_fit(fit_args)

    boot_args = argparse.Namespace(config=args.config, iterations=args.iterations)
    cmd_bootstrap(boot_args)

    report_args = argparse.Namespace(config=args.config)
    cmd_report(report_args)


def cmd_pilot_replicates(args):
    cfg = load_config(args.config)
    out = select_replicate_count(cfg, mode=args.mode)
    results_dir = _results_dir(cfg)
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "pilot_replicate_selection.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"selected_R_overall": out["selected_R_overall"]}, indent=2))


def cmd_pilot_initializations(args):
    cfg = load_config(args.config)
    df = _load_raw(cfg)
    shot_df = df[df["analysis_mode"] == CONFIRMATORY_MODE]
    pw = pointwise_statistics(shot_df, bootstrap_iterations=100)
    h2h4 = fit_h2h4_model(pw)
    out = select_initialization_count(cfg, None, h2h4)
    results_dir = _results_dir(cfg)
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "pilot_initialization_selection.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"selected_n": out["selected_n"]}, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m qnn_snr")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_config_arg(p):
        p.add_argument("--config", required=True)

    p = sub.add_parser("validate"); add_config_arg(p); p.set_defaults(func=cmd_validate)

    p = sub.add_parser("generate-exact"); add_config_arg(p)
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(func=cmd_generate_exact)

    p = sub.add_parser("generate-shots"); add_config_arg(p)
    p.add_argument("--mode", required=True, choices=SHOT_MODES)
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(func=cmd_generate_shots)

    p = sub.add_parser("aggregate"); add_config_arg(p)
    p.add_argument("--pointwise-bootstrap-iterations", dest="pointwise_bootstrap_iterations", type=int, default=500)
    p.set_defaults(func=cmd_aggregate)

    p = sub.add_parser("fit"); add_config_arg(p)
    p.add_argument("--mode", default=CONFIRMATORY_MODE, choices=SHOT_MODES,
                    help="analysis_mode to fit the H2-H4 model on. Default is the confirmatory "
                         "mode (finite_shot_end_to_end); finite_shot_conditional produces a "
                         "separate, explicitly-labeled diagnostic-only output.")
    p.set_defaults(func=cmd_fit)

    p = sub.add_parser("bootstrap"); add_config_arg(p)
    p.add_argument("--iterations", type=int, default=None)
    p.set_defaults(func=cmd_bootstrap)

    p = sub.add_parser("report"); add_config_arg(p); p.set_defaults(func=cmd_report)

    p = sub.add_parser("run-all"); add_config_arg(p)
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--iterations", type=int, default=None)
    p.add_argument("--pointwise-bootstrap-iterations", dest="pointwise_bootstrap_iterations", type=int, default=200)
    p.set_defaults(func=cmd_run_all)

    p = sub.add_parser("pilot-replicates"); add_config_arg(p)
    p.add_argument("--mode", default="finite_shot_end_to_end", choices=SHOT_MODES)
    p.set_defaults(func=cmd_pilot_replicates)

    p = sub.add_parser("pilot-initializations"); add_config_arg(p)
    p.set_defaults(func=cmd_pilot_initializations)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
