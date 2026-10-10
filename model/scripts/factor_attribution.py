#!/usr/bin/env python3
"""Marginal effect of each v2 factor on the headline numbers.

Two views, per scenario:
  * add-one:  v1 baseline (all factors OFF) + this one factor ON
  * drop-one: full v2 model (all ON) with this one factor OFF
Writes output/factor_attribution.json and output/factor_attribution.md.
Usage:  python scripts/factor_attribution.py [--sims 40000]
"""
import argparse, copy, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model import load_config, simulate, HERE


def headline(cfg, sc):
    r = simulate(cfg, sc["poll_bias_mean"], sc["poll_bias_sd"])
    return dict(senate_p_D=float(r["senate_d_ctrl"]), senate_p_R=float(r["senate_r_ctrl"]),
                senate_D_mean=float(r["senate_d_eff"].mean()), house_p_D=float(r["house_d_ctrl"]),
                house_D_median=float(np.median(r["house_d"])), house_D_mean=float(r["house_d"].mean()))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sims", type=int, default=40000)
    a = ap.parse_args()
    cfg = load_config(); cfg["simulations"] = a.sims
    names = list(cfg["factors"])
    out = {}
    for key, sc in cfg["scenarios"].items():
        off = copy.deepcopy(cfg); off["factors"] = {k: False for k in names}
        on = copy.deepcopy(cfg); on["factors"] = {k: True for k in names}
        res = {"v1_all_off": headline(off, sc), "v2_all_on": headline(on, sc), "add_one": {}, "drop_one": {}}
        for f in names:
            c = copy.deepcopy(off); c["factors"][f] = True; res["add_one"][f] = headline(c, sc)
            c = copy.deepcopy(on); c["factors"][f] = False; res["drop_one"][f] = headline(c, sc)
        out[key] = res
        print(key, "done", flush=True)
    od = os.path.join(HERE, "output")
    json.dump(out, open(os.path.join(od, "factor_attribution.json"), "w"), indent=2)
    L = ["# Factor attribution", "", f"{a.sims:,} sims per run (same seed). Deltas are in percentage points (probabilities) or seats.",
         "**add-one** = v1 baseline + only this factor. **drop-one** = full v2 minus this factor (shown as the factor's contribution, i.e. v2 − run without it).", ""]
    for key, res in out.items():
        b, f = res["v1_all_off"], res["v2_all_on"]
        L += [f"## {cfg['scenarios'][key]['label']}", "",
              f"v1 (all off): P(D Senate) {100*b['senate_p_D']:.1f}%, Senate D mean {b['senate_D_mean']:.2f}, P(D House) {100*b['house_p_D']:.1f}%, House D mean {b['house_D_mean']:.1f}  ",
              f"v2 (all on): P(D Senate) {100*f['senate_p_D']:.1f}%, Senate D mean {f['senate_D_mean']:.2f}, P(D House) {100*f['house_p_D']:.1f}%, House D mean {f['house_D_mean']:.1f}", "",
              "| Factor | add-one ΔP(D Sen) | add-one ΔSen seats | add-one ΔP(D House) | add-one ΔHouse seats | drop-one ΔP(D Sen) | drop-one ΔSen seats | drop-one ΔP(D House) | drop-one ΔHouse seats |",
              "|---|---|---|---|---|---|---|---|---|"]
        for fn in names:
            ad, dr = res["add_one"][fn], res["drop_one"][fn]
            L.append(f"| {fn} | {100*(ad['senate_p_D']-b['senate_p_D']):+.1f} | {ad['senate_D_mean']-b['senate_D_mean']:+.2f} | "
                     f"{100*(ad['house_p_D']-b['house_p_D']):+.1f} | {ad['house_D_mean']-b['house_D_mean']:+.1f} | "
                     f"{100*(f['senate_p_D']-dr['senate_p_D']):+.1f} | {f['senate_D_mean']-dr['senate_D_mean']:+.2f} | "
                     f"{100*(f['house_p_D']-dr['house_p_D']):+.1f} | {f['house_D_mean']-dr['house_D_mean']:+.1f} |")
        L.append("")
    open(os.path.join(od, "factor_attribution.md"), "w").write("\n".join(L) + "\n")
    print("wrote output/factor_attribution.{json,md}")


if __name__ == "__main__":
    main()
