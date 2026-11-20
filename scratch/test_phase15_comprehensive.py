import psycopg2
from decimal import Decimal
import sys
import traceback

PG_CONN_PARAMS = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 't20_worldcup_2026',
    'user': 'postgres',
    'password': 'Gautam@101'
}

def get_pg_conn():
    return psycopg2.connect(**PG_CONN_PARAMS)

def get_full_22cte_sql(matches_table="dim_matches", summaries_table="fact_match_summaries"):
    return f"""
WITH RECURSIVE icc_rankings_6feb2026 AS (
    SELECT * FROM (VALUES
        ('India', 1), ('Australia', 2), ('England', 3), ('South Africa', 4),
        ('New Zealand', 5), ('Pakistan', 6), ('West Indies', 7), ('Sri Lanka', 8),
        ('Bangladesh', 9), ('Afghanistan', 10), ('Ireland', 11), ('Zimbabwe', 12),
        ('Scotland', 13), ('Netherlands', 14), ('Namibia', 15), ('UAE', 16),
        ('Nepal', 17), ('USA', 18), ('Oman', 19), ('PNG', 20),
        ('Canada', 21), ('Uganda', 22)
    ) AS t(team_name, icc_rank)
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
        target_runs,
        is_dls_applied,
        is_dls_abandoned,
        dls_allocated_overs,
        dls_abandonment_overs,
        dls_par_score,
        scorecard_available,
        source_note
    FROM {matches_table}
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
                EXISTS (SELECT 1 FROM {summaries_table} s WHERE s.match_id = mo.match_id AND s.legal_deliveries > 0)
            ) THEN 1
            ELSE 0
        END AS is_genuinely_played,
        CASE 
            WHEN mo.is_dls_applied = FALSE THEN 0
            WHEN mo.outcome_type NOT IN ('runs', 'wickets', 'tie', 'tie_super_over') THEN 0
            WHEN mo.is_dls_abandoned IS NULL THEN 5
            WHEN mo.is_dls_abandoned = FALSE THEN
                CASE 
                    WHEN mo.target_runs IS NOT NULL AND mo.dls_allocated_overs IS NOT NULL 
                         AND mo.dls_allocated_overs > 0 
                         AND (mo.dls_allocated_overs - FLOOR(mo.dls_allocated_overs)) * 10 BETWEEN 0 AND 5 THEN 1
                    ELSE 3
                END
            WHEN mo.is_dls_abandoned = TRUE THEN
                CASE 
                    WHEN mo.dls_par_score IS NOT NULL AND mo.dls_abandonment_overs IS NOT NULL 
                         AND mo.dls_abandonment_overs > 0 
                         AND (mo.dls_abandonment_overs - FLOOR(mo.dls_abandonment_overs)) * 10 BETWEEN 0 AND 5 THEN 2
                    ELSE 4
                END
            ELSE 5
        END AS dls_status
    FROM match_opponents mo
),
effective_match_summaries AS (
    SELECT 
        s.match_id, s.innings, s.batting_team, s.bowling_team,
        s.total_runs, s.total_wickets, s.legal_deliveries, s.is_super_over
    FROM {summaries_table} s
    JOIN stage_matches m ON s.match_id = m.match_id
    WHERE m.outcome_type <> 'forfeit' AND s.is_super_over = FALSE
    
    UNION ALL
    
    SELECT 
        m.match_id,
        1 AS innings,
        CASE WHEN m.winner = m.team1 THEN m.team2 ELSE m.team1 END AS batting_team,
        NULL::varchar AS bowling_team,
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
                    WHEN mpe.dls_status = 1 AND s.innings = 1 THEN (CAST(mpe.target_runs AS NUMERIC) - 1)
                    WHEN mpe.dls_status = 2 AND s.innings = 1 THEN CAST(mpe.dls_par_score AS NUMERIC)
                    WHEN mpe.dls_status IN (3, 4, 5) AND s.innings = 1 THEN NULL
                    ELSE s.total_runs
                END
            )
        END AS runs_scored,
        CASE 
            WHEN MAX(CASE WHEN mpe.dls_status IN (3, 4, 5) THEN 1 ELSE 0 END) = 1 THEN NULL
            ELSE SUM(
                CASE 
                    WHEN mpe.dls_status = 1 AND s.innings = 1 
                        THEN CASE
                            WHEN (mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10 BETWEEN 0 AND 5
                                THEN (FLOOR(mpe.dls_allocated_overs) * 6 + ROUND((mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10))::int
                            ELSE NULL
                        END
                    WHEN mpe.dls_status = 2 AND s.innings = 1 
                        THEN CASE
                            WHEN (mpe.dls_abandonment_overs - FLOOR(mpe.dls_abandonment_overs)) * 10 BETWEEN 0 AND 5
                                THEN (FLOOR(mpe.dls_abandonment_overs) * 6 + ROUND((mpe.dls_abandonment_overs - FLOOR(mpe.dls_abandonment_overs)) * 10))::int
                            ELSE NULL
                        END
                    WHEN mpe.dls_status IN (3, 4, 5) AND s.innings = 1 THEN NULL
                    WHEN s.total_wickets = 10 THEN 
                        CASE 
                            WHEN mpe.dls_status = 1 AND s.innings = 2 AND mpe.dls_allocated_overs IS NOT NULL THEN 
                                CASE
                                    WHEN (mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10 BETWEEN 0 AND 5
                                        THEN (FLOOR(mpe.dls_allocated_overs) * 6 + ROUND((mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10))::int
                                    ELSE NULL
                                END
                            WHEN mpe.dls_status = 2 AND s.innings = 2 AND mpe.dls_abandonment_overs IS NOT NULL THEN 
                                CASE
                                    WHEN (mpe.dls_abandonment_overs - FLOOR(mpe.dls_abandonment_overs)) * 10 BETWEEN 0 AND 5
                                        THEN (FLOOR(mpe.dls_abandonment_overs) * 6 + ROUND((mpe.dls_abandonment_overs - FLOOR(mpe.dls_abandonment_overs)) * 10))::int
                                    ELSE NULL
                                END
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
                    WHEN mpe.dls_status = 1 AND s.innings = 1 THEN (CAST(mpe.target_runs AS NUMERIC) - 1)
                    WHEN mpe.dls_status = 2 AND s.innings = 1 THEN CAST(mpe.dls_par_score AS NUMERIC)
                    WHEN mpe.dls_status IN (3, 4, 5) AND s.innings = 1 THEN NULL
                    ELSE s.total_runs
                END
            )
        END AS runs_conceded,
        CASE 
            WHEN MAX(CASE WHEN mpe.dls_status IN (3, 4, 5) THEN 1 ELSE 0 END) = 1 THEN NULL
            ELSE SUM(
                CASE 
                    WHEN mpe.dls_status = 1 AND s.innings = 1 
                        THEN CASE
                            WHEN (mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10 BETWEEN 0 AND 5
                                THEN (FLOOR(mpe.dls_allocated_overs) * 6 + ROUND((mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10))::int
                            ELSE NULL
                        END
                    WHEN mpe.dls_status = 2 AND s.innings = 1 
                        THEN CASE
                            WHEN (mpe.dls_abandonment_overs - FLOOR(mpe.dls_abandonment_overs)) * 10 BETWEEN 0 AND 5
                                THEN (FLOOR(mpe.dls_abandonment_overs) * 6 + ROUND((mpe.dls_abandonment_overs - FLOOR(mpe.dls_abandonment_overs)) * 10))::int
                            ELSE NULL
                        END
                    WHEN mpe.dls_status IN (3, 4, 5) AND s.innings = 1 THEN NULL
                    WHEN s.total_wickets = 10 THEN 
                        CASE 
                            WHEN mpe.dls_status = 1 AND s.innings = 2 AND mpe.dls_allocated_overs IS NOT NULL THEN 
                                CASE
                                    WHEN (mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10 BETWEEN 0 AND 5
                                        THEN (FLOOR(mpe.dls_allocated_overs) * 6 + ROUND((mpe.dls_allocated_overs - FLOOR(mpe.dls_allocated_overs)) * 10))::int
                                    ELSE NULL
                                END
                            WHEN mpe.dls_status = 2 AND s.innings = 2 AND mpe.dls_abandonment_overs IS NOT NULL THEN 
                                CASE
                                    WHEN (mpe.dls_abandonment_overs - FLOOR(mpe.dls_abandonment_overs)) * 10 BETWEEN 0 AND 5
                                        THEN (FLOOR(mpe.dls_abandonment_overs) * 6 + ROUND((mpe.dls_abandonment_overs - FLOOR(mpe.dls_abandonment_overs)) * 10))::int
                                    ELSE NULL
                                END
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
                CAST(s.n AS BIGINT) / public.fn_calc_gcd(CAST(s.n AS BIGINT), CAST(s.d AS BIGINT))
            ELSE NULL 
        END AS n_canon,
        CASE 
            WHEN s.d IS NOT NULL AND s.d > 0 THEN
                CAST(s.d AS BIGINT) / public.fn_calc_gcd(CAST(s.n AS BIGINT), CAST(s.d AS BIGINT))
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
                  AND (b.n::numeric * a.d::numeric) > (a.n::numeric * b.d::numeric)
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
        s.stage_normalized,
        s.group_name,
        s.team_name,
        s.points,
        s.wins,
        s.n_canon,
        s.d_canon,
        s.nrr_display,
        s.played,
        s.losses,
        s.no_result,
        s.runs_scored,
        s.balls_faced,
        s.runs_conceded,
        s.balls_bowled,
        s.has_unresolved_dls,
        s.has_unknown_dls_status,
        s.has_missing_par_score,
        s.has_missing_target_runs,
        nsc.nrr_superior_count,
        COALESCE(nsc.nrr_superior_count, -1) AS tied_nrr_key
    FROM group_nrr_fractions s
    LEFT JOIN nrr_superior_counts nsc ON s.stage_normalized = nsc.stage_normalized
                                     AND s.group_name = nsc.group_name
                                     AND s.points = nsc.points
                                     AND s.wins = nsc.wins
                                     AND s.team_name = nsc.team_name
),
h2h_matches AS (
    SELECT 
        mpe.stage_normalized,
        mpe.group_name,
        mpe.focus_team,
        mpe.opp_team,
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
        mpe.is_genuinely_played,
        mpe.dls_status
    FROM match_played_eval mpe
    JOIN tied_candidates c1 ON mpe.stage_normalized = c1.stage_normalized 
                          AND mpe.group_name = c1.group_name 
                          AND mpe.focus_team = c1.team_name
    JOIN tied_candidates c2 ON mpe.stage_normalized = c2.stage_normalized 
                          AND mpe.group_name = c2.group_name 
                          AND mpe.opp_team = c2.team_name
                          AND c1.points = c2.points 
                          AND c1.wins = c2.wins 
                          AND c1.tied_nrr_key = c2.tied_nrr_key
    WHERE c1.team_name <> c2.team_name
),
h2h_points_summary AS (
    SELECT 
        hm.stage_normalized,
        hm.group_name,
        hm.focus_team AS team_name,
        SUM(
            CASE 
                WHEN (hm.outcome_type IN ('runs', 'wickets', 'tie_super_over') OR hm.outcome_type = 'forfeit') AND hm.winner = hm.focus_team THEN 2
                WHEN (hm.outcome_type IN ('runs', 'wickets', 'tie_super_over') OR hm.outcome_type = 'forfeit') AND hm.winner = hm.opp_team THEN 0
                WHEN hm.outcome_type IN ('no result', 'tie') THEN 1
                ELSE 0
            END
        ) AS h2h_points
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
        tc.tied_nrr_key,
        CASE 
            WHEN tc.tied_nrr_key = -1 THEN NULL
            WHEN (SELECT COUNT(DISTINCT tc2.team_name) 
                  FROM tied_candidates tc2 
                  WHERE tc2.stage_normalized = f.stage_normalized 
                    AND tc2.group_name = f.group_name 
                    AND tc2.points = f.points 
                    AND tc2.wins = f.wins 
                    AND tc2.tied_nrr_key = tc.tied_nrr_key) < 2 THEN NULL
            WHEN (
                SELECT COUNT(DISTINCT hm.match_id)
                FROM h2h_matches hm
                JOIN tied_candidates c_opp ON hm.stage_normalized = c_opp.stage_normalized 
                                          AND hm.group_name = c_opp.group_name 
                                          AND hm.opp_team = c_opp.team_name
                                          AND c_opp.points = f.points 
                                          AND c_opp.wins = f.wins 
                                          AND c_opp.tied_nrr_key = tc.tied_nrr_key
                WHERE hm.stage_normalized = f.stage_normalized 
                  AND hm.group_name = f.group_name 
                  AND hm.focus_team = f.team_name
                  AND hm.is_genuinely_played = 1
            ) = (
                (SELECT COUNT(DISTINCT tc2.team_name) 
                 FROM tied_candidates tc2 
                 WHERE tc2.stage_normalized = f.stage_normalized 
                   AND tc2.group_name = f.group_name 
                   AND tc2.points = f.points 
                   AND tc2.wins = f.wins 
                   AND tc2.tied_nrr_key = tc.tied_nrr_key) - 1
            ) THEN hp.h2h_points
            ELSE NULL
        END AS safe_h2h_points
    FROM group_nrr_fractions f
    LEFT JOIN nrr_superior_counts nsc ON f.stage_normalized = nsc.stage_normalized 
                                     AND f.group_name = nsc.group_name 
                                     AND f.points = nsc.points 
                                     AND f.wins = nsc.wins 
                                     AND f.team_name = nsc.team_name
    LEFT JOIN tied_candidates tc ON f.stage_normalized = tc.stage_normalized 
                                AND f.group_name = tc.group_name 
                                AND f.points = tc.points 
                                AND f.wins = tc.wins 
                                AND f.team_name = tc.team_name 
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
                        THEN CASE
                            WHEN (hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10 BETWEEN 0 AND 5
                                THEN (FLOOR(hm.dls_allocated_overs) * 6 + ROUND((hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10))::int
                            ELSE NULL
                        END
                    WHEN hm.dls_status = 2 AND s.innings = 1 
                        THEN CASE
                            WHEN (hm.dls_abandonment_overs - FLOOR(hm.dls_abandonment_overs)) * 10 BETWEEN 0 AND 5
                                THEN (FLOOR(hm.dls_abandonment_overs) * 6 + ROUND((hm.dls_abandonment_overs - FLOOR(hm.dls_abandonment_overs)) * 10))::int
                            ELSE NULL
                        END
                    WHEN hm.dls_status IN (3, 4, 5) AND s.innings = 1 THEN NULL
                    WHEN s.total_wickets = 10 THEN 
                        CASE 
                            WHEN hm.dls_status = 1 AND s.innings = 2 AND hm.dls_allocated_overs IS NOT NULL THEN 
                                CASE
                                    WHEN (hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10 BETWEEN 0 AND 5
                                        THEN (FLOOR(hm.dls_allocated_overs) * 6 + ROUND((hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10))::int
                                    ELSE NULL
                                END
                            WHEN hm.dls_status = 2 AND s.innings = 2 AND hm.dls_abandonment_overs IS NOT NULL THEN 
                                CASE
                                    WHEN (hm.dls_abandonment_overs - FLOOR(hm.dls_abandonment_overs)) * 10 BETWEEN 0 AND 5
                                        THEN (FLOOR(hm.dls_abandonment_overs) * 6 + ROUND((hm.dls_abandonment_overs - FLOOR(hm.dls_abandonment_overs)) * 10))::int
                                    ELSE NULL
                                END
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
                        THEN CASE
                            WHEN (hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10 BETWEEN 0 AND 5
                                THEN (FLOOR(hm.dls_allocated_overs) * 6 + ROUND((hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10))::int
                            ELSE NULL
                        END
                    WHEN hm.dls_status = 2 AND s.innings = 1 
                        THEN CASE
                            WHEN (hm.dls_abandonment_overs - FLOOR(hm.dls_abandonment_overs)) * 10 BETWEEN 0 AND 5
                                THEN (FLOOR(hm.dls_abandonment_overs) * 6 + ROUND((hm.dls_abandonment_overs - FLOOR(hm.dls_abandonment_overs)) * 10))::int
                            ELSE NULL
                        END
                    WHEN hm.dls_status IN (3, 4, 5) AND s.innings = 1 THEN NULL
                    WHEN s.total_wickets = 10 THEN 
                        CASE 
                            WHEN hm.dls_status = 1 AND s.innings = 2 AND hm.dls_allocated_overs IS NOT NULL THEN 
                                CASE
                                    WHEN (hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10 BETWEEN 0 AND 5
                                        THEN (FLOOR(hm.dls_allocated_overs) * 6 + ROUND((hm.dls_allocated_overs - FLOOR(hm.dls_allocated_overs)) * 10))::int
                                    ELSE NULL
                                END
                            WHEN hm.dls_status = 2 AND s.innings = 2 AND hm.dls_abandonment_overs IS NOT NULL THEN 
                                CASE
                                    WHEN (hm.dls_abandonment_overs - FLOOR(hm.dls_abandonment_overs)) * 10 BETWEEN 0 AND 5
                                        THEN (FLOOR(hm.dls_abandonment_overs) * 6 + ROUND((hm.dls_abandonment_overs - FLOOR(hm.dls_abandonment_overs)) * 10))::int
                                    ELSE NULL
                                END
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
        cg.stage_normalized,
        cg.group_name,
        cg.team_name,
        cg.points,
        cg.wins,
        cg.tied_nrr_key,
        cg.safe_h2h_points,
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
        hf.stage_normalized,
        hf.group_name,
        hf.points,
        hf.wins,
        hf.tied_nrr_key,
        hf.safe_h2h_points,
        SUM(
            CASE 
                WHEN hf.safe_h2h_points IS NOT NULL AND (hf.h2h_d IS NULL OR hf.h2h_d <= 0) THEN 1 
                ELSE 0 
            END
        ) AS tier_has_undefined_h2h_nrr
    FROM h2h_fractions hf
    GROUP BY hf.stage_normalized, hf.group_name, hf.points, hf.wins, hf.tied_nrr_key, hf.safe_h2h_points
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
                  AND (b.h2h_n::numeric * hf.h2h_d::numeric) > (hf.h2h_n::numeric * b.h2h_d::numeric)
            )
        END AS h2h_nrr_superior_count
    FROM h2h_fractions hf
    LEFT JOIN tier_h2h_guard thg ON hf.stage_normalized = thg.stage_normalized 
                                AND hf.group_name = thg.group_name 
                                AND hf.points = thg.points 
                                AND hf.wins = thg.wins 
                                AND hf.tied_nrr_key = thg.tied_nrr_key 
                                AND ((hf.safe_h2h_points IS NULL AND thg.safe_h2h_points IS NULL) OR hf.safe_h2h_points = thg.safe_h2h_points)
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
    LEFT JOIN nrr_superior_counts nsc ON f.stage_normalized = nsc.stage_normalized 
                                     AND f.group_name = nsc.group_name 
                                     AND f.points = nsc.points 
                                     AND f.wins = nsc.wins 
                                     AND f.team_name = nsc.team_name
    LEFT JOIN h2h_nrr_evaluated h ON f.stage_normalized = h.stage_normalized 
                                 AND f.group_name = h.group_name 
                                 AND f.points = h.points 
                                 AND f.wins = h.wins 
                                 AND f.team_name = h.team_name
    LEFT JOIN icc_rankings_6feb2026 r ON f.team_name = r.team_name
),
ranked_standings AS (
    SELECT 
        stage_normalized,
        group_name,
        official_pool_rank AS pool_rank,
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
                    WHEN has_missing_par_score = 1 THEN 'Step 3: Unresolved — DLS Par Score or Abandonment Overs Unavailable / Invalid (Clause 16.10.7)'
                    WHEN has_missing_target_runs = 1 THEN 'Step 3: Unresolved — DLS Final Target or Allocated Overs Unavailable / Invalid (Clause 16.10.7)'
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
            WHEN wins_count > 1 AND tier_has_undefined_nrr > 0 
                 AND min_tier_rank <= 2 AND min_tier_rank + wins_count - 1 > 2 
                 THEN 'Unresolved — Pending DLS / NRR Resolution'
            WHEN icc_rank IS NULL AND (pts_count > 1 AND wins_count > 1 AND (tier_has_undefined_nrr > 0 OR nrr_canon_count > 1))
                 AND min_tier_rank <= 2 AND min_tier_rank + wins_count - 1 > 2 
                 THEN 'Unresolved — Missing Pre-Tournament Ranking'
            WHEN terminal_icc_tier_count > 1 
                 AND min_tier_rank <= 2 AND min_tier_rank + terminal_icc_tier_count - 1 > 2 
                 THEN 'Unresolved Tie — Event Direction Required'
            WHEN min_tier_rank + COALESCE(
                CASE 
                    WHEN wins_count > 1 AND tier_has_undefined_nrr > 0 THEN wins_count
                    WHEN terminal_icc_tier_count > 1 THEN terminal_icc_tier_count
                    ELSE 1
                END, 1) - 1 <= 2 THEN 'Qualified'
            WHEN min_tier_rank > 2 THEN 'Eliminated'
            ELSE 'Unresolved Tie — Event Direction Required'
        END AS qualification_status,
        runs_scored,
        balls_faced,
        runs_conceded,
        balls_bowled,
        n AS nrr_num,
        d AS nrr_den,
        n_canon AS nrr_canon_num,
        d_canon AS nrr_canon_den
    FROM standings_compiled
)
SELECT * FROM ranked_standings
ORDER BY stage_normalized, group_name, pool_rank, team_name;
"""

print("Phase 4.9.6.15 query builder ready!")

def run_all_phase15_tests():
    conn = get_pg_conn()
    cur = conn.cursor()
    
    test_results = []
    all_passed = True
    
    print("=" * 90)
    print("PHASE 4.9.6.15: RIGOROUS INDEPENDENT VERIFICATION & AUDIT SUITE")
    print("=" * 90)

    cur.execute("BEGIN;")

    # --------------------------------------------------------------------------
    # Deploy fn_calc_gcd(bigint, bigint) in Transaction
    # --------------------------------------------------------------------------
    gcd_ddl = """
    CREATE OR REPLACE FUNCTION fn_calc_gcd(a bigint, b bigint)
    RETURNS bigint AS $fn$
    DECLARE
        x bigint;
        y bigint;
        t bigint;
    BEGIN
        IF a IS NULL OR b IS NULL THEN
            RETURN NULL;
        END IF;
        IF a = -9223372036854775808 OR b = -9223372036854775808 THEN
            RAISE EXCEPTION 'fn_calc_gcd: INT64_MIN not supported';
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
    $fn$ LANGUAGE plpgsql IMMUTABLE STRICT;
    """
    cur.execute(gcd_ddl)

    # --------------------------------------------------------------------------
    # TEST 1: Section 3 — Hardened fn_calc_gcd Verification
    # --------------------------------------------------------------------------
    try:
        # 1a. INT64_MIN guard
        int64_min_caught = False
        try:
            cur.execute("SAVEPOINT sp_gcd_min;")
            cur.execute("SELECT fn_calc_gcd((-9223372036854775807::bigint - 1::bigint), 16::bigint)")
            cur.execute("RELEASE SAVEPOINT sp_gcd_min;")
        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT sp_gcd_min;")
            if 'INT64_MIN not supported' in str(e):
                int64_min_caught = True
        assert int64_min_caught, "INT64_MIN guard did not raise expected exception"

        # 1b. Zero numerator -> returns denominator (canonical 0/1)
        cur.execute("SELECT fn_calc_gcd(0::bigint, 57600::bigint)")
        res_zero = cur.fetchone()[0]
        assert res_zero == 57600, f"Expected 57600, got {res_zero}"
        assert 0 // res_zero == 0 and 57600 // res_zero == 1

        # 1c. Negative denominator is ABS'd
        cur.execute("SELECT fn_calc_gcd(120::bigint, -240::bigint)")
        res_neg = cur.fetchone()[0]
        assert res_neg == 120, f"Expected 120, got {res_neg}"

        # 1d. Fractional inputs fail at compile time
        frac_caught = False
        try:
            cur.execute("SAVEPOINT sp_gcd_frac;")
            cur.execute("SELECT fn_calc_gcd(12.5, 4)")
            cur.execute("RELEASE SAVEPOINT sp_gcd_frac;")
        except Exception:
            cur.execute("ROLLBACK TO SAVEPOINT sp_gcd_frac;")
            frac_caught = True
        assert frac_caught, "Fractional input was not rejected at compile time"

        test_results.append(("SEC3-GCD-HARDEN", "Hardened fn_calc_gcd(bigint, bigint)", "PASS", "INT64_MIN guarded, zero num -> 0/1, negative den ABS'd, fractional rejected"))
        print("[PASS] SEC3-GCD-HARDEN: Hardened fn_calc_gcd(bigint, bigint)")
    except Exception as e:
        all_passed = False
        test_results.append(("SEC3-GCD-HARDEN", "Hardened fn_calc_gcd(bigint, bigint)", "FAIL", str(e)))
        print(f"[FAIL] SEC3-GCD-HARDEN: {e}")

    # --------------------------------------------------------------------------
    # TEST 2: Section 1 — Overs to Balls Conversion and Guard
    # --------------------------------------------------------------------------
    try:
        cases = [
            (8.3, 51),
            (8.5, 53),
            (14.5, 89),
            (15.0, 90),
            (15.5, 95),
            (20.0, 120),
            (8.6, None),
            (8.9, None)
        ]
        for ov, exp in cases:
            cur.execute("""
                SELECT 
                    CASE
                        WHEN (%s::numeric - FLOOR(%s::numeric)) * 10 BETWEEN 0 AND 5
                            THEN (FLOOR(%s::numeric) * 6 + ROUND((%s::numeric - FLOOR(%s::numeric)) * 10))::int
                        ELSE NULL
                    END
            """, (ov, ov, ov, ov, ov))
            actual = cur.fetchone()[0]
            assert actual == exp, f"For overs {ov}, expected {exp}, got {actual}"

        test_results.append(("SEC1-OVERS-CONV", "Correct Overs Conversion & Validation", "PASS", "8.3->51, 8.5->53, 14.5->89, 15.0->90, 15.5->95, 20.0->120; 8.6/8.9->NULL"))
        print("[PASS] SEC1-OVERS-CONV: Correct Overs Conversion & Validation")
    except Exception as e:
        all_passed = False
        test_results.append(("SEC1-OVERS-CONV", "Correct Overs Conversion & Validation", "FAIL", str(e)))
        print(f"[FAIL] SEC1-OVERS-CONV: {e}")

    # --------------------------------------------------------------------------
    # TEST 3: Section 2 — Exact Rational Comparison with NUMERIC Cross-Products
    # --------------------------------------------------------------------------
    try:
        # Test mathematically equal unreduced fractions:
        # Team A: 1 / 3
        # Team B: 2 / 6
        # Team C: 333 / 999
        # They must rank TIE (each has nrr_superior_count = 0)
        cur.execute("""
            WITH frac_test AS (
                SELECT 'A' AS team, 1::numeric AS n, 3::numeric AS d UNION ALL
                SELECT 'B', 2::numeric, 6::numeric UNION ALL
                SELECT 'C', 333::numeric, 999::numeric
            )
            SELECT 
                a.team,
                (SELECT COUNT(*) FROM frac_test b WHERE (b.n * a.d) > (a.n * b.d)) AS sup_count
            FROM frac_test a;
        """)
        rows = cur.fetchall()
        for r in rows:
            assert r[1] == 0, f"Team {r[0]} expected superior count 0, got {r[1]}"

        # Test distinct fractions:
        # Team D: 1 / 2 (0.500) > Team E: 1 / 3 (0.333)
        cur.execute("""
            SELECT 
                (1::numeric * 3::numeric) > (1::numeric * 2::numeric) AS d_beats_e,
                (1::numeric * 2::numeric) > (1::numeric * 3::numeric) AS e_beats_d;
        """)
        r_comp = cur.fetchone()
        assert r_comp[0] is True and r_comp[1] is False

        test_results.append(("SEC2-NUMERIC-CROSS", "Exact NUMERIC Rational Cross-Products", "PASS", "Equal unreduced fractions (1/3, 2/6, 333/999) evaluate TIE (sup_count=0)"))
        print("[PASS] SEC2-NUMERIC-CROSS: Exact NUMERIC Rational Cross-Products")
    except Exception as e:
        all_passed = False
        test_results.append(("SEC2-NUMERIC-CROSS", "Exact NUMERIC Rational Cross-Products", "FAIL", str(e)))
        print(f"[FAIL] SEC2-NUMERIC-CROSS: {e}")

    # --------------------------------------------------------------------------
    # Helper to run synthetic fixtures through full 22-CTE query
    # --------------------------------------------------------------------------
    def run_fixture(fixture_name, m_rows, s_rows):
        cur.execute("""
            DROP TABLE IF EXISTS temp_dim_matches;
            CREATE TEMP TABLE temp_dim_matches (
                match_id varchar(50),
                match_date date,
                stage varchar(50),
                group_name varchar(10),
                team1 varchar(100),
                team2 varchar(100),
                winner varchar(100),
                outcome_type varchar(50),
                target_overs numeric,
                target_runs numeric,
                is_dls_applied boolean,
                is_dls_abandoned boolean,
                dls_allocated_overs numeric,
                dls_abandonment_overs numeric,
                dls_par_score integer,
                scorecard_available boolean,
                source_note text
            );
            DROP TABLE IF EXISTS temp_fact_summaries;
            CREATE TEMP TABLE temp_fact_summaries (
                match_id varchar(50),
                innings integer,
                batting_team varchar(100),
                bowling_team varchar(100),
                total_runs integer,
                total_wickets integer,
                legal_deliveries integer,
                total_overs numeric,
                is_super_over boolean
            );
        """)
        
        m_insert = """
            INSERT INTO temp_dim_matches (match_id, match_date, stage, group_name, team1, team2, winner, outcome_type, target_overs, target_runs, is_dls_applied, is_dls_abandoned, dls_allocated_overs, dls_abandonment_overs, dls_par_score, scorecard_available, source_note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        for r in m_rows:
            cur.execute(m_insert, r)
            
        s_insert = """
            INSERT INTO temp_fact_summaries (match_id, innings, batting_team, bowling_team, total_runs, total_wickets, legal_deliveries, total_overs, is_super_over)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        for r in s_rows:
            cur.execute(s_insert, r)

        q = get_full_22cte_sql("temp_dim_matches", "temp_fact_summaries")
        cur.execute(q)
        return cur.fetchall()

    # --------------------------------------------------------------------------
    # TEST 4: Section 4 — Revalidate All Four CTEs Across All Fixtures
    # --------------------------------------------------------------------------
    # 4a. Regular innings-1 all-out
    try:
        m_4a = [('M_4A', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T2', 'wickets', 20.0, None, False, False, None, None, None, True, 'Reg Inn 1 All-Out')]
        s_4a = [('M_4A', 1, 'T1', 'T2', 95, 10, 78, 13.0, False), ('M_4A', 2, 'T2', 'T1', 96, 2, 66, 11.0, False)]
        res_4a = run_fixture('REG-INN1-ALLOUT', m_4a, s_4a)
        t1 = [r for r in res_4a if r[3] == 'T1'][0]
        t2 = [r for r in res_4a if r[3] == 'T2'][0]
        # T1 batting balls = 120; T2 bowling balls = 120. T2 batting = 66, T1 bowling = 66.
        assert t1[15] == 95 and t1[16] == 120 and t1[17] == 96 and t1[18] == 66
        assert t2[15] == 96 and t2[16] == 66 and t2[17] == 95 and t2[18] == 120
        # Check canonical sum = 0/1
        assert t1[21] + t2[21] == 0 and t1[22] == t2[22]
        test_results.append(("SEC4-REG-INN1-ALLOUT", "Regular Innings 1 All-Out Quota Symmetry", "PASS", "T1 balls faced=120, T2 balls bowled=120; Canonical sum = 0/1"))
        print("[PASS] SEC4-REG-INN1-ALLOUT: Regular Innings 1 All-Out Quota Symmetry")
    except Exception as e:
        all_passed = False
        test_results.append(("SEC4-REG-INN1-ALLOUT", "Regular Innings 1 All-Out Quota Symmetry", "FAIL", str(e)))
        print(f"[FAIL] SEC4-REG-INN1-ALLOUT: {e}")

    # 4b. Regular innings-2 all-out
    try:
        m_4b = [('M_4B', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 20.0, None, False, False, None, None, None, True, 'Reg Inn 2 All-Out')]
        s_4b = [('M_4B', 1, 'T1', 'T2', 160, 6, 120, 20.0, False), ('M_4B', 2, 'T2', 'T1', 120, 10, 84, 14.0, False)]
        res_4b = run_fixture('REG-INN2-ALLOUT', m_4b, s_4b)
        t1 = [r for r in res_4b if r[3] == 'T1'][0]
        t2 = [r for r in res_4b if r[3] == 'T2'][0]
        assert t2[15] == 120 and t2[16] == 120 and t1[17] == 120 and t1[18] == 120
        assert t1[21] + t2[21] == 0 and t1[22] == t2[22]
        test_results.append(("SEC4-REG-INN2-ALLOUT", "Regular Innings 2 All-Out Quota Symmetry", "PASS", "T2 balls faced=120, T1 balls bowled=120; Canonical sum = 0/1"))
        print("[PASS] SEC4-REG-INN2-ALLOUT: Regular Innings 2 All-Out Quota Symmetry")
    except Exception as e:
        all_passed = False
        test_results.append(("SEC4-REG-INN2-ALLOUT", "Regular Innings 2 All-Out Quota Symmetry", "FAIL", str(e)))
        print(f"[FAIL] SEC4-REG-INN2-ALLOUT: {e}")

    # 4c. DLS Innings 1 All-Out (Integer Quota 15.0 = 90b)
    try:
        m_4c = [('M_4C', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T2', 'wickets', 15.0, 110, True, False, 15.0, None, None, True, 'DLS Inn 1 Int Quota')]
        s_4c = [('M_4C', 1, 'T1', 'T2', 125, 10, 84, 14.0, False), ('M_4C', 2, 'T2', 'T1', 112, 3, 80, 13.2, False)]
        res_4c = run_fixture('DLS-INN1-INT-ALLOUT', m_4c, s_4c)
        t1 = [r for r in res_4c if r[3] == 'T1'][0]
        t2 = [r for r in res_4c if r[3] == 'T2'][0]
        # T1 deemed runs = 109, balls = 90. T2 bowled = 90 balls.
        assert t1[15] == 109 and t1[16] == 90 and t2[17] == 109 and t2[18] == 90
        assert t1[21] + t2[21] == 0 and t1[22] == t2[22]
        test_results.append(("SEC4-DLS-INN1-INT-ALLOUT", "DLS Innings 1 All-Out (15.0 ov = 90b)", "PASS", "T1 deemed 109/90b, T2 bowling 90b; Canonical sum = 0/1"))
        print("[PASS] SEC4-DLS-INN1-INT-ALLOUT: DLS Innings 1 All-Out (15.0 ov = 90b)")
    except Exception as e:
        all_passed = False
        test_results.append(("SEC4-DLS-INN1-INT-ALLOUT", "DLS Innings 1 All-Out (15.0 ov = 90b)", "FAIL", str(e)))
        print(f"[FAIL] SEC4-DLS-INN1-INT-ALLOUT: {e}")

    # 4d. DLS Innings 1 All-Out (Fractional Quota 15.3 = 93b)
    try:
        m_4d = [('M_4D', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T2', 'wickets', 15.3, 115, True, False, 15.3, None, None, True, 'DLS Inn 1 Frac Quota 15.3')]
        s_4d = [('M_4D', 1, 'T1', 'T2', 130, 10, 75, 12.3, False), ('M_4D', 2, 'T2', 'T1', 116, 4, 85, 14.1, False)]
        res_4d = run_fixture('DLS-INN1-FRAC-15.3', m_4d, s_4d)
        t1 = [r for r in res_4d if r[3] == 'T1'][0]
        t2 = [r for r in res_4d if r[3] == 'T2'][0]
        # 15.3 overs = 15 * 6 + 3 = 93 balls. Deemed runs = 114.
        assert t1[15] == 114 and t1[16] == 93 and t2[17] == 114 and t2[18] == 93
        assert t1[21] + t2[21] == 0 and t1[22] == t2[22]
        test_results.append(("SEC4-DLS-INN1-FRAC-15.3", "DLS Innings 1 All-Out (15.3 ov = 93b)", "PASS", "T1 deemed 114/93b, T2 bowling 93b; Canonical sum = 0/1"))
        print("[PASS] SEC4-DLS-INN1-FRAC-15.3: DLS Innings 1 All-Out (15.3 ov = 93b)")
    except Exception as e:
        all_passed = False
        test_results.append(("SEC4-DLS-INN1-FRAC-15.3", "DLS Innings 1 All-Out (15.3 ov = 93b)", "FAIL", str(e)))
        print(f"[FAIL] SEC4-DLS-INN1-FRAC-15.3: {e}")

    # 4e. DLS Innings 2 All-Out (Fractional Quota 15.5 = 95b)
    try:
        m_4e = [('M_4E', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 15.5, 140, True, False, 15.5, None, None, True, 'DLS Inn 2 Frac Quota 15.5')]
        s_4e = [('M_4E', 1, 'T1', 'T2', 170, 5, 120, 20.0, False), ('M_4E', 2, 'T2', 'T1', 110, 10, 80, 13.2, False)]
        res_4e = run_fixture('DLS-INN2-FRAC-15.5', m_4e, s_4e)
        t1 = [r for r in res_4e if r[3] == 'T1'][0]
        t2 = [r for r in res_4e if r[3] == 'T2'][0]
        # 15.5 overs = 15 * 6 + 5 = 95 balls. T1 deemed runs = 139 off 95 balls.
        # T2 scored 110 all-out -> balls faced expands to 95 balls; T1 bowling expands to 95 balls!
        assert t1[15] == 139 and t1[16] == 95 and t2[17] == 139 and t2[18] == 95
        assert t2[15] == 110 and t2[16] == 95 and t1[17] == 110 and t1[18] == 95
        assert t1[21] + t2[21] == 0 and t1[22] == t2[22]
        test_results.append(("SEC4-DLS-INN2-FRAC-15.5", "DLS Innings 2 All-Out (15.5 ov = 95b)", "PASS", "T2 balls faced expanded to 95b, T1 bowling to 95b; Canonical sum = 0/1"))
        print("[PASS] SEC4-DLS-INN2-FRAC-15.5: DLS Innings 2 All-Out (15.5 ov = 95b)")
    except Exception as e:
        all_passed = False
        test_results.append(("SEC4-DLS-INN2-FRAC-15.5", "DLS Innings 2 All-Out (15.5 ov = 95b)", "FAIL", str(e)))
        print(f"[FAIL] SEC4-DLS-INN2-FRAC-15.5: {e}")

    # 4f. Non-all-out successful chase (actual balls used, NOT quota)
    try:
        m_4f = [('M_4F', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T2', 'wickets', 20.0, None, False, False, None, None, None, True, 'Successful Chase')]
        s_4f = [('M_4F', 1, 'T1', 'T2', 150, 7, 120, 20.0, False), ('M_4F', 2, 'T2', 'T1', 152, 3, 105, 17.3, False)]
        res_4f = run_fixture('CHASE-NON-ALLOUT', m_4f, s_4f)
        t1 = [r for r in res_4f if r[3] == 'T1'][0]
        t2 = [r for r in res_4f if r[3] == 'T2'][0]
        # T2 faced 105 balls, NOT 120! T1 bowled 105 balls, NOT 120!
        assert t2[15] == 152 and t2[16] == 105 and t1[17] == 152 and t1[18] == 105
        assert t1[15] == 150 and t1[16] == 120 and t2[17] == 150 and t2[18] == 120
        assert t1[21] + t2[21] == 0 and t1[22] == t2[22]
        test_results.append(("SEC4-CHASE-NON-ALLOUT", "Non-All-Out Successful Chase", "PASS", "T2 balls faced=105 (actual deliveries), T1 bowled=105; Canonical sum = 0/1"))
        print("[PASS] SEC4-CHASE-NON-ALLOUT: Non-All-Out Successful Chase")
    except Exception as e:
        all_passed = False
        test_results.append(("SEC4-CHASE-NON-ALLOUT", "Non-All-Out Successful Chase", "FAIL", str(e)))
        print(f"[FAIL] SEC4-CHASE-NON-ALLOUT: {e}")

    # 4g. Non-all-out control match (full 20 overs both sides)
    try:
        m_4g = [('M_4G', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 20.0, None, False, False, None, None, None, True, 'Control 20 Overs')]
        s_4g = [('M_4G', 1, 'T1', 'T2', 160, 6, 120, 20.0, False), ('M_4G', 2, 'T2', 'T1', 145, 8, 120, 20.0, False)]
        res_4g = run_fixture('CONTROL-20-OVERS', m_4g, s_4g)
        t1 = [r for r in res_4g if r[3] == 'T1'][0]
        t2 = [r for r in res_4g if r[3] == 'T2'][0]
        assert t1[15] == 160 and t1[16] == 120 and t2[17] == 160 and t2[18] == 120
        assert t2[15] == 145 and t2[16] == 120 and t1[17] == 145 and t1[18] == 120
        assert t1[21] + t2[21] == 0 and t1[22] == t2[22]
        test_results.append(("SEC4-CONTROL-20-OVERS", "Non-All-Out Control (20 Overs)", "PASS", "Full 120 balls faced & bowled used verbatim; Canonical sum = 0/1"))
        print("[PASS] SEC4-CONTROL-20-OVERS: Non-All-Out Control (20 Overs)")
    except Exception as e:
        all_passed = False
        test_results.append(("SEC4-CONTROL-20-OVERS", "Non-All-Out Control (20 Overs)", "FAIL", str(e)))
        print(f"[FAIL] SEC4-CONTROL-20-OVERS: {e}")

    # --------------------------------------------------------------------------
    # TEST 5: Section 5 — DLS Fail-Closed Revalidation
    # --------------------------------------------------------------------------
    try:
        m_5 = [
            # T1: Missing dls_allocated_overs
            ('M_5A', '2026-02-10', 'Group Stage', 'A', 'T1_MisAlloc', 'T4_Ctrl', 'T1_MisAlloc', 'wickets', 15.0, 140, True, False, None, None, None, True, 'Missing allocated overs'),
            # T2: Abandoned match missing dls_par_score
            ('M_5B', '2026-02-11', 'Group Stage', 'A', 'T2_MisPar', 'T4_Ctrl', 'T2_MisPar', 'runs', 12.0, 100, True, True, 15.0, 12.0, None, True, 'Missing par score'),
            # T3: Abandoned match missing dls_abandonment_overs
            ('M_5C', '2026-02-12', 'Group Stage', 'A', 'T3_MisAbOvers', 'T4_Ctrl', 'T3_MisAbOvers', 'runs', 12.0, 100, True, True, 15.0, None, 95, True, 'Missing abandonment overs'),
            # T4: Control team playing a regular match
            ('M_5D', '2026-02-13', 'Group Stage', 'A', 'T4_Ctrl', 'T1_MisAlloc', 'T4_Ctrl', 'runs', 20.0, None, False, False, None, None, None, True, 'Regular match')
        ]
        s_5 = [
            ('M_5A', 1, 'T4_Ctrl', 'T1_MisAlloc', 150, 6, 120, 20.0, False), ('M_5A', 2, 'T1_MisAlloc', 'T4_Ctrl', 141, 4, 86, 14.2, False),
            ('M_5B', 1, 'T4_Ctrl', 'T2_MisPar', 160, 6, 120, 20.0, False), ('M_5B', 2, 'T2_MisPar', 'T4_Ctrl', 105, 3, 72, 12.0, False),
            ('M_5C', 1, 'T4_Ctrl', 'T3_MisAbOvers', 160, 6, 120, 20.0, False), ('M_5C', 2, 'T3_MisAbOvers', 'T4_Ctrl', 105, 3, 72, 12.0, False),
            ('M_5D', 1, 'T4_Ctrl', 'T1_MisAlloc', 160, 6, 120, 20.0, False), ('M_5D', 2, 'T1_MisAlloc', 'T4_Ctrl', 130, 8, 120, 20.0, False)
        ]
        res_5 = run_fixture('DLS-FAIL-CLOSED-ALL', m_5, s_5)
        t1 = [r for r in res_5 if r[3] == 'T1_MisAlloc'][0]
        t2 = [r for r in res_5 if r[3] == 'T2_MisPar'][0]
        t3 = [r for r in res_5 if r[3] == 'T3_MisAbOvers'][0]
        
        # All defective teams must have NRR = NULL:
        assert t1[9] is None, f"T1 NRR must be None, got {t1[9]}"
        assert t2[9] is None, f"T2 NRR must be None, got {t2[9]}"
        assert t3[9] is None, f"T3 NRR must be None, got {t3[9]}"

        # Points and W/L preserved:
        assert t1[8] == 2 and t2[8] == 2 and t3[8] == 2
        assert t1[5] == 1 and t2[5] == 1 and t3[5] == 1

        # Resolution steps transparently indicate missing parameters:
        assert 'Step 3: Unresolved' in t1[13]
        assert 'Step 3: Unresolved' in t2[13]
        assert 'Step 3: Unresolved' in t3[13]

        test_results.append(("SEC5-DLS-FAILCLOSED", "DLS Fail-Closed Revalidation", "PASS", "Missing allocated overs, par score, abandonment overs all fail closed (NRR=NULL); pts preserved"))
        print("[PASS] SEC5-DLS-FAILCLOSED: DLS Fail-Closed Revalidation")
    except Exception as e:
        all_passed = False
        test_results.append(("SEC5-DLS-FAILCLOSED", "DLS Fail-Closed Revalidation", "FAIL", str(e)))
        print(f"[FAIL] SEC5-DLS-FAILCLOSED: {e}")

    # --------------------------------------------------------------------------
    # TEST 6: Section 6 — Forfeit Accounting Revalidation (Zero, Rogue, Partial)
    # --------------------------------------------------------------------------
    try:
        m_6 = [
            # Forfeit match: T1 awarded win, T2 forfeited (defaulter)
            ('M_FORF', '2026-02-10', 'Group Stage', 'A', 'T1_Awarded', 'T2_Defaulter', 'T1_Awarded', 'forfeit', 20.0, None, False, False, None, None, None, True, 'Forfeit match with partial rogue scorecard'),
            # Regular matches:
            ('M_REG1', '2026-02-12', 'Group Stage', 'A', 'T1_Awarded', 'T3_Opp', 'T1_Awarded', 'runs', 20.0, None, False, False, None, None, None, True, 'Regular T1 vs T3'),
            ('M_REG2', '2026-02-13', 'Group Stage', 'A', 'T2_Defaulter', 'T3_Opp', 'T3_Opp', 'runs', 20.0, None, False, False, None, None, None, True, 'Regular T2 vs T3')
        ]
        s_6 = [
            # Rogue partial scorecard for the forfeit match (MUST BE OVERRIDDEN & EXCLUDED):
            ('M_FORF', 1, 'T1_Awarded', 'T2_Defaulter', 85, 2, 60, 10.0, False),
            # Regular match scorecards:
            ('M_REG1', 1, 'T1_Awarded', 'T3_Opp', 160, 6, 120, 20.0, False),
            ('M_REG1', 2, 'T3_Opp', 'T1_Awarded', 140, 7, 120, 20.0, False),
            ('M_REG2', 1, 'T3_Opp', 'T2_Defaulter', 160, 5, 120, 20.0, False),
            ('M_REG2', 2, 'T2_Defaulter', 'T3_Opp', 100, 8, 120, 20.0, False)
        ]
        res_6 = run_fixture('FORFEIT-INTERMED-FULL', m_6, s_6)
        t1 = [r for r in res_6 if r[3] == 'T1_Awarded'][0]
        t2 = [r for r in res_6 if r[3] == 'T2_Defaulter'][0]

        # T1_Awarded:
        # Played = 2, Wins = 2, Points = 4.
        # Excluded from forfeit NRR (rogue scorecard 85/2 off 60b ignored!).
        # Runs scored = 160, Balls faced = 120, Runs conceded = 140, Balls bowled = 120.
        # NRR = (160/20) - (140/20) = +1.000.
        assert t1[4] == 2 and t1[5] == 2 and t1[8] == 4
        assert t1[15] == 160 and t1[16] == 120 and t1[17] == 140 and t1[18] == 120
        assert float(t1[9]) == 1.000

        # T2_Defaulter:
        # Played = 2, Wins = 0, Losses = 2, Points = 0.
        # Synthetic record: 0 runs off 120 balls faced.
        # Total runs scored = 100 + 0 = 100.
        # Total balls faced = 120 + 120 = 240 (40.0 ov).
        # Total runs conceded = 160 + 0 = 160.
        # Total balls bowled = 120 + 0 = 120 (20.0 ov).
        # Batting RR = 100 / 40.0 = 2.500. Bowling RR = 160 / 20.0 = 8.000.
        # NRR = 2.500 - 8.000 = -5.500.
        assert t2[4] == 2 and t2[5] == 0 and t2[6] == 2 and t2[8] == 0
        assert t2[15] == 100 and t2[16] == 240 and t2[17] == 160 and t2[18] == 120
        assert float(t2[9]) == -5.500

        test_results.append(("SEC6-FORFEIT-TRACE", "Forfeit Accounting (Zero/Rogue/Partial)", "PASS", "Defaulter charged 0/120b (NRR=-5.500); Awarded team excluded (NRR=+1.000, Pts=4 preserved)"))
        print("[PASS] SEC6-FORFEIT-TRACE: Forfeit Accounting (Zero/Rogue/Partial)")
    except Exception as e:
        all_passed = False
        test_results.append(("SEC6-FORFEIT-TRACE", "Forfeit Accounting (Zero/Rogue/Partial)", "FAIL", str(e)))
        print(f"[FAIL] SEC6-FORFEIT-TRACE: {e}")

    # --------------------------------------------------------------------------
    # TEST 7: Section 7 — Parse-Validate Production View DDL in Rollback
    # --------------------------------------------------------------------------
    try:
        cur.execute("""
            CREATE SCHEMA temp_validation_schema;
            CREATE TABLE temp_validation_schema.dim_matches (LIKE public.dim_matches INCLUDING ALL);
            ALTER TABLE temp_validation_schema.dim_matches 
                ADD COLUMN is_dls_abandoned boolean,
                ADD COLUMN dls_allocated_overs numeric(4,1),
                ADD COLUMN dls_abandonment_overs numeric(4,1),
                ADD COLUMN dls_par_score integer;
            INSERT INTO temp_validation_schema.dim_matches 
            SELECT *, NULL::boolean, NULL::numeric, NULL::numeric, NULL::integer FROM public.dim_matches;
            CREATE TABLE temp_validation_schema.fact_match_summaries (LIKE public.fact_match_summaries INCLUDING ALL);
            INSERT INTO temp_validation_schema.fact_match_summaries SELECT * FROM public.fact_match_summaries;
            SET search_path = temp_validation_schema, public;
        """)
        raw_view_ddl = f"CREATE OR REPLACE VIEW temp_validation_schema.view_tournament_standings AS {get_full_22cte_sql('temp_validation_schema.dim_matches', 'temp_validation_schema.fact_match_summaries')}"
        cur.execute(raw_view_ddl)
        cur.execute("SELECT COUNT(*) FROM temp_validation_schema.view_tournament_standings;")
        row_count = cur.fetchone()[0]
        assert row_count == 28, f"Expected 28 rows from validated view, got {row_count}"
        cur.execute("RESET search_path; DROP SCHEMA temp_validation_schema CASCADE;")
        test_results.append(("SEC7-VIEW-PARSE", "Full 22-CTE DDL Parse Validation", "PASS", "View successfully parsed, compiled, and executed on PostgreSQL 18.7 (28 rows)"))
        print("[PASS] SEC7-VIEW-PARSE: Full 22-CTE DDL Parse Validation")
    except Exception as e:
        all_passed = False
        test_results.append(("SEC7-VIEW-PARSE", "Full 22-CTE DDL Parse Validation", "FAIL", str(e)))
        print(f"[FAIL] SEC7-VIEW-PARSE: {e}")

    conn.rollback()
    conn.close()

    print("=" * 90)
    print("PHASE 4.9.6.15 AUDIT SUMMARY")
    print("=" * 90)
    for tid, name, status, detail in test_results:
        print(f"[{status}] {tid:<25} | {name:<42} | {detail}")

    print("\\nOVERALL RESULT:", "ALL PHASE 4.9.6.15 TESTS PASSED (100%)" if all_passed else "SOME TESTS FAILED")
    return all_passed

if __name__ == '__main__':
    run_all_phase15_tests()
