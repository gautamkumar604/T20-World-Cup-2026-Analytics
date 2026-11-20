import re

with open('sql/analytics/view_tournament_standings_phase_4_9_6_15.sql', 'r') as f:
    sql = f.read()

# Update header comment
sql = sql.replace('Phase 4.9.6.15', 'Phase 4.9.6.16')
sql = sql.replace('PHASE 4.9.6.15', 'PHASE 4.9.6.16')

# 1. stage_matches: add dls_allocated_overs_team1, dls_team1_innings_shortened
stage_matches_old = """        dls_abandonment_overs,
        dls_par_score,
        scorecard_available,"""

stage_matches_new = """        dls_abandonment_overs,
        dls_par_score,
        dls_allocated_overs_team1,
        dls_team1_innings_shortened,
        scorecard_available,"""
assert stage_matches_old in sql, "stage_matches replacement target not found"
sql = sql.replace(stage_matches_old, stage_matches_new, 1)

# 2. match_opponents: add to both branches
match_opp_branch1_old = """        m.dls_abandonment_overs,
        m.dls_par_score,
        m.scorecard_available,"""
# There are two branches in match_opponents
assert sql.count(match_opp_branch1_old) == 2, f"match_opponents branches count {sql.count(match_opp_branch1_old)} != 2"
match_opp_branch1_new = """        m.dls_abandonment_overs,
        m.dls_par_score,
        m.dls_allocated_overs_team1,
        m.dls_team1_innings_shortened,
        m.scorecard_available,"""
sql = sql.replace(match_opp_branch1_old, match_opp_branch1_new)

# 3. match_played_eval: update dls_status check for status 1
eval_old = """            WHEN mo.is_dls_abandoned = FALSE THEN
                CASE 
                    WHEN mo.target_runs IS NOT NULL AND mo.dls_allocated_overs IS NOT NULL 
                         AND mo.dls_allocated_overs > 0 
                         AND (mo.dls_allocated_overs - FLOOR(mo.dls_allocated_overs)) * 10 BETWEEN 0 AND 5 THEN 1
                    ELSE 3
                END"""

eval_new = """            WHEN mo.is_dls_abandoned = FALSE THEN
                CASE 
                    WHEN mo.target_runs IS NOT NULL 
                         AND mo.dls_allocated_overs IS NOT NULL 
                         AND mo.dls_allocated_overs > 0 
                         AND (mo.dls_allocated_overs - FLOOR(mo.dls_allocated_overs)) * 10 BETWEEN 0 AND 5
                         AND mo.dls_allocated_overs_team1 IS NOT NULL
                         AND mo.dls_allocated_overs_team1 > 0
                         AND (mo.dls_allocated_overs_team1 - FLOOR(mo.dls_allocated_overs_team1)) * 10 BETWEEN 0 AND 5 THEN 1
                    ELSE 3
                END"""
assert eval_old in sql, "match_played_eval replacement target not found"
sql = sql.replace(eval_old, eval_new, 1)

# 4. team_batting_aggregates
bat_runs_old = """                    WHEN mpe.dls_status = 1 AND s.innings = 1 THEN (CAST(mpe.target_runs AS NUMERIC) - 1)
                    WHEN mpe.dls_status = 2 AND s.innings = 1 THEN CAST(mpe.dls_par_score AS NUMERIC)"""

bat_runs_new = """                    WHEN mpe.dls_status = 1 AND s.innings = 1 THEN
                        CASE 
                            -- R1 / R3: If Team 1 was all-out OR batted full 20 overs allocation, use ACTUAL runs
                            WHEN s.total_wickets = 10 
                              OR (mpe.dls_allocated_overs_team1 = 20.0 AND s.legal_deliveries >= 120) 
                              THEN s.total_runs
                            -- R2: Team 1 innings shortened by rain (< 20.0 ov): use par score
                            WHEN mpe.dls_allocated_overs_team1 < 20.0 
                              THEN COALESCE(mpe.dls_par_score, mpe.target_runs - 1, mpe.target_runs)
                            ELSE s.total_runs
                        END
                    WHEN mpe.dls_status = 2 AND s.innings = 1 THEN CAST(mpe.dls_par_score AS NUMERIC)"""
assert bat_runs_old in sql, "bat_runs replacement target not found"
sql = sql.replace(bat_runs_old, bat_runs_new, 1)

bat_balls_old = """                    WHEN mpe.dls_status = 1 AND s.innings = 1 
                        THEN CASE
                            WHEN (mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10 BETWEEN 0 AND 5
                                THEN (FLOOR(mpe.dls_allocated_overs) * 6 + ROUND((mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10))::int
                            ELSE NULL
                        END"""

bat_balls_new = """                    WHEN mpe.dls_status = 1 AND s.innings = 1 THEN
                        CASE
                            WHEN s.total_wickets = 10 THEN
                                CASE
                                    WHEN (mpe.dls_allocated_overs_team1 - FLOOR(mpe.dls_allocated_overs_team1)) * 10 BETWEEN 0 AND 5
                                        THEN (FLOOR(mpe.dls_allocated_overs_team1) * 6 + ROUND((mpe.dls_allocated_overs_team1 - FLOOR(mpe.dls_allocated_overs_team1)) * 10))::int
                                    ELSE 120
                                END
                            WHEN mpe.dls_allocated_overs_team1 = 20.0 THEN 120
                            WHEN mpe.dls_allocated_overs_team1 < 20.0 THEN
                                CASE
                                    WHEN (mpe.dls_allocated_overs_team1 - FLOOR(mpe.dls_allocated_overs_team1)) * 10 BETWEEN 0 AND 5
                                        THEN (FLOOR(mpe.dls_allocated_overs_team1) * 6 + ROUND((mpe.dls_allocated_overs_team1 - FLOOR(mpe.dls_allocated_overs_team1)) * 10))::int
                                    ELSE NULL
                                END
                            ELSE s.legal_deliveries
                        END"""
assert bat_balls_old in sql, "bat_balls replacement target not found"
sql = sql.replace(bat_balls_old, bat_balls_new, 1)

# 5. team_bowling_aggregates
bowl_runs_old = """                    WHEN mpe.dls_status = 1 AND s.innings = 1 THEN (CAST(mpe.target_runs AS NUMERIC) - 1)
                    WHEN mpe.dls_status = 2 AND s.innings = 1 THEN CAST(mpe.dls_par_score AS NUMERIC)"""
assert bowl_runs_old in sql, "bowl_runs replacement target not found"
sql = sql.replace(bowl_runs_old, bat_runs_new, 1)

bowl_balls_old = """                    WHEN mpe.dls_status = 1 AND s.innings = 1 
                        THEN CASE
                            WHEN (mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10 BETWEEN 0 AND 5
                                THEN (FLOOR(mpe.dls_allocated_overs) * 6 + ROUND((mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10))::int
                            ELSE NULL
                        END"""
assert bowl_balls_old in sql, "bowl_balls replacement target not found"
sql = sql.replace(bowl_balls_old, bat_balls_new, 1)

# 6. h2h_matches: add dls_allocated_overs_team1, dls_team1_innings_shortened
h2h_matches_old = """        mpe.dls_abandonment_overs,
        mpe.dls_par_score,
        mpe.is_genuinely_played,"""
h2h_matches_new = """        mpe.dls_abandonment_overs,
        mpe.dls_par_score,
        mpe.dls_allocated_overs_team1,
        mpe.dls_team1_innings_shortened,
        mpe.is_genuinely_played,"""
assert h2h_matches_old in sql, "h2h_matches replacement target not found"
sql = sql.replace(h2h_matches_old, h2h_matches_new, 1)

# 7. h2h_batting
h2h_bat_runs_old = """                    WHEN hm.dls_status = 1 AND s.innings = 1 THEN (CAST(hm.target_runs AS NUMERIC) - 1)
                    WHEN hm.dls_status = 2 AND s.innings = 1 THEN CAST(hm.dls_par_score AS NUMERIC)"""
h2h_bat_runs_new = """                    WHEN hm.dls_status = 1 AND s.innings = 1 THEN
                        CASE 
                            -- R1 / R3: If Team 1 was all-out OR batted full 20 overs allocation, use ACTUAL runs
                            WHEN s.total_wickets = 10 
                              OR (hm.dls_allocated_overs_team1 = 20.0 AND s.legal_deliveries >= 120) 
                              THEN s.total_runs
                            -- R2: Team 1 innings shortened by rain (< 20.0 ov): use par score
                            WHEN hm.dls_allocated_overs_team1 < 20.0 
                              THEN COALESCE(hm.dls_par_score, hm.target_runs - 1, hm.target_runs)
                            ELSE s.total_runs
                        END
                    WHEN hm.dls_status = 2 AND s.innings = 1 THEN CAST(hm.dls_par_score AS NUMERIC)"""
assert h2h_bat_runs_old in sql, "h2h_bat_runs replacement target not found"
sql = sql.replace(h2h_bat_runs_old, h2h_bat_runs_new, 1)

h2h_bat_balls_old = """                    WHEN hm.dls_status = 1 AND s.innings = 1 
                        THEN CASE
                            WHEN (hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10 BETWEEN 0 AND 5
                                THEN (FLOOR(hm.dls_allocated_overs) * 6 + ROUND((hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10))::int
                            ELSE NULL
                        END"""
h2h_bat_balls_new = """                    WHEN hm.dls_status = 1 AND s.innings = 1 THEN
                        CASE
                            WHEN s.total_wickets = 10 THEN
                                CASE
                                    WHEN (hm.dls_allocated_overs_team1 - FLOOR(hm.dls_allocated_overs_team1)) * 10 BETWEEN 0 AND 5
                                        THEN (FLOOR(hm.dls_allocated_overs_team1) * 6 + ROUND((hm.dls_allocated_overs_team1 - FLOOR(hm.dls_allocated_overs_team1)) * 10))::int
                                    ELSE 120
                                END
                            WHEN hm.dls_allocated_overs_team1 = 20.0 THEN 120
                            WHEN hm.dls_allocated_overs_team1 < 20.0 THEN
                                CASE
                                    WHEN (hm.dls_allocated_overs_team1 - FLOOR(hm.dls_allocated_overs_team1)) * 10 BETWEEN 0 AND 5
                                        THEN (FLOOR(hm.dls_allocated_overs_team1) * 6 + ROUND((hm.dls_allocated_overs_team1 - FLOOR(hm.dls_allocated_overs_team1)) * 10))::int
                                    ELSE NULL
                                END
                            ELSE s.legal_deliveries
                        END"""
assert h2h_bat_balls_old in sql, "h2h_bat_balls replacement target not found"
sql = sql.replace(h2h_bat_balls_old, h2h_bat_balls_new, 1)

# 8. h2h_bowling
h2h_bowl_runs_old = """                    WHEN hm.dls_status = 1 AND s.innings = 1 THEN (CAST(hm.target_runs AS NUMERIC) - 1)
                    WHEN hm.dls_status = 2 AND s.innings = 1 THEN CAST(hm.dls_par_score AS NUMERIC)"""
assert h2h_bowl_runs_old in sql, "h2h_bowl_runs replacement target not found"
sql = sql.replace(h2h_bowl_runs_old, h2h_bat_runs_new, 1)

h2h_bowl_balls_old = """                    WHEN hm.dls_status = 1 AND s.innings = 1 
                        THEN CASE
                            WHEN (hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10 BETWEEN 0 AND 5
                                THEN (FLOOR(hm.dls_allocated_overs) * 6 + ROUND((hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10))::int
                            ELSE NULL
                        END"""
assert h2h_bowl_balls_old in sql, "h2h_bowl_balls replacement target not found"
sql = sql.replace(h2h_bowl_balls_old, h2h_bat_balls_new, 1)

with open('sql/analytics/view_tournament_standings_phase_4_9_6_16.sql', 'w') as f:
    f.write(sql)

print("Successfully written sql/analytics/view_tournament_standings_phase_4_9_6_16.sql (length:", len(sql), ")")
