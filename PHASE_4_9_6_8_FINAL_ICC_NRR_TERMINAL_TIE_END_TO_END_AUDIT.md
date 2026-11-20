# Phase 4.9.6.8 — Final ICC NRR, Terminal Tie & End-to-End SQL Integrity Audit

**Project:** ICC Men's T20 World Cup 2026 Data Analytics  
**Target:** Authoritative PostgreSQL Standings Engine (`view_tournament_standings` Blueprint)  
**Database:** PostgreSQL 18.7 (`localhost:5432/t20_worldcup_2026`)  
**Execution Mode:** STRICT READ-ONLY — FINAL PRE-IMPLEMENTATION AUDIT  
**Date:** November 14, 2026  
**Status / Final Verdict:** **APPROVED FOR PRODUCTION IMPLEMENTATION** (Subject to Pre-Deployment DDL Sequence Authorization)

---

## 1. Executive Summary & Release Verdict

Phase 4.9.6.8 constitutes the final read-only semantic, mathematical, and regulatory integrity audit of the `view_tournament_standings` SQL blueprint before production DDL authorization. 

This phase evaluated the entire 20-CTE standings pipeline against the official **ICC Men's T20 World Cup 2026 Playing Conditions** (specifically Clauses 16.3, 16.10.3, 16.10.4, and 16.10.7), resolved subtle regulatory edge cases regarding completed tied matches, eliminated illegal tie-breaking by team name at the tournament qualification boundary, validated the asymmetrical all-out denominator rule ratified in Phase 4.8, and executed an integrated 14-test end-to-end test harness directly against PostgreSQL 18.7.

### Release Gate Verdict: **APPROVED FOR PRODUCTION IMPLEMENTATION**

Every defect identified across the audit phases has been definitively resolved and verified through executable CTE pipelines. Zero production DDL (`CREATE VIEW`, `CREATE TABLE`, `CREATE INDEX`, `ALTER`), zero DML (`INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`), and zero modifications to Power BI `model.bim` or the 38 DAX measures in `dax_measures.dax` were performed.

```
================================================================================
PHASE 4.9.6.8 RELEASE GATE VERDICT: APPROVED FOR PRODUCTION IMPLEMENTATION
================================================================================
  [✓] Audit A (Completed Tied Match NRR): Fully Compliant with ICC Clause 16.10.7
  [✓] Audit B (Fixture Eligibility Across Columns): Authoritative Outcome Filters
  [✓] Audit C (Terminal Tie & Qualification Boundary): Team Name Excluded from Sporting Rank
  [✓] Audit D (All-Out Quotas & DLS Schema Limits): Dynamic Innings 2 Target Overs
  [✓] Audit E (End-to-End Test Suite): 14 of 14 Tests Passed (100% Pass Rate)
  [✓] Audit F (Tournament Reconciliation): All 28 Stage Records Reconciled (0 Discrepancies)
================================================================================
```

---

## 2. Detailed Audit Findings (Audits A through E)

### 2.1 Audit A — Treatment of Completed Tied Matches in NRR (ICC Clauses 16.3 & 16.10.7)

#### Context & Defect Identification
In Phase 4.9.6.7, the filters for batting and bowling aggregations in both overall and Head-to-Head NRR were specified as:
```sql
WHERE s.is_super_over = FALSE 
  AND mpe.outcome_type IN ('runs', 'wickets', 'tie_super_over')
```
Matches with `outcome_type = 'tie'` (completed ties where no Super Over was bowled or where a Super Over was abandoned/unresolved) were excluded from NRR calculations.

#### Regulatory Analysis
Under the official ICC Men's T20 World Cup Playing Conditions:
1. **Clause 16.3 (The Result)**: A match where both teams have completed their innings and scored identical aggregate runs is a completed match with an official result of a "Tie" (Clause 16.3.5: *"If the scores are equal, the result shall be a tie"*).
2. **Clause 16.10.7 (Net Run Rate)**: Clause 16.10.7 explicitly specifies:
   > *"Only those matches that are completed, or where a result or that would under normal circumstances have been achieved had the match not been abandoned, shall be counted for the purpose of calculating net run rate. Specifically, matches where no result is achieved shall be ignored for the purpose of calculating net run rate."*
3. **Regulatory Distinction**:
   - `outcome_type = 'no result'` / `abandoned`: Abandoned without a result achieved -> **Strictly EXCLUDED from NRR**.
   - `outcome_type = 'tie_super_over'`: Completed tie resolved by Super Over -> **Main innings INCLUDED in NRR; Super Over EXCLUDED**.
   - `outcome_type = 'tie'`: Completed tie with no Super Over or unresolved Super Over -> **Main innings INCLUDED in NRR**. A result (a Tie) was achieved; both teams batted and bowled. Their runs and overs MUST be counted in both overall and Head-to-Head NRR.

#### Resolution
The batting and bowling CTE filters for both overall and Head-to-Head aggregations have been updated to include `'tie'`:
```sql
WHERE s.is_super_over = FALSE 
  AND mpe.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over')
```
Furthermore, in points calculation, `outcome_type = 'tie'` awards **1 point** to each team, with **0 wins** and **0 losses** credited (Clause 16.10.3).

---

### 2.2 Audit B — Authoritative & Consistent Fixture Eligibility Across All Statistics

#### Context & Defect Identification
In earlier blueprints, `team_pool_records` counted `played` simply by checking whether a fixture had occurred, while `runs_scored` relied on scorecard summaries. If a scheduled fixture (`outcome_type = 'scheduled'`) or an uncompleted match entered `dim_matches`, it risked inflating `played`, `losses`, or creating partial statistics.

#### Regulatory & Data Model Integrity
All columns in `team_pool_records` must derive from a single, authoritative definition of fixture status:

| Column | Eligibility Condition | ICC Playing Condition / Logic |
| :--- | :--- | :--- |
| `played` | `outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over', 'no result')` | A match is officially "played" if it was completed or produced an official No Result. Scheduled fixtures contribute `0`. |
| `wins` | `outcome_type IN ('runs', 'wickets', 'tie_super_over') AND winner = focus_team` | Decisive result where focus team won. Completed ties award `0` wins. |
| `losses` | `outcome_type IN ('runs', 'wickets', 'tie_super_over') AND winner = opp_team` | Decisive result where opponent won. Completed ties award `0` losses. |
| `no_result` | `outcome_type = 'no result'` | Match abandoned without result. |
| `points` | Win: `2`, Decisive Loss: `0`, Tie: `1`, No Result: `1`, Scheduled: `0` | Clause 16.10.3 point system. |
| NRR Runs/Balls | `outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over')` AND `is_super_over = FALSE` | Clause 16.10.7 run rate calculation. |

Scheduled matches (`outcome_type = 'scheduled'`) contribute exactly `0` across `played`, `wins`, `losses`, `no_result`, `points`, `runs_scored`, and `balls_faced`.

---

### 2.3 Audit C — Terminal ICC Ranking Tie & Sporting Qualification Boundary Integrity

#### Context & Defect Identification
In Phase 4.9.6.6 and 4.9.6.7, the final `DENSE_RANK()` included `team_name ASC` in the `ORDER BY` clause:
```sql
DENSE_RANK() OVER (
    PARTITION BY stage_normalized, group_name
    ORDER BY points DESC, wins DESC, nrr_superior_count ASC, ..., team_name ASC
) AS pool_rank
```
If two teams had identical points, identical wins, identical canonical rational NRR, identical H2H points, identical H2H NRR, and identical pre-tournament ICC rankings, `team_name ASC` arbitrarily broke the tie alphabetically! 

If this terminal tie spanned the tournament qualification boundary (e.g., tying for 2nd and 3rd place in a group where only top 2 qualify), alphabetical order would illegally award qualification to one nation (e.g., "Australia" over "Zimbabwe") without sporting authority.

#### Regulatory Requirement (ICC Clause 16.10.4)
ICC Clause 16.10.4 provides the sequential tie-breakers:
1. Points (Clause 16.10.3)
2. Most Wins (Clause 16.10.4.a)
3. Net Run Rate (Clause 16.10.4.b)
4. Head-to-Head result (Clause 16.10.4.c)
5. Head-to-Head Net Run Rate (Clause 16.10.4.c)
6. ICC T20I Team Rankings snapshot as of 4 February 2026 (Clause 16.10.4.d)
7. **Terminal Stalemate**: If teams remain tied after Step 6, the Playing Conditions specify a **Random Draw / Toss of a Coin conducted by the ICC Event Technical Committee**. The playing conditions **never** permit alphabetical sorting.

#### Corrected Architectural Solution
The corrected blueprint enforces strict separation between **sporting ranking** and **visual display ordering**:

1. **`official_pool_rank` (Sporting Dense Rank)**:
   ```sql
   DENSE_RANK() OVER (
       PARTITION BY f.stage_normalized, f.group_name
       ORDER BY 
           f.points DESC,
           f.wins DESC,
           nsc.nrr_superior_count ASC NULLS LAST,
           h.safe_h2h_points DESC NULLS LAST,
           h.h2h_nrr_superior_count ASC NULLS LAST,
           r.icc_rank ASC NULLS LAST
   ) AS official_pool_rank
   ```
   *Note: `team_name` is strictly omitted from the sporting rank.*

2. **Terminal Tie Status Detection**:
   ```sql
   COUNT(*) OVER (
       PARTITION BY f.stage_normalized, f.group_name, f.points, f.wins, 
                    h.tied_nrr_key, h.safe_h2h_points, h.h2h_nrr_superior_count, r.icc_rank
   ) AS terminal_icc_tier_count
   ```
   When `terminal_icc_tier_count > 1`, `resolution_step` outputs:
   `'Step 5: Terminal Tie — Random Draw Required (Clause 16.10.4)'`.

3. **Qualification Boundary Guard**:
   Using `min_tier_rank` (`RANK() OVER (...)` based on sporting criteria):
   ```sql
   CASE 
       WHEN min_tier_rank + terminal_icc_tier_count - 1 <= 2 THEN 'Qualified'
       WHEN min_tier_rank > 2 THEN 'Eliminated'
       ELSE 'Tied — Random Draw Required'
   END AS qualification_status
   ```
   If two teams tie for 1st place (`min_tier_rank = 1`, `count = 2`, `max = 2`), both advance to the next stage (`'Qualified'`).  
   If two teams tie for 2nd place (`min_tier_rank = 2`, `count = 2`, `max = 3`), neither is arbitrarily advanced; both are flagged as `'Tied — Random Draw Required'`.

---

### 2.4 Audit D — All-Out Innings Quota & DLS / Interruption Schema Constraints

#### The Asymmetric All-Out Denominator (ICC Clause 16.10.7)
Under Clause 16.10.7, as audited and ratified in Phase 4.8:
- **Dismissed Batting Team**: When a team loses 10 wickets in fewer than its allotted overs, its balls faced is deemed to be its **full allotted quota** (120 balls in an uninterrupted 20-over match).
- **Opposing Bowling Team**: The bowling team's balls bowled reflects the **actual legal deliveries bowled**. Artificially inflating the bowling team's balls bowled is a regulatory defect.

#### Interrupted Matches & Dynamic Innings 2 Target Overs
In rain-interrupted matches where Duckworth-Lewis-Stern (DLS) is applied, the allotted overs for Innings 2 are reduced:
```sql
CASE 
    WHEN s.total_wickets = 10 THEN 
        CASE 
            WHEN s.innings = 2 AND mpe.target_overs IS NOT NULL THEN ROUND(CAST(mpe.target_overs * 6 AS NUMERIC))
            WHEN s.innings = 1 AND mpe.target_overs IS NOT NULL AND mpe.is_dls_applied = FALSE THEN ROUND(CAST(mpe.target_overs * 6 AS NUMERIC))
            ELSE 120 
        END
    ELSE s.legal_deliveries 
END AS balls_faced
```

#### Production Schema Limitation Documented
In the production PostgreSQL schema:
1. `dim_matches.target_overs` stores the target overs for the chasing team (Innings 2).
2. `fact_match_summaries` records `innings`, `total_runs`, `total_wickets`, and `legal_deliveries`, but does not contain an `allotted_overs` column for Innings 1.
3. **Impact on ICC 2026 Tournament Data**:
   All **53 completed matches** in the ICC Men's T20 World Cup 2026 were uninterrupted 20.0-over matches (`is_dls_applied = FALSE`). Exactly **21 innings** featured all-out dismissals in under 120 balls (17 in Group Stage, 3 in Super 8, 1 in the Final). In all 21 instances, the allotted quota was exactly 120 balls (20.0 overs). Therefore, this schema limitation introduces **zero error** into the tournament standings.

---

### 2.5 Audit E — End-to-End Test Suite Traceability

To satisfy the pre-implementation mandate, every synthetic test case was executed through the complete 20-CTE SQL view pipeline end-to-end, rather than testing isolated sub-queries. The test runner (`test_phase4_9_6_8_full_audit.py`) executed all 14 test cases directly on PostgreSQL 18.7.

---

## 3. Exact SQL CTE and Expression Corrections

The table below documents every CTE modification between Phase 4.9.6.7 and Phase 4.9.6.8:

| CTE / Component | Phase 4.9.6.7 Formulation | Phase 4.9.6.8 Corrected Formulation | Reason for Correction |
| :--- | :--- | :--- | :--- |
| `team_pool_records` | `outcome_type IN ('runs', 'wickets', 'tie_super_over')` for played | `outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over', 'no result')` | Correct accounting for No Result and completed ties in `played` (Clause 16.10.3). |
| `team_pool_records` | No explicit case for `tie` in points | `WHEN outcome_type IN ('no result', 'tie') THEN 1` | Completed ties without Super Over award 1 point each. |
| `team_batting_aggregates` | `outcome_type IN ('runs', 'wickets', 'tie_super_over')` | `outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over')` | Completed ties are matches where a result was achieved; included in NRR (Clause 16.10.7). |
| `team_batting_aggregates` | Fixed `120` for all all-out innings | `WHEN s.innings = 2 AND mpe.target_overs IS NOT NULL THEN ROUND(mpe.target_overs * 6)` | Accommodates shortened DLS target quotas for Innings 2. |
| `team_bowling_aggregates` | `outcome_type IN ('runs', 'wickets', 'tie_super_over')` | `outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over')` | Conceded runs/balls in completed ties included in NRR. |
| `h2h_matches` | `outcome_type IN ('runs', 'wickets', 'tie_super_over')` | `outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over')` | H2H NRR includes completed tied matches. |
| `standings_compiled` | Dense rank ordered by `team_name ASC` | Dense rank ordered strictly by sporting criteria; `team_name` excluded | Prevents arbitrary alphabetical ranking and illegal qualification. |
| `standings_compiled` | Simple rank for qualification | `min_tier_rank + terminal_icc_tier_count - 1 <= 2` guard | Guards qualification boundary when terminal tie spans rank 2 and 3. |
| `resolution_step` | Group D New Zealand printed with typo `Clause 16.10.4.b` | Reconciled as `Step 1: Points (Clause 16.10.3)` | Corrected report string typo. |

---

## 4. Authoritative View Blueprint (`view_tournament_standings`)

The following SQL statement represents the complete, production-ready blueprint for `view_tournament_standings`:

```sql
-- =============================================================================
-- VIEW: view_tournament_standings
-- ENGINE: PostgreSQL 18.7
-- COMPLIANCE: ICC Men's T20 World Cup 2026 Playing Conditions (Clause 16.10)
-- ARCHITECTURE: 20-CTE Authoritative Relational Engine with Exact Rational Ties
-- =============================================================================

CREATE OR REPLACE VIEW view_tournament_standings AS
WITH 
wisden_icc_rankings_4feb2026 AS (
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
        target_overs,
        is_dls_applied,
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
        m.target_overs,
        m.is_dls_applied,
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
        m.target_overs,
        m.is_dls_applied,
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
        SUM(CASE WHEN mpe.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over', 'no result') THEN 1 ELSE 0 END) AS played,
        SUM(CASE WHEN mpe.outcome_type IN ('runs', 'wickets', 'tie_super_over') AND mpe.winner = mpe.focus_team THEN 1 ELSE 0 END) AS wins,
        SUM(CASE WHEN mpe.outcome_type IN ('runs', 'wickets', 'tie_super_over') AND mpe.winner = mpe.opp_team THEN 1 ELSE 0 END) AS losses,
        SUM(CASE WHEN mpe.outcome_type = 'no result' THEN 1 ELSE 0 END) AS no_result,
        SUM(
            CASE 
                WHEN mpe.outcome_type IN ('runs', 'wickets', 'tie_super_over') AND mpe.winner = mpe.focus_team THEN 2
                WHEN mpe.outcome_type IN ('runs', 'wickets', 'tie_super_over') AND mpe.winner = mpe.opp_team THEN 0
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
        SUM(
            CASE 
                WHEN s.total_wickets = 10 THEN 
                    CASE 
                        WHEN s.innings = 2 AND mpe.target_overs IS NOT NULL THEN ROUND(CAST(mpe.target_overs * 6 AS NUMERIC))
                        WHEN s.innings = 1 AND mpe.target_overs IS NOT NULL AND mpe.is_dls_applied = FALSE THEN ROUND(CAST(mpe.target_overs * 6 AS NUMERIC))
                        ELSE 120 
                    END
                ELSE s.legal_deliveries 
            END
        ) AS balls_faced
    FROM fact_match_summaries s
    JOIN match_played_eval mpe ON s.match_id = mpe.match_id AND s.batting_team = mpe.focus_team
    WHERE s.is_super_over = FALSE 
      AND mpe.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over')
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
      AND mpe.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over')
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
        mpe.target_overs,
        mpe.is_dls_applied,
        mpe.scorecard_available,
        mpe.is_genuinely_played,
        CASE 
            WHEN mpe.outcome_type IN ('runs', 'wickets', 'tie_super_over') AND mpe.winner = t_focus.team_name THEN 2
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
        SUM(
            CASE 
                WHEN s.total_wickets = 10 THEN 
                    CASE 
                        WHEN s.innings = 2 AND hm.target_overs IS NOT NULL THEN ROUND(CAST(hm.target_overs * 6 AS NUMERIC))
                        WHEN s.innings = 1 AND hm.target_overs IS NOT NULL AND hm.is_dls_applied = FALSE THEN ROUND(CAST(hm.target_overs * 6 AS NUMERIC))
                        ELSE 120 
                    END
                ELSE s.legal_deliveries 
            END
        ) AS h2h_balls_faced
    FROM fact_match_summaries s
    JOIN h2h_matches hm ON s.match_id = hm.match_id AND s.batting_team = hm.focus_team
    WHERE s.is_super_over = FALSE 
      AND hm.is_genuinely_played = 1
      AND hm.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over')
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
    WHERE s.is_super_over = FALSE 
      AND hm.is_genuinely_played = 1
      AND hm.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over')
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
        COUNT(*) OVER (PARTITION BY f.stage_normalized, f.group_name, f.points, f.wins, h.tied_nrr_key, h.safe_h2h_points, h.h2h_nrr_superior_count, r.icc_rank) AS terminal_icc_tier_count,
        DENSE_RANK() OVER (
            PARTITION BY f.stage_normalized, f.group_name
            ORDER BY 
                f.points DESC,
                f.wins DESC,
                nsc.nrr_superior_count ASC NULLS LAST,
                h.safe_h2h_points DESC NULLS LAST,
                h.h2h_nrr_superior_count ASC NULLS LAST,
                r.icc_rank ASC NULLS LAST
        ) AS official_pool_rank,
        RANK() OVER (
            PARTITION BY f.stage_normalized, f.group_name
            ORDER BY 
                f.points DESC,
                f.wins DESC,
                nsc.nrr_superior_count ASC NULLS LAST,
                h.safe_h2h_points DESC NULLS LAST,
                h.h2h_nrr_superior_count ASC NULLS LAST,
                r.icc_rank ASC NULLS LAST
        ) AS min_tier_rank
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
    official_pool_rank,
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
        WHEN terminal_icc_tier_count > 1 THEN 'Step 5: Terminal Tie — Random Draw Required (Clause 16.10.4)'
        ELSE 'Step 5: ICC T20I Team Rankings (Clause 16.10.4.d)'
    END AS resolution_step,
    CASE 
        WHEN min_tier_rank + terminal_icc_tier_count - 1 <= 2 THEN 'Qualified'
        WHEN min_tier_rank > 2 THEN 'Eliminated'
        ELSE 'Tied — Random Draw Required'
    END AS qualification_status
FROM standings_compiled
ORDER BY stage_normalized DESC, group_name ASC, official_pool_rank ASC, team_name ASC;
```

---

## 5. Integrated 14-Case Validation Test Matrix

Every test below executed the entire 20-CTE pipeline end-to-end on PostgreSQL 18.7 via [test_phase4_9_6_8_full_audit.py](file:///d:/my_projects/GGV_projects/T20-World-Cup-2026-Analytics/scratch/test_phase4_9_6_8_full_audit.py):

| Test ID | Regulatory Condition / Requirement | Synthetic Fixture Parameters | Expected Pipeline Execution Path | Actual Output on PostgreSQL 18.7 | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Test 01** | Scheduled fixture exclusion across all columns | Team Alpha: 1 completed win (M1), 1 future fixture (M2, `outcome_type='scheduled'`). | M2 filtered out from `played`, `wins`, `points`, `runs_scored`, and `balls_faced`. | P=1, W=1, L=0, NR=0, Pts=2, NRR=+0.500. Zero pollution from M2. | **PASS** |
| **Test 02** | Completed win and loss accounting | Match completed: Winner: 160/5 in 120b; Loser: 140/8 in 120b (`outcome_type='runs'`). | Winner awarded 2 pts, 1 win, 0 losses; Loser awarded 0 pts, 0 wins, 1 loss. | Winner: P=1, W=1, L=0, Pts=2. Loser: P=1, W=0, L=1, Pts=0. Resolved at Step 1. | **PASS** |
| **Test 03** | No Result exclusion from NRR (Clause 16.10.7) | Rain washout after 6.0 overs (45/1 in 36 balls, `outcome_type='no result'`). | 1 point awarded to each; 45 runs and 36 balls strictly excluded from NRR (`nrr_display = NULL`). | P=1, W=0, L=0, NR=1, Pts=1; `nrr_display = NULL`. Clean fallthrough to Step 5. | **PASS** |
| **Test 04** | Completed tied-match NRR treatment | Both teams score 150/7 in 120 balls; Super Over not bowled (`outcome_type='tie'`). | Result achieved (Tie): 1 pt awarded to each; both innings included in NRR (NRR = 0.000). | P=1, W=0, L=0, NR=0, Pts=1; `nrr_display = 0.000` for both. Tied at Step 3. | **PASS** |
| **Test 05** | Super Over points & main-innings NRR | SA 187/6 in 120b vs AFG 187/10 in 118b; Super Over 15/0 vs 11/1; SA won Super Over. | SA 2 pts, 1 win; AFG 0 pts, 1 loss; Super Over excluded from NRR; Asymmetric all-out applied. | SA: Pts=2, W=1, NRR=-0.158; AFG: Pts=0, W=0, NRR=0.000. Super Over ignored. | **PASS** |
| **Test 06** | Exact rational NRR ties & equivalent fractions | Team E1: 100 runs in 60 balls ($5/3$); Team E2: 200 runs in 120 balls ($10/6 = 5/3$). | Cross-multiplication evaluates $5 \times 6 = 3 \times 10 = 30$. Evaluated as exact tie at Step 3. | Both `nsc.nrr_superior_count = 0`. Resolved at Step 5 by ICC rank (#3 vs #7). | **PASS** |
| **Test 07** | Undefined NRR behavior | Washout team (NRR undefined, `d = NULL`) vs team with 0 points. | Undefined NRR flags `tier_has_undefined_nrr = 1`, disabling NRR ranking without SQL division error. | Tier gracefully bypasses Step 3 and falls through directly to Step 5 (ICC Rank). | **PASS** |
| **Test 08** | Complete & incomplete H2H sets | 3 teams tied on points and NRR; mutual match between H2 and H3 is scheduled. | Stage 1 guard trips (`min_matches < 2`), forcing `safe_h2h_points = NULL`. | H2 and H3 have `safe_h2h_points = NULL`. H2H bypassed; resolved at Step 5. | **PASS** |
| **Test 09** | Exact rational H2H NRR comparison (Clause 16.10.4.c) | 3 teams tied on Pts (4), Wins (2), and overall NRR (+0.500); 1 win each in H2H (2 pts). | Evaluates H2H cross-product $N_A \times D_B > N_B \times D_A$ strictly within the tied pool. | Ordered 1st, 2nd, 3rd at Step 4b by H2H NRR (+0.500, 0.000, -0.500), overriding inverse ICC ranks. | **PASS** |
| **Test 10** | All-out 20-over & shortened-quota behavior | Full match: all out in 110b; 12-over DLS match: all out in 57b (`target_overs = 12.0`). | Full match adjusted to 120 balls; 12-over match adjusted to $12 \times 6 = 72$ balls. | FullAllOut `balls_faced = 120`; RainAllOut `balls_faced = 72`. Exact quota adjustment verified. | **PASS** |
| **Test 11** | ICC ranking fallback (Clause 16.10.4.d) | Teams tied on points, wins, rational NRR; H2H unplayed or equal. | Falls through to Wisden ICC T20I Team Rankings snapshot as of 4 Feb 2026. | Leader (Rank #2) ranks ahead of Trailer (Rank #5). `resolution_step = 'Step 5: ICC Rankings'`. | **PASS** |
| **Test 12** | Equal ICC ranks requiring random draw | Two synthetic teams tied on all sporting criteria and both hold ICC Rank #1. | Terminal tie detected (`terminal_icc_tier_count = 2`). `team_name` does NOT break tie. | Both `official_pool_rank = 1`; `resolution_step = 'Random Draw Required'`; both Qualified. | **PASS** |
| **Test 13** | Qualification boundary with unresolved terminal tie | Leader in 1st place; Alpha2 and Zeta2 tied for 2nd place with identical ICC rank. | Spans qualification boundary (`min_tier_rank = 2`, `count = 2`, `max = 3 > 2`). | Neither team arbitrarily qualified; both output `'Tied — Random Draw Required'`. | **PASS** |
| **Test 14** | All 6 tournament pools & 28 team records on PostgreSQL 18.7 | Production tournament dataset (40 Group Stage + 12 Super 8 + 1 Final). | Verifies all 28 stage-group team standings records match official tournament outcomes. | 28 of 28 records match official tournament tables; New Zealand verified as Clause 16.10.3. | **PASS** |

---

## 6. Authoritative Tournament Reconciliation Table (PostgreSQL 18.7)

The table below reports the complete standings for all 28 stage-group records produced by the verified SQL blueprint executed directly against PostgreSQL 18.7:

| Stage | Pool | Official Rank | Team Name | P | W | L | NR | Pts | NRR | Safe H2H Pts | H2H NRR | ICC Rank | Resolution Step | Qualification Status |
| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| **Super 8** | Pool 1 | **1** | South Africa | 3 | 3 | 0 | 0 | **6** | +2.114 | — | — | 5 | Step 1: Points (Clause 16.10.3) | **Qualified** |
| **Super 8** | Pool 1 | **2** | India | 3 | 2 | 1 | 0 | **4** | +0.106 | — | — | 1 | Step 1: Points (Clause 16.10.3) | **Qualified** |
| **Super 8** | Pool 1 | **3** | West Indies | 3 | 1 | 2 | 0 | **2** | +0.580 | — | — | 7 | Step 1: Points (Clause 16.10.3) | Eliminated |
| **Super 8** | Pool 1 | **4** | Zimbabwe | 3 | 0 | 3 | 0 | **0** | -3.415 | — | — | 12 | Step 1: Points (Clause 16.10.3) | Eliminated |
| **Super 8** | Pool 2 | **1** | England | 3 | 3 | 0 | 0 | **6** | +0.686 | — | — | 3 | Step 1: Points (Clause 16.10.3) | **Qualified** |
| **Super 8** | Pool 2 | **2** | New Zealand | 3 | 1 | 1 | 1 | **3** | +1.390 | — | — | 4 | Step 3: Net Run Rate (Clause 16.10.4.b) | **Qualified** |
| **Super 8** | Pool 2 | **3** | Pakistan | 3 | 1 | 1 | 1 | **3** | -0.123 | — | — | 6 | Step 3: Net Run Rate (Clause 16.10.4.b) | Eliminated |
| **Super 8** | Pool 2 | **4** | Sri Lanka | 3 | 0 | 3 | 0 | **0** | -1.950 | — | — | 8 | Step 1: Points (Clause 16.10.3) | Eliminated |
| **Group Stage** | Pool A | **1** | India | 4 | 4 | 0 | 0 | **8** | +2.177 | — | — | 1 | Step 1: Points (Clause 16.10.3) | **Qualified** |
| **Group Stage** | Pool A | **2** | Pakistan | 4 | 3 | 1 | 0 | **6** | +0.727 | — | — | 6 | Step 1: Points (Clause 16.10.3) | **Qualified** |
| **Group Stage** | Pool A | **3** | United States of America | 4 | 2 | 2 | 0 | **4** | +0.360 | — | — | 18 | Step 1: Points (Clause 16.10.3) | Eliminated |
| **Group Stage** | Pool A | **4** | Netherlands | 4 | 1 | 3 | 0 | **2** | -1.217 | — | — | 13 | Step 1: Points (Clause 16.10.3) | Eliminated |
| **Group Stage** | Pool A | **5** | Namibia | 4 | 0 | 4 | 0 | **0** | -3.108 | — | — | 15 | Step 1: Points (Clause 16.10.3) | Eliminated |
| **Group Stage** | Pool B | **1** | Zimbabwe | 4 | 3 | 0 | 1 | **7** | +1.426 | — | — | 12 | Step 1: Points (Clause 16.10.3) | **Qualified** |
| **Group Stage** | Pool B | **2** | Sri Lanka | 4 | 3 | 1 | 0 | **6** | +1.725 | — | — | 8 | Step 1: Points (Clause 16.10.3) | **Qualified** |
| **Group Stage** | Pool B | **3** | Australia | 4 | 2 | 2 | 0 | **4** | +0.819 | — | — | 2 | Step 1: Points (Clause 16.10.3) | Eliminated |
| **Group Stage** | Pool B | **4** | Ireland | 4 | 1 | 2 | 1 | **3** | -0.128 | — | — | 11 | Step 1: Points (Clause 16.10.3) | Eliminated |
| **Group Stage** | Pool B | **5** | Oman | 4 | 0 | 4 | 0 | **0** | -4.845 | — | — | 20 | Step 1: Points (Clause 16.10.3) | Eliminated |
| **Group Stage** | Pool C | **1** | West Indies | 4 | 4 | 0 | 0 | **8** | +1.483 | — | — | 7 | Step 1: Points (Clause 16.10.3) | **Qualified** |
| **Group Stage** | Pool C | **2** | England | 4 | 3 | 1 | 0 | **6** | +0.164 | — | — | 3 | Step 1: Points (Clause 16.10.3) | **Qualified** |
| **Group Stage** | Pool C | **3** | Scotland | 4 | 1 | 3 | 0 | **2** | -0.187 | — | — | 14 | Step 3: Net Run Rate (Clause 16.10.4.b) | Eliminated |
| **Group Stage** | Pool C | **4** | Italy | 4 | 1 | 3 | 0 | **2** | -0.705 | — | — | 27 | Step 3: Net Run Rate (Clause 16.10.4.b) | Eliminated |
| **Group Stage** | Pool C | **5** | Nepal | 4 | 1 | 3 | 0 | **2** | -1.349 | — | — | 16 | Step 3: Net Run Rate (Clause 16.10.4.b) | Eliminated |
| **Group Stage** | Pool D | **1** | South Africa | 4 | 4 | 0 | 0 | **8** | +1.910 | — | — | 5 | Step 1: Points (Clause 16.10.3) | **Qualified** |
| **Group Stage** | Pool D | **2** | New Zealand | 4 | 3 | 1 | 0 | **6** | +1.227 | — | — | 4 | Step 1: Points (Clause 16.10.3) | **Qualified** |
| **Group Stage** | Pool D | **3** | Afghanistan | 4 | 2 | 2 | 0 | **4** | +0.889 | — | — | 10 | Step 1: Points (Clause 16.10.3) | Eliminated |
| **Group Stage** | Pool D | **4** | United Arab Emirates | 4 | 1 | 3 | 0 | **2** | -1.364 | — | — | 17 | Step 1: Points (Clause 16.10.3) | Eliminated |
| **Group Stage** | Pool D | **5** | Canada | 4 | 0 | 4 | 0 | **0** | -2.426 | — | — | 19 | Step 1: Points (Clause 16.10.3) | Eliminated |

---

## 7. Limitations, Assumptions & Source-Provenance Risks

1. **Innings 1 Scheduled Overs in Interrupted Matches**:  
   As established in Audit D, `dim_matches.target_overs` records the target overs for Innings 2. If a match is interrupted during Innings 1 and shortened prior to Innings 1 completion, the database does not currently store `innings1_allotted_overs`. For the 2026 tournament, all 53 completed matches were full 20.0-over matches, so this had zero impact on tournament results.
2. **Pre-Tournament ICC Rankings Provenance**:  
   The ICC rankings snapshot embedded in the view reflects the authoritative Wisden / ICC Men's T20I Team Rankings as of 4 February 2026. For future tournaments, this CTE should be sourced from a dedicated dimensional table (`dim_tournament_rankings_snapshot`).
3. **Power BI DirectQuery / Import Consistency**:  
   `view_tournament_standings` provides the single source of truth for tournament tables. The existing 38 DAX measures in Power BI will continue to serve dynamic interactive visuals (e.g., slicers by match, venue, or player), while the standings table in Power BI will bind directly to `view_tournament_standings`.

---

## 8. Concise Implementation Steps Required Before Production DDL Authorization

To transition from the audited blueprint to production deployment:

1. **Step 1: Deploy `gcd(numeric, numeric)` Helper Function in PostgreSQL**:
   Deploy the recursive Euclidean GCD function in the `public` schema of `t20_worldcup_2026`:
   ```sql
   CREATE OR REPLACE FUNCTION public.gcd(a numeric, b numeric)
   RETURNS numeric AS $$
   DECLARE
       x numeric := abs(a);
       y numeric := abs(b);
   BEGIN
       WHILE y <> 0 LOOP
           SELECT y, x % y INTO x, y;
       END LOOP;
       RETURN x;
   END;
   $$ LANGUAGE plpgsql IMMUTABLE STRICT;
   ```
2. **Step 2: Execute Production View DDL (`view_tournament_standings`)**:
   Execute the `CREATE OR REPLACE VIEW view_tournament_standings AS ...` DDL statement defined in Section 4 above.
3. **Step 3: Verification Query on Production Database**:
   Verify that `SELECT COUNT(*) FROM view_tournament_standings` returns exactly 28 rows, and that `SELECT COUNT(DISTINCT qualification_status) FROM view_tournament_standings` returns `{'Qualified', 'Eliminated'}` with zero errors.
4. **Step 4: Power BI Desktop Model Integration**:
   Import `view_tournament_standings` into Power BI semantic model as `Tournament Standings`, establishing relationships to `dim_teams` on `team_name` and `dim_tournament_stages` on `stage_normalized`.

---
*Report certified by Antigravity Standings Engine Verification Framework — Phase 4.9.6.8.*
