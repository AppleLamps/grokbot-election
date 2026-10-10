#!/usr/bin/env python3
"""Entry point.  Examples:
  .venv/bin/python run.py --scenario all
  .venv/bin/python run.py --scenario unbiased
  .venv/bin/python run.py --scenario custom --bias 1.5 --bias-sd 2.5
  .venv/bin/python run.py --scenario all --generic-ballot 5 --sims 20000
"""
import argparse, os, re, sys, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from model import load_config, simulate, seat_histogram, generic_ballot, HERE

ALIASES = {"i": "unbiased", "ii": "pres_style_D_overstatement", "iii": "r_overstatement_2025"}


def pct(x):
    return f"{100 * x:.1f}%"


def summarize(name, label, r):
    sen, hou = r["senate"], r["house"]
    deff, reff = r["senate_d_eff"], r["senate_r_eff"]
    hd = r["house_d"]
    tip_s = sen.sort_values("tipping_freq", ascending=False).head(5)
    tip_h = hou.sort_values("tipping_freq", ascending=False).head(5)
    return dict(
        scenario=name, label=label, bias_mean=r["bias_mean"], bias_sd=r["bias_sd"], sims=r["n"],
        senate_p_R=r["senate_r_ctrl"], senate_p_D=r["senate_d_ctrl"], senate_p_none=r["senate_none"],
        senate_D_mean=float(deff.mean()), senate_D_p10=int(np.percentile(deff, 10)), senate_D_p90=int(np.percentile(deff, 90)),
        senate_R_mean=float(reff.mean()), senate_R_p10=int(np.percentile(reff, 10)), senate_R_p90=int(np.percentile(reff, 90)),
        senate_I_mean=float(r["senate_i"].mean()),
        house_p_D=r["house_d_ctrl"], house_p_R=1 - r["house_d_ctrl"],
        house_D_mean=float(hd.mean()), house_D_median=int(np.median(hd)), house_D_p10=int(np.percentile(hd, 10)), house_D_p90=int(np.percentile(hd, 90)),
        senate_tipping=[(row.state, round(row.tipping_freq, 3)) for row in tip_s.itertuples()],
        house_tipping=[(row.district, round(row.tipping_freq, 3)) for row in tip_h.itertuples()],
        **governor_summary(r),
    )


GOV_NOT_UP = {"D": 6, "R": 8}   # 24 D / 26 R governors now; 18 D + 18 R seats are up in 2026


def governor_summary(r):
    gd = r.get("governor_d")
    if gd is None:
        return {}
    tot = GOV_NOT_UP["D"] + gd
    return dict(gov_races=int(len(r["governor"])), gov_D_wins_mean=float(gd.mean()),
                gov_D_total_mean=float(tot.mean()), gov_D_total_median=int(np.median(tot)),
                gov_D_total_p10=int(np.percentile(tot, 10)), gov_D_total_p90=int(np.percentile(tot, 90)),
                gov_p_D_majority=float((tot >= 26).mean()))


def governor_table(gov):
    t = gov[["state", "state_name", "holder", "incumbent", "inc_status", "dem_candidate", "rep_candidate", "challenger_party", "pvi_d", "rating_score",
             "prior_margin", "poll_margin_d", "poll_sources", "poll_end_date", "poll_weight", "est_margin", "race_sd",
             "sim_p10", "sim_p90", "p_dem", "market_p_dem_polymarket", "poll_note"]].copy()
    t["p_rep"] = 1 - t["p_dem"]
    return t.sort_values("p_dem", ascending=False)


def seat_distributions(r, cfg):
    """Full seat-by-seat histograms for one scenario run (counts per integer seat value)."""
    return dict(
        senate=dict(seat_histogram(r["senate_d_eff"], 100, 51),
                    description="Senate seats held by Democrats + independents caucusing with Democrats in that simulation (0-100). "
                                "51 = D majority; at 50 the VP (R) breaks ties."),
        house=dict(seat_histogram(r["house_d"], 435, cfg["house"]["majority"]),
                   description="House seats won by Democrats (0-435). 218 = majority."),
    )


def compact_json(obj, path):
    """indent=2 JSON, but keep integer count arrays on one line so the file stays small and readable."""
    txt = json.dumps(obj, indent=2, default=float)
    txt = re.sub(r"\[\s*((?:-?\d+,\s*)+-?\d+)\s*\]", lambda m: "[" + ",".join(x.strip() for x in m.group(1).split(",")) + "]", txt)
    with open(path, "w") as f:
        f.write(txt + "\n")


def senate_table(sen):
    t = sen[["state", "seat", "holder", "dem_side_candidate", "dem_side_party", "rep_candidate", "pvi_d",
             "poll_margin_d", "poll_margin_adj", "poll_sources", "poll_weight_base", "poll_weight", "candidate_quality_adj",
             "fundamentals_margin", "poll_fund_gap", "est_margin", "race_sd", "census_region", "hispanic_share", "mechanics_note",
             "sim_p10", "sim_p90", "p_dem_side", "tipping_freq"]].copy()
    t["p_rep"] = 1 - t["p_dem_side"]
    return t.sort_values("p_dem_side", ascending=False)


def md_table(df, cols, fmt):
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(fmt.get(c, str)(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def fm(x):
    if pd.isna(x): return "–"
    return f"{'D' if x > 0 else 'R'}+{abs(x):.1f}" if abs(x) >= 0.05 else "EVEN"


def charts(results, outdir):
    os.makedirs(outdir, exist_ok=True)
    names = list(results)
    colors = ["#555555", "#c0392b", "#2c6fbb", "#8e44ad"]
    # Senate distribution
    fig, axes = plt.subplots(len(names), 1, figsize=(9, 2.6 * len(names)), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, nm, c in zip(axes, names, colors):
        r = results[nm]["raw"]; d = r["senate_d_eff"]
        bins = np.arange(d.min() - 0.5, d.max() + 1.5)
        cnt, edges = np.histogram(d, bins=bins)
        x = (edges[:-1] + 0.5).astype(int)
        ax.bar(x, cnt / len(d), color=["#2c6fbb" if v >= 51 else ("#999999" if v == 50 else "#c0392b") for v in x])
        ax.axvline(50.5, color="k", ls="--", lw=1)
        ax.set_title(f"{results[nm]['label']}: P(D control)={pct(r['senate_d_ctrl'])}, P(R control)={pct(r['senate_r_ctrl'])}", fontsize=9)
        ax.set_ylabel("share of sims")
    axes[-1].set_xlabel("Senate seats held by Democrats + D-caucusing independents (51 = D majority; 50 = R control via VP)")
    fig.tight_layout(); p1 = os.path.join(outdir, "senate_seat_distribution.png"); fig.savefig(p1, dpi=130); plt.close(fig)
    # House distribution
    fig, axes = plt.subplots(len(names), 1, figsize=(9, 2.6 * len(names)), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, nm in zip(axes, names):
        r = results[nm]["raw"]; d = r["house_d"]
        ax.hist(d, bins=np.arange(d.min() - 0.5, d.max() + 1.5, 2), color="#2c6fbb", alpha=0.85)
        ax.axvline(217.5, color="k", ls="--", lw=1)
        ax.set_title(f"{results[nm]['label']}: P(D House)={pct(r['house_d_ctrl'])}, median D seats={int(np.median(d))}", fontsize=9)
        ax.set_ylabel("sims")
    axes[-1].set_xlabel("House seats won by Democrats (218 = majority)")
    fig.tight_layout(); p2 = os.path.join(outdir, "house_seat_distribution.png"); fig.savefig(p2, dpi=130); plt.close(fig)
    # Senate race probabilities across scenarios (competitive only)
    base = results[names[0]]["raw"]["senate"]
    comp = base[(base.p_dem_side > 0.02) & (base.p_dem_side < 0.98)].sort_values("p_dem_side")["state"].tolist()
    fig, ax = plt.subplots(figsize=(9, 0.42 * len(comp) + 1.5))
    y = np.arange(len(comp)); h = 0.8 / len(names)
    for k, (nm, c) in enumerate(zip(names, colors)):
        s = results[nm]["raw"]["senate"].set_index("state").loc[comp]
        ax.barh(y + k * h, s["p_dem_side"], height=h, color=c, label=results[nm]["label"])
    ax.axvline(0.5, color="k", lw=0.8)
    ax.set_yticks(y + h * (len(names) - 1) / 2); ax.set_yticklabels(comp)
    ax.set_xlabel("P(Democratic / Dem-side candidate wins)"); ax.set_xlim(0, 1); ax.legend(fontsize=7, loc="lower right")
    ax.set_title("Competitive Senate races by polling-error scenario")
    fig.tight_layout(); p3 = os.path.join(outdir, "senate_race_probabilities.png"); fig.savefig(p3, dpi=130); plt.close(fig)
    return [p1, p2, p3]


def write_report(results, cfg, outdir, chart_paths):
    names = list(results)
    L = ["# 2026 Midterm Model: Results", "",
         f"Generated by `run.py` (model v2: eight additional factors). Simulations per scenario: {cfg['simulations']:,}. "
         f"Generic ballot input: D+{cfg['generic_ballot_margin']} raw, D+{generic_ballot(cfg):.1f} after the likely-voter adjustment. "
         "This is a simplified, transparent model built for scenario analysis, **not a professional forecast**. See METHODOLOGY.md.", "",
         "## Headline by scenario", "",
         "| Scenario | Poll bias (mean ± sd) | P(D Senate) | P(R Senate) | P(no clear majority) | Senate D+I seats (mean, 80% range) | P(D House) | House D seats (median, 80% range) |",
         "|---|---|---|---|---|---|---|---|"]
    for nm in names:
        s = results[nm]["summary"]
        L.append(f"| {s['label']} | {s['bias_mean']:+.1f} ± {s['bias_sd']:.1f} | {pct(s['senate_p_D'])} | {pct(s['senate_p_R'])} | {pct(s['senate_p_none'])} | "
                 f"{s['senate_D_mean']:.1f} ({s['senate_D_p10']}–{s['senate_D_p90']}) | {pct(s['house_p_D'])} | {s['house_D_median']} ({s['house_D_p10']}–{s['house_D_p90']}) |")
    L += ["", "Poll bias > 0 means polls overstate Democrats (reality is more Republican). Senate D+I counts independents only when they caucus with Democrats in that simulation.", ""]
    v1p = os.path.join(outdir, "summary_v1.json")
    if os.path.exists(v1p):
        v1 = json.load(open(v1p))
        L += ["## Before (v1) vs after (v2: eight additional factors)", "",
              "| Scenario | P(D Senate) v1 → v2 | P(R Senate) v1 → v2 | Senate D+I mean v1 → v2 | P(D House) v1 → v2 | House D median v1 → v2 |",
              "|---|---|---|---|---|---|"]
        for nm in names:
            if nm not in v1: continue
            a, b = v1[nm], results[nm]["summary"]
            L.append(f"| {b['label']} | {pct(a['senate_p_D'])} → {pct(b['senate_p_D'])} | {pct(a['senate_p_R'])} → {pct(b['senate_p_R'])} | "
                     f"{a['senate_D_mean']:.2f} → {b['senate_D_mean']:.2f} | {pct(a['house_p_D'])} → {pct(b['house_p_D'])} | {a['house_D_median']} → {b['house_D_median']} |")
        L += ["", "Per-factor marginal effects: see `output/factor_attribution.md` (generated by `scripts/factor_attribution.py`).", ""]
    sp = os.path.join(outdir, "sensitivity.json")
    if os.path.exists(sp):
        sj = json.load(open(sp))
        L += ["## Sensitivity runs", "", "| Run | P(D Senate) | P(R Senate) | Senate D+I mean | P(D House) | House D median |", "|---|---|---|---|---|---|"]
        for k, v in sj.items():
            L.append(f"| {v['label']} | {pct(v['senate_p_D'])} | {pct(v['senate_p_R'])} | {v['senate_D_mean']:.2f} | {pct(v['house_p_D'])} | {v['house_D_median']} |")
        L.append("")
    L += ["## Election mechanics notes", "",
          "- **Alaska and Maine** use ranked-choice voting; the model adds transfer uncertainty (extra race sd 2.0 AK, 1.5 ME) but no mean shift.",
          "- **Montana** is a three-way race (Alme-R, Bodnar-I, Bankhead-D); fundamentals assume the runner-up gets 75% of the anti-Republican vote, plus 2.0 extra sd.",
          "- **Louisiana** House seats go to a **December 12** runoff if no candidate clears 50% under the new map, so some seats (and possibly House control on election night) may not be settled until then. The model scores the final winner only.",
          "- **Georgia** requires 50%+1; the model ignores runoff risk (Ossoff leads by ~8).",
          f"- Independent winners (Osborn NE, Bodnar MT, Achilles ID, Bengs SD) caucus with Democrats with probability {cfg['senate']['independent_caucus'].get('D', 0):.0%} each (assumption).", ""]
    L += ["## Tipping-point races", "",
          "Senate: the seat that gives Democrats their 51st seat when races are ordered from most- to least-Democratic in each simulation. House: the 218th most-Democratic district.", ""]
    for nm in names:
        s = results[nm]["summary"]
        L.append(f"- **{s['label']}** — Senate: " + ", ".join(f"{a} ({pct(b)})" for a, b in s["senate_tipping"][:4])
                 + "; House: " + ", ".join(f"{a} ({pct(b)})" for a, b in s["house_tipping"][:4]))
    L += ["", "## Senate race table", ""]
    for nm in names:
        t = senate_table(results[nm]["raw"]["senate"])
        L += [f"### {results[nm]['label']}", ""]
        t["candidates"] = t["dem_side_candidate"] + " (" + t["dem_side_party"] + ") vs " + t["rep_candidate"] + " (R)"
        L.append(md_table(t, ["state", "candidates", "pvi_d", "poll_margin_d", "poll_sources", "fundamentals_margin", "est_margin", "p_dem_side", "tipping_freq"],
                          {"pvi_d": lambda v: fm(v), "poll_margin_d": fm, "poll_sources": lambda v: str(int(v)),
                           "fundamentals_margin": fm, "est_margin": fm, "p_dem_side": pct, "tipping_freq": pct}))
        L.append("")
    L += ["Columns: pvi_d = Cook PVI (two-party share points); poll_margin_d = polling average margin; fundamentals_margin = 2×PVI + generic ballot + incumbency + candidate adj.; "
          "est_margin = blended pre-error estimate; p_dem_side = P(D or Dem-side independent wins) after polling-error simulation.", ""]
    if results[names[0]]["raw"].get("governor") is not None:
        L += ["## Governors", "",
              "Prior = average of 7 forecaster ratings (Cook, DDHQ, Fox, Inside Elections, RCP, Sabato, Silver Bulletin; Oct 1-8 2026) converted to a margin; "
              "blended with the polling average (mean of Wikipedia-listed aggregators, or recent nonpartisan polls where no aggregate exists). "
              "Shares the national/state/regional polling-error draws with the Senate and House. Polymarket odds are shown for comparison only.", "",
              "| Scenario | D governors after election (median, 80% range, of 50) | D wins of 36 races (mean) | P(D hold 26+ governorships) |", "|---|---|---|---|"]
        for nm in names:
            s_ = results[nm]["summary"]
            L.append(f"| {s_['label']} | {s_['gov_D_total_median']} ({s_['gov_D_total_p10']}–{s_['gov_D_total_p90']}) | {s_['gov_D_wins_mean']:.1f} | {pct(s_['gov_p_D_majority'])} |")
        L.append("")
        g0 = governor_table(results[names[0]]["raw"]["governor"])
        for nm in names[1:]:
            g0[f"p_dem_{nm}"] = results[nm]["raw"]["governor"].set_index("state").loc[g0["state"], "p_dem"].values
        g0["candidates"] = g0["dem_candidate"] + " (D) vs " + g0["rep_candidate"] + " (" + g0["challenger_party"] + ")"
        L.append(md_table(g0, ["state", "candidates", "holder", "rating_score", "prior_margin", "poll_margin_d", "poll_sources", "est_margin", "p_dem"]
                          + [f"p_dem_{nm}" for nm in names[1:]] + ["market_p_dem_polymarket"],
                          {"rating_score": lambda v: f"{v:+.2f}", "prior_margin": fm, "poll_margin_d": fm, "poll_sources": lambda v: str(int(v)),
                           "est_margin": fm, "p_dem": pct, **{f"p_dem_{nm}": pct for nm in names[1:]},
                           "market_p_dem_polymarket": lambda v: "–" if pd.isna(v) else pct(v)}))
        L.append("")
    L += ["## Most competitive House seats (unbiased scenario)", ""]
    h = results[names[0]]["raw"]["house"]
    hc = h[(h.p_dem > 0.1) & (h.p_dem < 0.9)].copy()
    for nm in names[1:]:
        hc[f"p_dem_{nm}"] = results[nm]["raw"]["house"].set_index("district").loc[hc["district"], "p_dem"].values
    hc = hc.sort_values("p_dem")
    cols = ["district", "member", "inc_party", "pvi_d", "est_margin", "p_dem"] + [f"p_dem_{nm}" for nm in names[1:]]
    L.append(f"{len(hc)} districts have a 10–90% Democratic win probability in the unbiased scenario.\n")
    L.append(md_table(hc, cols, {"pvi_d": fm, "est_margin": fm, "p_dem": pct, **{f"p_dem_{nm}": pct for nm in names[1:]},
                                  "member": lambda v: v if isinstance(v, str) and v else "(open/new)"}))
    L += ["", "## Charts", ""] + [f"- `{os.path.relpath(p, HERE)}`" for p in chart_paths]
    p = os.path.join(outdir, "REPORT.md")
    open(p, "w").write("\n".join(L) + "\n")
    return p


def main():
    ap = argparse.ArgumentParser(description="2026 midterm Monte Carlo model")
    ap.add_argument("--scenario", default="all", help="all | unbiased | pres_style_D_overstatement | r_overstatement_2025 | i | ii | iii | custom")
    ap.add_argument("--bias", type=float, help="custom: mean poll bias (positive = polls overstate D)")
    ap.add_argument("--bias-sd", type=float, default=3.0, help="custom: sd of national poll error")
    ap.add_argument("--sims", type=int, help="override number of simulations")
    ap.add_argument("--generic-ballot", type=float, help="override generic-ballot margin (D minus R)")
    ap.add_argument("--config", default=os.path.join(HERE, "config.yaml"))
    ap.add_argument("--out", default=os.path.join(HERE, "output"))
    a = ap.parse_args()
    cfg = load_config(a.config)
    if a.sims: cfg["simulations"] = a.sims
    if a.generic_ballot is not None: cfg["generic_ballot_margin"] = a.generic_ballot
    sc = cfg["scenarios"]
    if a.scenario == "all":
        todo = {k: sc[k] for k in sc}
    elif a.scenario == "custom":
        if a.bias is None: sys.exit("--scenario custom needs --bias")
        todo = {"custom": {"label": f"Custom: poll bias {a.bias:+.1f}", "poll_bias_mean": a.bias, "poll_bias_sd": a.bias_sd}}
    else:
        k = ALIASES.get(a.scenario, a.scenario)
        if k not in sc: sys.exit(f"unknown scenario {a.scenario}")
        todo = {k: sc[k]}
    os.makedirs(a.out, exist_ok=True)
    results = {}
    for k, v in todo.items():
        r = simulate(cfg, v["poll_bias_mean"], v["poll_bias_sd"])
        s = summarize(k, v["label"], r)
        results[k] = dict(raw=r, summary=s, label=v["label"], dist=seat_distributions(r, cfg))
        senate_table(r["senate"]).assign(scenario=k).to_csv(os.path.join(a.out, f"senate_races_{k}.csv"), index=False)
        r["house"][["district", "member", "inc_party", "inc_running", "pvi_d", "consensus_rating_score", "rating_margin", "rating_weight",
                    "census_region", "hispanic_share", "fundamentals_margin", "est_margin",
                    "sim_mean_margin", "p_dem", "tipping_freq"]].assign(scenario=k).to_csv(os.path.join(a.out, f"house_districts_{k}.csv"), index=False)
        if r.get("governor") is not None:
            governor_table(r["governor"]).assign(scenario=k).to_csv(os.path.join(a.out, f"governor_races_{k}.csv"), index=False)
        print(f"\n=== {v['label']}  (bias {v['poll_bias_mean']:+.1f} ± {v['poll_bias_sd']}) ===")
        print(f"Senate: P(D)={pct(s['senate_p_D'])}  P(R)={pct(s['senate_p_R'])}  P(none)={pct(s['senate_p_none'])}  "
              f"D+I seats mean {s['senate_D_mean']:.1f} [{s['senate_D_p10']}-{s['senate_D_p90']}]  tipping {s['senate_tipping'][:3]}")
        print(f"House : P(D)={pct(s['house_p_D'])}  D seats median {s['house_D_median']} [{s['house_D_p10']}-{s['house_D_p90']}]  tipping {s['house_tipping'][:3]}")
        if "gov_races" in s:
            print(f"Gov   : D governors after election median {s['gov_D_total_median']} [{s['gov_D_total_p10']}-{s['gov_D_total_p90']}] of 50; "
                  f"D wins {s['gov_D_wins_mean']:.1f} of {s['gov_races']} races; P(D majority of governorships)={pct(s['gov_p_D_majority'])}")
    if a.scenario == "all":
        sens = {}
        for key, lab, bm in [("pres_style_3p8", "Presidential-year average miss: polls overstate D by 3.8 (sd 3)", 3.8),
                             ("offyear_1p3", "Trump-era off-year average: polls overstate R by 1.3 (sd 3)", -1.3)]:
            r = simulate(cfg, bm, 3.0)
            sens[key] = summarize(key, lab, r)
            print(f"Sensitivity {lab}: Senate P(D)={pct(sens[key]['senate_p_D'])}  House P(D)={pct(sens[key]['house_p_D'])}")
        json.dump(sens, open(os.path.join(a.out, "sensitivity.json"), "w"), indent=2, default=float)
    # combined per-race CSV
    pd.concat([senate_table(results[k]["raw"]["senate"]).assign(scenario=k) for k in results]).to_csv(os.path.join(a.out, "senate_race_probabilities_all_scenarios.csv"), index=False)
    if all(results[k]["raw"].get("governor") is not None for k in results):
        pd.concat([governor_table(results[k]["raw"]["governor"]).assign(scenario=k) for k in results]).to_csv(
            os.path.join(a.out, "governor_race_probabilities_all_scenarios.csv"), index=False)
    json.dump({k: results[k]["summary"] for k in results}, open(os.path.join(a.out, "summary.json"), "w"), indent=2, default=float)
    compact_json({k: dict(scenario=k, label=results[k]["label"], **results[k]["dist"]) for k in results},
                 os.path.join(a.out, "seat_distributions.json"))
    cp = charts(results, os.path.join(a.out, "charts"))
    rp = write_report(results, cfg, a.out, cp)
    print("\nReport:", rp); print("Charts:", *cp, sep="\n  ")


if __name__ == "__main__":
    main()
