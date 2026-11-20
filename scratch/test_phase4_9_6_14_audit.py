import sys
import os
import psycopg2
from decimal import Decimal

PG_CONN_PARAMS = {
    'dbname': 't20_worldcup_2026',
    'user': 'postgres',
    'password': 'Gautam@101',
    'host': 'localhost',
    'port': 5432
}

def get_pg_conn():
    return psycopg2.connect(**PG_CONN_PARAMS)

def build_22cte_query(matches_source_sql, summaries_source_sql, rankings_source_sql=None):
    """
    Builds the authoritative 22-CTE standings query with:
    1. Perfect All-Out Quota Symmetry across all 4 aggregation CTEs (team_batting, team_bowling, h2h_batting, h2h_bowling).
    2. Strict DLS allocated overs validation (zero silent fallback to target_overs).
    3. Independent synthetic accounting for forfeits (including partial innings scorecards).
    4. Strict integer GCD validation and zero-denominator protection.
    5. Proportional ranking/qualification impact.
    """
    rankings_cte = rankings_source_sql if rankings_source_sql else """
        SELECT 'India'::varchar AS team_name, 1 AS icc_rank UNION ALL
        SELECT 'Australia', 2 UNION ALL
        SELECT 'England', 3 UNION ALL
        SELECT 'New Zealand', 4 UNION ALL
        SELECT 'South Africa', 5 UNION ALL
        SELECT 'Pakistan', 6 UNION ALL
        SELECT 'West Indies', 7 UNION ALL
        SELECT 'Sri Lanka', 8 UNION ALL
        SELECT 'Bangladesh', 9 UNION ALL
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
        SELECT 'Papua New Guinea', 21 UNION ALL
        SELECT 'Uganda', 22 UNION ALL
        SELECT 'Hong Kong', 23 UNION ALL
        SELECT 'Jersey', 24 UNION ALL
        SELECT 'Kuwait', 25 UNION ALL
        SELECT 'Malaysia', 26 UNION ALL
        SELECT 'Italy', 27 UNION ALL
        SELECT 'TeamA', 1 UNION ALL
        SELECT 'TeamB', 2 UNION ALL
        SELECT 'TeamC', 3 UNION ALL
        SELECT 'TeamD', 4 UNION ALL
        SELECT 'TeamE', 5
    """

    sql = f"""
    WITH RECURSIVE icc_rankings_6feb2026 AS (
        {rankings_cte}
    ),
    dim_matches_source AS (
        {matches_source_sql}
    ),
    fact_match_summaries_source AS (
        {summaries_source_sql}
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
            CAST(target_overs AS NUMERIC) AS target_overs,
            CAST(target_runs AS NUMERIC) AS target_runs,
            is_dls_applied,
            is_dls_abandoned,
            CAST(dls_allocated_overs AS NUMERIC) AS dls_allocated_overs,
            CAST(dls_abandonment_overs AS NUMERIC) AS dls_abandonment_overs,
            CAST(dls_par_score AS INTEGER) AS dls_par_score,
            scorecard_available,
            source_note
        FROM dim_matches_source
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
            m.target_runs,
            m.is_dls_applied,
            m.is_dls_abandoned,
            m.dls_allocated_overs,
            m.dls_abandonment_overs,
            m.dls_par_score,
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
            m.target_runs,
            m.is_dls_applied,
            m.is_dls_abandoned,
            m.dls_allocated_overs,
            m.dls_abandonment_overs,
            m.dls_par_score,
            m.scorecard_available,
            m.source_note
        FROM stage_matches m
    ),
    match_played_eval AS (
        SELECT 
            mo.*,
            CASE 
                WHEN mo.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over', 'forfeit') THEN 1
                WHEN mo.outcome_type = 'no result' AND (
                    EXISTS (SELECT 1 FROM fact_match_summaries_source s WHERE s.match_id = mo.match_id AND s.legal_deliveries > 0)
                ) THEN 1
                ELSE 0
            END AS is_genuinely_played,
            -- DLS Evaluation Status:
            -- 0 = Regular non-DLS match
            -- 1 = Valid Completed DLS match (target_runs & dls_allocated_overs present; ZERO fallback to target_overs)
            -- 2 = Valid Abandoned DLS match (dls_par_score & dls_abandonment_overs present)
            -- 3 = Unresolved Completed DLS match (target_runs or dls_allocated_overs missing)
            -- 4 = Unresolved Abandoned DLS match (dls_par_score or dls_abandonment_overs missing)
            -- 5 = Unresolved Unknown Historical DLS match (is_dls_abandoned IS NULL)
            CASE 
                WHEN mo.is_dls_applied = FALSE THEN 0
                WHEN mo.outcome_type NOT IN ('runs', 'wickets', 'tie', 'tie_super_over') THEN 0
                WHEN mo.is_dls_abandoned IS NULL THEN 5 -- Unknown historical abandonment status fails closed!
                WHEN mo.is_dls_abandoned = FALSE THEN
                    CASE 
                        WHEN mo.target_runs IS NOT NULL AND mo.dls_allocated_overs IS NOT NULL THEN 1
                        ELSE 3 -- Missing target or dls_allocated_overs (strict: never fall back to target_overs!)
                    END
                WHEN mo.is_dls_abandoned = TRUE THEN
                    CASE 
                        WHEN mo.dls_par_score IS NOT NULL AND mo.dls_abandonment_overs IS NOT NULL THEN 2
                        ELSE 4 -- Missing par score or dls_abandonment_overs (strict: never fall back to target_runs!)
                    END
                ELSE 5
            END AS dls_status
        FROM match_opponents mo
    ),
    effective_match_summaries AS (
        -- Normal completed scorecards from fact_match_summaries (excluding forfeits)
        SELECT 
            s.match_id, s.innings, s.batting_team, s.bowling_team,
            s.total_runs, s.total_wickets, s.legal_deliveries, s.is_super_over
        FROM fact_match_summaries_source s
        JOIN stage_matches m ON s.match_id = m.match_id
        WHERE m.outcome_type <> 'forfeit' AND s.is_super_over = FALSE
        
        UNION ALL
        
        -- Synthetic accounting record for forfeit matches (ICC Clause 16.10.4.b / 16.10.7)
        -- Created independently of scorecard availability (and overrides any partial scorecard rows!)
        SELECT 
            m.match_id,
            1 AS innings,
            CASE WHEN m.winner = m.team1 THEN m.team2 ELSE m.team1 END AS batting_team,
            NULL::varchar AS bowling_team,  -- Awarded team is completely excluded from bowling metrics
            0 AS total_runs,
            10 AS total_wickets,
            120 AS legal_deliveries,
            FALSE AS is_super_over
        FROM stage_matches m
        WHERE m.outcome_type = 'forfeit' AND m.winner IS NOT NULL
    ),
    team_pool_records AS (
        SELECT 
            mpe.stage_normalized,
            mpe.group_name,
            mpe.focus_team AS team_name,
            SUM(CASE WHEN mpe.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over', 'no result', 'forfeit') THEN 1 ELSE 0 END) AS played,
            SUM(CASE WHEN (mpe.outcome_type IN ('runs', 'wickets', 'tie_super_over') OR mpe.outcome_type = 'forfeit') AND mpe.winner = mpe.focus_team THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN (mpe.outcome_type IN ('runs', 'wickets', 'tie_super_over') OR mpe.outcome_type = 'forfeit') AND mpe.winner = mpe.opp_team THEN 1 ELSE 0 END) AS losses,
            SUM(CASE WHEN mpe.outcome_type = 'no result' THEN 1 ELSE 0 END) AS no_result,
            SUM(
                CASE 
                    WHEN (mpe.outcome_type IN ('runs', 'wickets', 'tie_super_over') OR mpe.outcome_type = 'forfeit') AND mpe.winner = mpe.focus_team THEN 2
                    WHEN (mpe.outcome_type IN ('runs', 'wickets', 'tie_super_over') OR mpe.outcome_type = 'forfeit') AND mpe.winner = mpe.opp_team THEN 0
                    WHEN mpe.outcome_type IN ('no result', 'tie') THEN 1
                    ELSE 0
                END
            ) AS points,
            MAX(CASE WHEN mpe.dls_status IN (3, 4, 5) THEN 1 ELSE 0 END) AS has_unresolved_dls,
            MAX(CASE WHEN mpe.dls_status = 5 THEN 1 ELSE 0 END) AS has_unknown_dls_status,
            MAX(CASE WHEN mpe.dls_status = 4 THEN 1 ELSE 0 END) AS has_missing_par_score,
            MAX(CASE WHEN mpe.dls_status = 3 THEN 1 ELSE 0 END) AS has_missing_target_runs
        FROM match_played_eval mpe
        GROUP BY mpe.stage_normalized, mpe.group_name, mpe.focus_team
    ),
    team_batting_aggregates AS (
        SELECT 
            mpe.stage_normalized,
            mpe.group_name,
            mpe.focus_team AS team_name,
            CASE 
                WHEN MAX(CASE WHEN mpe.dls_status IN (3, 4, 5) THEN 1 ELSE 0 END) = 1 THEN NULL
                ELSE SUM(
                    CASE 
                        -- Completed DLS match: Innings 1 deemed runs = target_runs - 1
                        WHEN mpe.dls_status = 1 AND s.innings = 1 
                            THEN (CAST(mpe.target_runs AS NUMERIC) - 1)
                        -- Abandoned DLS match: Innings 1 deemed runs = par score
                        WHEN mpe.dls_status = 2 AND s.innings = 1 
                            THEN CAST(mpe.dls_par_score AS NUMERIC)
                        WHEN mpe.dls_status IN (3, 4, 5) AND s.innings = 1 
                            THEN NULL
                        ELSE s.total_runs
                    END
                )
            END AS runs_scored,
            CASE 
                WHEN MAX(CASE WHEN mpe.dls_status IN (3, 4, 5) THEN 1 ELSE 0 END) = 1 THEN NULL
                ELSE SUM(
                    CASE 
                        -- Completed DLS match: Innings 1 deemed balls = allocated quota
                        WHEN mpe.dls_status = 1 AND s.innings = 1 
                            THEN (FLOOR(mpe.dls_allocated_overs) * 6 + ROUND((mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10))
                        -- Abandoned DLS match: Innings 1 deemed balls = abandonment overs faced
                        WHEN mpe.dls_status = 2 AND s.innings = 1 
                            THEN (FLOOR(mpe.dls_abandonment_overs) * 6 + ROUND((mpe.dls_abandonment_overs - FLOOR(mpe.dls_abandonment_overs)) * 10))
                        WHEN mpe.dls_status IN (3, 4, 5) AND s.innings = 1 
                            THEN NULL
                        -- ALL-OUT QUOTA EXPANSION (ICC Clause 16.10.7):
                        -- When an innings ends all-out, balls faced must equal the full allocated quota!
                        WHEN s.total_wickets = 10 THEN 
                            CASE 
                                -- Innings 2 in Completed DLS match: expands to allocated quota
                                WHEN mpe.dls_status = 1 AND s.innings = 2 AND mpe.dls_allocated_overs IS NOT NULL THEN 
                                    (FLOOR(mpe.dls_allocated_overs) * 6 + ROUND((mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10))
                                -- Innings 2 in Abandoned DLS match: expands to abandonment overs faced
                                WHEN mpe.dls_status = 2 AND s.innings = 2 AND mpe.dls_abandonment_overs IS NOT NULL THEN 
                                    (FLOOR(mpe.dls_abandonment_overs) * 6 + ROUND((mpe.dls_abandonment_overs - FLOOR(mpe.dls_abandonment_overs)) * 10))
                                -- Regular non-DLS match (both innings 1 and innings 2): full 20-over quota (120 balls)
                                ELSE 120 
                            END
                        ELSE s.legal_deliveries 
                    END
                )
            END AS balls_faced
        FROM effective_match_summaries s
        JOIN match_played_eval mpe ON s.match_id = mpe.match_id AND s.batting_team = mpe.focus_team
        WHERE s.is_super_over = FALSE 
          AND mpe.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over', 'forfeit')
        GROUP BY mpe.stage_normalized, mpe.group_name, mpe.focus_team
    ),
    team_bowling_aggregates AS (
        SELECT 
            mpe.stage_normalized,
            mpe.group_name,
            mpe.focus_team AS team_name,
            CASE 
                WHEN MAX(CASE WHEN mpe.dls_status IN (3, 4, 5) THEN 1 ELSE 0 END) = 1 THEN NULL
                ELSE SUM(
                    CASE 
                        -- Completed DLS match: Innings 1 conceded runs = target_runs - 1
                        WHEN mpe.dls_status = 1 AND s.innings = 1 
                            THEN (CAST(mpe.target_runs AS NUMERIC) - 1)
                        -- Abandoned DLS match: Innings 1 conceded runs = par score
                        WHEN mpe.dls_status = 2 AND s.innings = 1 
                            THEN CAST(mpe.dls_par_score AS NUMERIC)
                        WHEN mpe.dls_status IN (3, 4, 5) AND s.innings = 1 
                            THEN NULL
                        ELSE s.total_runs
                    END
                )
            END AS runs_conceded,
            CASE 
                WHEN MAX(CASE WHEN mpe.dls_status IN (3, 4, 5) THEN 1 ELSE 0 END) = 1 THEN NULL
                ELSE SUM(
                    CASE 
                        -- Completed DLS match: Innings 1 conceded balls = allocated quota
                        WHEN mpe.dls_status = 1 AND s.innings = 1 
                            THEN (FLOOR(mpe.dls_allocated_overs) * 6 + ROUND((mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10))
                        -- Abandoned DLS match: Innings 1 conceded balls = abandonment overs faced
                        WHEN mpe.dls_status = 2 AND s.innings = 1 
                            THEN (FLOOR(mpe.dls_abandonment_overs) * 6 + ROUND((mpe.dls_abandonment_overs - FLOOR(mpe.dls_abandonment_overs)) * 10))
                        WHEN mpe.dls_status IN (3, 4, 5) AND s.innings = 1 
                            THEN NULL
                        -- ALL-OUT QUOTA EXPANSION SYMMETRY (ICC Clause 16.10.7):
                        -- When the opponent was dismissed all-out, bowling balls bowled must equal the EXACT SAME full quota!
                        WHEN s.total_wickets = 10 THEN 
                            CASE 
                                -- Innings 2 in Completed DLS match: bowling balls expand to allocated quota
                                WHEN mpe.dls_status = 1 AND s.innings = 2 AND mpe.dls_allocated_overs IS NOT NULL THEN 
                                    (FLOOR(mpe.dls_allocated_overs) * 6 + ROUND((mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10))
                                -- Innings 2 in Abandoned DLS match: bowling balls expand to abandonment overs faced
                                WHEN mpe.dls_status = 2 AND s.innings = 2 AND mpe.dls_abandonment_overs IS NOT NULL THEN 
                                    (FLOOR(mpe.dls_abandonment_overs) * 6 + ROUND((mpe.dls_abandonment_overs - FLOOR(mpe.dls_abandonment_overs)) * 10))
                                -- Regular non-DLS match (both innings 1 and innings 2): full 20-over quota (120 balls)
                                ELSE 120 
                            END
                        ELSE s.legal_deliveries
                    END
                )
            END AS balls_bowled
        FROM effective_match_summaries s
        JOIN match_played_eval mpe ON s.match_id = mpe.match_id AND s.bowling_team = mpe.focus_team
        WHERE s.is_super_over = FALSE 
          AND mpe.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over', 'forfeit')
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
            r.has_unresolved_dls,
            r.has_unknown_dls_status,
            r.has_missing_par_score,
            r.has_missing_target_runs,
            b.runs_scored,
            b.balls_faced,
            w.runs_conceded,
            w.balls_bowled,
            CASE 
                WHEN r.has_unresolved_dls = 0 
                     AND COALESCE(b.balls_faced, 0) > 0 AND COALESCE(w.balls_bowled, 0) > 0 
                     AND b.runs_scored IS NOT NULL AND w.runs_conceded IS NOT NULL THEN
                    (CAST(b.runs_scored AS NUMERIC) * CAST(w.balls_bowled AS NUMERIC) - CAST(w.runs_conceded AS NUMERIC) * CAST(b.balls_faced AS NUMERIC))
                ELSE NULL 
            END AS n,
            CASE 
                WHEN r.has_unresolved_dls = 0 
                     AND COALESCE(b.balls_faced, 0) > 0 AND COALESCE(w.balls_bowled, 0) > 0 
                     AND b.runs_scored IS NOT NULL AND w.runs_conceded IS NOT NULL THEN
                    (CAST(b.balls_faced AS NUMERIC) * CAST(w.balls_bowled AS NUMERIC))
                ELSE NULL 
            END AS d,
            CASE 
                WHEN r.has_unresolved_dls = 0 
                     AND COALESCE(b.balls_faced, 0) > 0 AND COALESCE(w.balls_bowled, 0) > 0 
                     AND b.runs_scored IS NOT NULL AND w.runs_conceded IS NOT NULL THEN
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
            mpe.target_runs,
            mpe.is_dls_applied,
            mpe.is_dls_abandoned,
            mpe.dls_allocated_overs,
            mpe.dls_abandonment_overs,
            mpe.dls_par_score,
            mpe.scorecard_available,
            mpe.is_genuinely_played,
            mpe.dls_status,
            CASE 
                WHEN (mpe.outcome_type IN ('runs', 'wickets', 'tie_super_over') OR mpe.outcome_type = 'forfeit') AND mpe.winner = t_focus.team_name THEN 2
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
                -- If overall NRR is undefined, H2H points cannot be evaluated (Clause 16.10.4)
                WHEN tg.tier_has_undefined_nrr > 0 THEN NULL
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
        JOIN tier_nrr_guard tg ON f.stage_normalized = tg.stage_normalized
                              AND f.group_name = tg.group_name
                              AND f.points = tg.points
                              AND f.wins = tg.wins
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
            CASE 
                WHEN MAX(CASE WHEN hm.dls_status IN (3, 4, 5) THEN 1 ELSE 0 END) = 1 THEN NULL
                ELSE SUM(
                    CASE 
                        WHEN hm.dls_status = 1 AND s.innings = 1 THEN (CAST(hm.target_runs AS NUMERIC) - 1)
                        WHEN hm.dls_status = 2 AND s.innings = 1 THEN CAST(hm.dls_par_score AS NUMERIC)
                        WHEN hm.dls_status IN (3, 4, 5) AND s.innings = 1 THEN NULL
                        ELSE s.total_runs
                    END
                )
            END AS h2h_runs_scored,
            CASE 
                WHEN MAX(CASE WHEN hm.dls_status IN (3, 4, 5) THEN 1 ELSE 0 END) = 1 THEN NULL
                ELSE SUM(
                    CASE 
                        WHEN hm.dls_status = 1 AND s.innings = 1 
                            THEN (FLOOR(hm.dls_allocated_overs) * 6 + ROUND((hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10))
                        WHEN hm.dls_status = 2 AND s.innings = 1 
                            THEN (FLOOR(hm.dls_abandonment_overs) * 6 + ROUND((hm.dls_abandonment_overs - FLOOR(hm.dls_abandonment_overs)) * 10))
                        WHEN hm.dls_status IN (3, 4, 5) AND s.innings = 1 THEN NULL
                        -- H2H ALL-OUT QUOTA EXPANSION:
                        WHEN s.total_wickets = 10 THEN 
                            CASE 
                                WHEN hm.dls_status = 1 AND s.innings = 2 AND hm.dls_allocated_overs IS NOT NULL THEN 
                                    (FLOOR(hm.dls_allocated_overs) * 6 + ROUND((hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10))
                                WHEN hm.dls_status = 2 AND s.innings = 2 AND hm.dls_abandonment_overs IS NOT NULL THEN 
                                    (FLOOR(hm.dls_abandonment_overs) * 6 + ROUND((hm.dls_abandonment_overs - FLOOR(hm.dls_abandonment_overs)) * 10))
                                ELSE 120 
                            END
                        ELSE s.legal_deliveries 
                    END
                )
            END AS h2h_balls_faced
        FROM effective_match_summaries s
        JOIN h2h_matches hm ON s.match_id = hm.match_id AND s.batting_team = hm.focus_team
        WHERE s.is_super_over = FALSE 
          AND hm.is_genuinely_played = 1
          AND hm.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over', 'forfeit')
        GROUP BY hm.stage_normalized, hm.group_name, hm.focus_team
    ),
    h2h_bowling AS (
        SELECT 
            hm.stage_normalized,
            hm.group_name,
            hm.focus_team AS team_name,
            CASE 
                WHEN MAX(CASE WHEN hm.dls_status IN (3, 4, 5) THEN 1 ELSE 0 END) = 1 THEN NULL
                ELSE SUM(
                    CASE 
                        WHEN hm.dls_status = 1 AND s.innings = 1 THEN (CAST(hm.target_runs AS NUMERIC) - 1)
                        WHEN hm.dls_status = 2 AND s.innings = 1 THEN CAST(hm.dls_par_score AS NUMERIC)
                        WHEN hm.dls_status IN (3, 4, 5) AND s.innings = 1 THEN NULL
                        ELSE s.total_runs
                    END
                )
            END AS h2h_runs_conceded,
            CASE 
                WHEN MAX(CASE WHEN hm.dls_status IN (3, 4, 5) THEN 1 ELSE 0 END) = 1 THEN NULL
                ELSE SUM(
                    CASE 
                        WHEN hm.dls_status = 1 AND s.innings = 1 
                            THEN (FLOOR(hm.dls_allocated_overs) * 6 + ROUND((hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10))
                        WHEN hm.dls_status = 2 AND s.innings = 1 
                            THEN (FLOOR(hm.dls_abandonment_overs) * 6 + ROUND((hm.dls_abandonment_overs - FLOOR(hm.dls_abandonment_overs)) * 10))
                        WHEN hm.dls_status IN (3, 4, 5) AND s.innings = 1 THEN NULL
                        -- H2H ALL-OUT QUOTA EXPANSION SYMMETRY:
                        WHEN s.total_wickets = 10 THEN 
                            CASE 
                                WHEN hm.dls_status = 1 AND s.innings = 2 AND hm.dls_allocated_overs IS NOT NULL THEN 
                                    (FLOOR(hm.dls_allocated_overs) * 6 + ROUND((hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10))
                                WHEN hm.dls_status = 2 AND s.innings = 2 AND hm.dls_abandonment_overs IS NOT NULL THEN 
                                    (FLOOR(hm.dls_abandonment_overs) * 6 + ROUND((hm.dls_abandonment_overs - FLOOR(hm.dls_abandonment_overs)) * 10))
                                ELSE 120 
                            END
                        ELSE s.legal_deliveries
                    END
                )
            END AS h2h_balls_bowled
        FROM effective_match_summaries s
        JOIN h2h_matches hm ON s.match_id = hm.match_id AND s.bowling_team = hm.focus_team
        WHERE s.is_super_over = FALSE 
          AND hm.is_genuinely_played = 1
          AND hm.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over', 'forfeit')
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
                     AND COALESCE(hw.h2h_balls_bowled, 0) > 0 
                     AND hb.h2h_runs_scored IS NOT NULL 
                     AND hw.h2h_runs_conceded IS NOT NULL THEN
                    (CAST(hb.h2h_runs_scored AS NUMERIC) * CAST(hw.h2h_balls_bowled AS NUMERIC) - CAST(hw.h2h_runs_conceded AS NUMERIC) * CAST(hb.h2h_balls_faced AS NUMERIC))
                ELSE NULL 
            END AS h2h_n,
            CASE 
                WHEN cg.safe_h2h_points IS NOT NULL 
                     AND COALESCE(hb.h2h_balls_faced, 0) > 0 
                     AND COALESCE(hw.h2h_balls_bowled, 0) > 0 
                     AND hb.h2h_runs_scored IS NOT NULL 
                     AND hw.h2h_runs_conceded IS NOT NULL THEN
                    (CAST(hb.h2h_balls_faced AS NUMERIC) * CAST(hw.h2h_balls_bowled AS NUMERIC))
                ELSE NULL 
            END AS h2h_d,
            CASE 
                WHEN cg.safe_h2h_points IS NOT NULL 
                     AND COALESCE(hb.h2h_balls_faced, 0) > 0 
                     AND COALESCE(hw.h2h_balls_bowled, 0) > 0 
                     AND hb.h2h_runs_scored IS NOT NULL 
                     AND hw.h2h_runs_conceded IS NOT NULL THEN
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
            f.has_unresolved_dls,
            f.has_unknown_dls_status,
            f.has_missing_par_score,
            f.has_missing_target_runs,
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
            COUNT(*) OVER (
                PARTITION BY f.stage_normalized, f.group_name, f.points, f.wins, 
                             COALESCE(nsc.nrr_superior_count, -1),
                             COALESCE(h.safe_h2h_points, -1),
                             COALESCE(h.h2h_nrr_superior_count, -1),
                             r.icc_rank
            ) AS terminal_icc_tier_count,
            DENSE_RANK() OVER (
                PARTITION BY f.stage_normalized, f.group_name
                ORDER BY 
                    f.points DESC,
                    f.wins DESC,
                    nsc.nrr_superior_count ASC NULLS LAST,
                    CASE WHEN tng.tier_has_undefined_nrr > 0 THEN NULL ELSE h.safe_h2h_points END DESC NULLS LAST,
                    CASE WHEN tng.tier_has_undefined_nrr > 0 THEN NULL ELSE h.h2h_nrr_superior_count END ASC NULLS LAST,
                    CASE WHEN tng.tier_has_undefined_nrr > 0 THEN NULL ELSE r.icc_rank END ASC NULLS LAST
            ) AS official_pool_rank,
            RANK() OVER (
                PARTITION BY f.stage_normalized, f.group_name
                ORDER BY 
                    f.points DESC,
                    f.wins DESC,
                    nsc.nrr_superior_count ASC NULLS LAST,
                    CASE WHEN tng.tier_has_undefined_nrr > 0 THEN NULL ELSE h.safe_h2h_points END DESC NULLS LAST,
                    CASE WHEN tng.tier_has_undefined_nrr > 0 THEN NULL ELSE h.h2h_nrr_superior_count END ASC NULLS LAST,
                    CASE WHEN tng.tier_has_undefined_nrr > 0 THEN NULL ELSE r.icc_rank END ASC NULLS LAST
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
        LEFT JOIN icc_rankings_6feb2026 r ON f.team_name = r.team_name
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
            WHEN tier_has_undefined_nrr > 0 THEN 
                CASE 
                    WHEN has_unknown_dls_status = 1 THEN 'Step 3: Unresolved — Unknown DLS Abandonment Status (Clause 16.10.7)'
                    WHEN has_missing_par_score = 1 THEN 'Step 3: Unresolved — DLS Par Score or Abandonment Overs Unavailable (Clause 16.10.7)'
                    WHEN has_missing_target_runs = 1 THEN 'Step 3: Unresolved — DLS Final Target or Allocated Overs Unavailable (Clause 16.10.7)'
                    WHEN has_unresolved_dls = 1 THEN 'Step 3: Unresolved — DLS Parameters Unavailable (Clause 16.10.7)'
                    ELSE 'Step 3: Unresolved — Net Run Rate Undefined'
                END
            WHEN nrr_canon_count = 1 THEN 'Step 3: Net Run Rate (Clause 16.10.4.b)'
            WHEN safe_h2h_points IS NOT NULL AND h2h_pts_tier_count = 1 THEN 'Step 4a: Head-to-Head Points (Clause 16.10.4.c)'
            WHEN safe_h2h_points IS NOT NULL AND COALESCE(tier_has_undefined_h2h_nrr, 1) = 0 AND h2h_nrr_canon_count = 1 THEN 'Step 4b: Head-to-Head Net Run Rate (Clause 16.10.4.c)'
            WHEN icc_rank IS NULL AND (pts_count > 1 AND wins_count > 1 AND (tier_has_undefined_nrr > 0 OR nrr_canon_count > 1)) THEN 'Step 5: Unresolved — Missing Pre-Tournament ICC Ranking'
            WHEN terminal_icc_tier_count > 1 THEN 'Step 5: Unresolved Terminal Tie — Pre-Tournament Rankings Equal (Requires Event Direction)'
            ELSE 'Step 5: ICC T20I Team Rankings as at 6 Feb 2026 (Clause 16.10.4.d)'
        END AS resolution_step,
        CASE 
            -- 1. If tie straddles top-2 qualification boundary and cannot be resolved:
            WHEN wins_count > 1 AND tier_has_undefined_nrr > 0 
                 AND min_tier_rank <= 2 AND min_tier_rank + wins_count - 1 > 2 
                 THEN 'Unresolved — Pending DLS / NRR Resolution'
            WHEN icc_rank IS NULL AND (pts_count > 1 AND wins_count > 1 AND (tier_has_undefined_nrr > 0 OR nrr_canon_count > 1))
                 AND min_tier_rank <= 2 AND min_tier_rank + wins_count - 1 > 2 
                 THEN 'Unresolved — Missing Pre-Tournament Ranking'
            WHEN terminal_icc_tier_count > 1 
                 AND min_tier_rank <= 2 AND min_tier_rank + terminal_icc_tier_count - 1 > 2 
                 THEN 'Unresolved Tie — Event Direction Required'
            -- 2. If the team's entire tier is within top 2:
            WHEN min_tier_rank + COALESCE(
                CASE 
                    WHEN wins_count > 1 AND tier_has_undefined_nrr > 0 THEN wins_count
                    WHEN terminal_icc_tier_count > 1 THEN terminal_icc_tier_count
                    ELSE 1
                END, 1) - 1 <= 2 THEN 'Qualified'
            -- 3. If the team's entire tier is outside top 2:
            WHEN min_tier_rank > 2 THEN 'Eliminated'
            -- 4. Fallback:
            ELSE 'Unresolved Tie — Event Direction Required'
        END AS qualification_status,
        -- Expose intermediate accounting for audit verification:
        runs_scored,
        balls_faced,
        runs_conceded,
        balls_bowled,
        n,
        d,
        n_canon,
        d_canon
    FROM standings_compiled
    ORDER BY stage_normalized DESC, group_name ASC, official_pool_rank ASC, team_name ASC;
    """
    return sql

print("Phase 4.9.6.14 query builder ready!")


def run_tests():
    conn = get_pg_conn()
    cur = conn.cursor()
    test_results = []
    all_passed = True

    print("=" * 85)
    print("PHASE 4.9.6.14: ALL-OUT QUOTA SYMMETRY & NRR ACCOUNTING AUDIT SUITE")
    print("=" * 85)

    # --------------------------------------------------------------------------
    # 0. Strict GCD Helper Setup in Transaction
    # --------------------------------------------------------------------------
    cur.execute("BEGIN;")
    gcd_ddl = """
    CREATE OR REPLACE FUNCTION gcd(a NUMERIC, b NUMERIC)
    RETURNS NUMERIC AS $$
    DECLARE
        x NUMERIC;
        y NUMERIC;
        t NUMERIC;
    BEGIN
        IF a IS NULL OR b IS NULL THEN
            RETURN NULL;
        END IF;
        IF a != TRUNC(a) OR b != TRUNC(b) THEN
            RAISE EXCEPTION 'gcd(NUMERIC, NUMERIC) requires integer inputs, received a=%, b=%', a, b;
        END IF;
        x := ABS(a);
        y := ABS(b);
        IF x = 0 AND y = 0 THEN
            RETURN 1;
        ELSIF x = 0 THEN
            RETURN y;
        ELSIF y = 0 THEN
            RETURN x;
        END IF;
        WHILE y != 0 LOOP
            t := y;
            y := x % y;
            x := t;
        END LOOP;
        RETURN x;
    END;
    $$ LANGUAGE plpgsql IMMUTABLE STRICT;
    """
    cur.execute(gcd_ddl)

    # --------------------------------------------------------------------------
    # Test 1: ALLOUT-REG-01 - Regular First-Innings All-Out
    # --------------------------------------------------------------------------
    try:
        # Team 1 batted first and was bowled all-out in 80 balls (13.2 ov) for 110 runs.
        # Team 2 chased: 111/3 in 70 balls (11.4 ov).
        # Clause 16.10.7: Team 1 balls faced expanded to 120; Team 2 balls bowled symmetrically expanded to 120!
        matches_sql = """
            SELECT 'M_REG_ALLOUT_1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'T1_Inn1AllOut' AS team1, 'T2_Chaser' AS team2, 'T2_Chaser' AS winner, 'wickets' AS outcome_type, 20.0::numeric AS target_overs, 111::numeric AS target_runs, FALSE AS is_dls_applied, NULL::boolean AS is_dls_abandoned, NULL::numeric AS dls_allocated_overs, NULL::numeric AS dls_abandonment_overs, NULL::integer AS dls_par_score, TRUE AS scorecard_available, 'Reg match inn 1 all-out' AS source_note
        """
        summaries_sql = """
            SELECT 'M_REG_ALLOUT_1' AS match_id, 1 AS innings, 'T1_Inn1AllOut' AS batting_team, 'T2_Chaser' AS bowling_team, 110 AS total_runs, 10 AS total_wickets, 80 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_REG_ALLOUT_1', 2, 'T2_Chaser', 'T1_Inn1AllOut', 111, 3, 70, FALSE
        """
        q = build_22cte_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        t1 = [r for r in rows if r[3] == 'T1_Inn1AllOut'][0]
        t2 = [r for r in rows if r[3] == 'T2_Chaser'][0]

        # Verify intermediate runs and balls:
        # T1 (batting team 1): runs scored = 110, balls faced = 120 (expanded from 80!); runs conceded = 111, balls bowled = 70.
        assert t1[15] == 110 and t1[16] == 120 and t1[17] == 111 and t1[18] == 70
        # T2 (bowling team 1): runs scored = 111, balls faced = 70; runs conceded = 110, balls bowled = 120 (symmetrically expanded from 80!).
        assert t2[15] == 111 and t2[16] == 70 and t2[17] == 110 and t2[18] == 120

        # Exact rational fractions:
        # T1 n = 110*70 - 111*120 = 7700 - 13320 = -5620. d = 120*70 = 8400.
        # T2 n = 111*120 - 110*70 = 13320 - 7700 = +5620. d = 70*120 = 8400.
        assert t1[19] == -5620 and t1[20] == 8400
        assert t2[19] == 5620 and t2[20] == 8400
        # Reduced: gcd(5620, 8400) = 20 -> 281 / 420.
        assert t1[21] == -281 and t1[22] == 420
        assert t2[21] == 281 and t2[22] == 420

        # NRR display: T1 = -4.014, T2 = +4.014. Sum = 0.
        assert float(t1[9]) == -4.014 and float(t2[9]) == 4.014

        test_results.append(("ALLOUT-REG-01", "Regular First-Innings All-Out", "PASS", "T1 balls faced expanded to 120; T2 balls bowled symmetrically expanded to 120; NRR = -4.014 vs +4.014 (Sum=0)"))
        print("[PASS] ALLOUT-REG-01: Regular First-Innings All-Out")
    except Exception as e:
        all_passed = False
        test_results.append(("ALLOUT-REG-01", "Regular First-Innings All-Out", "FAIL", str(e)))
        print(f"[FAIL] ALLOUT-REG-01: {e}")

    # --------------------------------------------------------------------------
    # Test 2: ALLOUT-REG-02 - Regular Second-Innings All-Out
    # --------------------------------------------------------------------------
    try:
        # Team 1: 160/6 in 120 balls.
        # Team 2 was bowled all-out in 92 balls (15.2 ov) for 120 runs.
        # Clause 16.10.7: Team 2 balls faced expanded to 120; Team 1 balls bowled symmetrically expanded to 120!
        matches_sql = """
            SELECT 'M_REG_ALLOUT_2' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'T1_Defend' AS team1, 'T2_Inn2AllOut' AS team2, 'T1_Defend' AS winner, 'runs' AS outcome_type, 20.0::numeric AS target_overs, 161::numeric AS target_runs, FALSE AS is_dls_applied, NULL::boolean AS is_dls_abandoned, NULL::numeric AS dls_allocated_overs, NULL::numeric AS dls_abandonment_overs, NULL::integer AS dls_par_score, TRUE AS scorecard_available, 'Reg match inn 2 all-out' AS source_note
        """
        summaries_sql = """
            SELECT 'M_REG_ALLOUT_2' AS match_id, 1 AS innings, 'T1_Defend' AS batting_team, 'T2_Inn2AllOut' AS bowling_team, 160 AS total_runs, 6 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_REG_ALLOUT_2', 2, 'T2_Inn2AllOut', 'T1_Defend', 120, 10, 92, FALSE
        """
        q = build_22cte_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        t1 = [r for r in rows if r[3] == 'T1_Defend'][0]
        t2 = [r for r in rows if r[3] == 'T2_Inn2AllOut'][0]

        # Intermediate runs and balls:
        # T1: 160 runs scored, 120 balls faced; 120 runs conceded, 120 balls bowled (expanded from 92!).
        assert t1[15] == 160 and t1[16] == 120 and t1[17] == 120 and t1[18] == 120
        # T2: 120 runs scored, 120 balls faced (expanded from 92!); 160 runs conceded, 120 balls bowled.
        assert t2[15] == 120 and t2[16] == 120 and t2[17] == 160 and t2[18] == 120

        # Exact rational fractions:
        # T1: n = 160*120 - 120*120 = 4800. d = 120*120 = 14400. Fraction = 1/3. NRR = +2.000.
        # T2: n = 120*120 - 160*120 = -4800. d = 14400. Fraction = -1/3. NRR = -2.000.
        assert t1[21] == 1 and t1[22] == 3 and float(t1[9]) == 2.000
        assert t2[21] == -1 and t2[22] == 3 and float(t2[9]) == -2.000

        test_results.append(("ALLOUT-REG-02", "Regular Second-Innings All-Out", "PASS", "T2 balls faced expanded to 120; T1 balls bowled symmetrically expanded to 120; NRR = +2.000 vs -2.000 (Sum=0)"))
        print("[PASS] ALLOUT-REG-02: Regular Second-Innings All-Out")
    except Exception as e:
        all_passed = False
        test_results.append(("ALLOUT-REG-02", "Regular Second-Innings All-Out", "FAIL", str(e)))
        print(f"[FAIL] ALLOUT-REG-02: {e}")

    # --------------------------------------------------------------------------
    # Test 3: ALLOUT-DLS-01 - DLS First-Innings All-Out
    # --------------------------------------------------------------------------
    try:
        # Team 1 was all-out in 72 balls (12.0 ov) for 95 runs. Rain interrupted during the break.
        # Team 2 allocated quota: 15.0 overs (90 balls). Target: 110 runs.
        # Team 2 scored 112/4 in 80 balls (13.2 ov). Team 2 won.
        # Clause 16.10.7: Team 1 deemed scored target - 1 = 109 runs in 15.0 ov (90 balls).
        matches_sql = """
            SELECT 'M_DLS_ALLOUT_1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'T1_DlsInn1' AS team1, 'T2_DlsChaser' AS team2, 'T2_DlsChaser' AS winner, 'wickets' AS outcome_type, NULL::numeric AS target_overs, 110::numeric AS target_runs, TRUE AS is_dls_applied, FALSE AS is_dls_abandoned, 15.0::numeric AS dls_allocated_overs, NULL::numeric AS dls_abandonment_overs, NULL::integer AS dls_par_score, TRUE AS scorecard_available, 'DLS inn 1 all-out' AS source_note
        """
        summaries_sql = """
            SELECT 'M_DLS_ALLOUT_1' AS match_id, 1 AS innings, 'T1_DlsInn1' AS batting_team, 'T2_DlsChaser' AS bowling_team, 95 AS total_runs, 10 AS total_wickets, 72 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_DLS_ALLOUT_1', 2, 'T2_DlsChaser', 'T1_DlsInn1', 112, 4, 80, FALSE
        """
        q = build_22cte_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        t1 = [r for r in rows if r[3] == 'T1_DlsInn1'][0]
        t2 = [r for r in rows if r[3] == 'T2_DlsChaser'][0]

        # T1 deemed: 109 runs in 90 balls (15.0 ov). Conceded: 112 runs in 80 balls.
        assert t1[15] == 109 and t1[16] == 90 and t1[17] == 112 and t1[18] == 80
        # T2: scored 112 in 80 balls. Conceded deemed 109 runs in 90 balls.
        assert t2[15] == 112 and t2[16] == 80 and t2[17] == 109 and t2[18] == 90

        # Exact NRR: T2 = (112/(80/6)) - (109/15.0) = 8.400 - 7.267 = +1.133.
        # T1 = -1.133. Sum = 0.
        assert float(t2[9]) == 1.133 and float(t1[9]) == -1.133

        test_results.append(("ALLOUT-DLS-01", "DLS First-Innings All-Out", "PASS", "T1 deemed 109 runs off 90 balls; T2 scored 112 off 80 balls; NRR = +1.133 vs -1.133 (Sum=0)"))
        print("[PASS] ALLOUT-DLS-01: DLS First-Innings All-Out")
    except Exception as e:
        all_passed = False
        test_results.append(("ALLOUT-DLS-01", "DLS First-Innings All-Out", "FAIL", str(e)))
        print(f"[FAIL] ALLOUT-DLS-01: {e}")

    # --------------------------------------------------------------------------
    # Test 4: ALLOUT-DLS-02 - DLS Second-Innings All-Out
    # --------------------------------------------------------------------------
    try:
        # Team 1 scored 175/5 in 20.0 ov.
        # Team 2 allocated quota: 15.0 overs (90 balls). Target: 140 runs.
        # Team 2 was bowled out in 78 balls (13.0 ov) for 100 runs.
        # Clause 16.10.7: Team 1 deemed scored target - 1 = 139 runs in 15.0 ov (90 balls).
        # Team 2 was all-out, so Team 2 balls faced expanded to allocated quota: 15.0 ov (90 balls)!
        # Team 1 balls bowled symmetrically expanded to allocated quota: 15.0 ov (90 balls)!
        matches_sql = """
            SELECT 'M_DLS_ALLOUT_2' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'T1_DlsDef' AS team1, 'T2_DlsInn2' AS team2, 'T1_DlsDef' AS winner, 'runs' AS outcome_type, NULL::numeric AS target_overs, 140::numeric AS target_runs, TRUE AS is_dls_applied, FALSE AS is_dls_abandoned, 15.0::numeric AS dls_allocated_overs, NULL::numeric AS dls_abandonment_overs, NULL::integer AS dls_par_score, TRUE AS scorecard_available, 'DLS inn 2 all-out' AS source_note
        """
        summaries_sql = """
            SELECT 'M_DLS_ALLOUT_2' AS match_id, 1 AS innings, 'T1_DlsDef' AS batting_team, 'T2_DlsInn2' AS bowling_team, 175 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_DLS_ALLOUT_2', 2, 'T2_DlsInn2', 'T1_DlsDef', 100, 10, 78, FALSE
        """
        q = build_22cte_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        t1 = [r for r in rows if r[3] == 'T1_DlsDef'][0]
        t2 = [r for r in rows if r[3] == 'T2_DlsInn2'][0]

        # Intermediate runs and balls:
        # T1: deemed 139 runs in 90 balls; conceded 100 runs in 90 balls (expanded from 78!).
        assert t1[15] == 139 and t1[16] == 90 and t1[17] == 100 and t1[18] == 90
        # T2: scored 100 runs in 90 balls (expanded from 78!); conceded deemed 139 runs in 90 balls.
        assert t2[15] == 100 and t2[16] == 90 and t2[17] == 139 and t2[18] == 90

        # Exact NRR:
        # T1: (139/15.0) - (100/15.0) = 39 / 15.0 = +2.600.
        # T2: (100/15.0) - (139/15.0) = -39 / 15.0 = -2.600.
        assert float(t1[9]) == 2.600 and float(t2[9]) == -2.600

        test_results.append(("ALLOUT-DLS-02", "DLS Second-Innings All-Out", "PASS", "T2 balls faced expanded to allocated 90 balls; T1 bowling symmetrically expanded to 90; NRR = +2.600 vs -2.600 (Sum=0)"))
        print("[PASS] ALLOUT-DLS-02: DLS Second-Innings All-Out")
    except Exception as e:
        all_passed = False
        test_results.append(("ALLOUT-DLS-02", "DLS Second-Innings All-Out", "FAIL", str(e)))
        print(f"[FAIL] ALLOUT-DLS-02: {e}")

    # --------------------------------------------------------------------------
    # Test 5: ALLOUT-CTRL-01 - Non-All-Out Control Case
    # --------------------------------------------------------------------------
    try:
        # Both innings completed full 20 overs without all-out
        matches_sql = """
            SELECT 'M_CTRL' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'T1_Ctrl' AS team1, 'T2_Ctrl' AS team2, 'T1_Ctrl' AS winner, 'runs' AS outcome_type, 20.0::numeric AS target_overs, 161::numeric AS target_runs, FALSE AS is_dls_applied, NULL::boolean AS is_dls_abandoned, NULL::numeric AS dls_allocated_overs, NULL::numeric AS dls_abandonment_overs, NULL::integer AS dls_par_score, TRUE AS scorecard_available, 'Control non-all-out' AS source_note
        """
        summaries_sql = """
            SELECT 'M_CTRL' AS match_id, 1 AS innings, 'T1_Ctrl' AS batting_team, 'T2_Ctrl' AS bowling_team, 160 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_CTRL', 2, 'T2_Ctrl', 'T1_Ctrl', 145, 6, 120, FALSE
        """
        q = build_22cte_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        t1 = [r for r in rows if r[3] == 'T1_Ctrl'][0]
        t2 = [r for r in rows if r[3] == 'T2_Ctrl'][0]

        assert t1[15] == 160 and t1[16] == 120 and t1[17] == 145 and t1[18] == 120
        assert t2[15] == 145 and t2[16] == 120 and t2[17] == 160 and t2[18] == 120
        assert float(t1[9]) == 0.750 and float(t2[9]) == -0.750

        test_results.append(("ALLOUT-CTRL-01", "Non-All-Out Control Case", "PASS", "Legal deliveries (120 and 120) used verbatim; NRR = +0.750 vs -0.750 (Sum=0)"))
        print("[PASS] ALLOUT-CTRL-01: Non-All-Out Control Case")
    except Exception as e:
        all_passed = False
        test_results.append(("ALLOUT-CTRL-01", "Non-All-Out Control Case", "FAIL", str(e)))
        print(f"[FAIL] ALLOUT-CTRL-01: {e}")

    # --------------------------------------------------------------------------
    # Test 6: DLS-FALLBACK-NEG - Negative Test: No Fallback to target_overs
    # --------------------------------------------------------------------------
    try:
        # Match has target_overs = 15.0 and target_runs = 140, but dls_allocated_overs IS NULL!
        # Engine MUST NOT silently fallback to target_overs! Must fail closed (NRR=NULL).
        # We test both fail-closed NRR and tie-break resolution step.
        matches_sql = """
            SELECT 'M_DLS_NEG' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'T1_DlsNeg' AS team1, 'T3_Opp' AS team2, 'T1_DlsNeg' AS winner, 'wickets' AS outcome_type, 15.0::numeric AS target_overs, 140::numeric AS target_runs, TRUE AS is_dls_applied, FALSE AS is_dls_abandoned, NULL::numeric AS dls_allocated_overs, NULL::numeric AS dls_abandonment_overs, NULL::integer AS dls_par_score, TRUE AS scorecard_available, 'DLS with null allocated overs' AS source_note
            UNION ALL
            SELECT 'M_REG_CTRL', '2026-02-11'::date, 'Group Stage', 'Group Stage', 'A', 'T2_DlsNeg', 'T3_Opp', 'T2_DlsNeg', 'wickets', 20.0, NULL, FALSE, FALSE, NULL, NULL, NULL, TRUE, 'Regular control match'
        """
        summaries_sql = """
            SELECT 'M_DLS_NEG' AS match_id, 1 AS innings, 'T3_Opp' AS batting_team, 'T1_DlsNeg' AS bowling_team, 150 AS total_runs, 6 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_DLS_NEG', 2, 'T1_DlsNeg', 'T3_Opp', 141, 4, 86, FALSE UNION ALL
            SELECT 'M_REG_CTRL', 1, 'T3_Opp', 'T2_DlsNeg', 150, 6, 120, FALSE UNION ALL
            SELECT 'M_REG_CTRL', 2, 'T2_DlsNeg', 'T3_Opp', 151, 4, 110, FALSE
        """
        q = build_22cte_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        t1 = [r for r in rows if r[3] == 'T1_DlsNeg'][0]
        t2 = [r for r in rows if r[3] == 'T2_DlsNeg'][0]

        # Must fail closed: NRR is NULL for T1 (refusing to use target_overs = 15.0)
        assert t1[9] is None, f"Expected T1 NRR is None, got {t1[9]}"
        # Points and W/L preserved:
        assert t1[8] == 2 and t2[8] == 2, f"Expected 2 points each, got {t1[8]}, {t2[8]}"
        # Resolution step transparently indicates missing allocated overs on tie-break:
        assert 'Step 3: Unresolved' in t1[13], f"Expected Step 3: Unresolved in t1[13], got {t1[13]}"
        assert 'DLS Final Target or Allocated Overs Unavailable' in t1[13]

        test_results.append(("DLS-FALLBACK-NEG", "Missing dls_allocated_overs Negative Test", "PASS", "Engine refuses silent fallback to target_overs; fails closed (NRR=NULL); points preserved (2 vs 2); tie-break triggers Step 3 Unresolved"))
        print("[PASS] DLS-FALLBACK-NEG: Missing dls_allocated_overs Negative Test")
    except Exception as e:
        all_passed = False
        test_results.append(("DLS-FALLBACK-NEG", "Missing dls_allocated_overs Negative Test", "FAIL", str(e)))
        print(f"[FAIL] DLS-FALLBACK-NEG: {e}")

    # --------------------------------------------------------------------------
    # Test 7: FORFEIT-INTERMED-01 - Forfeit with Zero Scorecard Rows (Intermediate Verification)
    # --------------------------------------------------------------------------
    try:
        matches_sql = """
            SELECT 'M_FF_ZERO' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'T_Defaulter' AS team1, 'T_Awarded' AS team2, 'T_Awarded' AS winner, 'forfeit' AS outcome_type, NULL::numeric AS target_overs, NULL::numeric AS target_runs, FALSE AS is_dls_applied, NULL::boolean AS is_dls_abandoned, NULL::numeric AS dls_allocated_overs, NULL::numeric AS dls_abandonment_overs, NULL::integer AS dls_par_score, FALSE AS scorecard_available, 'Forfeit with zero scorecard' AS source_note UNION ALL
            SELECT 'M_REG_1', '2026-02-12'::date, 'Group Stage', 'Group Stage', 'A', 'T_Awarded', 'T_Other', 'T_Awarded', 'runs', 20.0, 160::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'M2' UNION ALL
            SELECT 'M_REG_2', '2026-02-14'::date, 'Group Stage', 'Group Stage', 'A', 'T_Defaulter', 'T_Other', 'T_Defaulter', 'runs', 20.0, 120::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'M3'
        """
        summaries_sql = """
            SELECT 'M_REG_1' AS match_id, 1 AS innings, 'T_Awarded' AS batting_team, 'T_Other' AS bowling_team, 160 AS total_runs, 4 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_REG_1', 2, 'T_Other', 'T_Awarded', 140, 6, 120, FALSE UNION ALL
            SELECT 'M_REG_2', 1, 'T_Defaulter' AS batting_team, 'T_Other' AS bowling_team, 120 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_REG_2', 2, 'T_Other', 'T_Defaulter', 120, 8, 120, FALSE
        """
        q = build_22cte_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        ta = [r for r in rows if r[3] == 'T_Awarded'][0]
        td = [r for r in rows if r[3] == 'T_Defaulter'][0]

        # Verify intermediate values:
        # T_Awarded: 160 runs scored off 120 balls; 140 runs conceded off 120 balls. Forfeit match completely excluded!
        assert ta[15] == 160 and ta[16] == 120 and ta[17] == 140 and ta[18] == 120
        # T_Defaulter: 120 runs scored off 240 balls (120 forfeit + 120 M_REG_2); 120 runs conceded off 120 balls (0 forfeit + 120 M_REG_2).
        assert td[15] == 120 and td[16] == 240 and td[17] == 120 and td[18] == 120

        # Exact NRR: T_Awarded = +1.000; T_Defaulter = (120/40) - (120/20) = 3.0 - 6.0 = -3.000.
        assert float(ta[9]) == 1.000 and float(td[9]) == -3.000

        test_results.append(("FORFEIT-INTERMED-01", "Forfeit with Zero Scorecard Rows", "PASS", "Intermediate values verified: Defaulter charged 0/120 balls (total 240 balls, NRR=-3.000); Awarded team excluded (NRR=+1.000)"))
        print("[PASS] FORFEIT-INTERMED-01: Forfeit with Zero Scorecard Rows")
    except Exception as e:
        all_passed = False
        test_results.append(("FORFEIT-INTERMED-01", "Forfeit with Zero Scorecard Rows", "FAIL", str(e)))
        print(f"[FAIL] FORFEIT-INTERMED-01: {e}")

    # --------------------------------------------------------------------------
    # Test 8: FORFEIT-PARTIAL-01 - Forfeit after Partial Innings
    # --------------------------------------------------------------------------
    try:
        # Match was forfeited after Team 1 batted 5 overs (40/2 in 30 balls). Team 2 awarded the match.
        # Scorecard has partial row.
        # Under Clause 16.10.4.b / 16.10.7, forfeit synthetic accounting overrides partial scorecard:
        # Defaulter (T1) is charged 0 runs / 120 balls. Awarded team (T2) is completely excluded.
        matches_sql = """
            SELECT 'M_FF_PARTIAL' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'T_PartDef' AS team1, 'T_PartAward' AS team2, 'T_PartAward' AS winner, 'forfeit' AS outcome_type, NULL::numeric AS target_overs, NULL::numeric AS target_runs, FALSE AS is_dls_applied, NULL::boolean AS is_dls_abandoned, NULL::numeric AS dls_allocated_overs, NULL::numeric AS dls_abandonment_overs, NULL::integer AS dls_par_score, TRUE AS scorecard_available, 'Forfeit after partial innings' AS source_note UNION ALL
            SELECT 'M_REG_1P', '2026-02-12'::date, 'Group Stage', 'Group Stage', 'A', 'T_PartAward', 'T_OtherP', 'T_PartAward', 'runs', 20.0, 160::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'M2' UNION ALL
            SELECT 'M_REG_2P', '2026-02-14'::date, 'Group Stage', 'Group Stage', 'A', 'T_PartDef', 'T_OtherP', 'T_PartDef', 'runs', 20.0, 120::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'M3'
        """
        summaries_sql = """
            -- Partial scorecard row:
            SELECT 'M_FF_PARTIAL' AS match_id, 1 AS innings, 'T_PartDef' AS batting_team, 'T_PartAward' AS bowling_team, 40 AS total_runs, 2 AS total_wickets, 30 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_REG_1P' AS match_id, 1 AS innings, 'T_PartAward' AS batting_team, 'T_OtherP' AS bowling_team, 160 AS total_runs, 4 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_REG_1P', 2, 'T_OtherP', 'T_PartAward', 140, 6, 120, FALSE UNION ALL
            SELECT 'M_REG_2P', 1, 'T_PartDef' AS batting_team, 'T_OtherP' AS bowling_team, 120 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_REG_2P', 2, 'T_OtherP', 'T_PartDef', 120, 8, 120, FALSE
        """
        q = build_22cte_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        ta = [r for r in rows if r[3] == 'T_PartAward'][0]
        td = [r for r in rows if r[3] == 'T_PartDef'][0]

        # Partial scorecard (40 runs in 30 balls) MUST BE OVERRIDDEN by synthetic forfeit record!
        assert ta[15] == 160 and ta[16] == 120 and ta[17] == 140 and ta[18] == 120
        assert td[15] == 120 and td[16] == 240 and td[17] == 120 and td[18] == 120
        assert float(ta[9]) == 1.000 and float(td[9]) == -3.000

        test_results.append(("FORFEIT-PARTIAL-01", "Forfeit after Partial Innings", "PASS", "Partial scorecard overridden by synthetic forfeit record; Defaulter debited 0/120 balls; Awarded team excluded"))
        print("[PASS] FORFEIT-PARTIAL-01: Forfeit after Partial Innings")
    except Exception as e:
        all_passed = False
        test_results.append(("FORFEIT-PARTIAL-01", "Forfeit after Partial Innings", "FAIL", str(e)))
        print(f"[FAIL] FORFEIT-PARTIAL-01: {e}")

    # --------------------------------------------------------------------------
    # Test 9: H2H-ALLOUT-TIE-01 - Integrated Multi-Team Tie with All-Out in Overall and H2H
    # --------------------------------------------------------------------------
    try:
        # 3 teams tied on 4 points and 2 wins: TeamA, TeamB, TeamC.
        # In their H2H round robin:
        # Match 1: TeamA beats TeamB (TeamB was all-out in 80 balls!).
        # Match 2: TeamB beats TeamC (TeamC was all-out in 80 balls!).
        # Match 3: TeamC beats TeamA (TeamA was all-out in 80 balls!).
        # Match 4, 5, 6: All three beat TeamD.
        # Verify that all-out expansion to 120 balls is applied symmetrically in BOTH overall NRR and H2H NRR!
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TeamA' AS team1, 'TeamB' AS team2, 'TeamA' AS winner, 'runs' AS outcome_type, 20.0::numeric AS target_overs, 161::numeric AS target_runs, FALSE AS is_dls_applied, NULL::boolean AS is_dls_abandoned, NULL::numeric AS dls_allocated_overs, NULL::numeric AS dls_abandonment_overs, NULL::integer AS dls_par_score, TRUE AS scorecard_available, 'A beats B' AS source_note UNION ALL
            SELECT 'M2', '2026-02-11'::date, 'Group Stage', 'Group Stage', 'A', 'TeamB', 'TeamC', 'TeamB', 'runs', 20.0, 161::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'B beats C' UNION ALL
            SELECT 'M3', '2026-02-12'::date, 'Group Stage', 'Group Stage', 'A', 'TeamC', 'TeamA', 'TeamC', 'runs', 20.0, 161::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'C beats A' UNION ALL
            SELECT 'M4', '2026-02-13'::date, 'Group Stage', 'Group Stage', 'A', 'TeamA', 'TeamD', 'TeamA', 'runs', 20.0, 160::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'A beats D' UNION ALL
            SELECT 'M5', '2026-02-14'::date, 'Group Stage', 'Group Stage', 'A', 'TeamB', 'TeamD', 'TeamB', 'runs', 20.0, 160::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'B beats D' UNION ALL
            SELECT 'M6', '2026-02-15'::date, 'Group Stage', 'Group Stage', 'A', 'TeamC', 'TeamD', 'TeamC', 'runs', 20.0, 160::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'C beats D'
        """
        summaries_sql = """
            -- M1: Team A 160/4 (120 b); Team B 100/10 (80 b -> expanded to 120!)
            SELECT 'M1' AS match_id, 1 AS innings, 'TeamA' AS batting_team, 'TeamB' AS bowling_team, 160 AS total_runs, 4 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'TeamB', 'TeamA', 100, 10, 80, FALSE UNION ALL
            -- M2: Team B 160/4 (120 b); Team C 100/10 (80 b -> expanded to 120!)
            SELECT 'M2', 1, 'TeamB', 'TeamC', 160, 4, 120, FALSE UNION ALL
            SELECT 'M2', 2, 'TeamC', 'TeamB', 100, 10, 80, FALSE UNION ALL
            -- M3: Team C 160/4 (120 b); Team A 100/10 (80 b -> expanded to 120!)
            SELECT 'M3', 1, 'TeamC', 'TeamA', 160, 4, 120, FALSE UNION ALL
            SELECT 'M3', 2, 'TeamA', 'TeamC', 100, 10, 80, FALSE UNION ALL
            -- M4: Team A 160/5; Team D 120/6 (both 120 b)
            SELECT 'M4', 1, 'TeamA', 'TeamD', 160, 5, 120, FALSE UNION ALL
            SELECT 'M4', 2, 'TeamD', 'TeamA', 120, 6, 120, FALSE UNION ALL
            -- M5: Team B 160/5; Team D 120/6 (both 120 b)
            SELECT 'M5', 1, 'TeamB', 'TeamD', 160, 5, 120, FALSE UNION ALL
            SELECT 'M5', 2, 'TeamD', 'TeamB', 120, 6, 120, FALSE UNION ALL
            -- M6: Team C 160/5; Team D 120/6 (both 120 b)
            SELECT 'M6', 1, 'TeamC', 'TeamD', 160, 5, 120, FALSE UNION ALL
            SELECT 'M6', 2, 'TeamD', 'TeamC', 120, 6, 120, FALSE
        """
        q = build_22cte_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        ta = [r for r in rows if r[3] == 'TeamA'][0]
        tb = [r for r in rows if r[3] == 'TeamB'][0]
        tc = [r for r in rows if r[3] == 'TeamC'][0]
        td = [r for r in rows if r[3] == 'TeamD'][0]

        # In overall standings: all 3 teams have 4 points, 2 wins, 1 loss.
        # Each scored 160 + 100 + 160 = 420 runs in 120 + 120 + 120 = 360 balls.
        # Each conceded 100 + 160 + 120 = 380 runs in 120 + 120 + 120 = 360 balls.
        # Overall NRR is identical for all 3: (420/60) - (380/60) = 7.000 - 6.333 = +0.667.
        assert float(ta[9]) == 0.667 and float(tb[9]) == 0.667 and float(tc[9]) == 0.667

        # H2H Points: Complete 3-way round robin played. Each won 1 match (2 pts).
        # H2H safe points = 2 for all three.
        assert ta[10] == 2 and tb[10] == 2 and tc[10] == 2

        # H2H NRR: In H2H matches, each played 2 matches.
        # In H2H, each scored 160 + 100 = 260 runs in 120 + 120 = 240 balls (all-out expanded to 120!).
        # Each conceded 100 + 160 = 260 runs in 120 + 120 = 240 balls (all-out bowling expanded to 120!).
        # H2H NRR = (260/40) - (260/40) = 0.000 for all three!
        assert float(ta[11]) == 0.000 and float(tb[11]) == 0.000 and float(tc[11]) == 0.000

        # Step 5 Pre-tournament rankings resolve the 3-way tie:
        # TeamA (#1) > TeamB (#2) > TeamC (#3).
        assert ta[2] == 1 and tb[2] == 2 and tc[2] == 3
        assert ta[14] == 'Qualified' and tb[14] == 'Qualified' and tc[14] == 'Eliminated'

        test_results.append(("H2H-ALLOUT-TIE-01", "Integrated 3-Way Tie with All-Out in Overall & H2H", "PASS", "All-out symmetry holds in both Overall (NRR=+0.667) and H2H (NRR=0.000); Step 5 ICC rank resolves"))
        print("[PASS] H2H-ALLOUT-TIE-01: Integrated 3-Way Tie with All-Out in Overall & H2H")
    except Exception as e:
        all_passed = False
        test_results.append(("H2H-ALLOUT-TIE-01", "Integrated 3-Way Tie with All-Out in Overall & H2H", "FAIL", str(e)))
        print(f"[FAIL] H2H-ALLOUT-TIE-01: {e}")

    # --------------------------------------------------------------------------
    # Test 10: PROD-RECON-01 - Live PostgreSQL 18.7 Reconciliation (All 28 Rows)
    # --------------------------------------------------------------------------
    try:
        matches_current_sql = """
            SELECT match_id, match_date, stage, group_name, team1, team2, winner, outcome_type,
                   target_overs, target_runs, is_dls_applied, NULL::boolean AS is_dls_abandoned,
                   NULL::numeric AS dls_allocated_overs, NULL::numeric AS dls_abandonment_overs,
                   NULL::integer AS dls_par_score, scorecard_available, source_note
            FROM dim_matches
        """
        summaries_current_sql = """
            SELECT match_id, innings, batting_team, bowling_team, total_runs, total_wickets,
                   legal_deliveries, total_overs, is_super_over
            FROM fact_match_summaries
        """
        q_prod = build_22cte_query(matches_current_sql, summaries_current_sql)
        cur.execute(q_prod)
        prod_rows = cur.fetchall()
        assert len(prod_rows) == 28, f"Expected 28 rows, got {len(prod_rows)}"

        sa = [r for r in prod_rows if r[0] == 'Super 8' and r[1] == '1' and r[3] == 'South Africa'][0]
        ind = [r for r in prod_rows if r[0] == 'Super 8' and r[1] == '1' and r[3] == 'India'][0]
        assert sa[2] == 1 and sa[8] == 6 and float(sa[9]) == 2.259 and sa[14] == 'Qualified'
        assert ind[2] == 2 and ind[8] == 4 and float(ind[9]) == 0.106 and ind[14] == 'Qualified'

        test_results.append(("PROD-RECON-01", "Live PostgreSQL 18.7 Reconciliation (All 28 Rows)", "PASS", "28/28 rows perfectly reconciled; zero data drift; SA & IND verified"))
        print("[PASS] PROD-RECON-01: Live PostgreSQL 18.7 Reconciliation (All 28 Rows)")
    except Exception as e:
        all_passed = False
        test_results.append(("PROD-RECON-01", "Live PostgreSQL 18.7 Reconciliation (All 28 Rows)", "FAIL", str(e)))
        print(f"[FAIL] PROD-RECON-01: {e}")

    # Rollback transaction so zero DDL remains in DB
    conn.rollback()
    conn.close()

    print("=" * 85)
    print("PHASE 4.9.6.14 AUDIT SUMMARY")
    print("=" * 85)
    for tid, name, res, detail in test_results:
        print(f"[{res}] {tid:<20} | {name:<45} | {detail}")
    print()
    if all_passed:
        print("OVERALL RESULT: ALL PHASE 4.9.6.14 TESTS PASSED (100%)")
    else:
        print("OVERALL RESULT: SOME TESTS FAILED")

    return all_passed

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
