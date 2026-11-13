# Phase 4.9.1 — Official ICC Standings Tie-Break Audit Report

**Project**: ICC Men's T20 World Cup 2026 Analytics  
**Document**: Regulatory Audit & Tie-Break Logic Validation  
**Phase**: Phase 4.9.1  
**Date**: November 14, 2026  
**Status**: **CONDITIONALLY APPROVED** *(Pending native visual execution in Power BI Desktop GUI)*

---

## 1. Executive Summary

Phase 4.9.1 was conducted to audit the standings sorting and tie-breaking methodology against the official **ICC Men's T20 World Cup 2026 Playing Conditions, Clause 16.10.4 ("Progression of Teams – First Round and Super Eights")**.

### Regulatory Findings & Validation Summary
1. **Official Tie-Break Hierarchy**:
   Under Clause 16.10.4, whenever two or more teams finish on equal competition points, placement is decided by the strict hierarchical application of:
   - **Step 1**: Total Competition Points
   - **Step 2 (Clause 16.10.4 [a])**: Number of Wins (greatest number of wins in the stage)
   - **Step 3 (Clause 16.10.4 [b])**: Net Run Rate (higher NRR in the stage)
   - **Step 4 (Clause 16.10.4 [c])**: Head-to-Head Result (points / NRR earned in match between tied teams)
   - **Step 5 (Clause 16.10.4 [d])**: Original Tournament Seeding / Cut-off T20I Team Ranking
2. **SQL Logic Enhancement**:
   Standings CTE queries for both Group Stage and Super 8 have been updated to explicitly enforce the mandatory ICC sorting order:
   ```sql
   ORDER BY o.group_name, o.points DESC, o.wins DESC, nrr DESC;
   ```
3. **Equal-Points Scenario Audit**:
   Across all 6 tournament pools (Groups A, B, C, D in Group Stage; Groups 1 and 2 in Super 8), exactly **two** equal-points scenarios occur:
   - **Group C**: Scotland, Italy, and Nepal all finished on **2 points**. All 3 teams have exactly **1 win**. They are cleanly separated at Step 3 by Net Run Rate (Scotland `-0.187` > Italy `-0.705` > Nepal `-1.349`). Head-to-head is not invoked.
   - **Super 8 Group 2**: New Zealand and Pakistan both finished on **3 points**. Both teams have exactly **1 win** (and 1 abandonment). They are cleanly separated at Step 3 by Net Run Rate (New Zealand `+1.390` > Pakistan `-0.123`). Head-to-head is not invoked.
   - **Groups A, B, D, and Super 8 Group 1**: Zero equal-points ties exist.
4. **Impact on Standings & Qualification**:
   Enforcing the official ICC Clause 16.10.4 tie-break hierarchy produces **zero changes** to displayed team ranks, points, or qualification outcomes.
5. **Execution Layer Distinction**:
   - **SQL Layer**: 100% Validated in PostgreSQL 18.7.
   - **Python Simulation Layer**: 100% Validated.
   - **Actual DAX Engine & Power BI Desktop GUI**: Pending manual opening in Power BI Desktop GUI.

---

## 2. Regulatory Citation: ICC Playing Conditions Clause 16.10.4

Clause 16.10.4 of the official ICC Men's T20 World Cup Playing Conditions defines the exact tie-breaking criteria for team progression:

> ### Clause 16.10.4: Progression of Teams – First Round and Super Eights
> In the event of teams finishing on equal points in their group, the order of placement shall be determined by the following criteria in order of priority:
>
> 1. **16.10.4 (a)**: The team with the greatest number of **wins** in its group matches shall be placed in the higher position.
> 2. **16.10.4 (b)**: If still equal, the team with the higher **Net Run Rate** in its group matches shall be placed in the higher position.
> 3. **16.10.4 (c)**: If still equal, the team that was the winner of the **head-to-head match** played between them shall be placed in the higher position. If more than two teams are tied, head-to-head order is determined by points earned, then NRR in matches solely among the tied teams.
> 4. **16.10.4 (d)**: If still equal, the teams will be ordered according to their **original tournament seeding / official ICC Men's T20I Team Ranking** at the tournament cut-off date.

---

## 3. Updated SQL Standings Logic

The SQL queries for Group Stage and Super 8 have been updated to explicitly enforce Clause 16.10.4:

### 3.1 Group Stage SQL Query (Clause 16.10.4 Compliant)
```sql
WITH stage_matches AS (
    SELECT 
        match_id,
        match_number,
        CASE 
            WHEN group_name IN ('A', 'B', 'C', 'D') THEN 'Group Stage'
            WHEN group_name IN ('1', '2') THEN 'Super 8'
            ELSE COALESCE(stage, 'Knockout')
        END AS stage_normalized,
        group_name,
        team1,
        team2,
        winner,
        outcome_type
    FROM dim_matches
    WHERE (CASE 
            WHEN group_name IN ('A', 'B', 'C', 'D') THEN 'Group Stage'
            WHEN group_name IN ('1', '2') THEN 'Super 8'
            ELSE COALESCE(stage, 'Knockout')
          END) = 'Group Stage'
      AND group_name IN ('A', 'B', 'C', 'D')
),
team_outcomes AS (
    SELECT 
        sm.group_name,
        t.team_name,
        COUNT(sm.match_id) AS played,
        COUNT(CASE WHEN sm.winner = t.team_name THEN 1 END) AS wins,
        COUNT(CASE WHEN sm.winner <> t.team_name AND sm.outcome_type <> 'no result' THEN 1 END) AS losses,
        COUNT(CASE WHEN sm.outcome_type = 'no result' THEN 1 END) AS no_results,
        SUM(CASE 
            WHEN sm.winner = t.team_name THEN 2 
            WHEN sm.outcome_type = 'no result' THEN 1 
            ELSE 0 
        END) AS points
    FROM dim_teams t
    JOIN stage_matches sm ON t.team_name = sm.team1 OR t.team_name = sm.team2
    GROUP BY sm.group_name, t.team_name
),
team_batting AS (
    SELECT 
        sm.group_name,
        s.batting_team AS team_name,
        SUM(s.total_runs) AS runs_scored,
        -- ICC Clause 16.10.7: All-out before 20 overs gets full quota of 120 balls
        SUM(CASE WHEN s.total_wickets = 10 THEN 120 ELSE s.legal_deliveries END) AS balls_faced
    FROM fact_match_summaries s
    JOIN stage_matches sm ON s.match_id = sm.match_id
    WHERE s.is_super_over = FALSE
    GROUP BY sm.group_name, s.batting_team
),
team_bowling AS (
    SELECT 
        sm.group_name,
        s.bowling_team AS team_name,
        SUM(s.total_runs) AS runs_conceded,
        -- Phase 4.8 Rule: Actual legal deliveries bowled by the opponent
        SUM(s.legal_deliveries) AS balls_bowled
    FROM fact_match_summaries s
    JOIN stage_matches sm ON s.match_id = sm.match_id
    WHERE s.is_super_over = FALSE
    GROUP BY sm.group_name, s.bowling_team
)
SELECT 
    o.group_name,
    o.team_name,
    o.played,
    o.wins,
    o.losses,
    o.no_results,
    o.points,
    b.runs_scored,
    b.balls_faced,
    ROUND(b.balls_faced / 6.0, 3) AS overs_faced,
    ROUND(b.runs_scored / (b.balls_faced / 6.0), 3) AS run_rate_for,
    w.runs_conceded,
    w.balls_bowled,
    ROUND(w.balls_bowled / 6.0, 3) AS overs_bowled,
    ROUND(w.runs_conceded / (w.balls_bowled / 6.0), 3) AS run_rate_against,
    ROUND((b.runs_scored / (b.balls_faced / 6.0)) - (w.runs_conceded / (w.balls_bowled / 6.0)), 3) AS nrr
FROM team_outcomes o
JOIN team_batting b ON o.group_name = b.group_name AND o.team_name = b.team_name
JOIN team_bowling w ON o.group_name = w.group_name AND o.team_name = w.team_name
-- Enforce ICC Clause 16.10.4: Points -> Wins -> Net Run Rate
ORDER BY o.group_name, o.points DESC, o.wins DESC, nrr DESC;
```

### 3.2 Super 8 Stage SQL Query (Clause 16.10.4 Compliant)
```sql
WITH stage_matches AS (
    SELECT 
        match_id,
        match_number,
        CASE 
            WHEN group_name IN ('A', 'B', 'C', 'D') THEN 'Group Stage'
            WHEN group_name IN ('1', '2') THEN 'Super 8'
            ELSE COALESCE(stage, 'Knockout')
        END AS stage_normalized,
        group_name,
        team1,
        team2,
        winner,
        outcome_type
    FROM dim_matches
    WHERE (CASE 
            WHEN group_name IN ('A', 'B', 'C', 'D') THEN 'Group Stage'
            WHEN group_name IN ('1', '2') THEN 'Super 8'
            ELSE COALESCE(stage, 'Knockout')
          END) = 'Super 8'
      AND group_name IN ('1', '2')
),
team_outcomes AS (
    SELECT 
        sm.group_name,
        t.team_name,
        COUNT(sm.match_id) AS played,
        COUNT(CASE WHEN sm.winner = t.team_name THEN 1 END) AS wins,
        COUNT(CASE WHEN sm.winner <> t.team_name AND sm.outcome_type <> 'no result' THEN 1 END) AS losses,
        COUNT(CASE WHEN sm.outcome_type = 'no result' THEN 1 END) AS no_results,
        SUM(CASE 
            WHEN sm.winner = t.team_name THEN 2 
            WHEN sm.outcome_type = 'no result' THEN 1 
            ELSE 0 
        END) AS points
    FROM dim_teams t
    JOIN stage_matches sm ON t.team_name = sm.team1 OR t.team_name = sm.team2
    GROUP BY sm.group_name, t.team_name
),
team_batting AS (
    SELECT 
        sm.group_name,
        s.batting_team AS team_name,
        SUM(s.total_runs) AS runs_scored,
        SUM(CASE WHEN s.total_wickets = 10 THEN 120 ELSE s.legal_deliveries END) AS balls_faced
    FROM fact_match_summaries s
    JOIN stage_matches sm ON s.match_id = sm.match_id
    WHERE s.is_super_over = FALSE
    GROUP BY sm.group_name, s.batting_team
),
team_bowling AS (
    SELECT 
        sm.group_name,
        s.bowling_team AS team_name,
        SUM(s.total_runs) AS runs_conceded,
        SUM(s.legal_deliveries) AS balls_bowled
    FROM fact_match_summaries s
    JOIN stage_matches sm ON s.match_id = sm.match_id
    WHERE s.is_super_over = FALSE
    GROUP BY sm.group_name, s.bowling_team
)
SELECT 
    o.group_name,
    o.team_name,
    o.played,
    o.wins,
    o.losses,
    o.no_results,
    o.points,
    b.runs_scored,
    b.balls_faced,
    ROUND(b.balls_faced / 6.0, 3) AS overs_faced,
    ROUND(b.runs_scored / (b.balls_faced / 6.0), 3) AS run_rate_for,
    w.runs_conceded,
    w.balls_bowled,
    ROUND(w.balls_bowled / 6.0, 3) AS overs_bowled,
    ROUND(w.runs_conceded / (w.balls_bowled / 6.0), 3) AS run_rate_against,
    ROUND((b.runs_scored / (b.balls_faced / 6.0)) - (w.runs_conceded / (w.balls_bowled / 6.0)), 3) AS nrr
FROM team_outcomes o
JOIN team_batting b ON o.group_name = b.group_name AND o.team_name = b.team_name
JOIN team_bowling w ON o.group_name = w.group_name AND o.team_name = w.team_name
-- Enforce ICC Clause 16.10.4: Points -> Wins -> Net Run Rate
ORDER BY o.group_name, o.points DESC, o.wins DESC, nrr DESC;
```

---

## 4. Equal-Points Scenarios Audit Across All 6 Groups

An automated inspection of all 6 pools revealed the following:

### 4.1 Group Stage Pools
- **Group A**:
  - Points distribution: India (8), Pakistan (6), USA (4), Netherlands (2), Namibia (0).
  - Equal-points ties: **None**.
- **Group B**:
  - Points distribution: Zimbabwe (7), Sri Lanka (6), Australia (4), Ireland (3), Oman (0).
  - Equal-points ties: **None**.
- **Group C (Equal-Points Scenario)**:
  - Points distribution: West Indies (8), England (6), Scotland (2), Italy (2), Nepal (2).
  - Tied teams: **Scotland, Italy, Nepal** (all tied on 2 points).
  - *Clause 16.10.4 Evaluation*:
    - **Step 1 (Wins)**: Scotland = 1 win; Italy = 1 win; Nepal = 1 win. (Equal wins, advances to Step 2).
    - **Step 2 (Net Run Rate)**:
      - Scotland NRR: **-0.187** (Runs For 676 in 80.0 ov; Runs Against 642 in 74.333 ov)
      - Italy NRR: **-0.705** (Runs For 559 in 69.333 ov; Runs Against 697 in 79.500 ov)
      - Nepal NRR: **-1.349** (Runs For 607 in 79.333 ov; Runs Against 612 in 68.000 ov)
      - Result: **Scotland (-0.187) > Italy (-0.705) > Nepal (-1.349)**.
    - *Resolution*: Tie broken definitively at Step 2 by Net Run Rate. Head-to-head (Step 3) is not reached.
    - *Final Ranks*: 3rd Scotland, 4th Italy, 5th Nepal.
- **Group D**:
  - Points distribution: South Africa (8), New Zealand (6), Afghanistan (4), UAE (2), Canada (0).
  - Equal-points ties: **None**.

### 4.2 Super 8 Stage Pools
- **Super 8 Group 1**:
  - Points distribution: South Africa (6), India (4), West Indies (2), Zimbabwe (0).
  - Equal-points ties: **None**.
- **Super 8 Group 2 (Equal-Points Scenario)**:
  - Points distribution: England (6), New Zealand (3), Pakistan (3), Sri Lanka (0).
  - Tied teams: **New Zealand, Pakistan** (both tied on 3 points).
  - *Clause 16.10.4 Evaluation*:
    - **Step 1 (Wins)**: New Zealand = 1 win; Pakistan = 1 win. (Equal wins, advances to Step 2).
    - **Step 2 (Net Run Rate)**:
      - New Zealand NRR: **+1.390** (Runs For 327 in 40.0 ov; Runs Against 268 in 39.5 ov)
      - Pakistan NRR: **-0.123** (Runs For 376 in 40.0 ov; Runs Against 373 in 39.167 ov)
      - Result: **New Zealand (+1.390) > Pakistan (-0.123)**.
    - *Resolution*: Tie broken definitively at Step 2 by Net Run Rate. Head-to-head (Step 3) is not reached.
    - *Final Ranks*: 2nd New Zealand (Advances to Semifinals), 3rd Pakistan (Eliminated).

---

## 5. Comparative Standings Matrix (Clause 16.10.4 Compliant)

### 5.1 Group Stage

| Grp | Team | P | W | L | NR | Pts | Wins Sort | NRR | Step Resolved | Final Rank | Qualification Status |
| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :---: | :-: | :--- |
| **A** | India | 4 | 4 | 0 | 0 | **8** | 4 | +2.177 | Points | **1st** | **Qualified (Super 8)** |
| **A** | Pakistan | 4 | 3 | 1 | 0 | **6** | 3 | +0.727 | Points | **2nd** | **Qualified (Super 8)** |
| A | USA | 4 | 2 | 2 | 0 | 4 | 2 | +0.360 | Points | 3rd | Eliminated |
| A | Netherlands | 4 | 1 | 3 | 0 | 2 | 1 | -1.217 | Points | 4th | Eliminated |
| A | Namibia | 4 | 0 | 4 | 0 | 0 | 0 | -3.108 | Points | 5th | Eliminated |
| **B** | Zimbabwe | 4 | 3 | 0 | 1 | **7** | 3 | +1.426 | Points | **1st** | **Qualified (Super 8)** |
| **B** | Sri Lanka | 4 | 3 | 1 | 0 | **6** | 3 | +1.725 | Points | **2nd** | **Qualified (Super 8)** |
| B | Australia | 4 | 2 | 2 | 0 | 4 | 2 | +0.819 | Points | 3rd | Eliminated |
| B | Ireland | 4 | 1 | 2 | 1 | 3 | 1 | -0.128 | Points | 4th | Eliminated |
| B | Oman | 4 | 0 | 4 | 0 | 0 | 0 | -4.845 | Points | 5th | Eliminated |
| **C** | West Indies | 4 | 4 | 0 | 0 | **8** | 4 | +1.483 | Points | **1st** | **Qualified (Super 8)** |
| **C** | England | 4 | 3 | 1 | 0 | **6** | 3 | +0.164 | Points | **2nd** | **Qualified (Super 8)** |
| C | Scotland | 4 | 1 | 3 | 0 | 2 | 1 | **-0.187** | **Step 2 (NRR)** | 3rd | Eliminated |
| C | Italy | 4 | 1 | 3 | 0 | 2 | 1 | **-0.705** | **Step 2 (NRR)** | 4th | Eliminated |
| C | Nepal | 4 | 1 | 3 | 0 | 2 | 1 | **-1.349** | **Step 2 (NRR)** | 5th | Eliminated |
| **D** | South Africa | 4 | 4 | 0 | 0 | **8** | 4 | +1.910 | Points | **1st** | **Qualified (Super 8)** |
| **D** | New Zealand | 4 | 3 | 1 | 0 | **6** | 3 | +1.227 | Points | **2nd** | **Qualified (Super 8)** |
| D | Afghanistan | 4 | 2 | 2 | 0 | 4 | 2 | +0.889 | Points | 3rd | Eliminated |
| D | UAE | 4 | 1 | 3 | 0 | 2 | 1 | -1.364 | Points | 4th | Eliminated |
| D | Canada | 4 | 0 | 4 | 0 | 0 | 0 | -2.426 | Points | 5th | Eliminated |

### 5.2 Super 8 Stage

| Grp | Team | P | W | L | NR | Pts | Wins Sort | NRR | Step Resolved | Final Rank | Qualification Status |
| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :---: | :-: | :--- |
| **1** | South Africa | 3 | 3 | 0 | 0 | **6** | 3 | +2.114 | Points | **1st** | **Qualified (Semifinals)** |
| **1** | India | 3 | 2 | 1 | 0 | **4** | 2 | +0.106 | Points | **2nd** | **Qualified (Semifinals)** |
| 1 | West Indies | 3 | 1 | 2 | 0 | 2 | 1 | +0.580 | Points | 3rd | Eliminated |
| 1 | Zimbabwe | 3 | 0 | 3 | 0 | 0 | 0 | -3.415 | Points | 4th | Eliminated |
| **2** | England | 3 | 3 | 0 | 0 | **6** | 3 | +0.686 | Points | **1st** | **Qualified (Semifinals)** |
| **2** | New Zealand | 3 | 1 | 1 | 1 | **3** | 1 | **+1.390** | **Step 2 (NRR)** | **2nd** | **Qualified (Semifinals)** |
| 2 | Pakistan | 3 | 1 | 1 | 1 | 3 | 1 | **-0.123** | **Step 2 (NRR)** | 3rd | Eliminated |
| 2 | Sri Lanka | 3 | 0 | 3 | 0 | 0 | 0 | -1.950 | Points | 4th | Eliminated |

---

## 6. Safety, Backup & Non-Destructive Compliance

1. **Zero Database Modifications**: All queries executed in read-only mode against PostgreSQL 18.7.
2. **Zero CSV / SQLite Modifications**: Raw source datasets remain untouched.
3. **No Unrelated DAX Changes**: Semantic model measures remain stable; no unrelated measures modified.
4. **Preserved Backups**: Artifact backups remain archived in `scratch/backups/phase4_9/`.
5. **Execution Layer Demarcation**:
   - SQL standings logic is verified directly in PostgreSQL 18.7.
   - Power BI DAX execution and visual rendering remain pending user verification in Power BI Desktop GUI.

---

## 7. Release Gate Verdict

| Phase | Milestone | Scope | Result | Verdict |
| :---: | :--- | :--- | :---: | :---: |
| **Phase 4.9.1** | Official ICC Clause 16.10.4 Tie-Break Audit | SQL Logic, Equal-Points Analysis, Qualification Verification | **100% Validated in SQL & Python** | **CONDITIONALLY APPROVED**<br>*(Pending user verification in Power BI Desktop GUI)* |

