"""Versioned experiment configuration: schema, defaults, and hashing.

Every unresolved architectural choice named in ASSUMPTIONS.md is a field
here with a documented default, so a run's exact assumption set is fully
determined by (this schema, the YAML file, config_hash).
"""
from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

# The 8 mandatory factorial configurations (Section 2). Order is fixed and
# used everywhere as the canonical configuration_id -> (E, L, R) mapping.
CONFIGURATION_TABLE: dict[int, tuple[int, int, int]] = {
    1: (0, 0, 0),
    2: (1, 0, 0),
    3: (0, 1, 0),
    4: (0, 0, 1),
    5: (1, 1, 0),
    6: (1, 0, 1),
    7: (0, 1, 1),
    8: (1, 1, 1),
}

BASELINE_SCHEDULE = [(0, 1), (1, 2), (2, 3), (3, 0)]
RESTRICTED_ODD_SCHEDULE = [(0, 1), (2, 3), (1, 0), (3, 2)]
RESTRICTED_EVEN_SCHEDULE = [(1, 2), (3, 0), (2, 1), (0, 3)]


def _default_seed_streams() -> dict[str, int]:
    return {"initialization": 1, "shot_sampling": 2, "optimization": 3, "bootstrap": 4}


def _default_representative_cells() -> list[dict[str, int]]:
    cells = []
    for config_id in (1, 8):
        for depth in (1, 6):
            for budget in (250, 2000):
                cells.append({"configuration_id": config_id, "depth": depth, "budget": budget})
    return cells


@dataclass
class TaskConfig:
    n_qubits: int = 4
    J: float = 1.0
    h: float = 0.5
    expected_E0: float = -3.4270
    expected_Emax: float = 3.4270
    spectrum_tol: float = 5e-3


@dataclass
class CircuitConfig:
    depths: list[int] = field(default_factory=lambda: [1, 2, 3, 4, 6])
    init_low: float = 0.0
    init_high: float = 2 * math.pi


@dataclass
class CostMapping:
    L0: str = "global"
    L1: str = "local"


@dataclass
class ResidualConfig:
    gamma_R0: float = 0.0
    gamma_R1: float = 1.0
    blocks_per_depth: str = "one_per_layer"  # A3
    x0_init: str = "zeros"  # A4
    hidden_dim: str = "n_qubits"  # A5 ("n_qubits" or an int)
    weight_init: str = "glorot_uniform"  # A5
    bias_init: str = "zeros"  # A5
    gamma_sensitivity_values: list[float] = field(default_factory=lambda: [0.5, 1.0])  # exploratory, A6


@dataclass
class GradientConfig:
    modes: list[str] = field(
        default_factory=lambda: [
            "statevector_exact",
            "finite_shot_conditional",
            "finite_shot_end_to_end",
        ]
    )
    hardware_noisy_enabled: bool = False  # A11
    hardware_noisy_kind: str = "depolarizing"


@dataclass
class BudgetConfig:
    values: list[int] = field(default_factory=lambda: [250, 500, 1000, 2000])
    allocator: str = "equal_deterministic_remainder"  # A8
    remainder_policy: str = "deterministic_sorted"  # A8
    sensitivity_allocator: str = "pilot_variance_optimized"


@dataclass
class ReplicatePilotConfig:
    start_R: int = 30
    increment: int = 10
    max_R: int = 200
    abs_halfwidth_tolerance: float = 0.05
    rel_halfwidth_tolerance: float = 0.10
    representative_cells: list[dict[str, int]] = field(default_factory=_default_representative_cells)  # A12


@dataclass
class InitializationPilotConfig:
    start_n: int = 50
    increment: int = 25
    max_n: int = 300
    target_percentile: float = 90.0
    target_halfwidth: float = 0.20


@dataclass
class PilotConfig:
    replicate_count: ReplicatePilotConfig = field(default_factory=ReplicatePilotConfig)
    initialization_count: InitializationPilotConfig = field(default_factory=InitializationPilotConfig)


@dataclass
class BootstrapConfig:
    iterations_dev: int = 200
    iterations_publication: int = 2000
    iterations: int | None = None  # if set, overrides dev/publication selection
    seed: int = 12345
    min_success_fraction: float = 0.90
    ci_method: str = "percentile"  # "percentile" or "bca"
    n_workers: int = 1


@dataclass
class StatsConfig:
    alpha_family_wise: float = 0.05
    p_value_method: str = "wald_normal"  # A9
    variance_zero_policy: str = "flag_and_stop"  # Section 9
    bootstrap: BootstrapConfig = field(default_factory=BootstrapConfig)


@dataclass
class DesignConfig:
    n_initializations: int = 50
    replicates: int = 30
    configurations: list[int] = field(default_factory=lambda: list(CONFIGURATION_TABLE.keys()))


@dataclass
class OutputConfig:
    results_dir: str = "results"


@dataclass
class ExperimentConfig:
    name: str = "confirmatory"
    seed_root: int = 20260726
    seed_streams: dict[str, int] = field(default_factory=_default_seed_streams)
    task: TaskConfig = field(default_factory=TaskConfig)
    circuit: CircuitConfig = field(default_factory=CircuitConfig)
    cost_mapping: CostMapping = field(default_factory=CostMapping)
    residual: ResidualConfig = field(default_factory=ResidualConfig)
    gradient: GradientConfig = field(default_factory=GradientConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    design: DesignConfig = field(default_factory=DesignConfig)
    pilot: PilotConfig = field(default_factory=PilotConfig)
    stats: StatsConfig = field(default_factory=StatsConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def resolved_hidden_dim(self) -> int:
        if self.residual.hidden_dim == "n_qubits":
            return self.task.n_qubits
        return int(self.residual.hidden_dim)

    def gamma_for(self, R: int) -> float:
        return self.residual.gamma_R1 if R == 1 else self.residual.gamma_R0

    def cost_type_for(self, L: int) -> str:
        return self.cost_mapping.L1 if L == 1 else self.cost_mapping.L0

    def bootstrap_iterations(self) -> int:
        if self.stats.bootstrap.iterations is not None:
            return self.stats.bootstrap.iterations
        return self.stats.bootstrap.iterations_dev


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _dataclass_from_dict(cls, data: dict):
    """Recursively build a nested dataclass tree from a plain dict, keeping
    dataclass defaults for any keys absent in `data`."""
    kwargs = {}
    for f in cls.__dataclass_fields__.values():
        if f.name not in data:
            continue
        val = data[f.name]
        default_factory = f.default_factory if f.default_factory is not dataclasses.MISSING else None
        nested_cls = None
        if default_factory is not None:
            sample = default_factory()
            if hasattr(sample, "__dataclass_fields__") and isinstance(val, dict):
                nested_cls = type(sample)
        if nested_cls is not None:
            kwargs[f.name] = _dataclass_from_dict(nested_cls, val)
        else:
            kwargs[f.name] = val
    return cls(**kwargs)


def load_config(path: str | Path) -> ExperimentConfig:
    with open(path, "r") as fh:
        raw = yaml.safe_load(fh) or {}
    cfg = _dataclass_from_dict(ExperimentConfig, raw)
    return cfg


def config_to_dict(cfg: ExperimentConfig) -> dict:
    return asdict(cfg)


def config_hash(cfg: ExperimentConfig) -> str:
    canonical = json.dumps(config_to_dict(cfg), sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def entangling_pairs(layer_idx: int, E: int) -> list[tuple[int, int]]:
    """Logical CNOT schedule for ansatz layer `layer_idx` (0-indexed).

    E=0: baseline schedule every layer (Section 4).
    E=1: restricted schedule, alternating odd/even by 1-indexed layer number.
    Both variants apply exactly 4 logical CNOTs per layer.
    """
    if E == 0:
        return list(BASELINE_SCHEDULE)
    layer_num = layer_idx + 1  # 1-indexed, matches spec wording
    return list(RESTRICTED_ODD_SCHEDULE if layer_num % 2 == 1 else RESTRICTED_EVEN_SCHEDULE)
