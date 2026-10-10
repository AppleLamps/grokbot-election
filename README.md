# Apple Lamps Grok Bot Election Analysis and Prediction

A static website and the transparent Python model behind it: a Monte Carlo analysis of the **2026 U.S. Senate and House midterms** under three polling-error scenarios. Snapshot as of **October 10, 2026**.

> A simplified, transparent scenario model built by Grok Bot. **Not a professional forecast.**

## Headline results (model v2, 100,000 simulations per scenario)

| Scenario | P(D Senate) | P(R Senate) | Senate D+I seats (mean, 80% range) | P(D House) | House D seats (median, 80% range) |
|---|---|---|---|---|---|
| (i) Polls unbiased (2018/2022 midterm record) | 68.6% | 30.5% | 51.6 (48–55) | 92.5% | 235 (220–254) |
| (ii) Polls overstate Dems by 3 (2016/2020/2024 pattern) | 35.2% | 64.0% | 49.5 (46–53) | 70.7% | 224 (209–240) |
| (iii) Polls overstate Reps by 6 (2025 pattern, tail case) | 98.0% | 1.9% | 55.1 (53–57) | 99.7% | 264 (243–291) |

**Bottom line:** if the polls are unbiased, Democrats are favored in both chambers. Republicans' realistic path to holding both requires the polls to be understating Republicans, and even then Democrats still win the House about 70% of the time. Senate tipping-point races: Ohio, Texas, Alaska and Iowa. Model v2 added eight factors (herding-aware poll weighting, demographic/regional error, expert House ratings, candidate quality, poll cleanup, incumbency reweight, fat tails, election mechanics); they largely offset, moving every headline number by under one point. See the before/after table in [model/output/REPORT.md](model/output/REPORT.md).

Baselines: Senate 53R / 45D / 2I with 35 seats up; House 218R / 214D; generic ballot D+8.4 (Oct 9, 2026), D+8.8 after the likely-voter adjustment.

## Repository layout

```
.
├── index.html            # the website (vanilla HTML/CSS/JS, no framework, no build step)
├── styles.css
├── app.js                # loads data/results.json; scenario switcher, SVG seat histograms, sortable race table
├── data/results.json     # site data, generated from the model outputs
├── vercel.json           # optional: static site, no framework/build
└── model/                # the Python model
    ├── run.py            # CLI: runs simulations, writes output/
    ├── model.py          # estimates + correlated Monte Carlo engine
    ├── config.yaml       # every tunable assumption
    ├── METHODOLOGY.md    # full methodology and sources
    ├── requirements.txt
    ├── data/             # senate_races.csv, house_districts.csv, house_district_polls.csv, raw/ snapshots
    ├── scripts/          # build_data.py (raw -> CSV), export_site_data.py (outputs -> ../data/results.json)
    └── output/           # REPORT.md, summary.json, seat_distributions.json, per-race CSVs, charts/*.png
```

## The model in brief

- **Senate:** each race's estimate blends its polling average with a fundamentals estimate (2 × Cook PVI + generic ballot + incumbency + candidate adjustments + candidate quality). Poll weight is discounted for stale, partisan-sponsored, or herding-suspect polls.
- **House:** all 435 districts (2026 maps): fundamentals (PVI + generic ballot + 1.8-pt incumbency) blended with expert race ratings.
- **Correlated error:** every simulation draws a fat-tailed national polling-error term that shifts all races together, plus state, Census-region and Hispanic-voter error layers and independent race-level noise. AK/ME ranked-choice and the Montana three-way race get extra uncertainty.
- **Scenarios** shift the mean of the national error: 0 (unbiased), +3 toward Republicans (polls overstate Dems), or −6 toward Democrats (polls overstate Reps), each with sd 3.
- Every coefficient is our assumption and lives in `model/config.yaml`; each v2 factor can be switched off under `factors:`. `python scripts/factor_attribution.py` measures each factor's marginal effect.

Full details: [model/METHODOLOGY.md](model/METHODOLOGY.md). Full results: [model/output/REPORT.md](model/output/REPORT.md).

## Running the model

Requires Python 3.10+.

```bash
cd model
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
python run.py --scenario all
```

Other options: `--scenario ii`, `--scenario custom --bias 1.5 --bias-sd 2.5`, `--generic-ballot 5`, `--sims 20000`.

After re-running, refresh the website data (standard library only):

```bash
python model/scripts/export_site_data.py   # from the repo root; writes data/results.json
```

## The website

Plain static files. The repo root is the site: `index.html` fetches `data/results.json` with a relative path, and every chart (including the seat-by-seat histograms built from each scenario's full simulated distribution) is drawn in the browser as inline SVG from that file. There are no external CDNs, fonts or dependencies.

- **Local preview:** `python3 -m http.server 8000` from the repo root, then open http://localhost:8000. Opening `index.html` straight from disk (`file://`) won't work, because browsers block `fetch` of local JSON.
- **Deploy on Vercel:** import this repo in Vercel and deploy. Framework preset "Other", root directory `./`, no build command, no output directory override. Or run `vercel --prod` from the repo root.

## Limitations

- Snapshot as of October 10, 2026. Nothing updates automatically.
- The House model uses only PVI, the generic ballot and incumbency, and likely over-credits the Democratic wave by roughly 10 seats.
- Scenario parameters are judgment calls, and several Senate races have sparse or no polling.
- Simplified and transparent by design. Not a professional forecast.

---
A simplified model by Grok Bot for Apple Lamps. Data as of October 10, 2026.
