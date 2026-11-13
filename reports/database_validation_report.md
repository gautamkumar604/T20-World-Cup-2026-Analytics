# PostgreSQL Relational Data Warehouse — Ingestion & Validation Report

**Database URL**: `postgresql+psycopg2://postgres:***@localhost:5432/t20_worldcup_2026`  
**Status**: `SUCCESS`  

---

## 1. Table Inventory & Record Parity Verification

| Table Name | Type | CSV Records | Database Records | Record Parity |
| :--- | :---: | :---: | :---: | :---: |
| `dim_teams` | Dimension | 20 | 20 | ✅ 100% Match |
| `dim_venues` | Dimension | 8 | 8 | ✅ 100% Match |
| `dim_players` | Dimension | 282 | 282 | ✅ 100% Match |
| `dim_matches` | Dimension | 55 | 55 | ✅ 100% Match |
| `fact_deliveries` | Fact | 11,555 | 11,555 | ✅ 100% Match |
| `fact_batting_scorecards` | Fact | 811 | 811 | ✅ 100% Match |
| `fact_bowling_scorecards` | Fact | 598 | 598 | ✅ 100% Match |
| `fact_match_summaries` | Fact | 106 | 106 | ✅ 100% Match |

**Total Warehouse Records Loaded**: **13,435**

---

## 2. Referential Integrity & Foreign Key Audit

| Foreign Key Relationship | Orphan Records | Audit Result |
| :--- | :---: | :---: |
| `dim_matches(team1, team2)` -> `dim_teams(team_name)` | 0 | ✅ Valid |
| `dim_matches(venue)` -> `dim_venues(venue_name)` | 0 | ✅ Valid |
| `fact_deliveries(match_id)` -> `dim_matches(match_id)` | 0 | ✅ Valid |
| `fact_batting_scorecards(match_id)` -> `dim_matches(match_id)` | 0 | ✅ Valid |
| `fact_bowling_scorecards(match_id)` -> `dim_matches(match_id)` | 0 | ✅ Valid |
| `fact_match_summaries(match_id)` -> `dim_matches(match_id)` | 0 | ✅ Valid |

---

## 3. Analytical Views Deployed (10 Views)

- ✅ `vw_batting_statistics`
- ✅ `vw_boundary_analysis`
- ✅ `vw_bowling_statistics`
- ✅ `vw_match_results`
- ✅ `vw_phase_wise_performance`
- ✅ `vw_team_performance`
- ✅ `vw_top_run_scorers`
- ✅ `vw_top_wicket_takers`
- ✅ `vw_toss_impact`
- ✅ `vw_venue_analysis`

