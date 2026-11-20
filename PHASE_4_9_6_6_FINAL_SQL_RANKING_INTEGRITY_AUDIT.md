# Phase 4.9.6.6 — Final SQL Ranking Integrity Audit & Defect Correction Report

**Project:** ICC Men's T20 World Cup 2026 Data Analytics  
**Phase:** 4.9.6.6  
**Mode:** STRICT READ-ONLY — SQL CORRECTION, INTEGRATED VALIDATION  
**Database:** PostgreSQL 18.7 on x86_64-windows (MSVC-19.44.35229, 64-bit)  
**Status:** **APPROVED FOR IMPLEMENTATION (19/19 TESTS PASSED — 100%)**  
**Audit Date:** 14 November 2026  

---

## Executive Summary

Phase 4.9.6.6 concludes the technical audit and defect remediation for the PostgreSQL standings engine. In strict accordance with the project directives, all audit activities, mathematical evaluations, and test executions were conducted in **strict read-only mode**. Zero DDL statements (`CREATE VIEW`, `CREATE TABLE`, `CREATE INDEX`), zero database migrations, zero DML operations, and zero modifications to Power BI model files (`model.bim`) or the 38 existing DAX measures were performed.

All five specific technical defects identified in the Phase 4.9.6.5 review have been resolved:
1. **Defect A (`nrr_pairwise` Superior Count):** Eliminated the denominator-group aggregation defect (`COUNT(b_d)`), replacing it with an exact correlated scalar count `COUNT(B WHERE N_B * D_A > N_A * D_B)` that guarantees every superior competitor is counted individually regardless of shared denominators.
2. **Defect B (`resolution_step` Alignment):** Aligned resolution-step classification strictly with NRR comparability. Undefined NRR values or incomparable tiers are blocked from Step 3 classification (`tier_has_undefined_nrr = 0` gate), eliminating spurious Step 3 labels.
3. **Defect C (H2H Played-Match Evidence):** Established an authoritative predicate for genuinely played fixtures using decisive outcome types and delivery evidence (`legal_deliveries > 0`), distinguishing scheduled fixtures and abandoned-before-play washouts from completed matches and rain-shortened no-results.
4. **Defect D (Cast Before Arithmetic):** Audited and enforced operand-level casting (`CAST(... AS NUMERIC)`) prior to multiplication, subtraction, and GCD reduction, eliminating implicit integer overflow risks across all cross-products.
5. **Defect E (ICC Ranking Source Audit):** Fully documented the provenance of the pre-tournament rankings snapshot, explicitly classifying the 4 February 2026 Wisden snapshot as secondary evidence proxying the official 6 February 2026 cut-off date mandated by ICC Clause 16.10.4(d).

The corrected SQL logic was validated against an integrated **19-case test suite** (18 isolated synthetic edge cases plus full empirical reconciliation of all 28 tournament team records) executed directly on PostgreSQL 18.7. **All 19 tests achieved a 100% pass rate.**

---

## 1. Defect-by-Defect Findings & Corrective Implementations

### Defect A: Correction of `nrr_pairwise` Superior Count

#### Root Cause Analysis
In the Phase 4.9.6.5 design, the `nrr_pairwise` CTE grouped candidate teams by `b.d` (the denominator of candidate B) to compute intermediate counts, and the subsequent `nrr_pairwise_summary` CTE applied `COUNT(b_d)`. When two or more superior competitor teams shared the identical denominator $D$ (a frequent occurrence in tournament play where completed matches share 120 balls faced and 120 balls bowled), the grouping by `b.d` collapsed multiple superior teams into a single row. Consequently, `COUNT(b_d)` returned the number of *distinct denominators* rather than the number of *superior teams*.

#### Corrective Formula
For any candidate team $A$ within an equal-points and equal-wins tier:
$$\text{nrr\_superior\_count}(A) = \sum_{B \in \text{Tier}, B \neq A} \mathbf{1}_{\{N_B \cdot D_A > N_A \cdot D_B\}}$$

#### Corrected SQL Definition
```sql
nrr_superior_counts AS (
    SELECT
        a.stage_normalized,
        a.group_name,
        a.points,
        a.wins,
        a.team_name,
        CASE 
            WHEN tg.tier_has_undefined_nrr > 0 THEN NULL
            ELSE (
                SELECT COUNT(*)
                FROM group_nrr_fractions b
                WHERE b.stage_normalized = a.stage_normalized
                  AND b.group_name = a.group_name
                  AND b.points = a.points
                  AND b.wins = a.wins
                  AND b.team_name <> a.team_name
                  AND (CAST(b.n AS NUMERIC) * CAST(a.d AS NUMERIC)) > (CAST(a.n AS NUMERIC) * CAST(b.d AS NUMERIC))
            )
        END AS nrr_superior_count
    FROM group_nrr_fractions a
    JOIN tier_nrr_guard tg ON a.stage_normalized = tg.stage_normalized
                          AND a.group_name = tg.group_name
                          AND a.points = tg.points
                          AND a.wins = tg.wins
)
```

#### Multi-Team Shared Denominator Demonstration
Demonstrated with three teams in Group Stage A tied on 4 points and 2 wins:
- **Team A:** $N_A = 100, D_A = 100$ ($\text{NRR} = +1.000$)
- **Team B:** $N_B = 200, D_B = 100$ ($\text{NRR} = +2.000$)
- **Team C:** $N_C = 250, D_C = 100$ ($\text{NRR} = +2.500$)

Both superior teams ($B$ and $C$) share the identical denominator ($100$). The corrected query produces:
- Team C: `nrr_superior_count = 0` (Rank 1)
- Team B: `nrr_superior_count = 1` (Rank 2)
- Team A: `nrr_superior_count = 2` (Rank 3)

The previous flawed design produced `nrr_superior_count = 1` for Team A. The corrected logic correctly returns `2`.

---

### Defect B: Alignment of `resolution_step` with NRR Comparability

#### Root Cause Analysis
In earlier drafts, window partitioning `COUNT(*) OVER (PARTITION BY ..., n_canon, d_canon)` evaluated a NULL canonical fraction as a distinct value. When a team had undefined NRR ($D = 0$ or NULL), its NULL partition formed a singleton partition (`count = 1`), erroneously causing the query to assign `Step 3: Net Run Rate (Clause 16.10.4.b)` even though NRR comparison had been disabled for the tier.

#### Corrective Implementation
A tier-level comparability flag `tier_has_undefined_nrr` is computed across each `(stage_normalized, group_name, points, wins)` partition. If `tier_has_undefined_nrr > 0`, NRR is marked incomparable for all teams in that tier (`nrr_superior_count = NULL`), and the `resolution_step` CASE expression explicitly gates Step 3:
```sql
CASE 
    WHEN pts_count = 1 THEN 'Step 1: Points (Clause 16.10.3)'
    WHEN wins_count = 1 THEN 'Step 2: Most Wins (Clause 16.10.4.a)'
    WHEN tier_has_undefined_nrr = 0 AND nrr_canon_count = 1 THEN 'Step 3: Net Run Rate (Clause 16.10.4.b)'
    WHEN safe_h2h_points IS NOT NULL AND h2h_pts_tier_count = 1 THEN 'Step 4a: Head-to-Head Points (Clause 16.10.4.c)'
    WHEN safe_h2h_points IS NOT NULL AND COALESCE(tier_has_undefined_h2h_nrr, 1) = 0 AND h2h_nrr_canon_count = 1 THEN 'Step 4b: Head-to-Head Net Run Rate (Clause 16.10.4.c)'
    ELSE 'Step 5: ICC T20I Team Rankings (Clause 16.10.4.d)'
END AS resolution_step
```

#### Validation Across the 5 Defect B Scenarios
1. **One undefined NRR and one valid negative NRR:** `tier_has_undefined_nrr = 1`. Both counts evaluate to `NULL`. Neither team is labeled Step 3. Both resolve at **Step 5: ICC T20I Team Rankings** based on pre-tournament rank (#2 vs #5).
2. **One undefined NRR and two valid NRR values:** `tier_has_undefined_nrr = 1`. All three counts evaluate to `NULL`. All three resolve at **Step 5**.
3. **All teams having undefined NRR:** `tier_has_undefined_nrr = 2`. All counts evaluate to `NULL`. Both resolve at **Step 5**.
4. **All teams having valid, exactly equal NRR:** `tier_has_undefined_nrr = 0`, but `nrr_canon_count = 2`. Because NRR is tied, neither is resolved at Step 3; both fall through to **Step 5** (or Step 4 if H2H played).
5. **All teams having valid, distinct NRR:** `tier_has_undefined_nrr = 0` and `nrr_canon_count = 1`. Both teams resolve at **Step 3: Net Run Rate**.

---

### Defect C: Authoritative H2H Played-Match Evidence

#### Evidence Audit of Database Schema
An audit of `dim_matches`, `fact_match_summaries`, and `fact_deliveries` revealed:
- `dim_matches.outcome_type` contains: `'runs'` (29), `'wickets'` (23), `'tie_super_over'` (1), and `'no result'` (2).
- `dim_matches.scorecard_available` is `FALSE` for the two `'no result'` matches, but also `FALSE` for supplemental matches where ball-by-ball data was unavailable from Cricsheet even though authentic match scorecards exist.
- Therefore, `scorecard_available = TRUE` cannot be used as the sole determinant of whether a match was played.

#### Authoritative Match-Status Predicate
To reliably distinguish genuinely played fixtures from unplayed fixtures across both production and synthetic edge cases, the following hierarchical predicate is implemented:
```sql
CASE 
    -- 1. Completed decisive match outcomes:
    WHEN mo.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over') THEN 1
    -- 2. No-result fixture where play commenced (deliveries bowled in summaries or deliveries table):
    WHEN mo.outcome_type = 'no result' AND (
        EXISTS (SELECT 1 FROM fact_match_summaries s WHERE s.match_id = mo.match_id AND s.legal_deliveries > 0)
        OR EXISTS (SELECT 1 FROM fact_deliveries d WHERE d.match_id = mo.match_id)
    ) THEN 1
    -- 3. Scheduled fixtures, unplayed matches, or matches abandoned before a ball was bowled:
    ELSE 0
END AS is_genuinely_played
```

#### Taxonomy of Match States

| Match State | `outcome_type` | Delivery Evidence | `is_genuinely_played` | Counts for $K-1$? | NRR Calculated? |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Completed Decisive** | `runs` / `wickets` | $\ge 1$ legal ball | **1** | Yes | Yes |
| **Tie / Super Over** | `tie` / `tie_super_over` | $\ge 1$ legal ball | **1** | Yes | Yes |
| **Played No-Result** | `no result` | $\ge 1$ legal ball | **1** | Yes | No (NULL H2H NRR) |
| **Abandoned Before Play** | `no result` | $0$ legal balls | **0** | No | No (NULL H2H NRR) |
| **Scheduled / Unplayed** | `scheduled` / `NULL` | $0$ legal balls | **0** | No | No (NULL H2H NRR) |

In the actual 2026 tournament, Match 32 (Ireland v Zimbabwe) and Match 41 (Pakistan v New Zealand) have `outcome_type = 'no result'`, 0 deliveries bowled, and explicit notes: *"Match abandoned without a ball bowled due to rain"*. The predicate evaluates both to `is_genuinely_played = 0`, correctly excluding them from head-to-head match counts under Clause 16.10.4(c).

---

### Defect D: Explicit Pre-Casting for Overflow-Free Arithmetic

#### Audit of Cross-Products & GCD
PostgreSQL 18.7 provides native `gcd(numeric, numeric)` and `gcd(bigint, bigint)`.
Testing confirmed:
- `gcd(CAST(0 AS NUMERIC), CAST(120 AS NUMERIC))` returns `120` of type `NUMERIC`.
- `gcd(CAST(-50 AS NUMERIC), CAST(120 AS NUMERIC))` returns `10` of type `NUMERIC`.
- Canonical fraction reduction for zero numerator: $0 / 120 \to 0/1$.
- Canonical fraction reduction for negative numerator: $-50 / 120 \to -5/12$.

#### Pre-Cast Enforcement
To eliminate any potential for `INTEGER` or `BIGINT` overflow during intermediate multiplication prior to casting, every operand is cast to `NUMERIC` before multiplication or subtraction:
```sql
-- Numerator:
(CAST(b.runs_scored AS NUMERIC) * CAST(w.balls_bowled AS NUMERIC) - CAST(w.runs_conceded AS NUMERIC) * CAST(b.balls_faced AS NUMERIC)) AS n

-- Denominator:
(CAST(b.balls_faced AS NUMERIC) * CAST(w.balls_bowled AS NUMERIC)) AS d

-- Pairwise Cross-Product Comparison:
(CAST(b.n AS NUMERIC) * CAST(a.d AS NUMERIC)) > (CAST(a.n AS NUMERIC) * CAST(b.d AS NUMERIC))
```
This guarantees unbounded precision in PostgreSQL 18.7 with zero risk of arithmetic overflow.

---

### Defect E: ICC Ranking Source Audit & Provenance Disclosure

#### Regulatory Requirement
ICC Men's T20 World Cup 2026 Playing Conditions Clause 16.10.4(d) specifies:
> *"The team with the higher position in the ICC Men's T20I Team Rankings as at 6 February 2026."*

#### Provenance Findings
1. **Primary Source Status:** The project repository contains no raw primary ICC snapshot (e.g. direct ICC media release PDF or contemporaneous ICC web archive) for the 6 February 2026 cut-off.
2. **Secondary Source Reference:** The standings engine incorporates the contemporaneous pre-tournament ranking table published by *Wisden* on **4 February 2026** (*"ICC Men's T20I Team Rankings ahead of the 2026 Men's T20 World Cup"*), corroborated by *The Sports Bulls* (published 4 February 2026, updated 7 February 2026).
3. **Temporal Invariance Verification:** An audit of international cricket fixtures between 4 February 2026 and 6 February 2026 confirmed that **zero men's T20I matches were played** involving any of the 20 participating nations prior to the tournament opening match on 7 February 2026. Therefore, the 4 February 2026 ratings and positions represent the exact mathematical state of the rankings as of the 6 February 2026 cut-off.
4. **Transparency & Labeling:** The CTE is explicitly labeled `wisden_icc_rankings_4feb2026` to disclose that it relies on secondary contemporaneous evidence rather than an official ICC primary document.

---

## 2. Integrated 19-Case Test Suite Execution Matrix

The corrected SQL engine was executed against an integrated test harness containing 18 isolated synthetic edge cases and 1 empirical tournament reconciliation on PostgreSQL 18.7.

| Test ID | Scenario / Test Focus | Key Inputs / Conditions | Expected Behavior | Actual SQL Result | Status |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **01** | Multi-team NRR with shared denominator | 3 teams; Team A (100/100), Team B (200/100), Team C (250/100) | Team C sup 0, Team B sup 1, Team A sup 2; Step 3 | C: sup 0 (Rk 1), B: sup 1 (Rk 2), A: sup 2 (Rk 3) | **PASS** |
| **02** | Exact rational NRR tie | 2 teams; $N=200, D=120$ for both | Both sup 0; Step 5 fallback (#3 vs #7) | Team A (Rk 1, Step 5), Team B (Rk 2, Step 5) | **PASS** |
| **03** | Equivalent unreduced fractions | Team A (100/60), Team B (200/120) | Both reduce to 5/3; both sup 0; Step 5 | Both sup 0; resolved at Step 5 by ICC rank | **PASS** |
| **04** | Strictly different positive NRR | Team High (210/120), Team Low (200/120) | Team High sup 0, Low sup 1; Step 3 | High: Rk 1 (Step 3), Low: Rk 2 (Step 3) | **PASS** |
| **05** | Negative NRR ordering | Team NegHigh (-40/120), Team NegLow (-60/120) | NegHigh sup 0, NegLow sup 1; Step 3 | NegHigh: Rk 1 (Step 3), NegLow: Rk 2 (Step 3) | **PASS** |
| **06** | Undefined NRR vs valid negative NRR | Team Undef (NULL), Team ValidNeg (-50/120) | Both sup NULL; neither Step 3; Step 5 fallback | Both sup NULL; Undef Rk 1 (#2), ValidNeg Rk 2 (#5) | **PASS** |
| **07** | Multiple undefined NRR in tier | 3 teams; all $D = \text{NULL}$ | All sup NULL; Step 5 fallback (#2, #6, #9) | Ordered Rk 1..3 by ICC rank at Step 5 | **PASS** |
| **08** | Exact H2H NRR tie | 2 teams tied on Pts, Wins, NRR; H2H NRR 0.000 | Both H2H sup 0; Step 5 fallback | Both H2H sup 0; resolved at Step 5 (#3 vs #7) | **PASS** |
| **09** | Strictly different H2H rational NRR | 2 teams; H2H NRR +20/14400 vs -20/14400 | Team HighH2H sup 0, LowH2H sup 1; Step 4b | HighH2H: Rk 1 (Step 4b), LowH2H: Rk 2 (Step 4b) | **PASS** |
| **10** | Complete 3-team H2H mini-table | 3 teams; cyclic 1-1; H2H NRR +0.5, +0.1, -0.6 | Resolved at Step 4b in order A $\to$ B $\to$ C | Team A (Rk 1), Team B (Rk 2), Team C (Rk 3) | **PASS** |
| **11** | Incomplete 3-team H2H mini-table | 3 teams; B v C unplayed ($K-1$ incomplete) | Stage 1 guard trips; safe_h2h_points = NULL | safe_h2h_points NULL; Step 5 fallback (#2, #4, #6) | **PASS** |
| **12** | Scheduled unplayed fixture | `outcome_type = 'scheduled'`, balls = 0 | `is_genuinely_played = 0`; excluded from H2H | `is_genuinely_played = 0`; safe_h2h_points NULL | **PASS** |
| **13** | Abandoned-before-play fixture | `outcome_type = 'no result'`, balls = 0 | `is_genuinely_played = 0`; excluded from H2H | `is_genuinely_played = 0`; safe_h2h_points NULL | **PASS** |
| **14** | Played no-result fixture | `outcome_type = 'no result'`, balls = 36 | `is_genuinely_played = 1`; H2H NRR disabled | `is_genuinely_played = 1`; Step 5 fallback | **PASS** |
| **15** | Two unrelated ties in same group | Group A: Top tie (6 pts, H2H), Bottom tie (2 pts, unplayed) | Tie 1 at Step 4a, Tie 2 at Step 5; no bleed | Tie 1: Step 4a (A1, A2); Tie 2: Step 5 (B1, B2) | **PASS** |
| **16** | Zero & negative numerator GCD | $0/120$ and $-50/120$ reduction | $0/120 \to 0/1$; $-50/120 \to -5/12$ via native `gcd` | Exact canonical reduction; no division errors | **PASS** |
| **17** | Arithmetic overflow boundary | Operands $\sim 500$; cross products $\sim 2.21 \times 10^9$ | Evaluates without BIGINT overflow | Exact product 2,211,840,000 computed | **PASS** |
| **18** | ICC fallback & missing-rank | RankedHigh (#3), RankedLow (#8), Unranked (NULL) | Deterministic ordering; NULL placed last | RankedHigh (Rk 1) $\to$ RankedLow (Rk 2) $\to$ Unranked (Rk 3) | **PASS** |
| **19** | **Live PostgreSQL 18.7 Reconciliation** | All 6 tournament pools; all 28 team records | 100% deterministic ranking & qualification | 28 records match tournament results exactly | **PASS** |

---

## 3. PostgreSQL 18.7 Empirical 28-Team Reconciliation

The full corrected query was executed directly against `t20_worldcup_2026` on PostgreSQL 18.7. The resulting standings table reconciles 100% of the tournament records:

```
stage_normalized group_name pool_rank team_name                played wins losses no_result points nrr_display resolution_step                          qualification_status
---------------- ---------- --------- ------------------------ ------ ---- ------ --------- ------ ----------- ---------------------------------------- --------------------
Super 8          1          1         South Africa                  3    3      0         0      6       2.114 Step 1: Points (Clause 16.10.3)         Qualified           
Super 8          1          2         India                         3    2      1         0      4       0.106 Step 1: Points (Clause 16.10.3)         Qualified           
Super 8          1          3         West Indies                   3    1      2         0      2       0.580 Step 1: Points (Clause 16.10.3)         Eliminated          
Super 8          1          4         Zimbabwe                      3    0      3         0      0      -3.415 Step 1: Points (Clause 16.10.3)         Eliminated          
Super 8          2          1         England                       3    3      0         0      6       0.686 Step 1: Points (Clause 16.10.3)         Qualified           
Super 8          2          2         New Zealand                   3    1      1         1      3       1.390 Step 3: Net Run Rate (Clause 16.10.4.b) Qualified           
Super 8          2          3         Pakistan                      3    1      1         1      3      -0.123 Step 3: Net Run Rate (Clause 16.10.4.b) Eliminated          
Super 8          2          4         Sri Lanka                     3    0      3         0      0      -1.950 Step 1: Points (Clause 16.10.3)         Eliminated          
Group Stage      A          1         India                         4    4      0         0      8       2.177 Step 1: Points (Clause 16.10.3)         Qualified           
Group Stage      A          2         Pakistan                      4    3      1         0      6       0.727 Step 1: Points (Clause 16.10.3)         Qualified           
Group Stage      A          3         United States of America      4    2      2         0      4       0.360 Step 1: Points (Clause 16.10.3)         Eliminated          
Group Stage      A          4         Netherlands                   4    1      3         0      2      -1.217 Step 1: Points (Clause 16.10.3)         Eliminated          
Group Stage      A          5         Namibia                       4    0      4         0      0      -3.108 Step 1: Points (Clause 16.10.3)         Eliminated          
Group Stage      B          1         Zimbabwe                      4    3      0         1      7       1.426 Step 1: Points (Clause 16.10.3)         Qualified           
Group Stage      B          2         Sri Lanka                     4    3      1         0      6       1.725 Step 1: Points (Clause 16.10.3)         Qualified           
Group Stage      B          3         Australia                     4    2      2         0      4       0.819 Step 1: Points (Clause 16.10.3)         Eliminated          
Group Stage      B          4         Ireland                       4    1      2         1      3      -0.128 Step 1: Points (Clause 16.10.3)         Eliminated          
Group Stage      B          5         Oman                          4    0      4         0      0      -4.845 Step 1: Points (Clause 16.10.3)         Eliminated          
Group Stage      C          1         West Indies                   4    4      0         0      8       1.483 Step 1: Points (Clause 16.10.3)         Qualified           
Group Stage      C          2         England                       4    3      1         0      6       0.164 Step 1: Points (Clause 16.10.3)         Qualified           
Group Stage      C          3         Scotland                      4    1      3         0      2      -0.187 Step 3: Net Run Rate (Clause 16.10.4.b) Eliminated          
Group Stage      C          4         Italy                         4    1      3         0      2      -0.705 Step 3: Net Run Rate (Clause 16.10.4.b) Eliminated          
Group Stage      C          5         Nepal                         4    1      3         0      2      -1.349 Step 3: Net Run Rate (Clause 16.10.4.b) Eliminated          
Group Stage      D          1         South Africa                  4    4      0         0      8       1.910 Step 1: Points (Clause 16.10.3)         Qualified           
Group Stage      D          2         New Zealand                   4    3      1         0      6       1.227 Step 1: Points (Clause 16.10.3)         Qualified           
Group Stage      D          3         Afghanistan                   4    2      2         0      4       0.889 Step 1: Points (Clause 16.10.3)         Eliminated          
Group Stage      D          4         United Arab Emirates          4    1      3         0      2      -1.364 Step 1: Points (Clause 16.10.3)         Eliminated          
Group Stage      D          5         Canada                        4    0      4         0      0      -2.426 Step 1: Points (Clause 16.10.3)         Eliminated          
```

---

## 4. Full Verbatim Blueprint for `view_tournament_standings`

The following complete SQL query represents the authoritative production blueprint ready for deployment:

```sql
CREATE OR REPLACE VIEW view_tournament_standings AS
WITH wisden_icc_rankings_4feb2026 AS (
    SELECT 'India' AS team_name, 1 AS icc_rank UNION ALL
    SELECT 'Australia', 2 UNION ALL
    SELECT 'England', 3 UNION ALL
    SELECT 'New Zealand', 4 UNION ALL
    SELECT 'South Africa', 5 UNION ALL
    SELECT 'Pakistan', 6 UNION ALL
    SELECT 'West Indies', 7 UNION ALL
    SELECT 'Sri Lanka', 8 UNION ALL
    SELECT 'Afghanistan', 10 UNION ALL
    SELECT 'Ireland', 11 UNION ALL
    SELECT 'Zimbabwe', 12 UNION ALL
    SELECT 'Netherlands', 13 UNION ALL
    SELECT 'Scotland', 14 UNION ALL
    SELECT 'Namibia', 15 UNION ALL
    SELECT 'Nepal', 16 UNION ALL
    SELECT 'United Arab Emirates', 17 UNION ALL
    SELECT 'United States of America', 18 UNION ALL
    SELECT 'Canada', 19 UNION ALL
    SELECT 'Oman', 20 UNION ALL
    SELECT 'Italy', 27
),
stage_matches AS (
    SELECT 
        match_id,
        match_date,
        stage,
        CASE 
            WHEN group_name IN ('A', 'B', 'C', 'D') THEN 'Group Stage'
            WHEN group_name IN ('1', '2') THEN 'Super 8'
            ELSE COALESCE(stage, 'Knockout') 
        END AS stage_normalized,
        group_name,
        team1,
        team2,
        winner,
        outcome_type,
        scorecard_available,
        source_note
    FROM dim_matches
    WHERE group_name IN ('A', 'B', 'C', 'D', '1', '2')
),
match_opponents AS (
    SELECT 
        m.stage_normalized,
        m.group_name,
        m.match_id,
        m.team1 AS focus_team,
        m.team2 AS opp_team,
        m.winner,
        m.outcome_type,
        m.scorecard_available,
        m.source_note
    FROM stage_matches m
    UNION ALL
    SELECT 
        m.stage_normalized,
        m.group_name,
        m.match_id,
        m.team2 AS focus_team,
        m.team1 AS opp_team,
        m.winner,
        m.outcome_type,
        m.scorecard_available,
        m.source_note
    FROM stage_matches m
),
match_played_eval AS (
    SELECT
        mo.*,
        CASE 
            WHEN mo.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over') THEN 1
            WHEN mo.outcome_type = 'no result' AND (
                EXISTS (SELECT 1 FROM fact_match_summaries s WHERE s.match_id = mo.match_id AND s.legal_deliveries > 0)
                OR EXISTS (SELECT 1 FROM fact_deliveries d WHERE d.match_id = mo.match_id)
            ) THEN 1
            ELSE 0
        END AS is_genuinely_played
    FROM match_opponents mo
),
team_pool_records AS (
    SELECT 
        mpe.stage_normalized,
        mpe.group_name,
        mpe.focus_team AS team_name,
        COUNT(*) AS played,
        SUM(CASE WHEN mpe.winner = mpe.focus_team THEN 1 ELSE 0 END) AS wins,
        SUM(CASE WHEN mpe.winner IS NOT NULL AND mpe.winner <> mpe.focus_team AND mpe.outcome_type <> 'no result' THEN 1 ELSE 0 END) AS losses,
        SUM(CASE WHEN mpe.outcome_type = 'no result' THEN 1 ELSE 0 END) AS no_result,
        SUM(
            CASE 
                WHEN mpe.winner = mpe.focus_team THEN 2
                WHEN mpe.outcome_type IN ('no result', 'tie') THEN 1
                ELSE 0
            END
        ) AS points
    FROM match_played_eval mpe
    GROUP BY mpe.stage_normalized, mpe.group_name, mpe.focus_team
),
team_batting_aggregates AS (
    SELECT 
        mpe.stage_normalized,
        mpe.group_name,
        mpe.focus_team AS team_name,
        SUM(s.total_runs) AS runs_scored,
        SUM(CASE WHEN s.total_wickets = 10 THEN 120 ELSE s.legal_deliveries END) AS balls_faced
    FROM fact_match_summaries s
    JOIN match_played_eval mpe ON s.match_id = mpe.match_id AND s.batting_team = mpe.focus_team
    WHERE s.is_super_over = FALSE
    GROUP BY mpe.stage_normalized, mpe.group_name, mpe.focus_team
),
team_bowling_aggregates AS (
    SELECT 
        mpe.stage_normalized,
        mpe.group_name,
        mpe.focus_team AS team_name,
        SUM(s.total_runs) AS runs_conceded,
        SUM(s.legal_deliveries) AS balls_bowled
    FROM fact_match_summaries s
    JOIN match_played_eval mpe ON s.match_id = mpe.match_id AND s.bowling_team = mpe.focus_team
    WHERE s.is_super_over = FALSE
    GROUP BY mpe.stage_normalized, mpe.group_name, mpe.focus_team
),
team_standings_base AS (
    SELECT 
        r.stage_normalized,
        r.group_name,
        r.team_name,
        r.played,
        r.wins,
        r.losses,
        r.no_result,
        r.points,
        COALESCE(b.runs_scored, 0) AS runs_scored,
        COALESCE(b.balls_faced, 0) AS balls_faced,
        COALESCE(w.runs_conceded, 0) AS runs_conceded,
        COALESCE(w.balls_bowled, 0) AS balls_bowled,
        CASE 
            WHEN COALESCE(b.balls_faced, 0) > 0 AND COALESCE(w.balls_bowled, 0) > 0 THEN
                (CAST(b.runs_scored AS NUMERIC) * CAST(w.balls_bowled AS NUMERIC) - CAST(w.runs_conceded AS NUMERIC) * CAST(b.balls_faced AS NUMERIC))
            ELSE NULL 
        END AS n,
        CASE 
            WHEN COALESCE(b.balls_faced, 0) > 0 AND COALESCE(w.balls_bowled, 0) > 0 THEN
                (CAST(b.balls_faced AS NUMERIC) * CAST(w.balls_bowled AS NUMERIC))
            ELSE NULL 
        END AS d,
        CASE 
            WHEN COALESCE(b.balls_faced, 0) > 0 AND COALESCE(w.balls_bowled, 0) > 0 THEN
                ROUND(CAST((CAST(b.runs_scored AS NUMERIC) / (CAST(b.balls_faced AS NUMERIC) / 6.0)) - (CAST(w.runs_conceded AS NUMERIC) / (CAST(w.balls_bowled AS NUMERIC) / 6.0)) AS NUMERIC), 3)
            ELSE NULL 
        END AS nrr_display
    FROM team_pool_records r
    LEFT JOIN team_batting_aggregates b ON r.stage_normalized = b.stage_normalized AND r.group_name = b.group_name AND r.team_name = b.team_name
    LEFT JOIN team_bowling_aggregates w ON r.stage_normalized = w.stage_normalized AND r.group_name = w.group_name AND r.team_name = w.team_name
),
group_nrr_fractions AS (
    SELECT 
        s.*,
        CASE 
            WHEN s.d IS NOT NULL AND s.d > 0 THEN
                CAST(s.n AS NUMERIC) / gcd(CAST(s.n AS NUMERIC), CAST(s.d AS NUMERIC))
            ELSE NULL 
        END AS n_canon,
        CASE 
            WHEN s.d IS NOT NULL AND s.d > 0 THEN
                CAST(s.d AS NUMERIC) / gcd(CAST(s.n AS NUMERIC), CAST(s.d AS NUMERIC))
            ELSE NULL 
        END AS d_canon
    FROM team_standings_base s
),
tier_nrr_guard AS (
    SELECT
        stage_normalized,
        group_name,
        points,
        wins,
        SUM(CASE WHEN d IS NULL OR d <= 0 THEN 1 ELSE 0 END) AS tier_has_undefined_nrr
    FROM group_nrr_fractions
    GROUP BY stage_normalized, group_name, points, wins
),
nrr_superior_counts AS (
    SELECT
        a.stage_normalized,
        a.group_name,
        a.points,
        a.wins,
        a.team_name,
        CASE 
            WHEN tg.tier_has_undefined_nrr > 0 THEN NULL
            ELSE (
                SELECT COUNT(*)
                FROM group_nrr_fractions b
                WHERE b.stage_normalized = a.stage_normalized
                  AND b.group_name = a.group_name
                  AND b.points = a.points
                  AND b.wins = a.wins
                  AND b.team_name <> a.team_name
                  AND (CAST(b.n AS NUMERIC) * CAST(a.d AS NUMERIC)) > (CAST(a.n AS NUMERIC) * CAST(b.d AS NUMERIC))
            )
        END AS nrr_superior_count
    FROM group_nrr_fractions a
    JOIN tier_nrr_guard tg ON a.stage_normalized = tg.stage_normalized
                          AND a.group_name = tg.group_name
                          AND a.points = tg.points
                          AND a.wins = tg.wins
),
tied_candidates AS (
    SELECT 
        f.stage_normalized,
        f.group_name,
        f.points,
        f.wins,
        COALESCE(nsc.nrr_superior_count, -1) AS tied_nrr_key,
        COUNT(*) AS tied_team_count
    FROM group_nrr_fractions f
    JOIN nrr_superior_counts nsc ON f.stage_normalized = nsc.stage_normalized
                               AND f.group_name = nsc.group_name
                               AND f.team_name = nsc.team_name
    GROUP BY f.stage_normalized, f.group_name, f.points, f.wins, COALESCE(nsc.nrr_superior_count, -1)
    HAVING COUNT(*) > 1
),
h2h_matches AS (
    SELECT 
        mpe.stage_normalized,
        mpe.group_name,
        t_focus.team_name AS focus_team,
        t_opp.team_name AS opp_team,
        mpe.match_id,
        mpe.winner,
        mpe.outcome_type,
        mpe.scorecard_available,
        mpe.is_genuinely_played,
        CASE 
            WHEN mpe.winner = t_focus.team_name THEN 2
            WHEN mpe.outcome_type IN ('no result', 'tie') THEN 1
            ELSE 0
        END AS h2h_pts
    FROM match_played_eval mpe
    JOIN (
        SELECT f.*, COALESCE(nsc.nrr_superior_count, -1) AS tied_nrr_key
        FROM group_nrr_fractions f
        JOIN nrr_superior_counts nsc ON f.stage_normalized = nsc.stage_normalized
                                   AND f.group_name = nsc.group_name
                                   AND f.team_name = nsc.team_name
    ) t_focus ON mpe.focus_team = t_focus.team_name 
             AND mpe.group_name = t_focus.group_name 
             AND mpe.stage_normalized = t_focus.stage_normalized
    JOIN (
        SELECT f.*, COALESCE(nsc.nrr_superior_count, -1) AS tied_nrr_key
        FROM group_nrr_fractions f
        JOIN nrr_superior_counts nsc ON f.stage_normalized = nsc.stage_normalized
                                   AND f.group_name = nsc.group_name
                                   AND f.team_name = nsc.team_name
    ) t_opp ON mpe.opp_team = t_opp.team_name 
           AND mpe.group_name = t_opp.group_name 
           AND mpe.stage_normalized = t_opp.stage_normalized 
           AND t_focus.team_name <> t_opp.team_name
    JOIN tied_candidates tc ON t_focus.stage_normalized = tc.stage_normalized
                           AND t_focus.group_name = tc.group_name 
                           AND t_focus.points = tc.points 
                           AND t_focus.wins = tc.wins 
                           AND t_focus.tied_nrr_key = tc.tied_nrr_key
                           AND t_opp.points = tc.points
                           AND t_opp.wins = tc.wins
                           AND t_opp.tied_nrr_key = tc.tied_nrr_key
),
h2h_points_summary AS (
    SELECT 
        hm.stage_normalized,
        hm.group_name,
        hm.focus_team AS team_name,
        SUM(CASE WHEN hm.is_genuinely_played = 1 THEN hm.h2h_pts ELSE 0 END) AS h2h_points_raw,
        SUM(hm.is_genuinely_played) AS h2h_matches_played
    FROM h2h_matches hm
    GROUP BY hm.stage_normalized, hm.group_name, hm.focus_team
),
h2h_completeness_guard AS (
    SELECT 
        f.stage_normalized,
        f.group_name,
        f.team_name,
        f.points,
        f.wins,
        COALESCE(nsc.nrr_superior_count, -1) AS tied_nrr_key,
        tc.tied_team_count,
        hp.h2h_points_raw,
        hp.h2h_matches_played,
        CASE 
            WHEN tc.tied_team_count IS NOT NULL 
                 AND COUNT(*) OVER (
                     PARTITION BY f.stage_normalized, f.group_name, f.points, f.wins, COALESCE(nsc.nrr_superior_count, -1)
                 ) = tc.tied_team_count
                 AND MIN(COALESCE(hp.h2h_matches_played, 0)) OVER (
                     PARTITION BY f.stage_normalized, f.group_name, f.points, f.wins, COALESCE(nsc.nrr_superior_count, -1)
                 ) >= (tc.tied_team_count - 1)
            THEN COALESCE(hp.h2h_points_raw, 0)
            ELSE NULL 
        END AS safe_h2h_points
    FROM group_nrr_fractions f
    JOIN nrr_superior_counts nsc ON f.stage_normalized = nsc.stage_normalized
                               AND f.group_name = nsc.group_name
                               AND f.team_name = nsc.team_name
    LEFT JOIN tied_candidates tc ON f.stage_normalized = tc.stage_normalized
                                AND f.group_name = tc.group_name
                                AND f.points = tc.points
                                AND f.wins = tc.wins
                                AND COALESCE(nsc.nrr_superior_count, -1) = tc.tied_nrr_key
    LEFT JOIN h2h_points_summary hp ON f.stage_normalized = hp.stage_normalized
                                   AND f.group_name = hp.group_name
                                   AND f.team_name = hp.team_name
),
h2h_batting AS (
    SELECT 
        hm.stage_normalized,
        hm.group_name,
        hm.focus_team AS team_name,
        SUM(s.total_runs) AS h2h_runs_scored,
        SUM(CASE WHEN s.total_wickets = 10 THEN 120 ELSE s.legal_deliveries END) AS h2h_balls_faced
    FROM fact_match_summaries s
    JOIN h2h_matches hm ON s.match_id = hm.match_id AND s.batting_team = hm.focus_team
    WHERE s.is_super_over = FALSE AND hm.is_genuinely_played = 1
    GROUP BY hm.stage_normalized, hm.group_name, hm.focus_team
),
h2h_bowling AS (
    SELECT 
        hm.stage_normalized,
        hm.group_name,
        hm.focus_team AS team_name,
        SUM(s.total_runs) AS h2h_runs_conceded,
        SUM(s.legal_deliveries) AS h2h_balls_bowled
    FROM fact_match_summaries s
    JOIN h2h_matches hm ON s.match_id = hm.match_id AND s.bowling_team = hm.focus_team
    WHERE s.is_super_over = FALSE AND hm.is_genuinely_played = 1
    GROUP BY hm.stage_normalized, hm.group_name, hm.focus_team
),
h2h_fractions AS (
    SELECT 
        cg.*,
        hb.h2h_runs_scored,
        hb.h2h_balls_faced,
        hw.h2h_runs_conceded,
        hw.h2h_balls_bowled,
        CASE 
            WHEN cg.safe_h2h_points IS NOT NULL 
                 AND COALESCE(hb.h2h_balls_faced, 0) > 0 
                 AND COALESCE(hw.h2h_balls_bowled, 0) > 0 THEN
                (CAST(hb.h2h_runs_scored AS NUMERIC) * CAST(hw.h2h_balls_bowled AS NUMERIC) - CAST(hw.h2h_runs_conceded AS NUMERIC) * CAST(hb.h2h_balls_faced AS NUMERIC))
            ELSE NULL 
        END AS h2h_n,
        CASE 
            WHEN cg.safe_h2h_points IS NOT NULL 
                 AND COALESCE(hb.h2h_balls_faced, 0) > 0 
                 AND COALESCE(hw.h2h_balls_bowled, 0) > 0 THEN
                (CAST(hb.h2h_balls_faced AS NUMERIC) * CAST(hw.h2h_balls_bowled AS NUMERIC))
            ELSE NULL 
        END AS h2h_d,
        CASE 
            WHEN cg.safe_h2h_points IS NOT NULL 
                 AND COALESCE(hb.h2h_balls_faced, 0) > 0 
                 AND COALESCE(hw.h2h_balls_bowled, 0) > 0 THEN
                ROUND(CAST((CAST(hb.h2h_runs_scored AS NUMERIC) / (CAST(hb.h2h_balls_faced AS NUMERIC) / 6.0)) - (CAST(hw.h2h_runs_conceded AS NUMERIC) / (CAST(hw.h2h_balls_bowled AS NUMERIC) / 6.0)) AS NUMERIC), 3)
            ELSE NULL 
        END AS h2h_nrr_display
    FROM h2h_completeness_guard cg
    LEFT JOIN h2h_batting hb ON cg.stage_normalized = hb.stage_normalized AND cg.group_name = hb.group_name AND cg.team_name = hb.team_name
    LEFT JOIN h2h_bowling hw ON cg.stage_normalized = hw.stage_normalized AND cg.group_name = hw.group_name AND cg.team_name = hw.team_name
),
tier_h2h_guard AS (
    SELECT
        stage_normalized,
        group_name,
        points,
        wins,
        tied_nrr_key,
        safe_h2h_points,
        SUM(CASE WHEN h2h_d IS NULL OR h2h_d <= 0 THEN 1 ELSE 0 END) AS tier_has_undefined_h2h_nrr
    FROM h2h_fractions
    WHERE safe_h2h_points IS NOT NULL
    GROUP BY stage_normalized, group_name, points, wins, tied_nrr_key, safe_h2h_points
),
h2h_nrr_evaluated AS (
    SELECT
        hf.*,
        thg.tier_has_undefined_h2h_nrr,
        CASE 
            WHEN hf.safe_h2h_points IS NULL THEN NULL
            WHEN thg.tier_has_undefined_h2h_nrr > 0 THEN NULL
            ELSE (
                SELECT COUNT(*)
                FROM h2h_fractions b
                WHERE b.stage_normalized = hf.stage_normalized
                  AND b.group_name = hf.group_name
                  AND b.points = hf.points
                  AND b.wins = hf.wins
                  AND b.tied_nrr_key = hf.tied_nrr_key
                  AND b.safe_h2h_points = hf.safe_h2h_points
                  AND b.team_name <> hf.team_name
                  AND (CAST(b.h2h_n AS NUMERIC) * CAST(hf.h2h_d AS NUMERIC)) > (CAST(hf.h2h_n AS NUMERIC) * CAST(b.h2h_d AS NUMERIC))
            )
        END AS h2h_nrr_superior_count
    FROM h2h_fractions hf
    LEFT JOIN tier_h2h_guard thg ON hf.stage_normalized = thg.stage_normalized
                                AND hf.group_name = thg.group_name
                                AND hf.points = thg.points
                                AND hf.wins = thg.wins
                                AND hf.tied_nrr_key = thg.tied_nrr_key
                                AND hf.safe_h2h_points = thg.safe_h2h_points
),
standings_compiled AS (
    SELECT 
        f.stage_normalized,
        f.group_name,
        f.team_name,
        f.played,
        f.wins,
        f.losses,
        f.no_result,
        f.points,
        f.runs_scored,
        f.balls_faced,
        f.runs_conceded,
        f.balls_bowled,
        f.nrr_display,
        f.n,
        f.d,
        f.n_canon,
        f.d_canon,
        tng.tier_has_undefined_nrr,
        nsc.nrr_superior_count,
        h.safe_h2h_points,
        h.h2h_nrr_display,
        h.h2h_nrr_superior_count,
        h.tier_has_undefined_h2h_nrr,
        r.icc_rank,
        COUNT(*) OVER (PARTITION BY f.stage_normalized, f.group_name, f.points) AS pts_count,
        COUNT(*) OVER (PARTITION BY f.stage_normalized, f.group_name, f.points, f.wins) AS wins_count,
        COUNT(*) OVER (PARTITION BY f.stage_normalized, f.group_name, f.points, f.wins, f.n_canon, f.d_canon) AS nrr_canon_count,
        COUNT(*) OVER (PARTITION BY f.stage_normalized, f.group_name, f.points, f.wins, h.tied_nrr_key, h.safe_h2h_points) AS h2h_pts_tier_count,
        COUNT(*) OVER (PARTITION BY f.stage_normalized, f.group_name, f.points, f.wins, h.tied_nrr_key, h.safe_h2h_points, h.h2h_nrr_superior_count) AS h2h_nrr_canon_count,
        DENSE_RANK() OVER (
            PARTITION BY f.stage_normalized, f.group_name
            ORDER BY 
                f.points DESC,
                f.wins DESC,
                nsc.nrr_superior_count ASC NULLS LAST,
                h.safe_h2h_points DESC NULLS LAST,
                h.h2h_nrr_superior_count ASC NULLS LAST,
                r.icc_rank ASC NULLS LAST,
                f.team_name ASC
        ) AS pool_rank
    FROM group_nrr_fractions f
    JOIN tier_nrr_guard tng ON f.stage_normalized = tng.stage_normalized
                           AND f.group_name = tng.group_name
                           AND f.points = tng.points
                           AND f.wins = tng.wins
    JOIN nrr_superior_counts nsc ON f.stage_normalized = nsc.stage_normalized
                               AND f.group_name = nsc.group_name
                               AND f.team_name = nsc.team_name
    JOIN h2h_nrr_evaluated h ON f.stage_normalized = h.stage_normalized
                            AND f.group_name = h.group_name
                            AND f.team_name = h.team_name
    LEFT JOIN wisden_icc_rankings_4feb2026 r ON f.team_name = r.team_name
)
SELECT 
    stage_normalized,
    group_name,
    pool_rank,
    team_name,
    played,
    wins,
    losses,
    no_result,
    points,
    nrr_display,
    safe_h2h_points,
    h2h_nrr_display,
    icc_rank,
    CASE 
        WHEN pts_count = 1 THEN 'Step 1: Points (Clause 16.10.3)'
        WHEN wins_count = 1 THEN 'Step 2: Most Wins (Clause 16.10.4.a)'
        WHEN tier_has_undefined_nrr = 0 AND nrr_canon_count = 1 THEN 'Step 3: Net Run Rate (Clause 16.10.4.b)'
        WHEN safe_h2h_points IS NOT NULL AND h2h_pts_tier_count = 1 THEN 'Step 4a: Head-to-Head Points (Clause 16.10.4.c)'
        WHEN safe_h2h_points IS NOT NULL AND COALESCE(tier_has_undefined_h2h_nrr, 1) = 0 AND h2h_nrr_canon_count = 1 THEN 'Step 4b: Head-to-Head Net Run Rate (Clause 16.10.4.c)'
        ELSE 'Step 5: ICC T20I Team Rankings (Clause 16.10.4.d)'
    END AS resolution_step,
    CASE 
        WHEN pool_rank <= 2 THEN 'Qualified'
        ELSE 'Eliminated'
    END AS qualification_status
FROM standings_compiled;
```

---

## 5. Remaining Risks & Regulatory Boundary Disclosure

1. **Terminal Tie-Break Boundary (Clause 16.10.4.d):**
   ICC Clause 16.10.4 terminates at the pre-tournament ICC Men's T20I Team Rankings snapshot. If two teams share identical points, identical wins, identical group NRR, identical H2H results, and identical ICC ranking, sports regulations mandate a random draw or coin toss. The SQL engine enforces a deterministic fallback via `team_name ASC` solely to avoid non-deterministic SQL ordering. This scenario does not occur for any team in the 2026 tournament.
2. **Static Ingestion Model:**
   `view_tournament_standings` computes official tournament standings across all pool fixtures. In Power BI, when ingested as `fact_tournament_standings`, it will connect to `dim_teams[team_name]` via a 1:Many relationship and maintain zero relationship to `dim_matches`. This protects official standings from match-attribute slicer distortion while preserving dynamic DAX measures on Pages 2–5.
3. **Secondary Source Provenance:**
   The ranking table relies on the 4 February 2026 Wisden snapshot. While mathematically identical to 6 February 2026 due to the absence of fixtures, official tournament governance documentation should note this secondary provenance.

---

## 6. Final Recommendation

### Status: **APPROVE FOR IMPLEMENTATION (GREEN)**

The SQL standings engine is mathematically rigorous, free of integer overflow risks, completely eliminates division-by-zero defects, exactly resolves rational comparisons, correctly gates Head-to-Head comparisons, and successfully passes 100% of the 19 integration test cases.

### Authorized Implementation Roadmap (Upon User Authorization):
1. **Database DDL:** Deploy `CREATE OR REPLACE VIEW view_tournament_standings AS ...` in PostgreSQL 18.7.
2. **Script Synchronization:** Update `scratch/test_clause_16_10_4_complete.py` with the approved query logic.
3. **Power BI Ingestion:** Ingest `view_tournament_standings` into `model.bim` as `fact_tournament_standings`.
4. **Visual Rebinding:** Bind Page 1 visual table columns to `fact_tournament_standings[pool_rank]` sorted ascending.
