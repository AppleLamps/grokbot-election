# Factor attribution

40,000 sims per run (same seed). Deltas are in percentage points (probabilities) or seats.
**add-one** = v1 baseline + only this factor. **drop-one** = full v2 minus this factor (shown as the factor's contribution, i.e. v2 − run without it).

## (i) Polls unbiased (2018/2022 midterm record)

v1 (all off): P(D Senate) 67.9%, Senate D mean 51.73, P(D House) 93.1%, House D mean 235.1  
v2 (all on): P(D Senate) 68.7%, Senate D mean 51.62, P(D House) 92.6%, House D mean 236.3

| Factor | add-one ΔP(D Sen) | add-one ΔSen seats | add-one ΔP(D House) | add-one ΔHouse seats | drop-one ΔP(D Sen) | drop-one ΔSen seats | drop-one ΔP(D House) | drop-one ΔHouse seats |
|---|---|---|---|---|---|---|---|---|
| herding | -4.6 | -0.41 | -0.0 | -0.0 | -1.0 | -0.16 | +0.0 | -0.0 |
| demographic_regional | -1.0 | -0.05 | -1.5 | +0.4 | -0.9 | -0.03 | -1.5 | +0.4 |
| expert_ratings | +0.0 | +0.00 | -1.7 | -1.6 | +0.0 | +0.00 | -1.7 | -2.9 |
| candidate_quality | +0.5 | +0.03 | +0.0 | +0.0 | +1.7 | +0.10 | +0.0 | +0.0 |
| poll_cleanup | +0.3 | +0.00 | +1.5 | +1.7 | +1.4 | +0.09 | +1.2 | +1.2 |
| incumbency_reweight | +0.5 | +0.04 | +0.7 | +2.2 | +1.5 | +0.11 | +0.5 | +1.5 |
| fat_tails | +1.9 | +0.03 | +0.9 | -0.2 | +1.5 | +0.03 | +1.0 | -0.2 |
| election_mechanics | -0.2 | -0.01 | -0.1 | -0.0 | -0.1 | -0.02 | -0.1 | +0.0 |

## (ii) Presidential-style miss: polls overstate D by 3

v1 (all off): P(D Senate) 34.5%, Senate D mean 49.29, P(D House) 70.3%, House D mean 223.8  
v2 (all on): P(D Senate) 35.2%, Senate D mean 49.52, P(D House) 71.4%, House D mean 224.3

| Factor | add-one ΔP(D Sen) | add-one ΔSen seats | add-one ΔP(D House) | add-one ΔHouse seats | drop-one ΔP(D Sen) | drop-one ΔSen seats | drop-one ΔP(D House) | drop-one ΔHouse seats |
|---|---|---|---|---|---|---|---|---|
| herding | -3.7 | -0.09 | -0.0 | +0.0 | +0.0 | +0.10 | +0.2 | +0.0 |
| demographic_regional | +0.4 | +0.01 | -1.1 | +0.3 | +0.8 | +0.01 | -1.4 | +0.2 |
| expert_ratings | +0.0 | +0.00 | -3.8 | -1.3 | +0.0 | +0.00 | -5.2 | -2.3 |
| candidate_quality | +0.5 | +0.04 | +0.0 | +0.0 | +1.7 | +0.09 | +0.0 | +0.0 |
| poll_cleanup | +0.3 | +0.04 | +4.1 | +1.4 | +1.6 | +0.10 | +3.3 | +1.1 |
| incumbency_reweight | +0.5 | +0.03 | +1.7 | +1.1 | +1.4 | +0.08 | +1.4 | +0.7 |
| fat_tails | -1.5 | -0.01 | +1.7 | -0.1 | -0.8 | +0.01 | +2.2 | +0.0 |
| election_mechanics | -0.1 | +0.01 | -0.0 | +0.0 | +0.0 | +0.00 | +0.1 | +0.0 |

## (iii) 2025-style miss (tail case): polls overstate R by 6

v1 (all off): P(D Senate) 98.7%, Senate D mean 55.58, P(D House) 100.0%, House D mean 263.6  
v2 (all on): P(D Senate) 98.1%, Senate D mean 55.13, P(D House) 99.7%, House D mean 266.1

| Factor | add-one ΔP(D Sen) | add-one ΔSen seats | add-one ΔP(D House) | add-one ΔHouse seats | drop-one ΔP(D Sen) | drop-one ΔSen seats | drop-one ΔP(D House) | drop-one ΔHouse seats |
|---|---|---|---|---|---|---|---|---|
| herding | -0.8 | -0.57 | +0.0 | -0.0 | -0.2 | -0.33 | -0.0 | +0.0 |
| demographic_regional | -0.4 | -0.07 | -0.1 | +0.5 | -0.2 | -0.04 | -0.1 | +0.7 |
| expert_ratings | +0.0 | +0.00 | -0.0 | -2.4 | +0.0 | +0.00 | -0.1 | -4.3 |
| candidate_quality | +0.0 | +0.01 | +0.0 | +0.0 | +0.2 | +0.05 | +0.0 | +0.0 |
| poll_cleanup | +0.0 | -0.11 | +0.0 | +2.2 | +0.2 | +0.00 | +0.0 | +1.6 |
| incumbency_reweight | +0.0 | +0.04 | +0.0 | +4.2 | +0.2 | +0.11 | -0.0 | +3.1 |
| fat_tails | -0.2 | +0.02 | -0.2 | -0.3 | -0.0 | +0.04 | -0.3 | -0.3 |
| election_mechanics | -0.0 | -0.03 | +0.0 | -0.0 | -0.0 | -0.04 | -0.0 | -0.0 |

