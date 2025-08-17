"""
directional_and_thirds.py
-------------------------
Passing metrics:
- Direction classification: forward / backward / sideways based on Δx.
- Pitch thirds: origin and destination thirds by x (0-120 by default).
- Flow between thirds: counts for origin_third -> destination_third.
- Direction per third: counts of attempts by direction within origin third.

Assumptions:
- Coordinates are normalised so the attacking team moves LEFT -> RIGHT (x increases toward goal).
  If your pipeline does not normalise, pass `x_flip_col` that is True for rows that need flipping.
  When flipped, we transform (x, end_x) to (x_max - x, x_max - end_x).

Dependencies:
- StatsBomb-like flattened columns: "x", "y", "end_x", "end_y", "type" == "Pass".
- Works if your columns are named "location_x" / "pass_end_x" too — map them via parameters.
"""

from __future__ import annotations
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np


def _pick(df: pd.DataFrame, candidates: Tuple[str, ...]) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    raise ValueError(f"None of the candidate columns found: {candidates}")


def _normalise_lr(
    df: pd.DataFrame, x_col: str, end_x_col: str, x_max: float, flip_mask: Optional[pd.Series]
) -> pd.DataFrame:
    if flip_mask is None:
        return df
    out = df.copy()
    idx = flip_mask.fillna(False)
    if idx.any():
        out.loc[idx, x_col] = x_max - out.loc[idx, x_col]
        out.loc[idx, end_x_col] = x_max - out.loc[idx, end_x_col]
    return out


def _third(x: float, x_max: float) -> str:
    if pd.isna(x):
        return "unknown"
    b1 = x_max / 3.0
    b2 = 2.0 * x_max / 3.0
    if x < b1:
        return "D3"  # Defensive third
    elif x < b2:
        return "M3"  # Middle third
    else:
        return "A3"  # Attacking third


def prepare_pass_df(
    events: pd.DataFrame,
    *,
    type_col: str = "type",
    pass_label: str = "Pass",
    x_col_candidates: Tuple[str, ...] = ("x", "location_x", "start_x"),
    y_col_candidates: Tuple[str, ...] = ("y", "location_y", "start_y"),
    end_x_col_candidates: Tuple[str, ...] = ("end_x", "pass_end_x"),
    end_y_col_candidates: Tuple[str, ...] = ("end_y", "pass_end_y"),
    x_max: float = 120.0,
    x_flip_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Return a pass-only dataframe with standardised columns:
    ['x','y','end_x','end_y','delta_x','origin_third','dest_third','direction'].
    """
    if type_col not in events.columns:
        raise ValueError(f"events missing '{type_col}'")

    df = events[events[type_col] == pass_label].copy()

    x_col = _pick(df, x_col_candidates)
    y_col = _pick(df, y_col_candidates)
    ex_col = _pick(df, end_x_col_candidates)
    ey_col = _pick(df, end_y_col_candidates)

    flip_mask = df[x_flip_col] if (x_flip_col and x_flip_col in df.columns) else None
    df = _normalise_lr(df, x_col, ex_col, x_max, flip_mask)

    df["x"] = df[x_col].astype(float)
    df["y"] = df[y_col].astype(float)
    df["end_x"] = df[ex_col].astype(float)
    df["end_y"] = df[ey_col].astype(float)

    df["delta_x"] = df["end_x"] - df["x"]

    sideways_eps = 5.0  # tolerance around zero for "sideways"
    df["direction"] = np.where(
        df["delta_x"] > sideways_eps, "forward",
        np.where(df["delta_x"] < -sideways_eps, "backward", "sideways")
    )

    df["origin_third"] = df["x"].apply(lambda v: _third(v, x_max))
    df["dest_third"]   = df["end_x"].apply(lambda v: _third(v, x_max))

    return df


def aggregate_passing_metrics(passes_df: pd.DataFrame, group_cols: List[str]) -> pd.DataFrame:
    """
    Build a compact metric table with:
      - pass_attempts
      - pass_fwd / pass_bwd / pass_side
      - pass_from_D3 / pass_from_M3 / pass_from_A3
      - flows between thirds (D3->M3, M3->A3, etc.)
    """
    req = set(group_cols + ["direction", "origin_third", "dest_third"])
    if not req.issubset(passes_df.columns):
        missing = req - set(passes_df.columns)
        raise ValueError(f"passes_df missing cols: {missing}")

    base = (
        passes_df.groupby(group_cols, as_index=False)
        .size().rename(columns={"size": "pass_attempts"})
    )

    dir_counts = (
        passes_df.groupby(group_cols + ["direction"], as_index=False)
        .size()
        .pivot(index=group_cols, columns="direction", values="size")
        .fillna(0)
        .reset_index()
        .rename(columns={"forward": "pass_fwd", "backward": "pass_bwd", "sideways": "pass_side"})
    )

    third_counts = (
        passes_df.groupby(group_cols + ["origin_third"], as_index=False)
        .size()
        .pivot(index=group_cols, columns="origin_third", values="size")
        .fillna(0)
        .reset_index()
        .rename(columns={"D3": "pass_from_D3", "M3": "pass_from_M3", "A3": "pass_from_A3"})
    )

    flows = (
        passes_df.groupby(group_cols + ["origin_third", "dest_third"], as_index=False)
        .size()
    )
    flows["flow"] = flows["origin_third"] + "->" + flows["dest_third"]
    flow_pivot = flows.pivot(index=group_cols, columns="flow", values="size").fillna(0).reset_index()

    out = base.merge(dir_counts, on=group_cols, how="left")
    out = out.merge(third_counts, on=group_cols, how="left")
    out = out.merge(flow_pivot, on=group_cols, how="left")

    preferred_flow_order = [
        "D3->D3","D3->M3","D3->A3",
        "M3->D3","M3->M3","M3->A3",
        "A3->D3","A3->M3","A3->A3",
    ]
    for col in preferred_flow_order:
        if col not in out.columns:
            out[col] = 0

    numeric_cols = [c for c in out.columns if c not in group_cols and pd.api.types.is_numeric_dtype(out[c])]
    out[numeric_cols] = out[numeric_cols].fillna(0).astype(float)

    return out
