# Methodology: 2026 Midterm Model (simplified, transparent)

**What this is:** an original, deliberately simple Monte Carlo model built on 2026-10-10 for scenario analysis. Every assumption is a number in `config.yaml` or a row in `data/*.csv`, so you can change it and re-run. **It is not a professional forecast.** It has no fundraising data, no economic model, no house effects per pollster, no time-decay of polls, and only light candidate-quality adjustments.

Sign convention everywhere: **margin = Democratic % minus Republican %** (positive = Dem ahead). For races where the main non-Republican is an independent (NE Osborn, MT Bodnar, ID Achilles, SD Bengs), "D side" means that independent.

---

## 1. Data sources (all pulled 2026-10-10, ~01:30 ET)

| Input | Value used | Source |
|---|---|---|
| Current Senate | 53 R, 45 D, 2 I (caucus D) | Clerk of the House Official List of Members (Oct 1 2026); 270toWin; congresscountdown.com (Oct 5 2026) |
| Senate seats up | 35 (33 Class 2 + FL & OH specials): 22 R-held, 13 D-held | Wikipedia "2026 United States Senate elections" (ratings table dated Oct 6–9 2026); Cook Political Report Senate ratings (Oct 6 2026: "34 D seats not up, 31 R seats not up") |
| VP tiebreak | JD Vance (R) | — |
| State PVIs | Cook PVI 2025 | Wikipedia Senate ratings table (cites Cook 2025 PVI) |
| Senate polling averages | Average of aggregators (270toWin, DDHQ, FiftyPlusOne, RCP, Silver Bulletin, Texas Tribune, Race to the WH) as tabulated on each Wikipedia race page, Sep 18–Oct 9 2026 | Wikipedia "2026 United States Senate election in <State>" pages |
| Sparse-race polls | VA: Public Sentiment Institute Jun 12–16 (Warner 51–33). NM: SurveyUSA Sep 25–30 (54–36), Research & Polling Aug 21–28 (53–38). MS: Data for Progress (D) Aug 5–15 (Hyde-Smith 47–41). LA: Race to the WH avg R+5.8 (from Hart (D) Sep and PPP (D) Jul) | Same Wikipedia race pages |
| Senate candidates | General-election nominees | Wikipedia "Elections leading to the next Congress" table |
| Current House | 218 R, 214 D, 1 I (Kevin Kiley, CA), 2 vacant (FL-20, TX-23) | House Press Gallery party breakdown; Clerk vacancies page |
| District list, incumbents, retirements, PVIs | All 435 districts on the **2026 maps** (incl. mid-decade redistricting in TX, CA, NC, OH, UT, etc.), Cook **2026** PVI (Missouri uses 2025 PVI because its new map was struck down) | Wikipedia "2026 United States House of Representatives elections" (state tables), parsed by `scripts/build_data.py` |
| House consensus ratings (comparison only, not a model input) | Avg of Cook/IE/Sabato/Economist/Split Ticket/DDHQ/FPO/Fox/Silver/RCP for 146 listed districts | Wikipedia "2026 United States House of Representatives election ratings" |
| Generic ballot | **D+8.4** | Wikipedia aggregate (DDHQ D+8.5, FiftyPlusOne D+7.8, NBC D+9.0, RCP D+7.9, Silver Bulletin D+9.0), updated Oct 9 2026. Cross-checked: Vugol D+7.5, TrackTheVote D+8.8, USPollingData D+7.4, PollingSource D+7.9 |
| Polling-error history (for scenarios) | Polls overstated D: 2016 +3.0, 2020 +4.7, 2024 +2.9; midterms ~even (2018 R+0.5, 2022 D+0.8); 2025 off-year overstated R by ~6 | Silver Bulletin (from earlier research this session) |
| Candidate-adjustment history | ME 2020: Collins won by 8.6 while Biden won ME by 9.1. NE 2024: Fischer 53.2–Osborn 46.5 (R+6.7) while Trump won NE by ~20.4. AK 2024: Begich beat Peltola ~51.3–48.7 while Trump won AK by ~13.1 | Public results (NE verified via uselectionatlas/Ballotpedia; ME/AK from public results, approximate) |

Raw snapshots are saved in `data/raw/` so the inputs are auditable. **No poll numbers were invented.** Races with no public general-election polls use fundamentals only and say so in `data/senate_races.csv` (`poll_note`).

---

## 2. Senate model

For each of the 35 races:

**Fundamentals**
```
fundamentals = 2 × PVI  +  GB  +  incumbency  +  candidate_adj
```
- `2 × PVI`: Cook PVI is expressed in two-party vote-share points relative to the nation; a margin is roughly twice that (`senate.pvi_multiplier`).
- `GB`: generic-ballot margin (D+8.4), the national environment.
- `incumbency`: +3.0 toward the holder's party if an elected incumbent is running, +1.5 if the incumbent was appointed (Moody FL, Husted OH, Darline Graham SC), 0 for open seats.
- `candidate_adj` (only 3 races, can be switched off with `use_candidate_adjustments: false`): half of the candidate's documented over-performance versus the presidential margin in their last race. ME Collins −7.4, NE Osborn +6.9, AK Peltola +5.2. These fix cases where a pure PVI model is clearly wrong because of a candidate's personal vote. Half, because past over-performance only partly carries forward.

**Blend with polls**
```
estimate = w × poll_average + (1 − w) × fundamentals   (+ optional early_vote_adjustment)
```
`w` depends on how many independent aggregators/polls exist: 0 sources → 0; 1 → 0.35; 2 → 0.60; 3 → 0.75; 4+ → 0.85. Polls get most of the weight where they're plentiful (3–4 weeks out), and fundamentals fill in elsewhere.

**Per-race uncertainty (idiosyncratic sd):** 4.0 (4+ sources), 4.5 (3), 5.0 (2), 6.0 (1), 7.0 (no polls).

**Majority math.** D seats = 34 not up + D wins. R seats = 31 not up + R wins. Each independent winner joins the Democratic caucus with probability 0.6, the Republican caucus with 0.0, and neither with 0.4 (`independent_caucus`). R controls with ≥50 (VP Vance breaks ties); D needs ≥51. If neither side gets there (for example R 49, D 50, Osborn with neither caucus), we report "no clear majority."

## 3. House model

For all 435 districts:
```
estimate = 2 × PVI_2026  +  GB  +  3.0 × (incumbent running: +1 D, −1 R)  +  seat_bias
```
- Open seats, new seats and vacancies get no incumbency term. Kevin Kiley (CA-6, independent, ex-Republican) is treated as an R-aligned incumbent and counts toward the R side.
- District polls: `data/house_district_polls.csv` is supported (blended at 0.5 weight, lower sd), but **it is empty**. I did not collect district polls (they're sparse and mostly partisan internals), so the House runs purely on PVI, generic ballot and incumbency.
- Idiosyncratic district sd = 6.0 points.
- D controls with ≥218 seats.

**Sanity check vs. professional ratings (unbiased scenario).** Mean P(D win) by consensus rating category: Safe R 6%, Likely R 18%, Lean R 37%, Toss-up 42%, Lean D 69%, Likely D 97%, Safe D 98%. Our ordering matches the pros. Our median (234 D) runs about 10 seats more Democratic than a ratings-implied count (~223), and our P(D House) of ~93% is close to Silver Bulletin's ~94%. Uniform-swing PVI models tend to over-credit the wave party in marginal seats held by entrenched incumbents, so treat the House seat count as the generous-to-the-environment end.

## 4. Monte Carlo engine (`model.py::simulate`)

For each of N = 100,000 simulations (config `simulations`):
```
national  ~ Normal(poll_bias_mean, poll_bias_sd)                 # ONE draw shared by every race
state_s   ~ Normal(0, 2.0)  for every state                      # shared by the Senate race + all House seats in the state
race_r    ~ Normal(0, race_sd_r)
simulated_margin_r = estimate_r − national + state_s(r) + race_r
```
- **Correlation:** the national term moves every race together, so a polling miss hits all of them at once (the 2016/2020/2024 failure mode). The state term correlates a state's Senate race with its House seats.
- **The bias applies to fundamentals too,** because the generic ballot is itself a poll. If polls overstate Democrats by 3, the House and Senate fundamentals shift by 3 as well.
- **Tipping point (Senate):** in each simulation, order the 35 races from most to least Democratic. The tipping race is the one that delivers Democrats their 51st seat (the 17th D-side win). We report how often each state fills that role. Because the national error shifts every race equally, it doesn't change the ordering, so the tipping-point shares are nearly identical across scenarios. That's expected.
- **Tipping point (House):** the 218th most-Democratic district in each simulation.

## 5. Scenarios (`config.yaml → scenarios`)

| Scenario | poll_bias_mean | poll_bias_sd | Meaning |
|---|---|---|---|
| (i) unbiased | 0 | 3.0 | Polls right on average; ±3 national error, typical of midterms |
| (ii) presidential-style | +3 | 3.0 | Polls overstate Dems by 3, like 2016/2020/2024 (the "missing Trump voter" theory) |
| (iii) 2025-style | −6 | 3.0 | Polls overstate Republicans by 6, like the 2025 off-year races |

Custom: `python run.py --scenario custom --bias 1.5 --bias-sd 2`.

## 6. Key assumptions you might disagree with
1. The generic ballot (D+8.4) is the right national anchor. Try `--generic-ballot 4`: at D+4 the House is a coin flip (P(D) ≈ 54%, median 219 D) and the Senate drops to ≈60% D.
2. Incumbency is worth 3 points everywhere.
3. A uniform national swing applied to Cook PVI.
4. Osborn joins the Democratic caucus 60% of the time if he wins. He says he won't caucus with either party.
5. Early vote is **not** used (all adjustments 0): turnout volume doesn't reveal vote choice. The hook exists in `early_vote_adjustment` if you want to encode a belief.
6. Normal (thin-tailed) errors. Real polling misses may be fatter-tailed.
7. Equal weight across aggregators. There are no pollster house-effect corrections.

## 7. Known limitations
- Static snapshot as of Oct 10, 2026. Re-pull polls and re-run to update.
- No fundraising, approval, or economic inputs. No poll recency weighting.
- House has no district polls and no candidate-quality data. Redistricted seats rely entirely on Cook's 2026 PVI.
- Alaska uses ranked-choice voting and Maine has RCV for Senate. Both are modeled as two-way margins.
- Sparse-race inputs (VA, MS, LA) rest on one or two old or partisan polls.
- Some numbers in the candidate adjustments are approximate (labeled above).
