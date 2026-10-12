# Methodology: 2026 Midterm Model (simplified, transparent)

**What this is:** an original, deliberately simple Monte Carlo model built on 2026-10-10 for scenario analysis. Every assumption is a number in `config.yaml` or a row in `data/*.csv`, so you can change it and re-run. **It is not a professional forecast.** It has no fundraising data, no economic model and no per-pollster house effects.

**Model v2 (2026-10-10):** eight additional factors were added: herding-aware poll weighting, demographic + regional error, expert ratings in the House, candidate quality, poll cleanup, incumbency reweight, fat tails, and election mechanics. Section 8 documents each one: coefficient, source, and measured effect. **Every v2 coefficient is our own assumption** informed by the cited research (`reports/additional_factors.md`), not a value fitted to past elections. Each factor has an on/off switch under `factors:` in `config.yaml`; with all eight off, the model reproduces v1 exactly (same seed, identical output).

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
| House consensus ratings (**v2: model input**, factor 3) | Avg of Cook/IE/Sabato/Economist/Split Ticket/DDHQ/FPO/Fox/Silver/RCP for 146 listed districts | Wikipedia "2026 United States House of Representatives election ratings" |
| Generic ballot | **D+8.4** raw, **D+8.8** after the v2 likely-voter adjustment (+0.4; Silver Bulletin LV D+8.8 vs RV D+8.1, Sep 23) | Wikipedia aggregate (DDHQ D+8.5, FiftyPlusOne D+7.8, NBC D+9.0, RCP D+7.9, Silver Bulletin D+9.0), updated Oct 9 2026. Cross-checked: Vugol D+7.5, TrackTheVote D+8.8, USPollingData D+7.4, PollingSource D+7.9 |
| Polling-error history (for scenarios) | Polls overstated D: 2016 +3.0, 2020 +4.7, 2024 +2.9; midterms ~even (2018 R+0.5, 2022 D+0.8); 2025 off-year overstated R by ~6 | Silver Bulletin (from earlier research this session) |
| Hispanic share by state (v2) | 2020 Census, % of population Hispanic or Latino, all 50 states (`data/state_demographics.csv`) | Wikipedia "List of U.S. states by Hispanic and Latino population" (Census 2020 table), snapshot in `data/raw/hispanic_by_state_2020census.wiki`. The Census API now requires a key, so the ACS route was not used |
| Census regions (v2) | Northeast / Midwest / South / West | U.S. Census Bureau regional definitions |
| Poll end dates and sponsors (v2) | `poll_end_date`, `poll_sponsor_partisan` columns in `senate_races.csv` | Read from the existing `poll_note` text (LA and MS are Democratic-sponsored) |
| Candidate-adjustment history | ME 2020: Collins won by 8.6 while Biden won ME by 9.1. NE 2024: Fischer 53.2–Osborn 46.5 (R+6.7) while Trump won NE by ~20.4. AK 2024: Begich beat Peltola ~51.3–48.7 while Trump won AK by ~13.1 | Public results (NE verified via uselectionatlas/Ballotpedia; ME/AK from public results, approximate) |

Raw snapshots are saved in `data/raw/` so the inputs are auditable. **No poll numbers were invented.** Races with no public general-election polls use fundamentals only and say so in `data/senate_races.csv` (`poll_note`).

---

## 2. Senate model

For each of the 35 races:

**Fundamentals**
```
fundamentals = 2 × PVI  +  GB  +  incumbency  +  candidate_adj  +  candidate_quality (v2)
```
- `2 × PVI`: Cook PVI is expressed in two-party vote-share points relative to the nation; a margin is roughly twice that (`senate.pvi_multiplier`).
- `GB`: generic-ballot margin, the national environment: D+8.4 polling average + 0.4 likely-voter adjustment = **D+8.8** (v2).
- `incumbency`: +3.0 toward the holder's party if an elected incumbent is running; **0 for appointed incumbents in v2** (Moody FL, Husted OH, Darline Graham SC; v1 gave them +1.5); 0 for open seats.
- `candidate_quality` (v2, factor 4): small fundamentals-only terms for TX, OH, NC and NH. See section 8.
- Montana (v2, factor 8): fundamentals are converted to a three-way runner-up margin (section 8).
- `candidate_adj` (only 3 races, can be switched off with `use_candidate_adjustments: false`): half of the candidate's documented over-performance versus the presidential margin in their last race. ME Collins −7.4, NE Osborn +6.9, AK Peltola +5.2. These fix cases where a pure PVI model is clearly wrong because of a candidate's personal vote. Half, because past over-performance only partly carries forward.

**Blend with polls**
```
estimate = w × poll_average + (1 − w) × fundamentals   (+ optional early_vote_adjustment)
```
`w` starts from how many independent aggregators/polls exist: 0 sources → 0; 1 → 0.35; 2 → 0.60; 3 → 0.75; 4+ → 0.85. In v2 it is then multiplied by:
- a **partisan-sponsor** factor (0.5 for D- or R-sponsored polls, which are also shifted 4 pts toward the other party),
- a **staleness** factor `0.5^(max(0, age_days − 14) / 45)`,
- a **herding** factor `max(0.5, 1 − 0.04 × (|poll − fundamentals| − 1))`.

**Per-race uncertainty (idiosyncratic sd):** 4.0 (4+ sources), 4.5 (3), 5.0 (2), 6.0 (1), 7.0 (no polls). v2 adds 0.1 × (|gap| − 1) for poll/fundamentals disagreement, and an RCV/three-way term (combined in quadrature) for AK, ME and MT.

**Majority math.** D seats = 34 not up + D wins. R seats = 31 not up + R wins. Each independent winner joins the Democratic caucus with probability 0.6, the Republican caucus with 0.0, and neither with 0.4 (`independent_caucus`). R controls with ≥50 (VP Vance breaks ties); D needs ≥51. If neither side gets there (for example R 49, D 50, Osborn with neither caucus), we report "no clear majority."

## 3. House model

For all 435 districts:
```
fundamentals = 2 × PVI_2026  +  GB (D+8.8)  +  1.8 × (incumbent running: +1 D, −1 R)  +  seat_bias
estimate     = w_r × rating_margin  +  (1 − w_r) × fundamentals        (v2, factor 3)
```
- v2 incumbency edge is 1.8 (v1: 3.0). See section 8.
- `rating_margin` comes from the consensus expert rating (factor 3). `w_r` = 0.30 for the 146 rated districts and 0.15 for unrated districts, which are treated as Safe for the PVI-favored party (PVI 0 → no rating).
- Open seats, new seats and vacancies get no incumbency term. Kevin Kiley (CA-6, independent, ex-Republican) is treated as an R-aligned incumbent and counts toward the R side.
- District polls: `data/house_district_polls.csv` is supported (blended at 0.5 weight, lower sd), but **it is empty**. I did not collect district polls (they're sparse and mostly partisan internals), so the House runs on PVI, generic ballot, incumbency and (v2) expert ratings.
- Idiosyncratic district sd = 6.0 points.
- D controls with ≥218 seats.

**Sanity check vs. professional ratings (v1, unbiased scenario).** Mean P(D win) by consensus rating category: Safe R 6%, Likely R 18%, Lean R 37%, Toss-up 42%, Lean D 69%, Likely D 97%, Safe D 98%. Our ordering matches the pros. Our median (234 D) runs about 10 seats more Democratic than a ratings-implied count (~223), and our P(D House) of ~93% is close to Silver Bulletin's ~94%. Uniform-swing PVI models tend to over-credit the wave party in marginal seats held by entrenched incumbents, so treat the House seat count as the generous-to-the-environment end. **v2:** blending the ratings in at 30% lowers the House by ~2–3 seats on its own, but the likely-voter adjustment and the smaller incumbency edge (most competitive incumbents are Republicans) push it back up ~2–3 seats, so the v2 unbiased median is 235 (v1: 234). The rating-implied margins in rated seats average 2.5 pts more Republican than our fundamentals.

## 4. Monte Carlo engine (`model.py::simulate`)

For each of N = 100,000 simulations (config `simulations`):
```
national  = poll_bias_mean + poll_bias_sd × t6 / sqrt(6/4)       # ONE draw shared by every race (v2: Student-t df 6, same sd)
state_s   ~ Normal(0, 2.0)  for every state                      # shared by the Senate race + all House seats in the state
region_g  ~ Normal(0, 1.5)  for each Census region               # v2: Northeast / Midwest / South / West
hisp      ~ Normal(0, 6.0)                                       # v2: one polling miss among Hispanic voters
race_r    = race_sd_r × t8 / sqrt(8/6)                           # v2: Student-t df 8, same sd
simulated_margin_r = estimate_r − national + state_s(r) + region_g(r) + hispanic_share(r) × hisp + race_r
```
- **Correlation:** the national term moves every race together, so a polling miss hits all of them at once (the 2016/2020/2024 failure mode). The state term correlates a state's Senate race with its House seats.
- **The bias applies to fundamentals too,** because the generic ballot is itself a poll. If polls overstate Democrats by 3, the House and Senate fundamentals shift by 3 as well.
- **Tipping point (Senate):** in each simulation, order the 35 races from most to least Democratic. The tipping race is the one that delivers Democrats their 51st seat (the 17th D-side win). We report how often each state fills that role. Because the national error shifts every race equally, it doesn't change the ordering, so the tipping-point shares are nearly identical across scenarios. That's expected.
- **Tipping point (House):** the 218th most-Democratic district in each simulation.

## 5. Scenarios (`config.yaml → scenarios`)

| Scenario | poll_bias_mean | poll_bias_sd | Meaning |
|---|---|---|---|
| (i) unbiased | 0 | 3.0 | Polls right on average, matching the 2018 and 2022 midterm record. **Our central case** |
| (ii) presidential-style | +3 | 3.0 | Polls overstate Dems by 3, like 2016/2020/2024. The 3-year average was 3.8; we keep 3.0 because Trump isn't on the ballot (and it's the site's default view). A +3.8 sensitivity run is in REPORT.md |
| (iii) 2025-style | −6 | 3.0 | Polls overstate Republicans by 6, like the 2025 off-year races. **A tail case:** the Trump-era off-year/special-election average was only 1.3 toward R. A −1.3 sensitivity run is in REPORT.md |

All three use fat-tailed (t, df 6) national errors in v2, with the regional and Hispanic layers on top. We tested cutting national sd to 2.5 to offset the new layers, but that made the model *more* confident, which is the opposite of what the history supports. So it stays at 3.0.

Custom: `python run.py --scenario custom --bias 1.5 --bias-sd 2`.

### 5a. User-directed state-specific polling adjustment (added 2026-10-11, ~19:05 ET)

`config.yaml → senate.state_poll_adjust: {TX: -3, OH: -3, ME: -3}`. At the user's direction, the Senate polling averages in Texas, Ohio and Maine are moved 3 points toward the Republican before they are blended with fundamentals. This happens in **every** scenario and stacks on top of the scenario-wide national bias, so the landing "Dems +3" scenario treats these three states as about 6 points too Democratic. It is applied in `model.py::senate_estimates`, after the sponsor and staleness cleanup and before the herding check. The raw Wikipedia averages in `data/senate_races.csv` are not edited, so future data refreshes keep the adjustment. The site shows the unadjusted poll average with a † marker, and the output CSVs carry a `state_poll_adjust` column. **It applies to Senate races only**: the user's request came out of a Senate polling audit, so it is not applied to the TX/OH/ME governor races.

Rationale (from the Oct 11 polling audit). The final polling average minus the result, where positive means the polls overstated the Democrat:
- **Texas.** 2020 Senate: Cornyn +5.2 (270toWin) / +6.5 (RCP) vs a result of Cornyn +9.6, so +3.1 to +4.4. 2024 Senate: Cruz +4.0 (aggregator average) vs Cruz +8.5, so +4.5. The counter-example is 2018: RCP had Cruz +6.8 and he won by 2.6, so the polls overstated the Republican by 4.2.
- **Ohio.** 2024 Senate: Moreno +1.0 (average of 538 +0.7, RCP +1.7, 270toWin Brown +0.3, DDHQ +2.1) vs a result of Moreno +3.6 (50.1-46.5), so +2.6. 2022 Senate: Vance +7.4 (average of RCP +8.0, 538 +6.2, 270toWin +7.8) vs Vance +6.1 (53.0-46.9), so polls overstated the Republican by 1.3.
- **Maine.** 2020 Senate: Gideon +3.8 (270toWin; RCP's last listed average was Gideon +6.5 in September) vs a result of Collins +8.6 (51.0-42.4), a miss of about 12. Maine fundamentals already include a -7.4 Collins candidate adjustment, but polls carry about 73% of the weight there.

The audit found no Democratic-sponsor skew in the current TX/ME polls; Republican-affiliated pollsters make up about a third of each sample. The adjustment is a judgment call about systematic state-level misses, not a correction for any identified bad polls. Ohio's record is mixed (2022 went the other way). Sources: the Wikipedia pages for each race (2018/2020/2024 TX, 2022/2024 OH, 2020 ME Senate) and RealClearPolling's 2018 Texas average.

## 6. Key assumptions you might disagree with
1. The generic ballot (D+8.4) is the right national anchor. Try `--generic-ballot 4`: at D+4 the House is a coin flip (P(D) ≈ 54%, median 219 D) and the Senate drops to ≈60% D.
2. Incumbency is worth 3 points for Senate incumbents and 1.8 for House incumbents (v2).
3. A uniform national swing applied to Cook PVI.
4. Osborn joins the Democratic caucus 60% of the time if he wins. He says he won't caucus with either party.
5. Early vote is **not** used (all adjustments 0): turnout volume doesn't reveal vote choice. The hook exists in `early_vote_adjustment` if you want to encode a belief.
6. v2 uses Student-t errors (df 6 national, df 8 race). The df values are judgment calls.
7. Equal weight across aggregators. There are no pollster house-effect corrections (only a blanket partisan-sponsor penalty).
8. All v2 coefficients (section 8) are our assumptions.

## 7. Known limitations
- Static snapshot as of Oct 10, 2026. Re-pull polls and re-run to update.
- No fundraising, approval, or economic inputs. Poll recency is handled only by a staleness discount on the poll's end date, not by a timeline adjustment for how the national environment has moved since.
- House has no district polls and no district-level candidate data. Redistricted seats rely on Cook's 2026 PVI plus expert ratings. House Hispanic exposure uses each **state's** share as a proxy, because we don't have Hispanic shares on the new 2026 lines. So South Texas seats (TX-28/34/15) are under-exposed and North Texas seats over-exposed.
- RCV in AK and ME is modeled as extra uncertainty, not a simulation of first-round shares plus transfers. Montana's three-way race uses a fixed 75% consolidation assumption.
- Sparse-race inputs (VA, MS, LA) rest on one or two old or partisan polls. v2 now discounts them heavily, so those races are effectively fundamentals-driven.
- The herding evidence comes from one source (PB Polls) and explicitly isn't proof. In 2024 the compression turned out mostly real.
- Some numbers in the candidate adjustments are approximate (labeled above).

---

## 8. Model v2: eight additional factors

The research and sources are in `reports/additional_factors.md`. Every coefficient is a key in `config.yaml`. **All coefficients are our assumptions**, chosen to be modest and informed by the cited work, not fitted. `scripts/factor_attribution.py` measures each factor's marginal effect: "drop-one" is the full v2 minus a run with that factor off; "add-one" is v1 plus only that factor. Results are in `output/factor_attribution.md`.

| # | Factor | What it does | Coefficients (config key) | Source / rationale |
|---|---|---|---|---|
| 1 | **Herding-aware poll weighting** | Shrinks the Senate poll weight as the poll-vs-fundamentals gap grows, and widens race sd | weight × max(0.5, 1 − 0.04 × (\|gap\| − 1)); sd + 0.10 per gap pt (`senate.herding`) | PB Polls herding analysis (slope 0.26 vs 0.52/0.58; dispersion ratio 0.80); FLIPR leans more on fundamentals in 2026 and widens sd when components disagree. Party-neutral: it pulls KS/NE/IA/SC/MT toward R and MN/MI/NH/ME toward D |
| 2 | **Demographic + regional error** | Adds one Hispanic-voter polling-miss shock per sim (effect = Hispanic share × shock) and one shock per Census region | Hispanic sd 6.0 (≈2.4 pts in TX/CA, 2.9 NM, 1.6 FL); region sd 1.5 (`demographic_regional`) | FLIPR's demographic error layer; Split Ticket's correlated demographic errors; Split Ticket "generic Texas R+1" on the Hispanic swing. Hispanic shares: 2020 Census. House uses state share as a proxy |
| 3 | **Expert ratings in the House** | Converts the consensus rating to a margin and blends it in | Toss-up 0, Tilt 2, Lean 4.5, Likely 9, Safe 16 (interpolated on the averaged score); weight 0.30 rated / 0.15 unrated-as-Safe / 0.17 if a district poll exists; env_shift 0 (`house.expert_ratings`) | FLIPR Deluxe blends Cook/IE/Sabato at ~1/6 weight in polled races and more in unpolled ones. We have no district polls, hence 0.30. Ratings are taken at face value (no environment de-bias) because October ratings already reflect a D-leaning environment |
| 4 | **Candidate quality** | Fundamentals-only D-margin terms, so well-polled races move only by the fundamentals share | TX +2.0 (Paxton weak), OH +1.5 (Brown), NC +1.5 (Cooper), NH −1.5 (Sununu) (`senate.candidate_quality`) | Split Ticket on Paxton ("may be the weakest candidate in the entire country"); PB Polls on former senators/governors "carrying their own votes". FLIPR: candidate effects are now ~half their historical size, hence small values. Collins/Osborn/Peltola terms unchanged |
| 5 | **Poll cleanup** | (a) LV adjustment to the generic ballot; (b) partisan polls shifted 4 pts toward the other party at 0.5 weight; (c) staleness discount | GB +0.4 (`generic_ballot_lv_adjustment`); shift 4.0, weight ×0.5, grace 14 days, half-life 45 days (`senate.poll_cleanup`) | Silver Bulletin LV D+8.8 vs D+8.1 (Sep 23); FLIPR's ~4-pt prior for released partisan polls. Effect: VA's June poll weight 0.35 → 0.07; MS 0.35 → 0.07; LA 0.35 → 0.14 |
| 6 | **Incumbency reweight** | Smaller House edge; appointed senators treated as open seats | House 1.8 (was 3.0) (`house.incumbency_bonus_v2`); appointed 0.0 (was 1.5); redrawn-state multiplier available but **off** (1.0), because we lack district-overlap data | Jacobson: 2024 House incumbency ≈1.2 (abstract-level); 2025 district estimate 2.58; FLIPR treats appointed incumbents as open seats |
| 7 | **Uncertainty structure / fat tails** | Student-t national and race errors at the same sd; scenarios documented against base rates; regional layer from #2 | national df 6, race df 8 (`error_model`); national sd kept 3.0 | Silver: presidential years +3.8 D overstatement, 2018/22 ~even, off-years 1.3 toward R; FLIPR uses mildly fat tails. (iii) relabeled as a tail case |
| 8 | **Election mechanics** | RCV transfer uncertainty; Montana three-way consolidation; runoff notes; independent caucus | AK +2.0 sd, ME +1.5 sd, no mean shift (`senate.rcv`); MT runner-up gets 75% of the anti-R vote, +2.0 sd (`senate.three_way`); independents caucus D 0.6 (unchanged) | FLIPR simulates RCV; the ASR poll has Peltola +2 in both rounds, so there's no mean shift. LA House seats go to a **Dec 12 runoff** if no one clears 50% (noted, not simulated). GA 50%+1 runoff risk ignored (Ossoff ~+8) |

### Measured effects (drop-one, 40,000 sims; P in percentage points)

See `output/factor_attribution.md` for the full tables in all three scenarios. Headline, unbiased scenario:
- **Herding:** Senate P(D) −1.0 in full v2. On its own on top of v1 it's −4.6, but candidate quality and open-seat treatment shrink the very gaps it reacts to.
- **Expert ratings:** House −2.9 D seats, P(D House) −1.7.
- **Incumbency reweight:** House +1.5 D seats, Senate P(D) +1.5 (open-seat OH/FL/SC).
- **Poll cleanup:** House +1.2 seats, Senate P(D) +1.4.
- **Candidate quality:** Senate P(D) +1.7.
- **Demographic/regional:** P(D House) −1.5 (wider), Senate P(D) −0.9.
- **Fat tails:** Senate P(D) +1.5 (t-draws concentrate more mass near the center at the same sd).
- **Mechanics:** ≈0.

Net: the factors largely offset, and every headline number moved by less than one point (see REPORT.md "Before vs after").

## 9. Governor races (added 2026-10-10, ~04:00 ET)

**Scope.** All 36 governorships up in 2026 (18 D-held, 18 R-held; 24 D / 26 R nationally today). Data in `data/governor_races.csv`, built by `scripts/build_governor_data.py` from raw snapshots in `data/raw/2026_United_States_gubernatorial_elections.wiki` and `data/raw/governor/gov_<State>.wiki` (Wikipedia wikitext pulled 2026-10-10 ~04:00 ET). Senate and House results are unchanged by this addition: governor draws come after all Senate/House draws, so the same seed reproduces the earlier Senate/House numbers exactly.

**Prior (no PVI fundamentals).** Governor races are much less nationalized than federal races (Phil Scott R leads in a D+17 state; Shapiro leads by 20+ in an R+1 state), so a PVI + generic-ballot prior would be badly wrong in several states. The prior is the average of seven forecaster ratings from the Wikipedia predictions table: Cook (Oct 1), DDHQ (Oct 8), Fox News (Oct 6), Inside Elections (Oct 1), RCP (Oct 5), Sabato (Oct 6), Silver Bulletin (Oct 8). Each rating is scored +3 Safe/Solid D … −3 Safe/Solid R (Likely 2, Lean 1, Tilt 0.5, Toss-up 0) and converted to a margin with the House table (Toss-up 0, Tilt 2, Lean 4.5, Likely 9, Safe 16).

**Polls.** Where the race page has an aggregate-polls table, the poll input is the simple mean of the listed aggregators (270toWin, DDHQ, FiftyPlusOne, RCP, Race to the WH, Silver Bulletin). We use our own mean rather than Wikipedia's "Average" row because the two disagree in some races (Georgia: aggregator mean R+1.6, Wikipedia row R+0.7). Where no aggregate exists and the race isn't unanimously safe, we use the mean of the most recent nonpartisan polls: Alaska (final RCV round, ASR Oct 1–3 D+8, NYT/Siena Sep 24–Oct 1 D+4), South Carolina (Resonance Media Sep 29–Oct 3, R+10), Vermont (State Navigate Oct 2–4 R+3, Braun/Vermont Public Sep 10–21 R+10, UNH Sep 17–21 D+6). Wisconsin's aggregate (RCP/Silver, polls through Aug 20) is stale, so it is **replaced** by the Marquette Law School Poll of Sep 16–23 (692 LV: Crowley 49, Tiffany 46 → D+3.0, one source). Z to A Research (D-sponsored) Sep 28–Oct 1 (D+5) is excluded. Unanimous Safe/Solid races without aggregates run on the ratings prior only. Poll weight, race sd, and the stale-poll and partisan-poll discounts follow the Senate settings (Wisconsin's aggregates end Aug 20 and get about 0.57× weight; Minnesota's end Sep 15). No herding or candidate-quality terms.

**Errors.** Same national (fat-tailed), state, Census-region and Hispanic draws as the Senate/House, plus Student-t race noise with the Senate race sd and an extra 1.0 pt (in quadrature) for less predictable governor races. Alaska gets +2.0 sd for ranked-choice transfers. Maine's governor general election is plurality, not RCV; Rick Bennett (I) is polling around 6%.

**Prediction markets** (`data/markets/`): Polymarket (Gamma API) and Kalshi (public trade API) snapshots from 2026-10-10 ~04:08 ET. They are exported to the site for comparison only. They are not a model input.

**Rhode Island (independent challenger).** Gov. Dan McKee lost the Sep 8 primary to Helena Foulkes. The main challenger is independent **Ken Block**, not the Republican: UNH Sep 17–21 (598 LV) has Foulkes 44, Block 25, Guckian (R) 17. RI is modeled as Foulkes (D) vs Block (I) with margin = Foulkes − Block = D+19 (one source). A Block-campaign poll (Opinion Diagnostics Sep 23–25: three-way 41–24–19; hypothetical head-to-head without Guckian Block 44–39) is excluded as sponsored. The ratings prior (Solid D from all seven forecasters) and the shared national error are applied unchanged. That is a simplification, because a national swing toward Republicans does not translate one-for-one to an independent.

**Refresh log.** 2026-10-10 ~06:05 ET: all Senate, House, House-ratings, gubernatorial and race pages were re-pulled. The ratings tables, the generic-ballot aggregate (D+8.4) and every aggregate-polls table were unchanged since the ~01:47/~04:00 ET pulls. Only individual polls were added (e.g., Wedgewood Oct 8–9 Michigan Senate D+6 and governor D+10), and those don't enter the model until the aggregators update. The Polymarket and Kalshi snapshots were refreshed with no move of 2 points or more. The early-vote adjustment stays 0, because early-vote volume does not reveal vote choice. 2026-10-10 ~18:15 ET: everything was re-pulled. Ratings, the generic ballot and the Senate averages were unchanged; the Texas Senate Wikipedia average is still Talarico +3.3. New York governor: 270toWin moved from D+14.0 to D+12.8, so the aggregator mean went from D+12.56 to D+12.32. Louisiana Senate: a Wikipedia editor removed the single Race to the WH aggregate (R+5.8). No new data replaced it, so the model input stays as it was. New individual polls (Trafalgar GA/TX, Rasmussen MN) wait until the aggregators pick them up. On Polymarket, TN-Sen D moved from 6.1% to 8.7% and MI-Sen R from 30.5% to 32.5%. 2026-10-10 ~21:07 ET: everything was re-pulled. No changes to ratings, the generic ballot, or any aggregate-polls table (the five Senate race pages that changed did not touch their aggregates). Model outputs are identical. The market snapshot was refreshed: Polymarket TX-Gov D (Hinojosa) moved from 22.5% to 19.0%. 2026-10-11 ~00:09 ET: everything was re-pulled. The overview ratings, the generic ballot and every aggregate-polls table were unchanged. The individual race pages, however, list newer Silver Bulletin governor ratings dated Oct 10 than the overview table (Oct 8): Iowa moved from Solid D (flip) to Likely D (flip) and Ohio from Likely D (flip) to Lean D (flip). Alaska and Michigan already matched. These were applied with `RATING_OVERRIDE` in `scripts/build_governor_data.py`. Landing-scenario P(D) moved from 82.4% to 81.9% in Iowa and from 58.4% to 57.7% in Ohio. Senate and House are unchanged. The market snapshot was refreshed with no move of 2 points or more; TX-Gov D went from 19.0% to 20.5%. 2026-10-11 ~03:12 ET: everything was re-pulled. The ratings, the generic ballot and every aggregate-polls table were unchanged, and model outputs are identical. Wikipedia's main governor ratings table still shows Silver Bulletin as of Oct 8, so the IA/OH `RATING_OVERRIDE` (Silver Bulletin, Oct 10) stays in place. No race page shows any other Silver Bulletin discrepancy. The market snapshot was refreshed: Polymarket OH-Gov D (Acton) moved from 70.5% to 68.5%. 2026-10-11 ~15:12 ET: everything was re-pulled. South Carolina Senate: the Wikipedia aggregate-polls table was updated Oct 11 (Race to the WH dropped; 270toWin R+1.0, FiftyPlusOne R+1.5, RCP R+2.0, Silver Bulletin R+2.5). The average moved from Graham +1.6 to +1.8 (polls through Oct 8). Landing-scenario P(D) in SC went from 13.8% to 13.4%; Senate P(D) went from 35.2% to 35.1% and P(R) stays at 64.0%. The Maine Senate table refreshed with its average unchanged (Jackson +2.0). Everything else was unchanged, including the main governor ratings table, which still shows Silver Bulletin as of Oct 8, so the IA/OH `RATING_OVERRIDE` stays. The market snapshot was refreshed: Polymarket TX-Sen R (Paxton) moved from 35.5% to 37.5%. 2026-10-11 ~18:14 ET: everything was re-pulled. Kansas Senate: the Wikipedia aggregate table was updated Oct 11 (DDHQ Hamilton +1.0 through Oct 10, FiftyPlusOne +1.5, RCP now a tie), moving the average from Hamilton +0.6 to +0.7. Landing-scenario P(D) in KS went from 10.8% to 10.9%. The IA and ME governor tables had 270toWin's date corrected back to Oct 6 and Oct 5, with margins unchanged. The ratings, the generic ballot and the main governor ratings table (Silver Bulletin still dated Oct 8) were unchanged, so the IA/OH `RATING_OVERRIDE` stays. The market snapshot was refreshed: Polymarket IA-Gov D (Sand) moved from 88.5% to 86.5%. 2026-10-11 ~19:10 ET: added the user-directed `state_poll_adjust` (TX/OH/ME Senate, -3 toward the Republican; see §5a). Data inputs are unchanged. 2026-10-12 ~00:08 ET: everything was re-pulled. The main governor ratings table now has Silver Bulletin dated Oct 11 and DDHQ dated Oct 11. Ohio now shows Silver Bulletin Lean D (flip), so the OH `RATING_OVERRIDE` was removed. DDHQ moved Ohio from Lean D (flip) to Tossup, so the OH ratings score went from 0.29 to 0.14. Silver Bulletin moved Vermont from Likely R to Solid R. Iowa's overview column still says Solid D (flip) while its race page shows Silver Bulletin Likely D (flip) dated Oct 11, so the IA override stays. Governor aggregate tables were edited across many race pages: MN went from D+10.8 (3 sources, through Sep 15) to D+8.0 (RCP 7.0 and Silver Bulletin 8.9, through Oct 7; Race to the WH dropped); AZ went from D+7.8 to D+8.1; CT from 13.6 to 13.9; NE from R+7.3 to R+7.5; MA from 20.0 to 20.1; CA from 19.9 to 19.75; FL from R+4.1 to R+4.2. Several 270toWin dates were corrected to administration dates. Landing-scenario governor moves: MN 91.6% to 85.5%, AZ 77.3% to 78.6%. Senate and House are unchanged; the user's TX/OH/ME Senate -3 adjustment stays. Market snapshot refreshed (no displayed market moved 2 points or more).

**Limitations.** Because the prior comes from ratings, the governor model inherits the forecasters' judgment and double-counts polls to some degree (forecasters already look at polls). Rating-only Safe races carry about 2–3% upset odds in the unbiased scenario, which is probably too generous. Rhode Island's D-vs-independent margin rests on a single nonpartisan poll.
- 2026-10-12 ~03:20 ET refresh: Senate/House/ratings/governor overview pages unchanged; per-race page edits did not change any aggregator average. Iowa RATING_OVERRIDE kept (overview still Solid D (flip); race page Silver Bulletin Likely D (flip)). Model outputs unchanged. Published fresh market snapshot (Polymarket 03:19 ET: Kansas Senate Hamilton 38.5% → 36.5%, a 2-pt move; Kalshi Senate D 61-62¢, House D 89-90¢).
- 2026-10-12 ~06:07 ET refresh: only edits were a Senate overview heading fix and non-polling text on the Kansas/Minnesota Senate pages; no aggregator average changed. Iowa RATING_OVERRIDE kept (sources still disagree). Model outputs unchanged. Published fresh market snapshot (Polymarket 06:07 ET: Vermont governor Janoo (D) 25.1% → 23.0%, a 2.1-pt move; Kalshi Senate D 61-62¢, House D 89-90¢).
- 2026-10-12 ~12:36 ET refresh: Senate poll averages updated from race-page aggregator tables (Wikipedia Average rows): MI El-Sayed +3.3 → +3.5 (Oct 5-12), GA Ossoff +8.3 → +8.5 (Oct 4-11), FL Moody +6.1 → +6.2 (Sep 27-Oct 9); AK (+2.4) and NC (+9.2) unchanged in value but end dates moved to Oct 12. Governor aggregates: MI Benson +7.4 → ~+7.7 (DDHQ 6.1 → 7.4, 50+1 7.5 → 7.7), AZ Silver 8.7 → 8.8, NM Silver 7.7 → 7.9. Iowa RATING_OVERRIDE kept (sources still disagree). Landing Senate R 70.7% → 70.6%; no race moved 1+ pt. Fresh market snapshot (Polymarket 12:36 ET: AL governor Jones (D) 7.9% → 4.3%, TX Senate Paxton (R) 37.5% → 35.5%).
- 2026-10-12 ~15:25 ET refresh: MN Senate average Flanagan +2.9 → +3.0 (DDHQ/50+1/RCP now Oct 12; Silver 3.5 → 3.9, Oct 9). Other page edits were non-polling text. Iowa RATING_OVERRIDE kept (sources still disagree). Model outputs changed only at the fourth decimal (landing Senate R 70.6%). Fresh market snapshot (Polymarket 15:25 ET: AZ governor Hobbs (D) 88.5% → 86.5%).
- 2026-10-12 ~18:20 ET refresh: NE Senate average Ricketts +0.9 → +1.1, now 4 aggregators (DDHQ added, Oct 2-12). NE governor average adds FiftyPlusOne (Pillen +5.0) → Pillen +6.7 (was +7.5, 2 sources). RCP moved its NE Senate rating Tossup → Lean R (Senate ratings are not a model input). Iowa RATING_OVERRIDE kept (sources still disagree). Small House/SC shifts are Monte Carlo noise: Osborn's independent-caucus binomial draws change RNG consumption downstream. Fresh market snapshot (Polymarket 18:20 ET; no displayed market moved 2+ pts).
