# Additional factors for the 2026 midterm model

*Researched 2026-10-10, about 3 AM ET. This builds on `METHODOLOGY.md` and on the user's document, which already covers partisan nonresponse, soft leaners, anti-Trump-anger, Hispanic/young/Black undecided voters, turnout geography and weighting, Trump-only voters, the off-year track record, LV screens and special-election overperformance. I don't repeat those here.*

## What the model has today (from `config.yaml`)
- Fundamentals = 2×Cook PVI + generic ballot (D+8.4) + incumbency (3.0 pts House/Senate, 1.5 for appointed senators).
- Poll weight goes up to 0.85 in well-polled Senate races. There are no house effects and no LV/RV adjustment.
- Error layers: one national error (scenario mean plus sd 3, normal), a state error (sd 2, shared by the Senate race and that state's House seats), and race error (sd 4–7 Senate, 4.5–6 House).
- Candidate adjustments exist only for ME, NE and AK. AK and ME RCV are modeled as plain two-way margins.
- House seats use the 2026 maps and Cook 2026 PVI. The `consensus_rating_score` column is loaded but not used.
- Current output, unbiased scenario: Senate 68% D, House 93% D, mean 235 D seats.

Benchmarks for comparison:
- Silver Bulletin FLIPR (Oct 9): about 94% D House, and Democrats "favored" in the Senate. [link](https://www.natesilver.net/p/nate-silver-2026-midterm-election-polls-model)
- Cook (Oct 9): D net +9 to +19, which means 224–234 D seats. [link](https://www.cookpolitical.com/analysis/house/house-overview/eighteen-more-house-race-ratings-move-democrats-favor)
- Other public Senate trackers: roughly 41–53% D (Call the Map, FutureBallot and others, via search summary; I didn't check each one).

So our House number is a little high compared with the pros, and our Senate number is at the high end of the public range.

---

## Priority ranking (what to add, in order)

| # | Factor | Main effect on our numbers | Effort |
|---|---|---|---|
| 1 | Poll compression / possible herding → shrink red-state Senate polls toward fundamentals | Lowers D odds in TX/OH/AK/IA/KS/NE, raises them in MN/NH/MI. Probably cuts Senate D odds a few points | Low |
| 2 | Demographic/regional correlated error (Hispanic layer + elasticity) | Wider, clustered outcomes in TX/FL/NV/AZ/NM and South TX/CA Central Valley House seats | Medium |
| 3 | Debiased expert-rating blend for House (data already loaded) | Pulls the House about 5–10 seats toward Cook's 224–234 | Low |
| 4 | Candidate quality and scandal scores beyond ME/NE/AK (Paxton etc.) | Mostly affects lightly polled races. Careful: in well-polled races the polls already contain it | Low–Med |
| 5 | Poll hygiene: house effects, LV adjustment, partisan-poll penalty, stale-poll timeline adjustment | GB about +0.4 to +0.7 D (LV). Fixes stale VA/MS/LA/NM polls | Medium |
| 6 | Re-size incumbency (Jacobson 1.2 pts in 2024) and treat appointed incumbents as open seats | Small shift toward D in House R-incumbent seats. OH/FL/SC Senate | Low |
| 7 | Better uncertainty structure: fat tails, drift vs Election-Day error, regional layer | Wider tails. P(control) moves a few points toward 50% | Low–Med |
| 8 | Election mechanics: AK/ME RCV, MT 3-way, GA/LA runoffs, independent caucus choice | AK and ME are top-5 tipping states, so this matters for Senate control | Medium |
| — | Presidential approval / midterm-penalty prior | Sanity check. It currently agrees with the GB (about D+8.5–8.7), so the effect is small | Low |
| — | Fundraising | Weak causal evidence and mostly already in polls. Optional small term | Low |
| — | Economy, abortion measures, redistricting | Already in GB/approval, or already in the data. Use as context, not new terms | — |

---

## 1. Poll compression / possible herding (HIGH)
**What it is.** Senate polls this year sit much closer to 50/50 than state partisanship plus the national environment would predict. Some of that is real (candidate quality, ticket-splitting). Some may be herding, or pollsters weighting toward a "close race" prior.

**Evidence** (PB Polls, as of Oct 10; [link](https://polls.politicalbetting.com/us/analysis/senate-herding)):
- Slope of polls on state lean in heavily polled races: **0.26 in 2026**, against 0.52 in 2022 and 0.58 in 2024 at the same point (±0.12 SE).
- How did those years finish? In 2022 the results came out much steeper than the polls (0.89), so the compression was false. In 2024 it was mostly real (0.62).
- Agreement between polls (observed spread ÷ sampling spread): **0.80 in 2026**. Below 1 means the polls agree more closely than sampling noise alone allows, which is a classic herding sign. The figures for 2022 and 2024 were 1.42 and 0.87.
- Gaps between polls and the "expected" margin (lean + GB D+9):
  - Bigger D-ward gaps: TX +6.5, AK +5.7, OH +5.2, KS +8.3, NE +10.2, IA +4.3.
  - R-ward gaps: MN −10.6, NH −5.5, MI −5.5, ME −15.2 (Collins).
- The source itself says compression is "consistent with herding but does not prove it."

**Why it matters for 2026.** Our Senate tipping states (AK, TX, OH, ME, IA) are exactly the races where the polls show Democrats well above fundamentals. This is a **party-neutral** reason, not "unskewing," to trust those D leads a bit less. It cuts the other way in MN, NH and MI. Silver makes the same point: his fundamentals pull SC Graham from +2.6 in polls to +5.3, and he expects Flanagan (MN) to outperform her polls ([link](https://www.natesilver.net/p/what-if-the-polls-are-wrong-again)). FLIPR has also increased the weight on fundamentals relative to polls for 2026 ([methodology](https://www.natesilver.net/p/flipr-midterms-model-methodology)).

**Magnitude.** This is my estimate, not a published coefficient. Dropping the max poll weight from 0.85 to about 0.65–0.70 moves each race by roughly 15–20% of its poll-vs-fundamentals gap. That's about 1 pt toward R in TX/AK/OH and about 1.5–2 pts in KS/NE.

**Feasibility: easy.** Change `poll_weight_by_sources`. A better option is to scale the poll weight down as |poll − fundamentals| grows, and widen race sd at the same time, which is what FLIPR does when components disagree. Keep the existing candidate adjustments so Collins isn't wrongly shrunk toward the Maine lean.

## 2. Demographic / regional correlated error, with Hispanic swing and elasticity (HIGH)
**What it is.** Today our error is national (uniform) + state + race. Real misses cluster by demographic group and region: a miss among Hispanics hits TX, NV, AZ, FL, NM and South Texas House seats together. FLIPR uses this layer ("Democrats beat their polls among Hispanics, but Republicans beat their polls in the Midwest"), and says midterm errors are spread fairly evenly across the national, demographic, state and race layers, *less uniform* than in presidential years. Split Ticket also uses "correlated error terms on demographic, state, and national levels" ([link](https://www.theargumentmag.com/p/split-ticket-2026-midterms-model)).

**Why it matters for 2026.**
- Split Ticket says Texas is "uniquely poised for a sharp leftward swing" because Democrats are gaining back Hispanic voters disproportionately (26% of the TX electorate). Their modeling puts generic Texas at about R+1, versus Trump's R+14 in 2024 ([link](https://www.theargumentmag.com/p/how-texas-finally-became-a-toss-up)).
- The redistricting picture depends on the same question. NDRC and Newsweek say the TX map "relied heavily on 2024 data" and may net only 2–3 seats if Hispanic voters swing back. TX-28 and TX-34 are already top House tipping seats in our presidential-miss scenario. NC-1 and NC-3 have a similar "dummymander" risk ([NDRC memo](https://democraticredistricting.com/wp-content/uploads/2026/10/2026-NDRC-Pre-Election-Landscape-Memo.pdf); [Newsweek](https://www.newsweek.com/republicans-shell-out-millions-to-win-red-districts-they-just-redrew-12538341)).
- **Elasticity:** swingy states and districts (NH, many white working-class seats) move more than 1:1 with the national environment. Polarized states (GA) move less. FLIPR says the elasticity effect is "relatively minor."

**Magnitude.** No published size for 2026. A Hispanic-specific error sd of about 3–4 margin pts, scaled by each district's Hispanic share, is my assumption. **Thin evidence; flag it as such.**

**Feasibility: medium.** Add Hispanic % (and optionally college %, Black %, region) per state and district from ACS. In each sim, draw one shock per group and add Σ(share × shock). The structure is simple. Getting district demographics on the new 2026 lines is the main work. Daily Kos Elections or Dave's Redistricting publish CD demographics for new maps.

## 3. Debiased expert-rating blend for the House (HIGH for the House, easy)
**What it is.** FLIPR "Deluxe" turns Cook, Inside Elections and Sabato ratings into implied margins. It shifts them so their implied national environment matches the model's (experts implicitly assume about a D+2 environment, against FLIPR's D+7 in August), then blends them in at about **1/6 weight** in polled congressional races, and more in unpolled ones ([methodology](https://www.natesilver.net/p/flipr-midterms-model-methodology)).

**Why it matters.** Our House model has no district polls and no candidate data. It sits at a mean of 235 D seats against Cook's 224–234, and our methodology already says it "over-credits the national wave." Expert ratings carry the race-by-race information we lack: candidate quality, spending, local issues.

**Magnitude.** Probably moves the House mean down by a few seats. It shouldn't change the national environment if the de-biasing is done correctly.

**Feasibility: easy.** `house_districts.csv` already has `consensus_rating_score` for 146 districts. Map score → margin, subtract the implied national mean shift, and blend at about 0.17–0.3.

## 4. Candidate quality and scandals beyond ME/NE/AK (MED–HIGH)
**What it is.** FLIPR's "fancy fundamentals" use several candidate inputs ([methodology](https://www.natesilver.net/p/flipr-midterms-model-methodology)):
- elected experience on a 0–3 scale;
- scandals, with new ones weighted more than ones voters have already absorbed;
- party-loyalty scores, where mavericks outperform;
- incumbent's previous margin and first-term status.

Split Ticket uses WAR (Wins Above Replacement) scores ([database](https://split-ticket.org/full-wins-above-replacement-war-database/)).

**2026 specifics:**
- **Paxton (TX).** Split Ticket: "may be the weakest candidate in the entire country," citing impeachment, the divorce, a bruising primary, and corruption and infidelity scandals. They put him in the same tier as Mark Robinson and Doug Mastriano. Talarico they rate "at best, replacement level" ([link](https://www.theargumentmag.com/p/how-texas-finally-became-a-toss-up)).
- **Experience edge.** Former senators and governors Brown (OH), Cooper (NC) and Sununu (NH-R) "carry their own votes" (PB Polls caveat).
- **Late replacements.** Troy Jackson (ME-D) and Darline Graham (SC-R, appointed) are flagged by FLIPR as late entrants with incomplete data.

**Magnitude.** FLIPR says candidate-quality factors (incl. incumbency) are now "only about half as important" as over 1990–2022, because of polarization. No public coefficient for Paxton exists. Robinson- and Mastriano-type candidates underperformed their tickets by double digits, but those were *governor* races, where there's more ticket-splitting. **Don't carry that size over to a Senate race.**

**Important caveat (double counting).** Where we give polls 0.85 weight, Paxton's weakness is already in the TX polls. A candidate term only changes the 15% fundamentals share, plus lightly polled races. Use it inside the fundamentals component only.

**Feasibility: easy.** Add `experience` (0–3) and `scandal` (0/1/2) columns to `senate_races.csv` with small fixed coefficients, e.g. ±1–3 pts on fundamentals. Those coefficients would be our judgment; document them as such.

## 5. Poll hygiene: house effects, LV adjustment, partisan polls, stale polls (MED)
- **LV adjustment.** Silver Bulletin: in 2026, LV versions of polls have been better for Democrats than RV versions. Their LV-adjusted generic ballot is D+8.8 against D+8.1 unadjusted (Sep 23; [link](https://www.natesilver.net/p/generic-ballot-average-2026-nate-silver-bulletin-congress-polls)). In August it was about 6.5 → 8. So our D+8.4 mixed-population average is probably about 0.4–0.7 pts too *low* for D. This partly offsets #1.
- **House effects.** FLIPR shifts consistently D-leaning or R-leaning firms toward the consensus (e.g., Marist "very good numbers for Democrats this cycle"). Released partisan/internal polls start from a prior of about **4 pts** bias toward the sponsor.
- **Timeline adjustment.** Old polls get shifted by a fraction of the GB change since fieldwork. This matters for us because VA (June poll), MS (August, a D-sponsored poll) and LA (D-sponsored polls) are stale or partisan.
- **Feasibility: medium.** Easy version: add a constant +0.5 LV shift to the GB, and haircut partisan-sponsored polls by about 4 pts toward the other party. Full house effects need a poll-level database (NYT, which FLIPR uses, or VoteHub's API, which Split Ticket uses).

## 6. Incumbency sizing and open/appointed seats (MED)
- **Evidence:**
  - Jacobson estimates the **2024 House incumbency advantage at 1.2 pts**, down from 3.0–3.7 in 2014 ([T&F 2026](https://www.tandfonline.com/doi/full/10.1080/07343469.2026.2726753), via search summary).
  - Another 2025 district-level estimate puts it at 2.58 ([JPIA](https://jpia.princeton.edu/news/year-change-incumbents-held-ground-us-house)).
  - FLIPR fits separate incumbent and open-seat regressions. It also shrinks the incumbency bonus where an incumbent's new district has little overlap with the old one, which matters for TX, CA, NC, OH, UT, FL, TN, LA. It treats **appointed incumbents as open seats**, and adjusts for an anti-incumbent environment using congressional approval.
- **For us:** the 3.0 House bonus is probably on the high side. Most incumbents running are Republicans, so lowering the bonus moves things slightly *toward D*. That cuts against fix #3, but the expert blend should dominate. Appointed Senate incumbents in our data are Husted (OH), Moody (FL) and Graham (SC), each with a 1.5 bonus. FLIPR would give them 0.
- **Feasibility: easy.** Set `incumbency_bonus` to about 2.0 with sensitivity runs at 1.2 and 3.0, and halve it in redistricted seats.

## 7. Uncertainty structure (MED)
- **Drift vs Election-Day error.** FLIPR splits national error into drift (which goes to zero by Election Day and is smaller in polarized eras; "the national picture now 'locks in' earlier") and Election-Day polling error. At 24 days out, drift should be small.
- **Midterm errors are less uniform** than presidential ones. In 2018 and 2022 the national polls were about unbiased but there were big regional misses (e.g., the 2022 NY/NJ "mini red wave"). This supports #2 plus a lower national sd and higher regional/state sd.
- **Fat tails.** FLIPR uses mildly fat-tailed distributions. Our normals understate the chance of a 2010/1994-type blowout.
- **Polling-error base rates** (Silver, [link](https://www.natesilver.net/p/what-if-the-polls-are-wrong-again)):
  - Final-3-week polls overstated Democrats by **3.8 pts** on average in 2016/2020/2024.
  - Midterms 2018 and 2022 were about unbiased.
  - Trump-era off-year and special elections were biased toward R by **1.3 pts**.
  - Silver deliberately keeps the model party-neutral.
  - Our 2025-style scenario (polls overstate R by 6) is much larger than his 1.3-pt off-year average. It's best treated as a tail case, not a central one.
- **Feasibility: easy to medium.** Use a Student-t (df ≈ 5–8) for the national and race draws. Add a 4-region error (sd about 1.5–2). Optionally replace the three discrete scenarios with one mixture prior, keeping them as labeled sensitivities on the site.

## 8. Election mechanics: RCV, three-way races, runoffs, caucus choice (MED, Senate-critical)
- **Ranked-choice voting in Alaska and Maine.** FLIPR now simulates RCV explicitly. **AK and ME are two of our top-4 Senate tipping states.** Peltola leads by 2 pts in both the first and final rounds in the latest Alaska Survey Research poll (Silver Bulletin, Oct 9). That makes the AK transfer effect small *in that poll*, but transfers add variance. Whether Maine has notable minor candidates needs checking.
- **Montana** is a 3-way race (Bodnar-I and Bankhead-D split the anti-Republican vote). We model it as Alme vs the runner-up. A vote-split model would be more accurate.
- **Runoffs.** Georgia requires 50%+1 (low risk, with Ossoff at about +8.5). Louisiana House general elections have runoffs on Dec 12 under the new map ([LA notice](https://redistricting.lls.edu/wp-content/uploads/LA-callais-20260529-notice-of-leg.pdf)), so a few House seats may not be settled on election night.
- **Independents.** FLIPR treats Osborn-type independents who displaced the Democrat as de facto Democrats, and simulates other independents with a right-skewed vote-share distribution. Our `independent_caucus: {D: 0.6}` is a judgment call worth a sensitivity run, since it decides control in tied-ish sims.
- **Feasibility: medium.** For RCV, simulate first-round shares plus transfer rates. For MT, draw a three-way vote share.

---

## Lower-priority or already-covered factors (checked, don't add as separate terms)

**Presidential approval / midterm penalty (use as a prior or sanity check).**
- Trump approval on Oct 9 was about **36.7–38.4% approve, net −22 to −24** in the NYT-based, Crosstab and PolitiKool averages ([NYT-based tracker](https://theelectionnewspaper.com/polls/approval); [Crosstab](https://crosstab.vote/trump-approval-rating/)). One tracker, Poliwave, shows 34.5%. Gallup was 35% in early August and 33% in late August, the lowest pre-midterm reading in the APP table except Truman's in 1946.
- From the [APP table](https://www.presidency.ucsb.edu/statistics/data/seats-congress-gainedlost-the-presidents-party-mid-term-elections), 1946–2022 (20 midterms), my calculation:
  - The president's party lost **25.7 House seats on average** (median 22) and **3.6 Senate seats**.
  - In the 11 midterms with approval under 50%, the averages are **−34.7 House and −4.5 Senate**.
  - That's a *net* seat-change prior. Redistricting (Sabato: GOP map edge), the GOP's 220-seat starting point and polarization all temper it.
- FLIPR's 1946+ prior (approval, last House vote, midterm status, polarization) gives **D+8.7** on the House vote. That's almost the same as our GB, so blending it in barely moves the mean but adds confidence ([link](https://www.natesilver.net/p/everything-is-breaking-democrats-way)).
- Abramowitz's generic-ballot model finds approval adds **no** predictive value beyond the GB ([Sabato](https://centerforpolitics.org/crystalball/generic-ballot-model-gives-democrats-strong-chance-to-take-back-house-in-2026/)).
- **Bottom line:** low value as a new term. Worth one line on the site: history argues *against* the GOP-holds-both case.

**Fundraising.**
- FLIPR uses individual contributions only, with in-state dollars weighted **5×**.
- In TX, Talarico raised $27M in Q1 and about $28–30M in Q2. Paxton raised $18M in Q3. But Republican outside groups had spent **$323M vs Democrats' $116M** per AdImpact ([Texas Tribune](https://www.texastribune.org/2026/10/05/ken-paxton-third-quarter-fundraising-texas-senate-race-2026/); [Newsweek](https://www.newsweek.com/how-talarico-and-paxtons-midterms-war-chests-compare-12535730)). That's a reminder that candidate cash ≠ total air cover.
- In AK, Sullivan had $7.3M cash on hand vs Peltola's $4.6M ([VoteLog](https://votelog.org/investigations/alaska-senate-general-money)).
- Causal evidence that late spending persuades voters is weak: Kalla & Broockman's 49-experiment meta-analysis finds about zero persuasion in general elections ([APSR](https://www.cambridge.org/core/journals/american-political-science-review/article/abs/minimal-persuasive-effects-of-campaign-contact-in-general-elections-evidence-from-49-field-experiments/753665A313C4AB433DBF7110299B7433)). Fundraising works as a *signal* of candidate strength, and that's mostly already in polls.
- Q3 FEC reports are due **Oct 15**. If we add this, use a small capped log-ratio term in the fundamentals component only.

**Economy.**
- UMich sentiment was 46.3 (preliminary, Oct). It's the second-lowest on record, and current conditions hit an all-time low of 44.7.
- Year-ahead inflation expectations are 4.7%, up from 3.4% before the February Iran war pushed gas prices up. The Fed hiked in September ([CNN via KQ2](https://www.kq2.com/cnn-business-consumer/2026/10/09/with-midterms-approaching-americans-confidence-in-the-economy-is-in-a-tailspin/)).
- A search summary said gas is around $4.36/gal, but **I didn't verify that.**
- All of this runs *through* approval and the GB, so adding it separately would double count. Use it only to argue that late drift toward the GOP is unlikely.

**Abortion ballot measures.**
- On the ballot: MO (repeal of the 2024 abortion right), NV Q6, ID Prop 1 and VA ([Ballotpedia](https://ballotpedia.org/Ballot_measures_related_to_abortion_policy,_2026)).
- None of these states has a top-tier competitive Senate race in our model.
- In 2024, abortion measures in AZ, NV, MO, MT and FL coincided with Trump wins in all five, so there's no clear evidence of a turnout boost. **Thin evidence; skip.**

**Redistricting** (already in our data; small residuals only).
- We use the 2026 maps and Cook 2026 PVI. Spot check: LA has 1 D-lean seat, TN 0, FL 4, AL 1. MO uses the old map because the new one is on hold pending a referendum ([Ballotpedia](https://ballotpedia.org/Redistricting_ahead_of_the_2026_elections)). VA uses its 2021 map, 6 D-lean, because the VA Supreme Court voided the amendment on May 8 and SCOTUS denied the appeal ([CNN](https://www.cnn.com/2026/05/08/politics/virginia-supreme-court-redistricting)). All consistent.
- Sabato's net map effects: TX R+3–4, CA D+4–5, NC R+1, OH R+0–1 ([Sabato](https://centerforpolitics.org/crystalball/estimating-the-gop-edge-from-redistricting-a-state-by-state-accounting-with-caveats/)). Note this article predates the Missouri hold.
- What's left is covered by #2 (Hispanic reversion / dummymander) and #6 (incumbency in low-overlap seats).

---

## Suggested implementation order
1. **#1 + #5 together.** Shrink poll weight for large poll-vs-fundamentals gaps, add the LV +0.5 to the GB, and penalize partisan polls. These pull in opposite directions, so run them together.
2. **#3** expert blend for the House (data already there).
3. **#6** incumbency re-size and **#7** fat tails plus a regional layer (config changes).
4. **#4** candidate columns (experience/scandal), used inside fundamentals only.
5. **#2** demographic layer (needs ACS data on the new districts).
6. **#8** RCV and MT three-way simulation.
7. Then the two items the user already asked for: the per-race "softness" adjustment and the soft-lead (hard-ID D+5) scenario.

## Evidence-quality flags
- Every coefficient proposed above (poll-weight cut, Hispanic sd, candidate points, regional sd) is **our assumption**. None are published values, so they should be labeled that way on the site.
- The herding analysis comes from one source (PB Polls) and explicitly isn't proof. The 2024 benchmark shows compression can be real.
- Some numbers came from search summaries I didn't open:
  - the 41–53% Senate tracker range;
  - the gas price;
  - Jacobson's 1.2 pts (abstract-level).
- 2026-specific Hispanic swing sizes aren't published in a citable form beyond Split Ticket's "R+1 generic Texas" estimate.
