# 2026 Midterm Forecast Model

Transparent Monte Carlo model for 2026 Senate & House control. See `METHODOLOGY.md` for every assumption and source; results land in `output/REPORT.md`.

```
cd model                                          # from the repo root
pip install -r requirements.txt
python run.py --scenario all              # all 3 polling-error scenarios
python run.py --scenario ii               # one scenario (i | ii | iii or full name)
python run.py --scenario custom --bias 1.5 --bias-sd 2.5
python run.py --scenario all --generic-ballot 5 --sims 20000
python scripts/build_data.py              # rebuild data/house_districts.csv from data/raw/
python scripts/factor_attribution.py      # marginal effect of each v2 factor (add-one / drop-one)
python scripts/export_site_data.py        # rebuild ../data/results.json
```

Layout:
- `config.yaml` – all tunable assumptions (generic ballot, poll-error scenarios, incumbency, sds, caucus probs)
- `data/senate_races.csv` – 35 Senate races: PVI, polls, sources, notes, candidate adjustments
- `data/house_districts.csv` – 435 districts (2026 maps): PVI, incumbent party, running/open, consensus rating score
- `data/house_district_polls.csv` – optional district polls (empty by default)
- `data/state_demographics.csv` – Census region + 2020 Census Hispanic share for all 50 states (v2 demographic/regional error)
- `reports/additional_factors.md` – research behind the eight v2 factors
- `data/raw/` – raw source snapshots (Wikipedia wikitext, pulled 2026-10-10)
- `model.py` – estimates + correlated Monte Carlo engine
- `run.py` – CLI, CSV/JSON outputs, charts, report
- `scripts/export_site_data.py` – exports outputs to `../data/results.json` for the website
- `requirements.txt` – Python dependencies
- `output/` – REPORT.md, summary.json, per-race CSVs, charts/, and `seat_distributions.json`: per scenario, the full simulated seat histogram (count of simulations at every integer seat value; Senate D+I seats 0–100, House D seats 0–435) with mean/median/10th–90th percentiles
