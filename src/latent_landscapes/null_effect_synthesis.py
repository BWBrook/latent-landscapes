"""Goal 054 null-effect decision synthesis.

The module consumes the frozen statistic tables written by the production
runner.  It does not fit models, generate histories, or alter the input
arrays.  The reference and evaluation blocks are the independent resampling
units throughout.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]

REFERENCE_BLOCKS = 999
EVALUATION_BLOCKS = 1000
BETA_COUNT = 81
EFFECT_COUNT = 181
CELL_COUNT = 8
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 2026092905
TOLERANCE = 1e-12
ALPHA = 0.05
BERGER_BOOS_GAMMA = 0.01
POINT_ERROR_THRESHOLD = float(np.log(1.5))

CELL_IDS = (
    "E0_h1",
    "E0_h3",
    "E06_h1",
    "E06_h3",
    "B100-A_h1",
    "B100-A_h3",
    "N100-A_h1",
    "N100-A_h3",
)

# The first three are the registered calibrated rules.  The four textbook
# cutoffs are retained as descriptive comparisons only.
RULE_NAMES = (
    "adjusted_fullsup",
    "constant_beta0",
    "berger_boos",
    "adjusted_textbook_2.71",
    "adjusted_textbook_3.84",
    "constant_textbook_2.71",
    "constant_textbook_3.84",
)
PRIMARY_RULE_INDEX = 0
CONSTANT_RULE_INDEX = 1
BB_RULE_INDEX = 2
TEXTBOOK_CUTOFFS = (2.71, 3.84)

REQUIRED_ARRAYS = (
    "reference_t_adj",
    "reference_t_constant",
    "reference_d_beta",
    "evaluation_t_adj",
    "evaluation_t_constant",
    "evaluation_d_beta",
    "evaluation_h_hat_adj",
    "evaluation_beta_hat_adj",
    "evaluation_h_hat_constant",
    "evaluation_beta_hat_null",
    "evaluation_delta_holdout_adj_constant",
    "evaluation_delta_holdout_adj_neutral",
    "evaluation_delta_holdout_constant_neutral",
    "betas",
    "effects",
    "cell_ids",
    "truth_h",
    "truth_beta",
)


def _as_float(value: Any, name: str) -> FloatArray:
    array = cast(FloatArray, np.asarray(value, dtype=np.float64))
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain only finite values")
    return array


def _tail_pvalues(observed: FloatArray, reference: FloatArray, tolerance: float) -> FloatArray:
    """Inclusive plus-one upper-tail p-values for reference rows.

    ``reference`` has shape ``(R, J)`` and ``observed`` has any shape of scalar
    statistics.  A one-dimensional reference is accepted for scalar statistics.
    """
    if tolerance < 0 or not np.isfinite(tolerance):
        raise ValueError("tolerance must be finite and nonnegative")
    obs = _as_float(observed, "observed")
    ref = _as_float(reference, "reference")
    if ref.ndim == 1:
        counts = np.sum(ref[None, ...] >= obs[..., None] - tolerance, axis=-1)
        return cast(FloatArray, (counts + 1.0) / (ref.shape[0] + 1.0))
    if ref.ndim != 2:
        raise ValueError("reference must be (R,J)")
    # Goal 054's T statistics are scalar observations.  They are broadcast
    # over the J reference columns; node-wise D statistics use the explicit
    # helper below so that a dimension equal to J cannot be misinterpreted.
    counts = np.sum(ref[None, ...] >= obs[..., None, None] - tolerance, axis=-2)
    return cast(FloatArray, (counts + 1.0) / (ref.shape[0] + 1.0))


def _nodewise_pvalues(observed: FloatArray, reference: FloatArray, tolerance: float) -> FloatArray:
    obs = _as_float(observed, "observed")
    ref = _as_float(reference, "reference")
    if ref.ndim != 2 or obs.shape[-1] != ref.shape[1]:
        raise ValueError("node-wise observed/reference dimensions are incompatible")
    counts = np.sum(ref.T[None, ...] >= obs[..., None] - tolerance, axis=-1)
    return cast(FloatArray, (counts + 1.0) / (ref.shape[0] + 1.0))


def pvalues(
    observed: FloatArray,
    reference: FloatArray,
    *,
    tolerance: float = TOLERANCE,
) -> FloatArray:
    """Return inclusive plus-one upper-tail p-values.

    Equal statistics are retained in the reference tail.  The tolerance is
    subtracted from the observed statistic before comparison, so ties within
    the frozen numerical tolerance remain conservative.
    """
    return _tail_pvalues(observed, reference, tolerance)


def _validate_decision_inputs(
    t_adj: Any,
    reference_t_adj: Any,
    t_constant: Any | None,
    reference_t_constant: Any | None,
    d_beta: Any | None,
    reference_d_beta: Any | None,
) -> tuple[
    FloatArray,
    FloatArray,
    FloatArray | None,
    FloatArray | None,
    FloatArray | None,
    FloatArray | None,
]:
    observed = _as_float(t_adj, "t_adj")
    reference = _as_float(reference_t_adj, "reference_t_adj")
    if reference.ndim != 2 or observed.ndim < 1:
        raise ValueError("t_adj/reference_t_adj dimensions are invalid")
    if reference.shape[0] < 1:
        raise ValueError("reference table must contain at least one block")
    constant = None if t_constant is None else _as_float(t_constant, "t_constant")
    constant_reference = (
        None
        if reference_t_constant is None
        else _as_float(reference_t_constant, "reference_t_constant")
    )
    if (constant is None) != (constant_reference is None):
        raise ValueError("constant observed and reference statistics must be supplied together")
    if constant is not None and (
        constant.shape not in (observed.shape, observed.shape[:-1])
        or constant_reference is None
        or constant_reference.ndim != 1
        or constant_reference.shape[0] != reference.shape[0]
    ):
        raise ValueError("constant statistics have incompatible dimensions")
    d_observed = None if d_beta is None else _as_float(d_beta, "d_beta")
    d_reference = (
        None if reference_d_beta is None else _as_float(reference_d_beta, "reference_d_beta")
    )
    if (d_observed is None) != (d_reference is None):
        raise ValueError("Berger-Boos observed and reference statistics must be supplied together")
    if d_observed is not None and (
        d_observed.shape != (*observed.shape, reference.shape[1])
        or d_reference is None
        or d_reference.shape != reference.shape
    ):
        raise ValueError("Berger-Boos statistics have incompatible dimensions")
    return observed, reference, constant, constant_reference, d_observed, d_reference


def _order_cutoff(reference: FloatArray, rank: int) -> FloatArray:
    size = reference.shape[0]
    if rank == size + 1:
        # No finite statistic can reach a tail with zero allowable reference
        # exceedances; for q-membership the same +inf cutoff includes every
        # finite observed statistic.
        return cast(
            FloatArray,
            np.inf if reference.ndim == 1 else np.full(reference.shape[1], np.inf),
        )
    if rank < 1:
        return cast(
            FloatArray,
            -np.inf if reference.ndim == 1 else np.full(reference.shape[1], -np.inf),
        )
    if reference.ndim == 1:
        if rank > size:
            raise ValueError("order-statistic rank is outside the reference table")
        return cast(FloatArray, np.partition(reference, rank - 1)[rank - 1])
    if rank > size:
        raise ValueError("order-statistic rank is outside the reference table")
    return cast(FloatArray, np.partition(reference, rank - 1, axis=0)[rank - 1])


def _decision_from_cutoffs(
    t_adj: FloatArray,
    reference_t_adj: FloatArray,
    t_constant: FloatArray | None,
    reference_t_constant: FloatArray | None,
    d_beta: FloatArray | None,
    reference_d_beta: FloatArray | None,
    *,
    tolerance: float,
    alpha: float,
    gamma: float,
) -> dict[str, FloatArray | BoolArray | None]:
    """Use order-statistic cutoffs while retaining the direct p-value outputs."""
    r = reference_t_adj.shape[0]
    primary_rank = r - int(np.floor(alpha * (r + 1))) + 1
    bb_rank = r - int(np.floor((alpha - gamma) * (r + 1))) + 1
    q_rank = r - int(np.floor(gamma * (r + 1))) + 1
    if min(primary_rank, bb_rank, q_rank) < 1:
        raise ValueError("reference table is too small for the requested decision levels")
    primary_cutoff = _order_cutoff(reference_t_adj, primary_rank)
    direct_p_adj = _tail_pvalues(t_adj, reference_t_adj, tolerance)
    primary_by_cutoff = np.all(t_adj[..., None] - tolerance > primary_cutoff, axis=-1)
    primary_direct = np.all(direct_p_adj <= alpha, axis=-1)
    if not np.array_equal(primary_by_cutoff, primary_direct):
        raise AssertionError("primary order-statistic rule disagrees with direct p-values")

    result: dict[str, FloatArray | BoolArray | None] = {
        "p_adj": direct_p_adj,
        "max_p_adj": np.max(direct_p_adj, axis=-1),
        "primary": primary_direct,
        "constant_p": None,
        "constant": None,
        "q": None,
        "candidate": None,
        "p_bb": None,
        "berger_boos": None,
        "primary_cutoff": primary_cutoff,
        "berger_boos_t_cutoff": _order_cutoff(reference_t_adj, bb_rank),
        "q_d_cutoff": None,
    }
    if t_constant is not None and reference_t_constant is not None:
        constant_p = _tail_pvalues(t_constant, reference_t_constant, tolerance)
        constant_cutoff = _order_cutoff(reference_t_constant, primary_rank)
        constant_by_cutoff = t_constant - tolerance > constant_cutoff
        constant_direct = constant_p <= alpha
        if not np.array_equal(constant_by_cutoff, constant_direct):
            raise AssertionError("constant order-statistic rule disagrees with direct p-values")
        result["constant_p"] = constant_p
        result["constant"] = constant_direct
        result["constant_cutoff"] = constant_cutoff
    if d_beta is not None and reference_d_beta is not None:
        q = _nodewise_pvalues(d_beta, reference_d_beta, tolerance)
        candidate = q > gamma
        q_cutoff = _order_cutoff(reference_d_beta, q_rank)
        candidate_by_cutoff = d_beta - tolerance <= q_cutoff
        if not np.array_equal(candidate, candidate_by_cutoff):
            raise AssertionError("Berger-Boos candidate cutoff disagrees with direct q-values")
        bb_cutoff = _order_cutoff(reference_t_adj, bb_rank)
        bb_by_cutoff = t_adj[..., None] - tolerance > bb_cutoff
        p_bb = np.where(
            candidate.any(axis=-1),
            np.minimum(1.0, np.max(np.where(candidate, direct_p_adj + gamma, -np.inf), axis=-1)),
            1.0,
        )
        bb_direct = p_bb <= alpha
        bb_from_cutoff = candidate.any(axis=-1) & np.all(~candidate | bb_by_cutoff, axis=-1)
        if not np.array_equal(bb_direct, bb_from_cutoff):
            raise AssertionError("Berger-Boos order-statistic rule disagrees with direct p-values")
        result.update(
            q=q,
            candidate=candidate,
            p_bb=p_bb,
            berger_boos=bb_direct,
            q_d_cutoff=q_cutoff,
        )
    return result


def decision_rule(
    t_adj: FloatArray,
    reference_t_adj: FloatArray,
    t_constant: FloatArray | None = None,
    reference_t_constant: FloatArray | None = None,
    d_beta: FloatArray | None = None,
    reference_d_beta: FloatArray | None = None,
    tolerance: float = TOLERANCE,
    alpha: float = ALPHA,
    gamma: float = BERGER_BOOS_GAMMA,
) -> dict[str, FloatArray | BoolArray | None]:
    """Evaluate the registered primary, constant and Berger--Boos rules.

    ``t_adj`` is a scalar statistic array such as ``(N, 8)``; p-values are
    returned with an added beta-node dimension.  ``d_beta`` is explicitly
    node-wise and has shape ``(*t_adj.shape, J)``.
    """
    if not 0 < alpha <= 1 or not 0 <= gamma < alpha:
        raise ValueError("alpha/gamma must satisfy 0 < gamma < alpha <= 1")
    values = _validate_decision_inputs(
        t_adj, reference_t_adj, t_constant, reference_t_constant, d_beta, reference_d_beta
    )
    return _decision_from_cutoffs(*values, tolerance=tolerance, alpha=alpha, gamma=gamma)


def _load_npz(path: Path) -> dict[str, NDArray[Any]]:
    with np.load(path, allow_pickle=False) as archive:
        missing = sorted(set(REQUIRED_ARRAYS) - set(archive.files))
        if missing:
            raise ValueError(f"input NPZ lacks required arrays: {missing}")
        return {name: np.asarray(archive[name]) for name in archive.files}


def _validate_inputs(values: Mapping[str, Any], *, strict: bool) -> dict[str, Any]:
    missing = sorted(set(REQUIRED_ARRAYS) - set(values))
    if missing:
        raise ValueError(f"input lacks required arrays: {missing}")
    arrays = {name: values[name] for name in REQUIRED_ARRAYS}
    ref_adj = _as_float(arrays["reference_t_adj"], "reference_t_adj")
    ref_const = _as_float(arrays["reference_t_constant"], "reference_t_constant")
    ref_d = _as_float(arrays["reference_d_beta"], "reference_d_beta")
    eval_adj = _as_float(arrays["evaluation_t_adj"], "evaluation_t_adj")
    eval_const = _as_float(arrays["evaluation_t_constant"], "evaluation_t_constant")
    eval_d = _as_float(arrays["evaluation_d_beta"], "evaluation_d_beta")
    if ref_adj.ndim != 2 or ref_const.ndim != 1 or ref_d.shape != ref_adj.shape:
        raise ValueError("reference tables must be (R,J), (R), and (R,J)")
    if eval_adj.ndim != 2 or eval_const.ndim != 2 or eval_const.shape != eval_adj.shape:
        raise ValueError("evaluation t tables must both be (N,8)")
    n, cells = eval_adj.shape
    r, nodes = ref_adj.shape
    if eval_const.shape != (n, cells) or eval_d.shape != (n, cells, nodes):
        raise ValueError("evaluation statistic tables have incompatible shapes")
    if strict and (r, n, cells, nodes) != (
        REFERENCE_BLOCKS,
        EVALUATION_BLOCKS,
        CELL_COUNT,
        BETA_COUNT,
    ):
        raise ValueError("strict Goal 054 input requires reference 999 x evaluation 1000 x 8 x 81")
    if not strict and (cells != CELL_COUNT or nodes < 1):
        raise ValueError("test input must retain eight evaluation cells and at least one beta node")
    betas = _as_float(arrays["betas"], "betas")
    effects = _as_float(arrays["effects"], "effects")
    if betas.shape != (nodes,) or effects.ndim != 1:
        raise ValueError("betas/effects must be one-dimensional and match the beta axis")
    if strict and effects.shape != (EFFECT_COUNT,):
        raise ValueError("strict Goal 054 input requires 181 effect nodes")
    if strict and (
        not np.array_equal(betas, np.linspace(-2.0, 2.0, BETA_COUNT))
        or not np.array_equal(effects, np.linspace(1.0, 10.0, EFFECT_COUNT))
    ):
        raise ValueError("strict Goal 054 input has the wrong frozen beta/effect grid")
    if np.any(np.diff(betas) <= 0) or np.any(np.diff(effects) <= 0):
        raise ValueError("beta and effect grids must be strictly increasing")
    cell_ids = np.asarray(arrays["cell_ids"])
    if cell_ids.ndim != 1 or cell_ids.shape != (cells,) or cell_ids.dtype.kind not in "SU":
        raise ValueError("cell_ids must be a one-dimensional string array of length eight")
    cell_ids = cell_ids.astype(str)
    if len(np.unique(cell_ids)) != cells:
        raise ValueError("cell_ids must be unique")
    truth_h = _as_float(arrays["truth_h"], "truth_h")
    truth_beta = np.asarray(arrays["truth_beta"], dtype=np.float64)
    if truth_h.shape != (cells,) or truth_beta.shape != (cells,):
        raise ValueError("truth_h and truth_beta must contain one value per cell")
    if not np.isfinite(truth_beta[~np.isnan(truth_beta)]).all() or np.isinf(truth_beta).any():
        raise ValueError("truth_beta must contain finite values or NaN for unknown beta")
    for name in (
        "evaluation_h_hat_adj",
        "evaluation_beta_hat_adj",
        "evaluation_h_hat_constant",
        "evaluation_beta_hat_null",
        "evaluation_delta_holdout_adj_constant",
        "evaluation_delta_holdout_adj_neutral",
        "evaluation_delta_holdout_constant_neutral",
    ):
        array = _as_float(arrays[name], name)
        if array.shape != (n, cells):
            raise ValueError(f"{name} must have shape {(n, cells)}")
    if (
        (truth_h <= 0).any()
        or (arrays["evaluation_h_hat_adj"] <= 0).any()
        or (arrays["evaluation_h_hat_constant"] <= 0).any()
    ):
        raise ValueError("h values must be positive")
    if strict and tuple(cell_ids) != CELL_IDS:
        raise ValueError("strict Goal 054 input has the wrong frozen cell order")
    if strict and not np.array_equal(truth_h, np.tile([1.0, 3.0], 4)):
        raise ValueError("strict Goal 054 input has the wrong frozen h truths")
    if strict and any(
        (array < 0).any() for array in (ref_adj, ref_const, ref_d, eval_adj, eval_const, eval_d)
    ):
        raise ValueError("strict Goal 054 T and D statistics must be nonnegative")
    return {
        "reference_t_adj": ref_adj,
        "reference_t_constant": ref_const,
        "reference_d_beta": ref_d,
        "evaluation_t_adj": eval_adj,
        "evaluation_t_constant": eval_const,
        "evaluation_d_beta": eval_d,
        "betas": betas,
        "effects": effects,
        "cell_ids": cell_ids,
        "truth_h": truth_h,
        "truth_beta": truth_beta,
        **{
            name: np.asarray(arrays[name], dtype=np.float64)
            for name in REQUIRED_ARRAYS
            if name.startswith("evaluation_")
            and name
            not in {
                "evaluation_t_adj",
                "evaluation_t_constant",
                "evaluation_d_beta",
            }
        },
    }


def _rule_array(
    values: Mapping[str, Any],
    reference_t_adj: FloatArray,
    reference_t_constant: FloatArray,
    reference_d_beta: FloatArray,
    *,
    truth_beta_indices: NDArray[np.int64],
    fast: bool = False,
) -> tuple[BoolArray, dict[str, Any]]:
    if fast:
        reference_count = reference_t_adj.shape[0]
        primary_rank = reference_count - int(np.floor(ALPHA * (reference_count + 1))) + 1
        bb_rank = (
            reference_count - int(np.floor((ALPHA - BERGER_BOOS_GAMMA) * (reference_count + 1))) + 1
        )
        q_rank = reference_count - int(np.floor(BERGER_BOOS_GAMMA * (reference_count + 1))) + 1
        primary_cutoff = _order_cutoff(reference_t_adj, primary_rank)
        bb_cutoff = _order_cutoff(reference_t_adj, bb_rank)
        constant_cutoff = _order_cutoff(reference_t_constant, primary_rank)
        q_cutoff = _order_cutoff(reference_d_beta, q_rank)
        adjusted = values["evaluation_t_adj"]
        constant = values["evaluation_t_constant"]
        candidate = values["evaluation_d_beta"] - TOLERANCE <= q_cutoff
        primary = np.all(adjusted[..., None] - TOLERANCE > primary_cutoff, axis=-1)
        constant_rule = constant - TOLERANCE > constant_cutoff
        bb_rule = candidate.any(axis=-1) & np.all(
            ~candidate | (adjusted[..., None] - TOLERANCE > bb_cutoff), axis=-1
        )
        result: dict[str, Any] = {"candidate": candidate}
    else:
        result = decision_rule(
            values["evaluation_t_adj"],
            reference_t_adj,
            t_constant=values["evaluation_t_constant"],
            reference_t_constant=reference_t_constant,
            d_beta=values["evaluation_d_beta"],
            reference_d_beta=reference_d_beta,
        )
        candidate = np.asarray(result["candidate"], dtype=bool)
        primary = np.asarray(result["primary"], dtype=bool)
        constant_rule = np.asarray(result["constant"], dtype=bool)
        bb_rule = np.asarray(result["berger_boos"], dtype=bool)
    rules = np.stack(
        (
            primary,
            constant_rule,
            bb_rule,
            values["evaluation_t_adj"] - TOLERANCE > TEXTBOOK_CUTOFFS[0],
            values["evaluation_t_adj"] - TOLERANCE > TEXTBOOK_CUTOFFS[1],
            values["evaluation_t_constant"] - TOLERANCE > TEXTBOOK_CUTOFFS[0],
            values["evaluation_t_constant"] - TOLERANCE > TEXTBOOK_CUTOFFS[1],
        ),
        axis=-1,
    )
    return rules, result


def _metric_values(values: Mapping[str, Any], rules: BoolArray) -> dict[str, FloatArray]:
    truth = values["truth_h"][None, :]
    adj_signed = np.log(values["evaluation_h_hat_adj"] / truth)
    constant_signed = np.log(values["evaluation_h_hat_constant"] / truth)
    adj_abs = np.abs(adj_signed)
    constant_abs = np.abs(constant_signed)
    return {
        "adjusted_signed_log_error": adj_signed,
        "constant_signed_log_error": constant_signed,
        "adjusted_mae": adj_abs,
        "constant_mae": constant_abs,
        "adjusted_1p5_error": adj_abs >= POINT_ERROR_THRESHOLD,
        "constant_1p5_error": constant_abs >= POINT_ERROR_THRESHOLD,
        "adjusted_minus_constant_holdout": values["evaluation_delta_holdout_adj_constant"],
        "adjusted_minus_neutral_holdout": values["evaluation_delta_holdout_adj_neutral"],
        "constant_minus_neutral_holdout": values["evaluation_delta_holdout_constant_neutral"],
    }


def _mean_summary(samples: FloatArray, estimate: float) -> dict[str, float]:
    finite = samples[np.isfinite(samples)]
    se = float("nan") if finite.size < 2 else float(np.std(finite, ddof=1))
    low, high = np.quantile(finite, (0.025, 0.975)) if finite.size else (np.nan, np.nan)
    return {
        "estimate": float(estimate),
        "se": se,
        "low": float(low),
        "high": float(high),
    }


def _json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"cannot serialize {type(value)!r}")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _plot_outputs(
    output: Path,
    betas: FloatArray,
    cutoff_curve: FloatArray,
    cell_ids: NDArray[np.str_],
    rule_rates: FloatArray,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axis = plt.subplots(figsize=(9, 5.5), layout="constrained")
    for index, label in enumerate(("primary 0.05", "Berger--Boos T 0.04", "q 0.01")):
        axis.plot(betas, cutoff_curve[:, index], label=label)
    axis.set(xlabel="beta node", ylabel="statistic cutoff", title="Goal 054 reference cutoffs")
    axis.grid(alpha=0.2)
    axis.legend()
    fig.savefig(output / "cutoff_curve.png", dpi=180)
    fig.savefig(output / "cutoff_curve.pdf")
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(12, 5.5), layout="constrained")
    x = np.arange(len(cell_ids))
    for index, label in enumerate(("adjusted fullsup", "constant beta0", "Berger--Boos")):
        axis.plot(x, rule_rates[:, index], "o-", label=label)
    axis.axhline(ALPHA, color="black", ls="--", lw=0.8)
    axis.set(
        xticks=x,
        xticklabels=cell_ids,
        ylim=(-0.02, 1.02),
        ylabel="rate",
        title="Goal 054 declaration rates",
    )
    axis.tick_params(axis="x", rotation=45)
    axis.grid(axis="y", alpha=0.2)
    axis.legend()
    fig.savefig(output / "declaration_rates.png", dpi=180)
    fig.savefig(output / "declaration_rates.pdf")
    plt.close(fig)


def synthesize(
    input_npz: str | Path,
    output_dir: str | Path,
    bootstrap_draws: int = BOOTSTRAP_DRAWS,
    strict: bool = True,
) -> dict[str, Any]:
    """Synthesize a registered Goal 054 statistics NPZ into reviewable tables."""
    input_path = Path(input_npz)
    output = Path(output_dir)
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    generated_names = {
        "cutoff_curve.csv",
        "rule_rates.csv",
        "error_metrics.csv",
        "prediction_metrics.csv",
        "paired_rule_contrasts.csv",
        "rule_diagnostics.csv",
        "cutoff_curve.png",
        "cutoff_curve.pdf",
        "declaration_rates.png",
        "declaration_rates.pdf",
        "bootstrap_draws.npz",
    }
    if output.exists() and (
        not output.is_dir()
        or (output / "summary.json").exists()
        or any(path.name in generated_names for path in output.iterdir())
    ):
        raise FileExistsError(f"refusing to overwrite existing synthesis outputs: {output}")
    if bootstrap_draws < 2 or (strict and bootstrap_draws != BOOTSTRAP_DRAWS):
        raise ValueError("strict Goal 054 synthesis requires exactly 2,000 bootstrap draws")
    digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    values = _validate_inputs(_load_npz(input_path), strict=strict)
    n, cells = values["evaluation_t_adj"].shape
    nodes = values["reference_t_adj"].shape[1]
    truth_indices = np.full(cells, -1, dtype=np.int64)
    for cell, truth in enumerate(values["truth_beta"]):
        if np.isfinite(truth):
            matches = np.flatnonzero(np.isclose(values["betas"], truth, rtol=0, atol=TOLERANCE))
            if len(matches) != 1:
                raise ValueError(f"truth_beta for cell {cell} is not represented exactly once")
            truth_indices[cell] = int(matches[0])

    rules, decision = _rule_array(
        values,
        values["reference_t_adj"],
        values["reference_t_constant"],
        values["reference_d_beta"],
        truth_beta_indices=truth_indices,
    )
    metrics = _metric_values(values, rules)
    # A single fixed stream is split into independent reference and evaluation
    # generators.  No outcome can alter the draw count or either seed.
    reference_rng, evaluation_rng = np.random.SeedSequence(BOOTSTRAP_SEED).spawn(2)
    ref_rng = np.random.default_rng(reference_rng)
    eval_rng = np.random.default_rng(evaluation_rng)
    frozen_rule = np.empty((bootstrap_draws, cells, len(RULE_NAMES)), dtype=np.float64)
    calibration_rule = np.empty_like(frozen_rule)
    metric_names = tuple(metrics)
    frozen_metric = {
        name: np.empty((bootstrap_draws, cells), dtype=np.float64) for name in metric_names
    }
    calibration_metric = {
        name: np.empty((bootstrap_draws, cells), dtype=np.float64) for name in metric_names
    }
    frozen_declared = {
        name: np.empty((bootstrap_draws, cells, len(RULE_NAMES)), dtype=np.float64)
        for name in metrics
    }
    calibration_declared = {name: np.empty_like(array) for name, array in frozen_declared.items()}
    frozen_joint = {
        "adjusted": np.empty((bootstrap_draws, cells, len(RULE_NAMES)), dtype=np.float64),
        "constant": np.empty((bootstrap_draws, cells, len(RULE_NAMES)), dtype=np.float64),
    }
    calibration_joint = {name: np.empty_like(array) for name, array in frozen_joint.items()}
    for draw in range(bootstrap_draws):
        ref_index = ref_rng.integers(
            values["reference_t_adj"].shape[0], size=values["reference_t_adj"].shape[0]
        )
        eval_index = eval_rng.integers(n, size=n)
        # Frozen tables use the original decision and only the paired evaluation
        # resample.  Re-indexing after evaluation keeps all eight cells paired.
        frozen_sample_rules = rules[eval_index]
        frozen_rule[draw] = frozen_sample_rules.mean(axis=0)
        sampled_metrics = {name: array[eval_index] for name, array in metrics.items()}
        for name, array in sampled_metrics.items():
            frozen_metric[name][draw] = np.asarray(array, dtype=np.float64).mean(axis=0)
            for rule in range(len(RULE_NAMES)):
                mask = frozen_sample_rules[..., rule]
                if array.dtype == bool:
                    numerator = (np.asarray(array, dtype=float) * mask).sum(axis=0)
                else:
                    numerator = (np.asarray(array, dtype=float) * mask).sum(axis=0)
                counts = mask.sum(axis=0)
                frozen_declared[name][draw, :, rule] = np.divide(
                    numerator, counts, out=np.full(cells, np.nan), where=counts > 0
                )
        for method, one_name in (
            ("adjusted", "adjusted_1p5_error"),
            ("constant", "constant_1p5_error"),
        ):
            frozen_joint[method][draw] = np.mean(
                frozen_sample_rules * np.asarray(sampled_metrics[one_name], dtype=float)[..., None],
                axis=0,
            )
        # Calibration-aware draws resample whole reference blocks paired across
        # beta.  The same evaluation draw is used for the matched comparison.
        cal_refs_adj = values["reference_t_adj"][ref_index]
        cal_refs_const = values["reference_t_constant"][ref_index]
        cal_refs_d = values["reference_d_beta"][ref_index]
        cal_rules, _ = _rule_array(
            values,
            cal_refs_adj,
            cal_refs_const,
            cal_refs_d,
            truth_beta_indices=truth_indices,
            fast=True,
        )
        cal_sample_rules = cal_rules[eval_index]
        calibration_rule[draw] = cal_sample_rules.mean(axis=0)
        for name, array in sampled_metrics.items():
            calibration_metric[name][draw] = np.asarray(array, dtype=float).mean(axis=0)
            for rule in range(len(RULE_NAMES)):
                mask = cal_sample_rules[..., rule]
                numerator = (np.asarray(array, dtype=float) * mask).sum(axis=0)
                counts = mask.sum(axis=0)
                calibration_declared[name][draw, :, rule] = np.divide(
                    numerator, counts, out=np.full(cells, np.nan), where=counts > 0
                )
        for method, one_name in (
            ("adjusted", "adjusted_1p5_error"),
            ("constant", "constant_1p5_error"),
        ):
            calibration_joint[method][draw] = np.mean(
                cal_sample_rules * np.asarray(sampled_metrics[one_name], dtype=float)[..., None],
                axis=0,
            )

    # The exact point rates and the three cutoff curves are direct outputs from
    # the registered tables, while bootstrap rows carry uncertainty only.
    output.mkdir(parents=True, exist_ok=True)
    cutoff_curve = np.column_stack(
        (
            decision["primary_cutoff"],
            decision["berger_boos_t_cutoff"],
            decision["q_d_cutoff"],
        )
    )
    cutoff_rows = [
        {
            "beta_index": i,
            "beta": float(values["betas"][i]),
            "primary_t_cutoff_rank950": float(cutoff_curve[i, 0]),
            "berger_boos_t_cutoff_rank960": float(cutoff_curve[i, 1]),
            "q_d_cutoff_rank990": float(cutoff_curve[i, 2]),
        }
        for i in range(nodes)
    ]
    _write_csv(output / "cutoff_curve.csv", cutoff_rows)

    rule_rows: list[dict[str, Any]] = []
    point_rates = rules.mean(axis=0)
    for cell, cell_id in enumerate(values["cell_ids"]):
        for rule, name in enumerate(RULE_NAMES):
            point = float(point_rates[cell, rule])
            frozen = frozen_rule[:, cell, rule]
            calibrated = calibration_rule[:, cell, rule]
            f = _mean_summary(frozen, point)
            c = _mean_summary(calibrated, point)
            rule_rows.append(
                {
                    "cell_id": str(cell_id),
                    "rule": name,
                    "n": n,
                    "count": int(rules[:, cell, rule].sum()),
                    "rate": point,
                    "frozen_se": f["se"],
                    "frozen_low": f["low"],
                    "frozen_high": f["high"],
                    "calibration_aware_se": c["se"],
                    "calibration_aware_low": c["low"],
                    "calibration_aware_high": c["high"],
                }
            )
    _write_csv(output / "rule_rates.csv", rule_rows)

    error_rows: list[dict[str, Any]] = []
    for cell, cell_id in enumerate(values["cell_ids"]):
        for method, signed_name, mae_name, one_name in (
            ("adjusted", "adjusted_signed_log_error", "adjusted_mae", "adjusted_1p5_error"),
            ("constant", "constant_signed_log_error", "constant_mae", "constant_1p5_error"),
        ):
            subsets: list[tuple[str, int | None]] = [("unconditional", None)] + [
                (f"declared_{name}", i) for i, name in enumerate(RULE_NAMES)
            ]
            for subset, subset_rule in subsets:
                if subset_rule is None:
                    mask = np.ones(n, dtype=bool)
                    declared_count = n
                else:
                    mask = rules[:, cell, subset_rule]
                    declared_count = int(mask.sum())
                signed = metrics[signed_name][:, cell]
                mae = metrics[mae_name][:, cell]
                one = np.asarray(metrics[one_name][:, cell], dtype=float)
                estimate_signed = float(np.mean(signed[mask])) if mask.any() else float("nan")
                estimate_mae = float(np.mean(mae[mask])) if mask.any() else float("nan")
                estimate_one = float(np.mean(one[mask])) if mask.any() else float("nan")
                joints = int(np.sum(mask & (one > 0.5)))
                if subset_rule is None:
                    boot_signed_frozen = frozen_metric[signed_name][:, cell]
                    boot_signed_calibrated = calibration_metric[signed_name][:, cell]
                    boot_mae_frozen = frozen_metric[mae_name][:, cell]
                    boot_mae_calibrated = calibration_metric[mae_name][:, cell]
                    boot_one_frozen = frozen_metric[one_name][:, cell]
                    boot_one_calibrated = calibration_metric[one_name][:, cell]
                    joint_frozen = np.full(bootstrap_draws, np.nan)
                    joint_calibrated = np.full(bootstrap_draws, np.nan)
                    undefined_frozen = undefined_calibrated = 0
                else:
                    boot_signed_frozen = frozen_declared[signed_name][:, cell, subset_rule]
                    boot_signed_calibrated = calibration_declared[signed_name][:, cell, subset_rule]
                    boot_mae_frozen = frozen_declared[mae_name][:, cell, subset_rule]
                    boot_mae_calibrated = calibration_declared[mae_name][:, cell, subset_rule]
                    boot_one_frozen = frozen_declared[one_name][:, cell, subset_rule]
                    boot_one_calibrated = calibration_declared[one_name][:, cell, subset_rule]
                    joint_frozen = frozen_joint[method][:, cell, subset_rule]
                    joint_calibrated = calibration_joint[method][:, cell, subset_rule]
                    undefined_frozen = int(np.isnan(boot_signed_frozen).sum())
                    undefined_calibrated = int(np.isnan(boot_signed_calibrated).sum())
                signed_frozen = _mean_summary(boot_signed_frozen, estimate_signed)
                signed_calibrated = _mean_summary(boot_signed_calibrated, estimate_signed)
                mae_frozen = _mean_summary(boot_mae_frozen, estimate_mae)
                mae_calibrated = _mean_summary(boot_mae_calibrated, estimate_mae)
                one_frozen = _mean_summary(boot_one_frozen, estimate_one)
                one_calibrated = _mean_summary(boot_one_calibrated, estimate_one)
                joint_point = float(joints / n) if subset_rule is not None else float("nan")
                joint_frozen_summary = _mean_summary(joint_frozen, joint_point)
                joint_calibrated_summary = _mean_summary(joint_calibrated, joint_point)
                # Declared subsets are descriptive selected-subset summaries.
                error_rows.append(
                    {
                        "cell_id": str(cell_id),
                        "method": method,
                        "subset": subset,
                        "n": int(mask.sum()),
                        "declared_count": declared_count,
                        "signed_log_error": estimate_signed,
                        "mae": estimate_mae,
                        "one_point_five_error_rate": estimate_one,
                        "one_point_five_error_count": int(np.sum(one[mask] > 0.5))
                        if mask.any()
                        else 0,
                        "declaration_and_one_point_five_error_count": joints,
                        "joint_rate_all_history_denominator": joint_point,
                        "signed_frozen_se": signed_frozen["se"],
                        "signed_frozen_low": signed_frozen["low"],
                        "signed_frozen_high": signed_frozen["high"],
                        "signed_calibration_aware_se": signed_calibrated["se"],
                        "signed_calibration_aware_low": signed_calibrated["low"],
                        "signed_calibration_aware_high": signed_calibrated["high"],
                        "mae_frozen_se": mae_frozen["se"],
                        "mae_frozen_low": mae_frozen["low"],
                        "mae_frozen_high": mae_frozen["high"],
                        "mae_calibration_aware_se": mae_calibrated["se"],
                        "mae_calibration_aware_low": mae_calibrated["low"],
                        "mae_calibration_aware_high": mae_calibrated["high"],
                        "one_frozen_se": one_frozen["se"],
                        "one_frozen_low": one_frozen["low"],
                        "one_frozen_high": one_frozen["high"],
                        "one_calibration_aware_se": one_calibrated["se"],
                        "one_calibration_aware_low": one_calibrated["low"],
                        "one_calibration_aware_high": one_calibrated["high"],
                        "joint_frozen_se": joint_frozen_summary["se"],
                        "joint_frozen_low": joint_frozen_summary["low"],
                        "joint_frozen_high": joint_frozen_summary["high"],
                        "joint_calibration_aware_se": joint_calibrated_summary["se"],
                        "joint_calibration_aware_low": joint_calibrated_summary["low"],
                        "joint_calibration_aware_high": joint_calibrated_summary["high"],
                        "undefined_frozen_bootstrap_count": undefined_frozen,
                        "undefined_calibration_aware_bootstrap_count": undefined_calibrated,
                    }
                )
    _write_csv(output / "error_metrics.csv", error_rows)

    prediction_rows: list[dict[str, Any]] = []
    for cell, cell_id in enumerate(values["cell_ids"]):
        for name in (
            "adjusted_minus_constant_holdout",
            "adjusted_minus_neutral_holdout",
            "constant_minus_neutral_holdout",
        ):
            point = float(np.mean(metrics[name][:, cell]))
            frozen = frozen_metric[name][:, cell]
            calibrated = calibration_metric[name][:, cell]
            f, c = _mean_summary(frozen, point), _mean_summary(calibrated, point)
            prediction_rows.append(
                {
                    "cell_id": str(cell_id),
                    "metric": name,
                    "estimate": point,
                    "frozen_se": f["se"],
                    "frozen_low": f["low"],
                    "frozen_high": f["high"],
                    "calibration_aware_se": c["se"],
                    "calibration_aware_low": c["low"],
                    "calibration_aware_high": c["high"],
                }
            )
    _write_csv(output / "prediction_metrics.csv", prediction_rows)

    # Explicit paired adjusted-minus-constant declaration contrasts.
    contrast_rows: list[dict[str, Any]] = []
    for cell, cell_id in enumerate(values["cell_ids"]):
        comparisons = (
            (PRIMARY_RULE_INDEX, CONSTANT_RULE_INDEX, "adjusted_fullsup_minus_constant_beta0"),
            (BB_RULE_INDEX, CONSTANT_RULE_INDEX, "berger_boos_minus_constant_beta0"),
            (3, 5, "adjusted_textbook_2.71_minus_constant_textbook_2.71"),
            (4, 6, "adjusted_textbook_3.84_minus_constant_textbook_3.84"),
        )
        for left, right, label in comparisons:
            point = float(point_rates[cell, left] - point_rates[cell, right])
            frozen = frozen_rule[:, cell, left] - frozen_rule[:, cell, right]
            calibrated = calibration_rule[:, cell, left] - calibration_rule[:, cell, right]
            f, c = _mean_summary(frozen, point), _mean_summary(calibrated, point)
            contrast_rows.append(
                {
                    "cell_id": str(cell_id),
                    "comparison": label,
                    "estimate": point,
                    "frozen_se": f["se"],
                    "frozen_low": f["low"],
                    "frozen_high": f["high"],
                    "calibration_aware_se": c["se"],
                    "calibration_aware_low": c["low"],
                    "calibration_aware_high": c["high"],
                }
            )
    _write_csv(output / "paired_rule_contrasts.csv", contrast_rows)

    # Max-p contributors and Berger--Boos candidate diagnostics are retained at
    # cell level so boundary behaviour is visible without writing 8,000 rows.
    max_contributor = np.isclose(
        np.asarray(decision["p_adj"]),
        np.asarray(decision["max_p_adj"])[..., None],
        rtol=0,
        atol=TOLERANCE,
    )
    candidate = np.asarray(decision["candidate"], dtype=bool)
    candidate_rows = []
    for cell, cell_id in enumerate(values["cell_ids"]):
        candidate_cell = candidate[:, cell]
        contributors = max_contributor[:, cell]
        candidate_rows.append(
            {
                "cell_id": str(cell_id),
                "candidate_size_mean": float(candidate_cell.sum(axis=-1).mean()),
                "candidate_size_min": int(candidate_cell.sum(axis=-1).min()),
                "candidate_size_max": int(candidate_cell.sum(axis=-1).max()),
                "candidate_empty_count": int((~candidate_cell.any(axis=-1)).sum()),
                "candidate_lower_edge_rate": float(candidate_cell[:, 0].mean()),
                "candidate_upper_edge_rate": float(candidate_cell[:, -1].mean()),
                "max_contributor_mean_count": float(contributors.sum(axis=-1).mean()),
                "max_contributor_lower_boundary_rate": float(contributors[:, 0].mean()),
                "max_contributor_upper_boundary_rate": float(contributors[:, -1].mean()),
                "max_contributor_beta_indices": json.dumps(
                    np.flatnonzero(contributors.any(axis=0)).tolist()
                ),
                "max_contributor_betas": json.dumps(
                    values["betas"][np.flatnonzero(contributors.any(axis=0))].tolist()
                ),
                "max_contributor_touches_boundary": bool(
                    contributors[:, 0].any() or contributors[:, -1].any()
                ),
            }
        )
    _write_csv(output / "rule_diagnostics.csv", candidate_rows)

    bootstrap_metrics_frozen = np.stack([frozen_metric[name] for name in metric_names], axis=-1)
    bootstrap_metrics_calibrated = np.stack(
        [calibration_metric[name] for name in metric_names], axis=-1
    )
    bootstrap_declared_frozen = np.stack([frozen_declared[name] for name in metric_names], axis=-1)
    bootstrap_declared_calibrated = np.stack(
        [calibration_declared[name] for name in metric_names], axis=-1
    )
    np.savez_compressed(
        output / "bootstrap_draws.npz",
        rule_rates_frozen=frozen_rule,
        rule_rates_calibration_aware=calibration_rule,
        metrics_frozen=bootstrap_metrics_frozen,
        metrics_calibration_aware=bootstrap_metrics_calibrated,
        declared_metrics_frozen=bootstrap_declared_frozen,
        declared_metrics_calibration_aware=bootstrap_declared_calibrated,
        paired_rule_contrasts_frozen=np.stack(
            [frozen_rule[:, :, left] - frozen_rule[:, :, right] for left, right, _ in comparisons],
            axis=-1,
        ),
        paired_rule_contrasts_calibration_aware=np.stack(
            [
                calibration_rule[:, :, left] - calibration_rule[:, :, right]
                for left, right, _ in comparisons
            ],
            axis=-1,
        ),
        metric_names=np.asarray(metric_names),
        rule_names=np.asarray(RULE_NAMES),
        bootstrap_seed=np.asarray(BOOTSTRAP_SEED, dtype=np.int64),
    )

    _plot_outputs(output, values["betas"], cutoff_curve, values["cell_ids"], point_rates)
    cell_index = {str(cell_id): index for index, cell_id in enumerate(values["cell_ids"])}
    forecast_rows: list[dict[str, Any]] = []

    def forecast(
        name: str,
        estimate: float,
        samples: FloatArray,
        relation: str,
        lower: float | None = None,
        upper: float | None = None,
    ) -> None:
        interval = _mean_summary(samples, estimate)
        low, high = interval["low"], interval["high"]
        if relation == "between":
            assert lower is not None and upper is not None
            status = (
                "supported"
                if low >= lower and high <= upper
                else "contradicted"
                if high < lower or low > upper
                else "unresolved"
            )
        elif relation == "le":
            assert upper is not None
            status = (
                "supported" if high <= upper else "contradicted" if low > upper else "unresolved"
            )
        elif relation == "ge":
            assert lower is not None
            status = (
                "supported" if low >= lower else "contradicted" if high < lower else "unresolved"
            )
        elif relation == "gt":
            assert lower is not None
            status = (
                "supported" if low > lower else "contradicted" if high <= lower else "unresolved"
            )
        else:
            raise ValueError(relation)
        forecast_rows.append(
            {
                "forecast": name,
                "estimate": estimate,
                "calibration_aware_low": low,
                "calibration_aware_high": high,
                "relation": relation,
                "lower": lower,
                "upper": upper,
                "status": status,
                "descriptive_only": True,
                "gate": False,
            }
        )

    for cell_id in ("E0_h1", "E06_h1"):
        cell = cell_index[cell_id]
        forecast(
            f"{cell_id} primary fullsup null size 0.02--0.05",
            float(point_rates[cell, PRIMARY_RULE_INDEX]),
            calibration_rule[:, cell, PRIMARY_RULE_INDEX],
            "between",
            lower=0.02,
            upper=0.05,
        )
    for cell_id, lower, upper in (("E0_h3", 0.65, 0.80), ("E06_h3", 0.88, None)):
        cell = cell_index[cell_id]
        forecast(
            f"{cell_id} primary fullsup sensitivity",
            float(point_rates[cell, PRIMARY_RULE_INDEX]),
            calibration_rule[:, cell, PRIMARY_RULE_INDEX],
            "between" if upper is not None else "ge",
            lower=lower,
            upper=upper,
        )
    b100 = cell_index["B100-A_h1"]
    forecast(
        "B100-A_h1 primary fullsup <= 0.06",
        float(point_rates[b100, PRIMARY_RULE_INDEX]),
        calibration_rule[:, b100, PRIMARY_RULE_INDEX],
        "le",
        upper=0.06,
    )
    forecast(
        "B100-A_h1 constant beta0 >= 0.18",
        float(point_rates[b100, CONSTANT_RULE_INDEX]),
        calibration_rule[:, b100, CONSTANT_RULE_INDEX],
        "ge",
        lower=0.18,
    )
    nonlinear = cell_index["N100-A_h1"]
    delta_samples = (
        calibration_rule[:, nonlinear, PRIMARY_RULE_INDEX]
        - calibration_rule[:, b100, PRIMARY_RULE_INDEX]
    )
    forecast(
        "N100-A_h1 primary fullsup > B100-A_h1",
        float(point_rates[nonlinear, PRIMARY_RULE_INDEX] - point_rates[b100, PRIMARY_RULE_INDEX]),
        delta_samples,
        "gt",
        lower=0.0,
    )
    sidecar = input_path.with_name("run_summary.json")
    summary: dict[str, Any] = {
        "status": "complete_descriptive_null_effect_synthesis",
        "input_sha256": digest,
        "input_path_name": input_path.name,
        "strict": strict,
        "reference_blocks": int(values["reference_t_adj"].shape[0]),
        "evaluation_blocks": int(n),
        "beta_nodes": int(nodes),
        "effect_nodes": int(values["effects"].shape[0]),
        "cell_ids": [str(value) for value in values["cell_ids"]],
        "bootstrap_draws": int(bootstrap_draws),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "reference_bootstrap_pairing": "whole blocks paired across beta nodes",
        "evaluation_bootstrap_pairing": "whole blocks paired across all eight cells",
        "tolerance": TOLERANCE,
        "alpha": ALPHA,
        "berger_boos_gamma": BERGER_BOOS_GAMMA,
        "methods": ["adjusted", "constant"],
        "textbook_cutoffs_descriptive_only": list(TEXTBOOK_CUTOFFS),
        "undefined_conditional_bootstrap_count": int(
            sum(np.isnan(array).sum() for array in calibration_declared.values())
            + sum(np.isnan(array).sum() for array in frozen_declared.values())
        ),
        "primary_rule": "max_j p_j(T_adj) <= 0.05",
        "constant_rule": "p_beta0(T_constant) <= 0.05",
        "berger_boos_rule": (
            "min(1, max_{j:q_j>0.01} p_j(T_adj)+0.01) <= 0.05; empty candidate set is 1"
        ),
        "order_statistic_ranks": {
            "primary": int(
                values["reference_t_adj"].shape[0]
                - np.floor(ALPHA * (values["reference_t_adj"].shape[0] + 1))
                + 1
            ),
            "berger_boos_t": int(
                values["reference_t_adj"].shape[0]
                - np.floor((ALPHA - BERGER_BOOS_GAMMA) * (values["reference_t_adj"].shape[0] + 1))
                + 1
            ),
            "q_membership": int(
                values["reference_t_adj"].shape[0]
                - np.floor(BERGER_BOOS_GAMMA * (values["reference_t_adj"].shape[0] + 1))
                + 1
            ),
        },
        "rule_rates": rule_rows,
        "paired_rule_contrasts": contrast_rows,
        "registered_forecasts": forecast_rows,
        "provenance_sidecar": sidecar.name if sidecar.is_file() else None,
    }
    if sidecar.is_file():
        summary["provenance_sidecar_sha256"] = hashlib.sha256(sidecar.read_bytes()).hexdigest()
    primary_cutoffs = np.asarray(decision["primary_cutoff"])
    critical_nodes = np.flatnonzero(
        np.isclose(primary_cutoffs, primary_cutoffs.max(), rtol=0, atol=TOLERANCE)
    )
    summary["effective_primary_cutoff"] = float(primary_cutoffs.max())
    summary["critical_beta_indices"] = critical_nodes.tolist()
    summary["critical_betas"] = values["betas"][critical_nodes].tolist()
    summary["critical_cutoff_at_boundary"] = bool(
        0 in critical_nodes or len(primary_cutoffs) - 1 in critical_nodes
    )
    summary["constant_calibrated_cutoff"] = float(np.asarray(decision["constant_cutoff"]))
    summary["fit_boundary_rates"] = [
        {
            "cell_id": str(cell_id),
            "adjusted_h_lower": float(np.mean(values["evaluation_h_hat_adj"][:, c] == 1.0)),
            "adjusted_h_upper": float(np.mean(values["evaluation_h_hat_adj"][:, c] == 10.0)),
            "constant_h_lower": float(np.mean(values["evaluation_h_hat_constant"][:, c] == 1.0)),
            "constant_h_upper": float(np.mean(values["evaluation_h_hat_constant"][:, c] == 10.0)),
            "adjusted_beta_edge": float(
                np.mean(np.abs(values["evaluation_beta_hat_adj"][:, c]) == 2.0)
            ),
            "null_beta_edge": float(
                np.mean(np.abs(values["evaluation_beta_hat_null"][:, c]) == 2.0)
            ),
        }
        for c, cell_id in enumerate(values["cell_ids"])
    ]
    summary["output_hashes"] = {
        name: hashlib.sha256((output / name).read_bytes()).hexdigest()
        for name in sorted(generated_names)
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=_json_default, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    return summary


__all__ = [
    "ALPHA",
    "BERGER_BOOS_GAMMA",
    "BOOTSTRAP_DRAWS",
    "BOOTSTRAP_SEED",
    "CELL_IDS",
    "RULE_NAMES",
    "TOLERANCE",
    "decision_rule",
    "pvalues",
    "synthesize",
]
