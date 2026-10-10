"""Core engine for the 2026 midterm Monte Carlo model.

Every margin is D-minus-R in percentage points (positive = Democratic / Dem-side ahead).
See METHODOLOGY.md for the reasoning behind each formula.
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))


def load_config(path=None):
    with open(path or os.path.join(HERE, "config.yaml")) as f:
        return yaml.safe_load(f)


def _lookup(table: dict, n: int):
    n = int(n)
    keys = sorted(int(k) for k in table)
    k = max(x for x in keys if x <= n) if n >= keys[0] else keys[0]
    return float(table[k] if k in table else table[str(k)])


# --------------------------------------------------------------------------- Senate
def senate_estimates(cfg) -> pd.DataFrame:
    s = cfg["senate"]
    gb = cfg["generic_ballot_margin"]
    ev = cfg.get("early_vote_adjustment", {}) or {}
    df = pd.read_csv(os.path.join(HERE, "data", "senate_races.csv"))
    df["poll_sources"] = df["poll_sources"].fillna(0).astype(int)
    sign = np.where(df["holder"] == "D", 1.0, -1.0)
    inc = np.select([df["inc_status"] == "running", df["inc_status"] == "appointed"],
                    [s["incumbency_bonus"], s["appointed_incumbency_bonus"]], 0.0) * sign
    cand = df["candidate_adj"].fillna(0.0) if s.get("use_candidate_adjustments", True) else 0.0
    df["fundamentals_margin"] = s["pvi_multiplier"] * df["pvi_d"] + gb + inc + cand
    df["poll_weight"] = [(_lookup(s["poll_weight_by_sources"], n) if pd.notna(p) else 0.0)
                         for n, p in zip(df["poll_sources"], df["poll_margin_d"])]
    df["race_sd"] = [_lookup(s["race_sd_by_sources"], n if pd.notna(p) else 0)
                     for n, p in zip(df["poll_sources"], df["poll_margin_d"])]
    poll = df["poll_margin_d"].fillna(0.0)
    df["early_vote_adj"] = df["state"].map(lambda x: float(ev.get(x, 0.0)))
    df["est_margin"] = df["poll_weight"] * poll + (1 - df["poll_weight"]) * df["fundamentals_margin"] + df["early_vote_adj"]
    return df


# --------------------------------------------------------------------------- House
def house_estimates(cfg) -> pd.DataFrame:
    h = cfg["house"]
    gb = cfg["generic_ballot_margin"]
    ev = cfg.get("early_vote_adjustment", {}) or {}
    df = pd.read_csv(os.path.join(HERE, "data", "house_districts.csv"))
    sign = df["inc_party"].map({"D": 1.0, "R": -1.0, "I": -1.0}).fillna(0.0)  # Kiley (I) treated as R-aligned incumbent
    inc = h["incumbency_bonus"] * sign * df["inc_running"]
    df["fundamentals_margin"] = h["pvi_multiplier"] * df["pvi_d"] + gb + inc + h.get("seat_bias", 0.0) \
        + df["state"].map(lambda x: float(ev.get(x, 0.0)))
    polls = pd.read_csv(os.path.join(HERE, "data", "house_district_polls.csv"))
    df = df.merge(polls[["district", "poll_margin_d"]], on="district", how="left")
    w = np.where(df["poll_margin_d"].notna(), h["district_poll_weight"], 0.0)
    df["est_margin"] = w * df["poll_margin_d"].fillna(0) + (1 - w) * df["fundamentals_margin"]
    df["race_sd"] = np.where(df["poll_margin_d"].notna(), h["district_sd_with_poll"], h["district_sd"])
    return df


# --------------------------------------------------------------------------- Seat distributions
def seat_histogram(seats, max_seats: int, majority: int):
    """Full simulated distribution of a seat count: one integer count per seat value 0..max_seats.

    `seats` is the per-simulation array (Senate D+I seats or House D seats). Returns a dict with the
    count vector plus summary stats so downstream consumers never need the raw sims.
    """
    seats = np.asarray(seats).astype(np.int64)
    counts = np.bincount(seats, minlength=max_seats + 1)
    if len(counts) > max_seats + 1:
        raise ValueError(f"seat count above {max_seats} in simulation output")
    n = int(len(seats))
    return dict(
        sims=n, max_seats=int(max_seats), majority=int(majority), majority_line=majority - 0.5,
        mean=float(seats.mean()), median=float(np.median(seats)),
        p10=int(np.percentile(seats, 10)), p90=int(np.percentile(seats, 90)),
        min=int(seats.min()), max=int(seats.max()),
        p_at_or_above_majority=float((seats >= majority).mean()),
        counts=[int(c) for c in counts],
    )


# --------------------------------------------------------------------------- Simulation
def simulate(cfg, bias_mean: float, bias_sd: float, n: int | None = None, seed: int | None = None):
    n = int(n or cfg["simulations"])
    rng = np.random.default_rng(cfg.get("seed", 0) if seed is None else seed)
    sen = senate_estimates(cfg)
    hou = house_estimates(cfg)

    states = sorted(set(sen["state"]) | set(hou["state"]))
    sidx = {s: i for i, s in enumerate(states)}
    # Correlated components ------------------------------------------------
    national = rng.normal(bias_mean, bias_sd, size=n).astype(np.float32)          # polls overstate D by this much
    state_err = rng.normal(0, cfg["state_error_sd"], size=(n, len(states))).astype(np.float32)

    # ---------------- Senate
    s_est = sen["est_margin"].to_numpy(np.float32)
    s_sd = sen["race_sd"].to_numpy(np.float32)
    s_st = np.array([sidx[x] for x in sen["state"]])
    s_m = s_est[None, :] - national[:, None] + state_err[:, s_st] + rng.normal(0, 1, (n, len(sen))).astype(np.float32) * s_sd
    dside_win = s_m > 0
    is_ind = (sen["dem_side_party"] == "I").to_numpy()
    scfg = cfg["senate"]
    d_seats = scfg["seats_not_up_D"] + (dside_win & ~is_ind).sum(1)
    r_seats = scfg["seats_not_up_R"] + (~dside_win).sum(1)
    i_seats = (dside_win & is_ind).sum(1)
    pD, pR = scfg["independent_caucus"].get("D", 0.0), scfg["independent_caucus"].get("R", 0.0)
    # each independent winner independently picks a caucus
    i_to_D = rng.binomial(i_seats, pD)
    rem = i_seats - i_to_D
    i_to_R = rng.binomial(rem, pR / (1 - pD)) if pD < 1 and pR > 0 else np.zeros_like(rem)
    d_eff, r_eff = d_seats + i_to_D, r_seats + i_to_R
    vp = scfg["vp_party"]
    r_ctrl = (r_eff >= 51) | ((r_eff == 50) & (vp == "R"))
    d_ctrl = ~r_ctrl & ((d_eff >= 51) | ((d_eff == 50) & (vp == "D")))
    # tipping point: order races from most-D to most-R; D needs (51 - not-up D) D-side wins
    need = 51 - scfg["seats_not_up_D"]
    order = np.argsort(-s_m, axis=1)
    tip = order[:, need - 1]

    sen_out = sen.copy()
    sen_out["p_dem_side"] = dside_win.mean(0)
    sen_out["sim_mean_margin"] = s_m.mean(0)
    sen_out["sim_p10"] = np.percentile(s_m, 10, axis=0)
    sen_out["sim_p90"] = np.percentile(s_m, 90, axis=0)
    sen_out["tipping_freq"] = np.bincount(tip, minlength=len(sen)) / n

    # ---------------- House
    h_est = hou["est_margin"].to_numpy(np.float32)
    h_sd = hou["race_sd"].to_numpy(np.float32)
    h_st = np.array([sidx[x] for x in hou["state"]])
    hcfg = cfg["house"]
    maj = hcfg["majority"]
    d_house = np.empty(n, dtype=np.int32)
    tip_h = np.empty(n, dtype=np.int32)
    p_d = np.zeros(len(hou)); msum = np.zeros(len(hou))
    tip_counts = np.zeros(len(hou))
    chunk = 5000
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        m = h_est[None, :] - national[a:b, None] + state_err[a:b][:, h_st] \
            + rng.normal(0, 1, (b - a, len(hou))).astype(np.float32) * h_sd
        w = m > 0
        d_house[a:b] = w.sum(1)
        p_d += w.sum(0); msum += m.sum(0)
        # 218th most-Democratic seat
        part = np.argpartition(-m, maj - 1, axis=1)[:, maj - 1]
        tip_h[a:b] = part
        tip_counts += np.bincount(part, minlength=len(hou))
    hou_out = hou.copy()
    hou_out["p_dem"] = p_d / n
    hou_out["sim_mean_margin"] = msum / n
    hou_out["tipping_freq"] = tip_counts / n

    return dict(
        n=n, bias_mean=bias_mean, bias_sd=bias_sd,
        senate=sen_out, house=hou_out,
        senate_d_eff=d_eff, senate_r_eff=r_eff, senate_d=d_seats, senate_r=r_seats, senate_i=i_seats,
        senate_r_ctrl=r_ctrl.mean(), senate_d_ctrl=d_ctrl.mean(), senate_none=1 - r_ctrl.mean() - d_ctrl.mean(),
        house_d=d_house, house_d_ctrl=(d_house >= maj).mean(), national=national,
    )
