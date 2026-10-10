"""Export model outputs (output/summary.json, output/seat_distributions.json + per-race CSV) to ../data/results.json for the static site.

Usage (from repo root or model/):  python model/scripts/export_site_data.py
Uses only the Python standard library.
"""
import csv, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.dirname(HERE)
ROOT = os.path.dirname(MODEL)
OUT = os.path.join(MODEL, "output")

KEYS = [("unbiased", "i", "Polls unbiased", "Polling error centered on zero (mean 0, sd 3 pts)."),
        ("pres_style_D_overstatement", "ii", "Polls overstate Dems +3",
         "Like 2016/2020/2024: polls overstate Democrats by 3 pts on average (sd 3)."),
        ("r_overstatement_2025", "iii", "Polls overstate Reps +6",
         "Like the 2025 off-year elections: polls overstate Republicans by 6 pts on average (sd 3).")]

STATES = {"AL":"Alabama","AK":"Alaska","AR":"Arkansas","CO":"Colorado","DE":"Delaware","FL":"Florida","GA":"Georgia",
 "ID":"Idaho","IL":"Illinois","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MA":"Massachusetts",
 "MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MT":"Montana","NE":"Nebraska","NH":"New Hampshire","NJ":"New Jersey",
 "NM":"New Mexico","NC":"North Carolina","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","RI":"Rhode Island","SC":"South Carolina",
 "SD":"South Dakota","TN":"Tennessee","TX":"Texas","VA":"Virginia","WV":"West Virginia","WY":"Wyoming"}

def num(x):
    try:
        return None if x in ("", None) else round(float(x), 5)
    except ValueError:
        return None

def histogram(d):
    """Trim a full 0..max_seats count vector (from seat_distributions.json) to the simulated support and
    convert to parallel arrays: seats[i] occurred with probability prob[i] (= count / sims)."""
    counts, n = d["counts"], d["sims"]
    nz = [i for i, c in enumerate(counts) if c > 0]
    lo, hi = nz[0], nz[-1]
    return {"sims": n, "max_seats": d["max_seats"], "majority": d["majority"], "majority_line": d["majority_line"],
            "mean": round(d["mean"], 3), "median": d["median"], "p10": d["p10"], "p90": d["p90"],
            "seats": list(range(lo, hi + 1)), "count": counts[lo:hi + 1],
            "prob": [round(c / n, 6) for c in counts[lo:hi + 1]]}


def main():
    summ = json.load(open(os.path.join(OUT, "summary.json")))
    dist = json.load(open(os.path.join(OUT, "seat_distributions.json")))
    scenarios = []
    for key, short, label, desc in KEYS:
        s = summ[key]
        scenarios.append({
            "key": key, "short": short, "label": label, "model_label": s["label"], "description": desc,
            "bias_mean": s["bias_mean"], "bias_sd": s["bias_sd"], "sims": s["sims"],
            "senate": {"p_D": s["senate_p_D"], "p_R": s["senate_p_R"], "p_none": s["senate_p_none"],
                       "D_mean": s["senate_D_mean"], "D_p10": s["senate_D_p10"], "D_p90": s["senate_D_p90"],
                       "R_mean": s["senate_R_mean"], "R_p10": s["senate_R_p10"], "R_p90": s["senate_R_p90"],
                       "tipping": s["senate_tipping"], "majority": 51, "majority_line": 50.5,
                       "D_median": dist[key]["senate"]["median"], "hist": histogram(dist[key]["senate"])},
            "house": {"p_D": s["house_p_D"], "p_R": s["house_p_R"], "D_mean": s["house_D_mean"],
                      "D_median": s["house_D_median"], "D_p10": s["house_D_p10"], "D_p90": s["house_D_p90"],
                      "tipping": s["house_tipping"], "majority": 218, "majority_line": 217.5,
                      "hist": histogram(dist[key]["house"])},
        })

    races = {}
    with open(os.path.join(OUT, "senate_race_probabilities_all_scenarios.csv")) as f:
        for r in csv.DictReader(f):
            k = (r["state"], r["seat"])
            if k not in races:
                races[k] = {"state": r["state"], "state_name": STATES.get(r["state"], r["state"]),
                            "seat": r["seat"], "holder": r["holder"],
                            "dem_side_candidate": r["dem_side_candidate"], "dem_side_party": r["dem_side_party"],
                            "rep_candidate": r["rep_candidate"], "pvi_d": num(r["pvi_d"]),
                            "poll_margin_d": num(r["poll_margin_d"]), "poll_sources": int(float(r["poll_sources"] or 0)),
                            "est_margin": num(r["est_margin"]), "tipping_freq": num(r["tipping_freq"]), "p_dem": {}}
            races[k]["p_dem"][r["scenario"]] = num(r["p_dem_side"])
    race_list = sorted(races.values(), key=lambda x: -x["p_dem"]["unbiased"])

    out = {
        "title": "Apple Lamps Grok Bot Election Analysis and Prediction",
        "as_of": "2026-10-10",
        "generic_ballot_d": 8.4, "generic_ballot_as_of": "2026-10-09",
        "baseline": {"senate": {"R": 53, "D": 45, "I": 2, "up": len(race_list)}, "house": {"R": 218, "D": 214}},
        "scenarios": scenarios,
        "senate_races": race_list,
    }
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    path = os.path.join(ROOT, "data", "results.json")
    with open(path, "w") as f:
        txt = json.dumps(out, indent=1)
        # keep long numeric arrays (histograms) on one line
        txt = re.sub(r"\[\s*((?:-?[\d.e-]+,\s*)+-?[\d.e-]+)\s*\]",
                     lambda m: "[" + ",".join(x.strip() for x in m.group(1).split(",")) + "]", txt)
        f.write(txt + "\n")
    print(f"wrote {path}: {len(scenarios)} scenarios, {len(race_list)} races")

if __name__ == "__main__":
    main()
