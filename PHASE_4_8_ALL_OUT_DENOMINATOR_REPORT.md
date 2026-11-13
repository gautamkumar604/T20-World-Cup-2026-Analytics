# Phase 4.8 — Critical ICC NRR All-Out Denominator Audit & Standings Verification

**Project**: ICC Men's T20 World Cup 2026 Analytics  
**Document**: Technical Audit Report & Release Gate  
**Phase**: Phase 4.8 (NRR All-Out Denominator Audit)  
**Date**: November 14, 2026  
**Status / Final Verdict**: **CONDITIONALLY APPROVED** *(Pending user review and Power BI Desktop GUI rendering validation)*

---

## 1. Executive Summary

Phase 4.8 was commissioned to investigate a critical defect in the Net Run Rate (NRR) denominator calculations identified in Phase 4.7. Specifically, previous implementations symmetrically inflated deliveries to the full 120-ball quota for **both** the dismissed batting team and the opposing bowling team.

Under the definitive ICC tournament playing conditions (Clause 16.10.7):
1. **Batting Team All-Out**: When a team is bowled out (loses all 10 wickets) in fewer than 20 overs, its balls-faced denominator is adjusted to the full quota (**120 legal balls / 20.0 overs**).
2. **Opposing Bowling Team**: The opposing bowling team's balls-bowled denominator must reflect the **actual legal deliveries bowled** in that innings. The opponent's bowling denominator must **never** be artificially inflated to 120 balls.

### Key Audit Findings
- **Edge-Case Validation**: All 5 mandatory test cases (Cases A through E) successfully passed.
- **Tournament In-Scope Inning Census**: Exactly **21 innings** across the 53 completed tournament matches featured an all-out dismissal in fewer than 120 balls (17 in Group Stage, 3 in Super 8, 1 in the Final).
- **Standings & Qualification Impact**: Recalculating NRR using the corrected asymmetric all-out rule changed the NRR values for several teams (e.g., Australia in Group B from +1.523 to +0.819; India in Group A from +2.500 to +2.177; South Africa in Super 8 from +2.259 to +2.114). However, **zero team rankings, points, or qualification outcomes were altered**. The qualified teams for the Super 8 and Semifinals remain 100% identical.
- **Artifacts Updated**: `power_bi/dax_measures.dax`, `power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim`, and `power_bi/T20_World_Cup_2026_Analytics.pbit` have been updated and verified.
- **Safety Compliance**: Zero writes to PostgreSQL 18.7, zero modifications to source CSV/SQLite data, and zero premature dashboard development on Pages 2–5.

---

## 2. Denominator Audit: Symmetrical vs Asymmetrical Rules

### 2.1 The Defect Identified in Phase 4.7
In Phase 4.7, the DAX measure `[Team Balls Bowled (ICC NRR)]` was formulated as:
```dax
// INCORRECT (Phase 4.7 Symmetrical Application):
Team Balls Bowled (ICC NRR) = 
CALCULATE(
    SUMX(
        fact_match_summaries,
        IF(fact_match_summaries[total_wickets] = 10, 120, fact_match_summaries[legal_deliveries])
    ),
    TREATAS(VALUES(dim_teams[team_name]), fact_match_summaries[bowling_team]),
    fact_match_summaries[is_super_over] = FALSE()
)
```
This formula replaced the opponent's balls bowled with 120 whenever the batting side was dismissed for 10 wickets.

### 2.2 The Regulatory Requirement (ICC Clause 16.10.7)
Clause 16.10.7 of the official ICC Playing Conditions states:
> *"In the event of a team being all out in less than its full quota of overs, the calculation of its net run rate shall be based on the full quota of overs to which it would have been entitled and not on the number of overs in which the team was dismissed."*

The grammatical antecedent of *"its net run rate"* and *"it would have been entitled"* is strictly the **dismissed batting team**. The rule penalizes a batting collapse by denying the dismissed team an artificially elevated run rate denominator. Conversely, the bowling side bowled fewer deliveries to dismiss the opposition; crediting the bowling side with 20.0 overs would artificially deflate its bowling run rate ($Runs / Overs$), giving it an unjustified penalty or distortion.

### 2.3 The Corrected Formulation (Phase 4.8 Asymmetrical Rule)
$$\text{Team Balls Faced (ICC NRR)} = \sum_{\text{batting innings}} \left( \text{total\_wickets} = 10 \;\; ? \;\; 120 \;\; : \;\; \text{legal\_deliveries} \right)$$

$$\text{Team Balls Bowled (ICC NRR)} = \sum_{\text{bowling innings}} \text{legal\_deliveries}$$

$$\text{Net Run Rate (ICC)} = \left( \frac{\text{Selected Team Runs Scored}}{\text{Team Balls Faced} / 6.0} \right) - \left( \frac{\text{Selected Team Opponent Runs}}{\text{Team Balls Bowled} / 6.0} \right)$$

---

## 3. Edge-Case Test Suite Results

The 5 edge-case scenarios required by the Phase 4.8 specification were evaluated using automated unit test logic:

| Test Case | Scenario Description | Innings Parameters | Batting Balls Faced (NRR) | Bowling Balls Bowled (NRR) | Result / Status |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Case A** | Batting team all out in 92 balls in a 20-over match | 110 runs, 10 wkts, 92 legal balls | **120** (20.0 ov) | **92** (15.333 ov) | **PASSED** |
| **Case B** | Batting team all out in 105 balls in a 20-over match | 130 runs, 10 wkts, 105 legal balls | **120** (20.0 ov) | **105** (17.500 ov) | **PASSED** |
| **Case C** | Completed 20-over innings with 7 wickets down | 165 runs, 7 wkts, 120 legal balls | **120** (20.0 ov) | **120** (20.0 ov) | **PASSED** |
| **Case D** | Successful chase in 95 balls with 4 wickets down (not all out) | 140 runs, 4 wkts, 95 legal balls | **95** (15.833 ov) | **95** (15.833 ov) | **PASSED** |
| **Case E** | Super Over innings (`is_super_over = TRUE`) | 15 runs, 1 wkt, 6 legal balls | **0** (Excluded) | **0** (Excluded) | **PASSED** |

**Summary**: 5 of 5 tests passed.

---

## 4. Tournament Data Audit: 21 All-Out Innings (< 120 Balls)

PostgreSQL query inspection of `fact_match_summaries` and `dim_matches` reveals exactly **21 innings** where `total_wickets = 10` and `legal_deliveries < 120`:

| Match ID | Match # | Stage / Group | Inn | Batting Team (All Out) | Bowling Team | Runs | Balls | Overs | Prev Bowling Balls | Corr Bowling Balls |
| :--- | :---: | :---: | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `M_2026_01` | 1 | Group A | 1 | Netherlands | Pakistan | 147 | 119 | 19.5 | 120 | **119** |
| `M_2026_02` | 2 | Group C | 2 | Scotland | West Indies | 147 | 113 | 18.5 | 120 | **113** |
| `M_2026_06` | 6 | Group B | 2 | Ireland | Sri Lanka | 143 | 119 | 19.5 | 120 | **119** |
| `M_2026_08` | 8 | Group B | 1 | Oman | Zimbabwe | 103 | 119 | 19.5 | 120 | **119** |
| `M_2026_13` | 13 | Group D | 2 | Afghanistan | South Africa | 187 | 118 | 19.4 | 120 | **118** |
| `M_2026_14` | 14 | Group B | 2 | Ireland | Australia | 115 | 101 | 16.5 | 120 | **101** |
| `M_2026_15` | 15 | Group C | 2 | England | West Indies | 166 | 114 | 19.0 | 120 | **114** |
| `M_2026_17` | 17 | Group C | 1 | Nepal | Italy | 123 | 117 | 19.3 | 120 | **117** |
| `M_2026_18` | 18 | Group A | 2 | Namibia | India | 116 | 110 | 18.2 | 120 | **110** |
| `M_2026_19` | 19 | Group B | 2 | Australia | Zimbabwe | 146 | 117 | 19.3 | 120 | **117** |
| `M_2026_21` | 21 | Group A | 2 | Netherlands | USA | 103 | 95 | 15.5 | 120 | **95** |
| `M_2026_22` | 22 | Group B | 2 | Oman | Ireland | 139 | 108 | 18.0 | 120 | **108** |
| `M_2026_23` | 23 | Group C | 1 | Scotland | England | 152 | 118 | 19.4 | 120 | **118** |
| `M_2026_27` | 27 | Group A | 2 | Pakistan | India | 114 | 108 | 18.0 | 120 | **108** |
| `M_2026_35` | 35 | Group A | 2 | Namibia | Pakistan | 97 | 105 | 17.3 | 120 | **105** |
| `M_2026_37` | 37 | Group C | 2 | Italy | West Indies | 123 | 108 | 18.0 | 120 | **108** |
| `M_2026_40` | 40 | Group B | 1 | Oman | Australia | 104 | 98 | 16.2 | 120 | **98** |
| `M_2026_42` | 42 | Super 8 G2 | 2 | Sri Lanka | England | 95 | 100 | 16.4 | 120 | **100** |
| `M_2026_43` | 43 | Super 8 G1 | 2 | India | South Africa | 111 | 113 | 18.5 | 120 | **113** |
| `M_2026_44` | 44 | Super 8 G1 | 2 | Zimbabwe | West Indies | 147 | 106 | 17.4 | 120 | **106** |
| `M_2026_55` | Final | Knockout | 2 | New Zealand | India | 159 | 114 | 19.0 | 120 | **114** |

---

## 5. Standings & Net Run Rate Recalculation

All 20 teams across the 4 Group Stage pools and 8 teams across the 2 Super 8 pools were evaluated.

### 5.1 Group Stage Standings

#### Group A
| Rk | Team | P | W | L | NR | Pts | Runs For | Ov For | Runs Ag | Ov Ag (Corr) | Corrected NRR | Prev NRR | NRR Diff | Rank Status |
| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **1** | **India** | 4 | 4 | 0 | 0 | **8** | 738 | 80.000 | 538 | 76.333 | **+2.177** | +2.500 | -0.323 | Unchanged |
| **2** | **Pakistan** | 4 | 3 | 1 | 0 | **6** | 651 | 79.500 | 577 | 77.333 | **+0.727** | +0.976 | -0.249 | Unchanged |
| 3 | United States of America | 4 | 2 | 2 | 0 | 4 | 685 | 80.000 | 622 | 75.833 | **+0.360** | +0.787 | -0.427 | Unchanged |
| 4 | Netherlands | 4 | 1 | 3 | 0 | 2 | 585 | 78.000 | 693 | 79.500 | **-1.217** | -1.217 | 0.000 | Unchanged |
| 5 | Namibia | 4 | 0 | 4 | 0 | 0 | 537 | 80.000 | 766 | 78.000 | **-3.108** | -3.108 | 0.000 | Unchanged |

*Qualification: India & Pakistan advance to Super 8.*

#### Group B
| Rk | Team | P | W | L | NR | Pts | Runs For | Ov For | Runs Ag | Ov Ag (Corr) | Corrected NRR | Prev NRR | NRR Diff | Rank Status |
| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **1** | **Zimbabwe** | 4 | 3 | 0 | 1 | **7** | 457 | 53.000 | 427 | 59.333 | **+1.426** | +1.506 | -0.080 | Unchanged |
| **2** | **Sri Lanka** | 4 | 3 | 1 | 0 | **6** | 750 | 78.000 | 626 | 79.333 | **+1.725** | +1.741 | -0.017 | Unchanged |
| 3 | Australia | 4 | 2 | 2 | 0 | 4 | 617 | 69.667 | 572 | 71.167 | **+0.819** | +1.523 | -0.704 | Unchanged |
| 4 | Ireland | 4 | 1 | 2 | 1 | 3 | 493 | 60.000 | 484 | 58.000 | **-0.128** | +0.150 | -0.278 | Unchanged |
| 5 | Oman | 4 | 0 | 4 | 0 | 0 | 466 | 80.000 | 674 | 63.167 | **-4.845** | -4.845 | 0.000 | Unchanged |

*Qualification: Zimbabwe & Sri Lanka advance to Super 8. Australia eliminated.*

#### Group C
| Rk | Team | P | W | L | NR | Pts | Runs For | Ov For | Runs Ag | Ov Ag (Corr) | Corrected NRR | Prev NRR | NRR Diff | Rank Status |
| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **1** | **West Indies** | 4 | 4 | 0 | 0 | **8** | 677 | 75.333 | 569 | 75.833 | **+1.483** | +1.874 | -0.391 | Unchanged |
| **2** | **England** | 4 | 3 | 1 | 0 | **6** | 707 | 78.333 | 706 | 79.667 | **+0.164** | +0.201 | -0.037 | Unchanged |
| 3 | Scotland | 4 | 1 | 3 | 0 | 2 | 676 | 80.000 | 642 | 74.333 | **-0.187** | -0.187 | 0.000 | Unchanged |
| 4 | Italy | 4 | 1 | 3 | 0 | 2 | 559 | 69.333 | 697 | 79.500 | **-0.705** | -0.650 | -0.055 | Unchanged |
| 5 | Nepal | 4 | 1 | 3 | 0 | 2 | 607 | 79.333 | 612 | 68.000 | **-1.349** | -1.349 | 0.000 | Unchanged |

*Qualification: West Indies & England advance to Super 8.*

#### Group D
| Rk | Team | P | W | L | NR | Pts | Runs For | Ov For | Runs Ag | Ov Ag (Corr) | Corrected NRR | Prev NRR | NRR Diff | Rank Status |
| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **1** | **South Africa** | 4 | 4 | 0 | 0 | **8** | 701 | 70.500 | 640 | 79.667 | **+1.910** | +1.943 | -0.033 | Unchanged |
| **2** | **New Zealand** | 4 | 3 | 1 | 0 | **6** | 709 | 68.333 | 706 | 77.167 | **+1.227** | +1.227 | 0.000 | Unchanged |
| 3 | Afghanistan | 4 | 2 | 2 | 0 | 4 | 731 | 79.333 | 648 | 77.833 | **+0.889** | +0.889 | 0.000 | Unchanged |
| 4 | United Arab Emirates | 4 | 1 | 3 | 0 | 2 | 606 | 79.667 | 610 | 68.000 | **-1.364** | -1.364 | 0.000 | Unchanged |
| 5 | Canada | 4 | 0 | 4 | 0 | 0 | 597 | 80.000 | 740 | 74.833 | **-2.426** | -2.426 | 0.000 | Unchanged |

*Qualification: South Africa & New Zealand advance to Super 8.*

---

### 5.2 Super 8 Stage Standings

#### Super 8 Group 1
| Rk | Team | P | W | L | NR | Pts | Runs For | Ov For | Runs Ag | Ov Ag (Corr) | Corrected NRR | Prev NRR | NRR Diff | Rank Status |
| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **1** | **South Africa** | 3 | 3 | 0 | 0 | **6** | 518 | 54.000 | 440 | 58.833 | **+2.114** | +2.259 | -0.145 | Unchanged |
| **2** | **India** | 3 | 2 | 1 | 0 | **4** | 566 | 59.333 | 566 | 60.000 | **+0.106** | +0.106 | 0.000 | Unchanged |
| 3 | West Indies | 3 | 1 | 2 | 0 | 2 | 625 | 60.000 | 523 | 53.167 | **+0.580** | +0.993 | -0.414 | Unchanged |
| 4 | Zimbabwe | 3 | 0 | 3 | 0 | 0 | 484 | 60.000 | 664 | 57.833 | **-3.415** | -3.415 | 0.000 | Unchanged |

*Qualification: South Africa & India advance to Semifinals.*

#### Super 8 Group 2
| Rk | Team | P | W | L | NR | Pts | Runs For | Ov For | Runs Ag | Ov Ag (Corr) | Corrected NRR | Prev NRR | NRR Diff | Rank Status |
| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **1** | **England** | 3 | 3 | 0 | 0 | **6** | 473 | 58.667 | 418 | 56.667 | **+0.686** | +1.096 | -0.410 | Unchanged |
| **2** | **New Zealand** | 3 | 1 | 1 | 1 | **3** | 327 | 40.000 | 268 | 39.500 | **+1.390** | +1.390 | 0.000 | Unchanged |
| 3 | Pakistan | 3 | 1 | 1 | 1 | 3 | 376 | 40.000 | 373 | 39.167 | **-0.123** | -0.123 | 0.000 | Unchanged |
| 4 | Sri Lanka | 3 | 0 | 3 | 0 | 0 | 409 | 60.000 | 526 | 60.000 | **-1.950** | -1.950 | 0.000 | Unchanged |

*Qualification: England (6 pts) & New Zealand (3 pts, NRR +1.390) advance to Semifinals. Pakistan (3 pts, NRR -0.123) eliminated.*

---

## 6. Power BI Semantic Model & DAX Implementation

### 6.1 Updated DAX Measure Definitions
The three core NRR measures in `power_bi/dax_measures.dax` and `power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim` are confirmed as follows:

```dax
// Measure: Team Balls Faced (ICC NRR)
// Description: Legal balls faced with ICC 120-ball all-out rule applied
Team Balls Faced (ICC NRR) = 
CALCULATE(
    SUMX(
        fact_match_summaries,
        IF(fact_match_summaries[total_wickets] = 10, 120, fact_match_summaries[legal_deliveries])
    ),
    TREATAS(VALUES(dim_teams[team_name]), fact_match_summaries[batting_team]),
    fact_match_summaries[is_super_over] = FALSE()
)

// Measure: Team Balls Bowled (ICC NRR)
// Description: Actual legal deliveries bowled by the team (ICC Clause 16.10.7: all-out full quota adjustment applies strictly to batting team balls faced)
Team Balls Bowled (ICC NRR) = 
CALCULATE(
    SUM(fact_match_summaries[legal_deliveries]),
    TREATAS(VALUES(dim_teams[team_name]), fact_match_summaries[bowling_team]),
    fact_match_summaries[is_super_over] = FALSE()
)

// Measure: Net Run Rate (ICC)
// Description: Official ICC Net Run Rate (Run Rate For minus Run Rate Against)
Net Run Rate (ICC) = 
VAR RunsFor = [Selected Team Runs Scored]
VAR BallsFor = [Team Balls Faced (ICC NRR)]
VAR OversFor = DIVIDE(BallsFor, 6, 0)
VAR RunsAgainst = [Selected Team Opponent Runs]
VAR BallsAgainst = [Team Balls Bowled (ICC NRR)]
VAR OversAgainst = DIVIDE(BallsAgainst, 6, 0)
RETURN
    IF(
        OversFor > 0 && OversAgainst > 0,
        DIVIDE(RunsFor, OversFor, 0) - DIVIDE(RunsAgainst, OversAgainst, 0),
        BLANK()
    )
```

### 6.2 SQL Verification Baseline (PostgreSQL 18.7 CTE)
The exact SQL logic to calculate standings and NRR natively in PostgreSQL:

```sql
WITH stage_batting AS (
    SELECT 
        m.group_name,
        s.batting_team AS team_name,
        SUM(s.total_runs) AS runs_scored,
        SUM(CASE WHEN s.total_wickets = 10 THEN 120 ELSE s.legal_deliveries END) AS balls_faced
    FROM fact_match_summaries s
    JOIN dim_matches m ON s.match_id = m.match_id
    WHERE s.is_super_over = FALSE 
      AND m.group_name IN ('A', 'B', 'C', 'D')
    GROUP BY m.group_name, s.batting_team
),
stage_bowling AS (
    SELECT 
        m.group_name,
        s.bowling_team AS team_name,
        SUM(s.total_runs) AS runs_conceded,
        SUM(s.legal_deliveries) AS balls_bowled
    FROM fact_match_summaries s
    JOIN dim_matches m ON s.match_id = m.match_id
    WHERE s.is_super_over = FALSE 
      AND m.group_name IN ('A', 'B', 'C', 'D')
    GROUP BY m.group_name, s.bowling_team
)
SELECT 
    b.group_name,
    b.team_name,
    b.runs_scored,
    ROUND(b.balls_faced / 6.0, 3) AS overs_faced_dec,
    ROUND(b.runs_scored / (b.balls_faced / 6.0), 3) AS run_rate_for,
    w.runs_conceded,
    ROUND(w.balls_bowled / 6.0, 3) AS overs_bowled_dec,
    ROUND(w.runs_conceded / (w.balls_bowled / 6.0), 3) AS run_rate_against,
    ROUND((b.runs_scored / (b.balls_faced / 6.0)) - (w.runs_conceded / (w.balls_bowled / 6.0)), 3) AS net_run_rate
FROM stage_batting b
JOIN stage_bowling w ON b.group_name = w.group_name AND b.team_name = w.team_name
ORDER BY b.group_name, net_run_rate DESC;
```

---

## 7. Artifact Verification & Release Gate Status

### 7.1 Integrity Check of Modified Artifacts
1. `power_bi/dax_measures.dax`: 38 validated DAX measures; `Team Balls Bowled (ICC NRR)` updated to use `SUM(fact_match_summaries[legal_deliveries])`.
2. `power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim`: Structurally valid JSON; 9 tables; 13 relationships; zero ambiguous active paths.
3. `power_bi/T20_World_Cup_2026_Analytics.pbit`: Rebuilt package with updated `DataModelSchema` (66,076 bytes).
4. `scratch/test_phase4_8_nrr.py`: Unit test and regression suite passing 100%.

### 7.2 Release Gate Verdict
- **Status**: **CONDITIONALLY APPROVED**
- **Condition**: Pending user formal review and visual confirmation in Power BI Desktop GUI.
- **Strict Adherence**: Dashboard pages 2 through 5 remain untouched and await user authorization.

