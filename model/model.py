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


def factor_on(cfg, name: str) -> bool:
    return bool((cfg.get("factors") or {}).get(name, False))


def generic_ballot(cfg) -> float:
    gb = float(cfg["generic_ballot_margin"])
    if factor_on(cfg, "poll_cleanup"):
        gb += float(cfg.get("generic_ballot_lv_adjustment", 0.0))
    return gb


def load_demographics():
    d = pd.read_csv(os.path.join(HERE, "data", "state_demographics.csv"))
    return d.set_index("state")


def _interp_margin(score, table: dict):
    xs = sorted(float(k) for k in table)
    ys = [float(table[k] if k in table else table[str(k)]) for k in sorted(table, key=float)]
    return np.sign(score) * np.interp(np.abs(score), xs, ys)


# --------------------------------------------------------------------------- Senate
def senate_estimates(cfg) -> pd.DataFrame:
    s = cfg["senate"]
    gb = generic_ballot(cfg)
    ev = cfg.get("early_vote_adjustment", {}) or {}
    demo = load_demographics()
    df = pd.read_csv(os.path.join(HERE, "data", "senate_races.csv"))
    df["poll_sources"] = df["poll_sources"].fillna(0).astype(int)
    df["census_region"] = df["state"].map(demo["census_region"])
    df["hispanic_share"] = df["state"].map(demo["hispanic_share_2020"])
    sign = np.where(df["holder"] == "D", 1.0, -1.0)
    appointed = s["appointed_incumbency_bonus_v2"] if factor_on(cfg, "incumbency_reweight") else s["appointed_incumbency_bonus"]
    inc = np.select([df["inc_status"] == "running", df["inc_status"] == "appointed"],
                    [s["incumbency_bonus"], appointed], 0.0) * sign
    cand = df["candidate_adj"].fillna(0.0) if s.get("use_candidate_adjustments", True) else 0.0
    cq = df["state"].map(lambda x: float((s.get("candidate_quality") or {}).get(x, 0.0))) \
        if factor_on(cfg, "candidate_quality") else 0.0
    df["candidate_quality_adj"] = cq
    df["incumbency_adj"] = inc
    fund = s["pvi_multiplier"] * df["pvi_d"] + gb + inc + cand + cq
    # Factor 8: three-way races - runner-up only gets part of the anti-R vote
    df["mechanics_extra_sd"] = 0.0
    df["mechanics_note"] = ""
    if factor_on(cfg, "election_mechanics"):
        for st, tw in (s.get("three_way") or {}).items():
            m = df["state"] == st
            c = float(tw["runner_up_share_of_anti_r"])
            anti_r, rep = 50 + fund[m] / 2, 50 - fund[m] / 2
            fund[m] = c * anti_r - rep
            df.loc[m, "mechanics_extra_sd"] += float(tw.get("extra_sd", 0.0))
            df.loc[m, "mechanics_note"] = f"three-way: runner-up gets {c:.0%} of anti-R vote"
        for st, rc in (s.get("rcv") or {}).items():
            m = df["state"] == st
            fund[m] = fund[m] + float(rc.get("mean_shift", 0.0))
            df.loc[m, "mechanics_extra_sd"] += float(rc.get("extra_sd", 0.0))
            df.loc[m, "mechanics_note"] = "ranked-choice transfer uncertainty"
    df["fundamentals_margin"] = fund

    has_poll = df["poll_margin_d"].notna()
    base_w = np.array([(_lookup(s["poll_weight_by_sources"], n) if hp else 0.0)
                       for n, hp in zip(df["poll_sources"], has_poll)])
    df["race_sd_base"] = [_lookup(s["race_sd_by_sources"], n if hp else 0) for n, hp in zip(df["poll_sources"], has_poll)]
    poll = df["poll_margin_d"].copy()
    # Factor 5b: partisan-sponsor shift + weight discount, staleness discount
    df["poll_weight_mult_cleanup"] = 1.0
    if factor_on(cfg, "poll_cleanup"):
        pc = s["poll_cleanup"]
        spons = df["poll_sponsor_partisan"].fillna("")
        shift = np.select([spons == "D", spons == "R"], [-pc["partisan_poll_shift"], pc["partisan_poll_shift"]], 0.0)
        poll = poll + shift
        mult = np.where(spons.isin(["D", "R"]), pc["partisan_poll_weight_mult"], 1.0)
        asof = pd.Timestamp(cfg.get("as_of", "2026-10-10"))
        days = (asof - pd.to_datetime(df["poll_end_date"])).dt.days.fillna(0).clip(lower=0)
        stale = 0.5 ** (np.clip(days - pc["stale_grace_days"], 0, None) / pc["stale_half_life_days"])
        df["poll_age_days"] = days
        df["poll_weight_mult_cleanup"] = mult * stale
    df["poll_margin_adj"] = poll
    # Factor 1: herding-aware weighting
    gap = (poll - df["fundamentals_margin"]).abs().fillna(0.0)
    df["poll_fund_gap"] = (poll - df["fundamentals_margin"])
    df["poll_weight_mult_herding"] = 1.0
    herd_sd = 0.0
    if factor_on(cfg, "herding"):
        hz = s["herding"]
        excess = np.clip(gap - hz["threshold"], 0, None)
        df["poll_weight_mult_herding"] = np.maximum(hz["floor"], 1 - hz["sensitivity"] * excess)
        herd_sd = hz["sd_per_gap_pt"] * excess * has_poll
    df["poll_weight_base"] = base_w
    df["poll_weight"] = base_w * df["poll_weight_mult_cleanup"] * df["poll_weight_mult_herding"]
    df["race_sd"] = np.sqrt((df["race_sd_base"] + herd_sd) ** 2 + df["mechanics_extra_sd"] ** 2)
    df["early_vote_adj"] = df["state"].map(lambda x: float(ev.get(x, 0.0)))
    df["est_margin"] = df["poll_weight"] * poll.fillna(0.0) + (1 - df["poll_weight"]) * df["fundamentals_margin"] + df["early_vote_adj"]
    return df


# --------------------------------------------------------------------------- House
def house_estimates(cfg) -> pd.DataFrame:
    h = cfg["house"]
    gb = generic_ballot(cfg)
    ev = cfg.get("early_vote_adjustment", {}) or {}
    demo = load_demographics()
    df = pd.read_csv(os.path.join(HERE, "data", "house_districts.csv"))
    df["census_region"] = df["state"].map(demo["census_region"])
    df["hispanic_share"] = df["state"].map(demo["hispanic_share_2020"]) if \
        (cfg.get("demographic_regional") or {}).get("house_use_state_hispanic_share", True) else 0.0
    sign = df["inc_party"].map({"D": 1.0, "R": -1.0, "I": -1.0}).fillna(0.0)  # Kiley (I) treated as R-aligned incumbent
    if factor_on(cfg, "incumbency_reweight"):
        bonus = h["incumbency_bonus_v2"] * np.where(df["state"].isin(h.get("redrawn_states", [])),
                                                    h.get("redrawn_incumbency_mult", 1.0), 1.0)
    else:
        bonus = h["incumbency_bonus"]
    inc = bonus * sign * df["inc_running"]
    df["fundamentals_margin"] = h["pvi_multiplier"] * df["pvi_d"] + gb + inc + h.get("seat_bias", 0.0) \
        + df["state"].map(lambda x: float(ev.get(x, 0.0)))
    polls = pd.read_csv(os.path.join(HERE, "data", "house_district_polls.csv"))
    df = df.merge(polls[["district", "poll_margin_d"]], on="district", how="left")
    has_poll = df["poll_margin_d"].notna()
    # Factor 3: expert ratings
    df["rating_margin"] = np.nan
    df["rating_weight"] = 0.0
    if factor_on(cfg, "expert_ratings"):
        er = h["expert_ratings"]
        score = df["consensus_rating_score"].copy()
        rated = score.notna()
        if er.get("unrated_as_safe", True):
            score = score.where(rated, np.sign(df["pvi_d"]) * 3.0)
            score = score.where(~(~rated & (df["pvi_d"] == 0)), np.nan)
        df["rating_margin"] = _interp_margin(score, er["score_to_margin"]) + er.get("env_shift", 0.0)
        w_r = np.where(has_poll, er["weight_polled"], er["weight_unpolled"])
        w_r = np.where(rated, w_r, er["weight_unrated_safe"])
        df["rating_weight"] = np.where(df["rating_margin"].notna(), w_r, 0.0)
    w_p = np.where(has_poll, h["district_poll_weight"], 0.0)
    w_r = df["rating_weight"].to_numpy()
    w_f = 1 - w_p - w_r
    df["est_margin"] = w_p * df["poll_margin_d"].fillna(0) + w_r * df["rating_margin"].fillna(0) + w_f * df["fundamentals_margin"]
    df["race_sd"] = np.where(has_poll, h["district_sd_with_poll"], h["district_sd"])
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
    fat = factor_on(cfg, "fat_tails")
    em = cfg.get("error_model") or {}
    if not fat:
        bias_sd = float(cfg.get("legacy_poll_bias_sd", bias_sd))

    def draw(shape, df_t):
        """Unit-variance noise: Student-t (rescaled) when fat tails are on, else normal."""
        if fat and df_t:
            return (rng.standard_t(df_t, size=shape) * np.sqrt((df_t - 2) / df_t)).astype(np.float32)
        return rng.standard_normal(shape).astype(np.float32)

    national = (bias_mean + bias_sd * draw(n, em.get("national_t_df"))).astype(np.float32)  # polls overstate D by this much
    state_err = rng.normal(0, cfg["state_error_sd"], size=(n, len(states))).astype(np.float32)
    # Factor 2: demographic (Hispanic) + regional shared shocks
    dr = cfg.get("demographic_regional") or {}
    regions = ["Northeast", "Midwest", "South", "West"]
    ridx = {r: i for i, r in enumerate(regions)}
    if factor_on(cfg, "demographic_regional"):
        hisp_shock = rng.normal(0, dr.get("hispanic_error_sd", 0.0), size=n).astype(np.float32)
        reg_err = rng.normal(0, dr.get("regional_error_sd", 0.0), size=(n, len(regions))).astype(np.float32)
    else:
        hisp_shock = np.zeros(n, np.float32)
        reg_err = np.zeros((n, len(regions)), np.float32)
    race_df = em.get("race_t_df")

    # ---------------- Senate
    s_est = sen["est_margin"].to_numpy(np.float32)
    s_sd = sen["race_sd"].to_numpy(np.float32)
    s_st = np.array([sidx[x] for x in sen["state"]])
    s_rg = np.array([ridx[x] for x in sen["census_region"]])
    s_h = sen["hispanic_share"].to_numpy(np.float32)
    s_m = s_est[None, :] - national[:, None] + state_err[:, s_st] + reg_err[:, s_rg] + hisp_shock[:, None] * s_h[None, :] \
        + draw((n, len(sen)), race_df) * s_sd
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
    h_rg = np.array([ridx[x] for x in hou["census_region"]])
    h_h = hou["hispanic_share"].to_numpy(np.float32)
    hcfg = cfg["house"]
    maj = hcfg["majority"]
    d_house = np.empty(n, dtype=np.int32)
    tip_h = np.empty(n, dtype=np.int32)
    p_d = np.zeros(len(hou)); msum = np.zeros(len(hou))
    tip_counts = np.zeros(len(hou))
    chunk = 5000
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        m = h_est[None, :] - national[a:b, None] + state_err[a:b][:, h_st] + reg_err[a:b][:, h_rg] \
            + hisp_shock[a:b, None] * h_h[None, :] + draw((b - a, len(hou)), race_df) * h_sd
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
