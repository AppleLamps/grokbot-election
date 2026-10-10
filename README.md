# Apple Lamps Grok Bot Election Analysis and Prediction

A static website and the transparent Python model behind it: a Monte Carlo analysis of the **2026 U.S. Senate and House midterms** under three polling-error scenarios. Snapshot as of **October 10, 2026**.

> A simplified, transparent scenario model built by Grok Bot. **Not a professional forecast.**

## Headline results (100,000 simulations per scenario)

| Scenario | P(D Senate) | P(R Senate) | Senate D+I seats (mean, 80% range) | P(D House) | House D seats (median, 80% range) |
|---|---|---|---|---|---|
| (i) Polls unbiased | 67.9% | 31.1% | 51.7 (48–55) | 93.0% | 234 (219–252) |
| (ii) Polls overstate Dems by 3 (2016/2020/2024 pattern) | 34.5% | 64.6% | 49.3 (46–53) | 70.2% | 223 (210–238) |
| (iii) Polls overstate Reps by 6 (2025 pattern) | 98.7% | 1.2% | 55.6 (53–58) | >99.9% | 263 (242–287) |

**Bottom line:** if the polls are unbiased, Democrats are favored in both chambers. Republicans' realistic path to holding both requires the polls to be understating Republicans, and even then Democrats still win the House about 70% of the time. Senate tipping-point races: Alaska, Texas, Ohio, then Maine and Iowa.

Baselines: Senate 53R / 45D / 2I with 35 seats up; House 218R / 214D; generic ballot D+8.4 (Oct 9, 2026).

## Repository layout

```
.
├── index.html            # the website (vanilla HTML/CSS/JS, no framework, no build step)
├── styles.css
├── app.js                # loads data/results.json; scenario switcher + sortable race table
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
    └── output/           # REPORT.md, summary.json, per-race CSVs, charts/*.png
```

## The model in brief

- **Senate:** each race's estimate blends its polling average with a fundamentals estimate (2 × Cook PVI + generic ballot + incumbency + candidate adjustments).
- **House:** all 435 districts (2026 maps) from fundamentals only: PVI + generic ballot + incumbency.
- **Correlated error:** every simulation draws one national polling-error term that shifts all races together, plus independent race-level noise.
- **Scenarios** shift the mean of that national error: 0 (unbiased), +3 toward Republicans (polls overstate Dems), or −6 toward Democrats (polls overstate Reps), each with sd 3.

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

Plain static files. The repo root is the site: `index.html` fetches `data/results.json` with a relative path, and the charts load from `model/output/charts/`. There are no external CDNs, fonts or dependencies.

- **Local preview:** `python3 -m http.server 8000` from the repo root, then open http://localhost:8000. Opening `index.html` straight from disk (`file://`) won't work, because browsers block `fetch` of local JSON.
- **Deploy on Vercel:** import this repo in Vercel and deploy. Framework preset "Other", root directory `./`, no build command, no output directory override. Or run `vercel --prod` from the repo root.

## Limitations

- Snapshot as of October 10, 2026. Nothing updates automatically.
- The House model uses only PVI, the generic ballot and incumbency, and likely over-credits the Democratic wave by roughly 10 seats.
- Scenario parameters are judgment calls, and several Senate races have sparse or no polling.
- Simplified and transparent by design. Not a professional forecast.

---
A simplified model by Grok Bot for Apple Lamps. Data as of October 10, 2026.
