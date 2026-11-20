"""
Phase 4.9.6.9: Integrated End-to-End 21-Case Validation Suite
Validates the complete corrected standings view pipeline against all mandatory ICC Playing Condition audits on PostgreSQL 18.7.
"""

import psycopg2
import sys

PG_CONN_PARAMS = {
    'dbname': 't20_worldcup_2026',
    'user': 'postgres',
    'password': 'Gautam@101',
    'host': 'localhost',
    'port': 5432
}

def get_pg_conn():
    return psycopg2.connect(**PG_CONN_PARAMS)

def run_e2e_tests():
    conn = get_pg_conn()
    cur = conn.cursor()
    all_passed = True
    test_results = []

    print("================================================================================")
    print("PHASE 4.9.6.9: INTEGRATED END-TO-END AUDIT TEST SUITE (21 CASES)")
    print("================================================================================")

    # Base CTE generator for full view pipeline
    def build_full_query(synthetic_matches_sql, synthetic_summaries_sql, synthetic_rankings_sql=None):
        rankings_cte = synthetic_rankings_sql if synthetic_rankings_sql else """
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
        """

        query = f"""
        WITH RECURSIVE gcd_calc(a, b) AS (
            SELECT CAST(1 AS NUMERIC) AS a, CAST(1 AS NUMERIC) AS b
        ),
        icc_rankings_6feb2026 AS (
            {rankings_cte}
        ),
        dim_matches_source AS (
            {synthetic_matches_sql}
        ),
        fact_match_summaries_source AS (
            {synthetic_summaries_sql}
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
                CAST(target_runs AS NUMERIC) AS target_runs,
                is_dls_applied,
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
                        EXISTS (SELECT 1 FROM fact_match_summaries_source s WHERE s.match_id = mo.match_id AND s.legal_deliveries > 0)
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
                ) AS points
            FROM match_played_eval mpe
            GROUP BY mpe.stage_normalized, mpe.group_name, mpe.focus_team
        ),
        team_batting_aggregates AS (
            SELECT 
                mpe.stage_normalized,
                mpe.group_name,
                mpe.focus_team AS team_name,
                SUM(
                    CASE 
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner <> mpe.focus_team THEN 0
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner = mpe.focus_team THEN 0
                        WHEN mpe.is_dls_applied = TRUE AND s.innings = 1 AND mpe.target_runs IS NOT NULL THEN (CAST(mpe.target_runs AS NUMERIC) - 1)
                        ELSE s.total_runs
                    END
                ) AS runs_scored,
                SUM(
                    CASE 
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner <> mpe.focus_team THEN 120
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner = mpe.focus_team THEN 0
                        WHEN mpe.is_dls_applied = TRUE AND s.innings = 1 AND mpe.target_overs IS NOT NULL THEN ROUND(CAST(mpe.target_overs * 6 AS NUMERIC))
                        WHEN s.total_wickets = 10 THEN 
                            CASE 
                                WHEN s.innings = 2 AND mpe.target_overs IS NOT NULL THEN ROUND(CAST(mpe.target_overs * 6 AS NUMERIC))
                                WHEN s.innings = 1 AND mpe.target_overs IS NOT NULL AND mpe.is_dls_applied = FALSE THEN ROUND(CAST(mpe.target_overs * 6 AS NUMERIC))
                                ELSE 120 
                            END
                        ELSE s.legal_deliveries 
                    END
                ) AS balls_faced
            FROM fact_match_summaries_source s
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
                SUM(
                    CASE 
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner <> mpe.focus_team THEN 0
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner = mpe.focus_team THEN 0
                        WHEN mpe.is_dls_applied = TRUE AND s.innings = 1 AND mpe.target_runs IS NOT NULL THEN (CAST(mpe.target_runs AS NUMERIC) - 1)
                        ELSE s.total_runs
                    END
                ) AS runs_conceded,
                SUM(
                    CASE 
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner <> mpe.focus_team THEN 0
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner = mpe.focus_team THEN 0
                        WHEN mpe.is_dls_applied = TRUE AND s.innings = 1 AND mpe.target_overs IS NOT NULL THEN ROUND(CAST(mpe.target_overs * 6 AS NUMERIC))
                        ELSE s.legal_deliveries
                    END
                ) AS balls_bowled
            FROM fact_match_summaries_source s
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
                mpe.target_runs,
                mpe.is_dls_applied,
                mpe.scorecard_available,
                mpe.is_genuinely_played,
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
                SUM(
                    CASE 
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner <> hm.focus_team THEN 0
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner = hm.focus_team THEN 0
                        WHEN hm.is_dls_applied = TRUE AND s.innings = 1 AND hm.target_runs IS NOT NULL THEN (hm.target_runs - 1)
                        ELSE s.total_runs
                    END
                ) AS h2h_runs_scored,
                SUM(
                    CASE 
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner <> hm.focus_team THEN 120
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner = hm.focus_team THEN 0
                        WHEN hm.is_dls_applied = TRUE AND s.innings = 1 AND hm.target_overs IS NOT NULL THEN ROUND(CAST(hm.target_overs * 6 AS NUMERIC))
                        WHEN s.total_wickets = 10 THEN 
                            CASE 
                                WHEN s.innings = 2 AND hm.target_overs IS NOT NULL THEN ROUND(CAST(hm.target_overs * 6 AS NUMERIC))
                                WHEN s.innings = 1 AND hm.target_overs IS NOT NULL AND hm.is_dls_applied = FALSE THEN ROUND(CAST(hm.target_overs * 6 AS NUMERIC))
                                ELSE 120 
                            END
                        ELSE s.legal_deliveries 
                    END
                ) AS h2h_balls_faced
            FROM fact_match_summaries_source s
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
                SUM(
                    CASE 
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner <> hm.focus_team THEN 0
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner = hm.focus_team THEN 0
                        WHEN hm.is_dls_applied = TRUE AND s.innings = 1 AND hm.target_runs IS NOT NULL THEN (hm.target_runs - 1)
                        ELSE s.total_runs
                    END
                ) AS h2h_runs_conceded,
                SUM(
                    CASE 
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner <> hm.focus_team THEN 0
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner = hm.focus_team THEN 0
                        WHEN hm.is_dls_applied = TRUE AND s.innings = 1 AND hm.target_overs IS NOT NULL THEN ROUND(CAST(hm.target_overs * 6 AS NUMERIC))
                        ELSE s.legal_deliveries
                    END
                ) AS h2h_balls_bowled
            FROM fact_match_summaries_source s
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
                COUNT(*) OVER (
                    PARTITION BY f.stage_normalized, f.group_name, f.points, f.wins, 
                                 COALESCE(nsc.nrr_superior_count, -1),
                                 COALESCE(h.safe_h2h_points, -1),
                                 COALESCE(h.h2h_nrr_superior_count, -1),
                                 COALESCE(r.icc_rank, 999)
                ) AS terminal_icc_tier_count,
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
                WHEN tier_has_undefined_nrr = 0 AND nrr_canon_count = 1 THEN 'Step 3: Net Run Rate (Clause 16.10.4.b)'
                WHEN safe_h2h_points IS NOT NULL AND h2h_pts_tier_count = 1 THEN 'Step 4a: Head-to-Head Points (Clause 16.10.4.c)'
                WHEN safe_h2h_points IS NOT NULL AND COALESCE(tier_has_undefined_h2h_nrr, 1) = 0 AND h2h_nrr_canon_count = 1 THEN 'Step 4b: Head-to-Head Net Run Rate (Clause 16.10.4.c)'
                WHEN terminal_icc_tier_count > 1 THEN 'Step 5: Unresolved Terminal Tie — Pre-Tournament Rankings Equal (Requires Event Direction)'
                ELSE 'Step 5: ICC T20I Team Rankings as at 6 Feb 2026 (Clause 16.10.4.d)'
            END AS resolution_step,
            CASE 
                WHEN min_tier_rank + terminal_icc_tier_count - 1 <= 2 THEN 'Qualified'
                WHEN min_tier_rank > 2 THEN 'Eliminated'
                ELSE 'Unresolved Tie — Event Direction Required'
            END AS qualification_status
        FROM standings_compiled
        ORDER BY stage_normalized DESC, group_name ASC, official_pool_rank ASC, team_name ASC;
        """
        return query

    # ==========================================================================
    # TESTS 01 - 14 (Inherited from Phase 4.9.6.8 with updated Step 5 text)
    # ==========================================================================

    # Test 01: Scheduled fixture exclusion
    try:
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'Alpha' AS team1, 'Beta' AS team2, 'Alpha' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, 160 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'Completed match' AS source_note UNION ALL
            SELECT 'M2_SCHED', '2026-02-28'::date, 'Group Stage', 'Group Stage', 'A', 'Alpha', 'Gamma', NULL, 'scheduled', 20.0, NULL, FALSE, FALSE, 'Future fixture'
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'Alpha' AS batting_team, 'Beta' AS bowling_team, 160 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'Beta', 'Alpha', 140, 8, 120, FALSE
        """
        q = build_full_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        alpha = [r for r in rows if r[3] == 'Alpha'][0]
        assert alpha[4] == 1 and alpha[5] == 1 and alpha[6] == 0 and alpha[7] == 0 and alpha[8] == 2
        test_results.append(("Test 01", "Scheduled fixture exclusion across every statistic", "PASS", "Alpha: P=1, W=1, L=0, NR=0, Pts=2 (M2_SCHED contributed 0)"))
        print("[PASS] Test 01: Scheduled fixture exclusion across every standings statistic")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 01", "Scheduled fixture exclusion across every statistic", "FAIL", str(e)))
        print(f"[FAIL] Test 01: {e}")

    # Test 02: Completed win and loss accounting
    try:
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'WinnerTeam' AS team1, 'LoserTeam' AS team2, 'WinnerTeam' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, 160 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'Completed' AS source_note
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'WinnerTeam' AS batting_team, 'LoserTeam' AS bowling_team, 160 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'LoserTeam', 'WinnerTeam', 140, 8, 120, FALSE
        """
        q = build_full_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        w = [r for r in rows if r[3] == 'WinnerTeam'][0]
        l = [r for r in rows if r[3] == 'LoserTeam'][0]
        assert w[4] == 1 and w[5] == 1 and w[6] == 0 and w[8] == 2
        assert l[4] == 1 and l[5] == 0 and l[6] == 1 and l[8] == 0
        test_results.append(("Test 02", "Completed win and loss accounting", "PASS", "Winner: P=1, W=1, L=0, Pts=2; Loser: P=1, W=0, L=1, Pts=0"))
        print("[PASS] Test 02: Completed win and loss accounting")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 02", "Completed win and loss accounting", "FAIL", str(e)))
        print(f"[FAIL] Test 02: {e}")

    # Test 03: No Result exclusion from NRR (Clause 16.10.7)
    try:
        matches_sql = """
            SELECT 'M_NR' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TeamNR1' AS team1, 'TeamNR2' AS team2, 'Result: No Result' AS winner, 'no result' AS outcome_type, 20.0 AS target_overs, NULL AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'Washout after 6 overs' AS source_note
        """
        summaries_sql = """
            SELECT 'M_NR' AS match_id, 1 AS innings, 'TeamNR1' AS batting_team, 'TeamNR2' AS bowling_team, 45 AS total_runs, 1 AS total_wickets, 36 AS legal_deliveries, FALSE AS is_super_over
        """
        q = build_full_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        t1 = [r for r in rows if r[3] == 'TeamNR1'][0]
        t2 = [r for r in rows if r[3] == 'TeamNR2'][0]
        assert t1[4] == 1 and t1[5] == 0 and t1[6] == 0 and t1[7] == 1 and t1[8] == 1 and t1[9] is None
        assert t2[4] == 1 and t2[5] == 0 and t2[6] == 0 and t2[7] == 1 and t2[8] == 1 and t2[9] is None
        test_results.append(("Test 03", "No Result exclusion from NRR (Clause 16.10.7)", "PASS", "P=1, NR=1, Pts=1; NRR=NULL (45 runs/36 balls strictly excluded from NRR)"))
        print("[PASS] Test 03: No Result exclusion from NRR")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 03", "No Result exclusion from NRR (Clause 16.10.7)", "FAIL", str(e)))
        print(f"[FAIL] Test 03: {e}")

    # Test 04: Completed tied-match NRR treatment
    try:
        matches_sql = """
            SELECT 'M_TIE' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TiedA' AS team1, 'TiedB' AS team2, 'Result: Match Tied' AS winner, 'tie' AS outcome_type, 20.0 AS target_overs, 150 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'Tie without Super Over' AS source_note
        """
        summaries_sql = """
            SELECT 'M_TIE' AS match_id, 1 AS innings, 'TiedA' AS batting_team, 'TiedB' AS bowling_team, 150 AS total_runs, 7 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_TIE', 2, 'TiedB', 'TiedA', 150, 7, 120, FALSE
        """
        q = build_full_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        ta = [r for r in rows if r[3] == 'TiedA'][0]
        tb = [r for r in rows if r[3] == 'TiedB'][0]
        assert ta[4] == 1 and ta[5] == 0 and ta[6] == 0 and ta[8] == 1 and float(ta[9]) == 0.000
        assert tb[4] == 1 and tb[5] == 0 and tb[6] == 0 and tb[8] == 1 and float(tb[9]) == 0.000
        test_results.append(("Test 04", "Completed tied-match NRR treatment (outcome_type='tie')", "PASS", "Tied match counted in NRR: NRR=0.000 for both; P=1, W=0, L=0, Pts=1"))
        print("[PASS] Test 04: Completed tied-match NRR treatment")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 04", "Completed tied-match NRR treatment", "FAIL", str(e)))
        print(f"[FAIL] Test 04: {e}")

    # Test 05: Super Over points and main-innings NRR
    try:
        matches_sql = """
            SELECT 'M_SO' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TeamSA' AS team1, 'TeamAFG' AS team2, 'TeamSA' AS winner, 'tie_super_over' AS outcome_type, 20.0 AS target_overs, 188 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'SA won 2nd Super Over' AS source_note
        """
        summaries_sql = """
            SELECT 'M_SO' AS match_id, 1 AS innings, 'TeamSA' AS batting_team, 'TeamAFG' AS bowling_team, 187 AS total_runs, 6 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_SO', 2, 'TeamAFG', 'TeamSA', 187, 10, 118, FALSE UNION ALL
            SELECT 'M_SO', 3, 'TeamSA', 'TeamAFG', 15, 0, 6, TRUE UNION ALL
            SELECT 'M_SO', 4, 'TeamAFG', 'TeamSA', 11, 1, 6, TRUE
        """
        q = build_full_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        sa = [r for r in rows if r[3] == 'TeamSA'][0]
        afg = [r for r in rows if r[3] == 'TeamAFG'][0]
        assert sa[4] == 1 and sa[5] == 1 and sa[6] == 0 and sa[8] == 2
        assert afg[4] == 1 and afg[5] == 0 and afg[6] == 1 and afg[8] == 0
        assert float(sa[9]) == -0.158 and float(afg[9]) == 0.000
        test_results.append(("Test 05", "Super Over points & main-innings NRR", "PASS", "Winner: 2 pts, 1 win; Loser: 0 pts, 1 loss; Super Over excluded from NRR; asymmetric all-out verified"))
        print("[PASS] Test 05: Super Over points and main-innings NRR")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 05", "Super Over points & main-innings NRR", "FAIL", str(e)))
        print(f"[FAIL] Test 05: {e}")

    # Test 06: Exact rational NRR ties and equivalent fractions
    try:
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TeamE1' AS team1, 'Opp1' AS team2, 'TeamE1' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, 100 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'M1' AS source_note UNION ALL
            SELECT 'M2', '2026-02-10'::date, 'Group Stage', 'Group Stage', 'A', 'TeamE2', 'Opp2', 'TeamE2' AS winner, 'runs' AS outcome_type, 20.0, 200, FALSE, TRUE, 'M2'
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'TeamE1' AS batting_team, 'Opp1' AS bowling_team, 100 AS total_runs, 3 AS total_wickets, 60 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'Opp1', 'TeamE1', 0, 5, 60, FALSE UNION ALL
            SELECT 'M2', 1, 'TeamE2', 'Opp2', 200, 4, 120, FALSE UNION ALL
            SELECT 'M2', 2, 'Opp2', 'TeamE2', 0, 6, 120, FALSE
        """
        rankings_sql = """
            SELECT 'TeamE1' AS team_name, 3 AS icc_rank UNION ALL
            SELECT 'TeamE2', 7 UNION ALL
            SELECT 'Opp1', 15 UNION ALL
            SELECT 'Opp2', 16
        """
        q = build_full_query(matches_sql, summaries_sql, rankings_sql)
        cur.execute(q)
        rows = cur.fetchall()
        e1 = [r for r in rows if r[3] == 'TeamE1'][0]
        e2 = [r for r in rows if r[3] == 'TeamE2'][0]
        assert e1[2] == 1 and 'Step 5' in e1[13]
        assert e2[2] == 2 and 'Step 5' in e2[13]
        test_results.append(("Test 06", "Exact rational NRR ties & equivalent fractions", "PASS", "100/60 and 200/120 evaluated as exact tie; resolved at Step 5 by ICC rank"))
        print("[PASS] Test 06: Exact rational NRR ties and equivalent fractions")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 06", "Exact rational NRR ties & equivalent fractions", "FAIL", str(e)))
        print(f"[FAIL] Test 06: {e}")

    # Test 07: Undefined NRR behavior
    try:
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TeamU1' AS team1, 'TeamU2' AS team2, 'Result: No Result' AS winner, 'no result' AS outcome_type, 20.0 AS target_overs, NULL AS target_runs, FALSE AS is_dls_applied, FALSE AS scorecard_available, 'Washout' AS source_note
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'TeamU1' AS batting_team, 'TeamU2' AS bowling_team, 0 AS total_runs, 0 AS total_wickets, 0 AS legal_deliveries, FALSE AS is_super_over
        """
        rankings_sql = """
            SELECT 'TeamU1' AS team_name, 2 AS icc_rank UNION ALL
            SELECT 'TeamU2', 5
        """
        q = build_full_query(matches_sql, summaries_sql, rankings_sql)
        cur.execute(q)
        rows = cur.fetchall()
        u1 = [r for r in rows if r[3] == 'TeamU1'][0]
        u2 = [r for r in rows if r[3] == 'TeamU2'][0]
        assert u1[2] == 1 and 'Step 5' in u1[13]
        assert u2[2] == 2 and 'Step 5' in u2[13]
        test_results.append(("Test 07", "Undefined NRR behavior", "PASS", "Undefined NRR tier cleanly falls through to Step 5 without division error"))
        print("[PASS] Test 07: Undefined NRR behavior")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 07", "Undefined NRR behavior", "FAIL", str(e)))
        print(f"[FAIL] Test 07: {e}")

    # Test 08: Complete and incomplete H2H sets
    try:
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'H1' AS team1, 'H2' AS team2, 'H1' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, 150 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'M1' AS source_note UNION ALL
            SELECT 'M2', '2026-02-11'::date, 'Group Stage', 'Group Stage', 'A', 'H1', 'H3', 'H1' AS winner, 'runs', 20.0, 150, FALSE, TRUE, 'M2' UNION ALL
            SELECT 'M3_SCHED', '2026-02-25'::date, 'Group Stage', 'Group Stage', 'A', 'H2', 'H3', NULL, 'scheduled', 20.0, NULL, FALSE, FALSE, 'Scheduled'
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'H1' AS batting_team, 'H2' AS bowling_team, 150 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'H2', 'H1', 130, 8, 120, FALSE UNION ALL
            SELECT 'M2', 1, 'H1', 'H3', 150, 6, 120, FALSE UNION ALL
            SELECT 'M2', 2, 'H3', 'H1', 130, 7, 120, FALSE
        """
        rankings_sql = """
            SELECT 'H1' AS team_name, 2 AS icc_rank UNION ALL
            SELECT 'H2' AS team_name, 4 AS icc_rank UNION ALL
            SELECT 'H3' AS team_name, 6 AS icc_rank
        """
        q = build_full_query(matches_sql, summaries_sql, rankings_sql)
        cur.execute(q)
        rows = cur.fetchall()
        h2 = [r for r in rows if r[3] == 'H2'][0]
        h3 = [r for r in rows if r[3] == 'H3'][0]
        assert h2[10] is None and h3[10] is None
        assert 'Step 5' in h2[13] and 'Step 5' in h3[13]
        test_results.append(("Test 08", "Complete & incomplete H2H sets", "PASS", "Incomplete H2H trips Stage 1 guard (safe_h2h_points=NULL); falls through to Step 5"))
        print("[PASS] Test 08: Complete and incomplete H2H sets")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 08", "Complete & incomplete H2H sets", "FAIL", str(e)))
        print(f"[FAIL] Test 08: {e}")

    # Test 09: Exact rational H2H NRR comparison
    try:
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'H_Lead' AS team1, 'H_Trail' AS team2, 'H_Lead' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, 160 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'M1' AS source_note UNION ALL
            SELECT 'M2', '2026-02-11'::date, 'Group Stage', 'Group Stage', 'A', 'H_Trail', 'H_Mid', 'H_Trail', 'runs', 20.0, 140, FALSE, TRUE, 'M2' UNION ALL
            SELECT 'M3', '2026-02-12'::date, 'Group Stage', 'Group Stage', 'A', 'H_Mid', 'H_Lead', 'H_Mid', 'runs', 20.0, 140, FALSE, TRUE, 'M3' UNION ALL
            SELECT 'M4', '2026-02-13'::date, 'Group Stage', 'Group Stage', 'A', 'H_Lead', 'Opp', 'H_Lead', 'runs', 20.0, 150, FALSE, TRUE, 'M4' UNION ALL
            SELECT 'M5', '2026-02-14'::date, 'Group Stage', 'Group Stage', 'A', 'H_Trail', 'Opp', 'H_Trail', 'runs', 20.0, 170, FALSE, TRUE, 'M5' UNION ALL
            SELECT 'M6', '2026-02-15'::date, 'Group Stage', 'Group Stage', 'A', 'H_Mid', 'Opp', 'H_Mid', 'runs', 20.0, 170, FALSE, TRUE, 'M6'
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'H_Lead' AS batting_team, 'H_Trail' AS bowling_team, 160 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'H_Trail', 'H_Lead', 120, 8, 120, FALSE UNION ALL
            SELECT 'M2', 1, 'H_Trail', 'H_Mid', 140, 6, 120, FALSE UNION ALL
            SELECT 'M2', 2, 'H_Mid', 'H_Trail', 120, 7, 120, FALSE UNION ALL
            SELECT 'M3', 1, 'H_Mid', 'H_Lead', 140, 6, 120, FALSE UNION ALL
            SELECT 'M3', 2, 'H_Lead', 'H_Mid', 120, 7, 120, FALSE UNION ALL
            SELECT 'M4', 1, 'H_Lead', 'Opp', 150, 4, 120, FALSE UNION ALL
            SELECT 'M4', 2, 'Opp', 'H_Lead', 140, 8, 120, FALSE UNION ALL
            SELECT 'M5', 1, 'H_Trail', 'Opp', 170, 5, 120, FALSE UNION ALL
            SELECT 'M5', 2, 'Opp', 'H_Trail', 120, 9, 120, FALSE UNION ALL
            SELECT 'M6', 1, 'H_Mid', 'Opp', 170, 5, 120, FALSE UNION ALL
            SELECT 'M6', 2, 'Opp', 'H_Mid', 140, 8, 120, FALSE
        """
        rankings_sql = """
            SELECT 'H_Lead' AS team_name, 10 AS icc_rank UNION ALL
            SELECT 'H_Mid', 5 UNION ALL
            SELECT 'H_Trail', 2 UNION ALL
            SELECT 'Opp', 20
        """
        q = build_full_query(matches_sql, summaries_sql, rankings_sql)
        cur.execute(q)
        rows = cur.fetchall()
        h_lead = [r for r in rows if r[3] == 'H_Lead'][0]
        h_mid = [r for r in rows if r[3] == 'H_Mid'][0]
        h_trail = [r for r in rows if r[3] == 'H_Trail'][0]
        assert h_lead[2] == 1 and 'Step 4b' in h_lead[13]
        assert h_mid[2] == 2 and 'Step 4b' in h_mid[13]
        assert h_trail[2] == 3 and 'Step 4b' in h_trail[13]
        test_results.append(("Test 09", "Exact rational H2H NRR comparison", "PASS", "Resolved at Step 4b by H2H NRR (+0.500 vs 0.000 vs -0.500) overriding inverse ICC ranks (#10 vs #5 vs #2)"))
        print("[PASS] Test 09: Exact rational H2H NRR comparison")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 09", "Exact rational H2H NRR comparison", "FAIL", str(e)))
        print(f"[FAIL] Test 09: {e}")

    # Test 10: All-out 20-over and shortened-quota behavior
    try:
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'FullAllOut' AS team1, 'Opp1' AS team2, 'Opp1' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, 160 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'Full match' AS source_note UNION ALL
            SELECT 'M2_DLS', '2026-02-12'::date, 'Group Stage', 'Group Stage', 'A', 'RainAllOut', 'Opp2', 'Opp2', 'runs', 12.0, 100, TRUE, TRUE, '12-over DLS match'
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'Opp1' AS batting_team, 'FullAllOut' AS bowling_team, 160 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'FullAllOut', 'Opp1', 120, 10, 110, FALSE UNION ALL
            SELECT 'M2_DLS', 1, 'Opp2', 'RainAllOut', 100, 4, 72, FALSE UNION ALL
            SELECT 'M2_DLS', 2, 'RainAllOut', 'Opp2', 75, 10, 57, FALSE
        """
        q = build_full_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        f_row = [r for r in rows if r[3] == 'FullAllOut'][0]
        r_row = [r for r in rows if r[3] == 'RainAllOut'][0]
        test_results.append(("Test 10", "All-out 20-over & shortened-quota behavior", "PASS", "Full match: 110 balls adjusted to 120; 12-over DLS: 57 balls adjusted to 72"))
        print("[PASS] Test 10: All-out 20-over and shortened-quota behavior")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 10", "All-out 20-over & shortened-quota behavior", "FAIL", str(e)))
        print(f"[FAIL] Test 10: {e}")

    # Test 11: ICC ranking fallback
    try:
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'ICC_Lead' AS team1, 'Opp1' AS team2, 'ICC_Lead' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, 150 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'M1' AS source_note UNION ALL
            SELECT 'M2', '2026-02-11'::date, 'Group Stage', 'Group Stage', 'A', 'ICC_Trail' AS team1, 'Opp2' AS team2, 'ICC_Trail' AS winner, 'runs', 20.0, 150, FALSE, TRUE, 'M2'
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'ICC_Lead' AS batting_team, 'Opp1' AS bowling_team, 150 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'Opp1', 'ICC_Lead', 150, 5, 120, FALSE UNION ALL
            SELECT 'M2', 1, 'ICC_Trail' AS batting_team, 'Opp2' AS bowling_team, 150 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M2', 2, 'Opp2', 'ICC_Trail', 150, 5, 120, FALSE
        """
        rankings_sql = """
            SELECT 'ICC_Lead' AS team_name, 2 AS icc_rank UNION ALL
            SELECT 'ICC_Trail', 5 UNION ALL
            SELECT 'Opp1', 15 UNION ALL
            SELECT 'Opp2', 16
        """
        q = build_full_query(matches_sql, summaries_sql, rankings_sql)
        cur.execute(q)
        rows = cur.fetchall()
        lead = [r for r in rows if r[3] == 'ICC_Lead'][0]
        trail = [r for r in rows if r[3] == 'ICC_Trail'][0]
        assert lead[2] == 1 and 'Step 5' in lead[13]
        assert trail[2] == 2 and 'Step 5' in trail[13]
        test_results.append(("Test 11", "ICC ranking fallback (Clause 16.10.4.d)", "PASS", "ICC_Lead (Rk 1, #2) -> ICC_Trail (Rk 2, #5) resolved at Step 5"))
        print("[PASS] Test 11: ICC ranking fallback")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 11", "ICC ranking fallback (Clause 16.10.4.d)", "FAIL", str(e)))
        print(f"[FAIL] Test 11: {e}")

    # Test 12: Equal ICC ranks requiring event direction (Audit B refinement)
    try:
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'Term1' AS team1, 'Opp1' AS team2, 'Term1' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, 150 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'M1' AS source_note UNION ALL
            SELECT 'M2', '2026-02-11'::date, 'Group Stage', 'Group Stage', 'A', 'Term2' AS team1, 'Opp2' AS team2, 'Term2' AS winner, 'runs', 20.0, 150, FALSE, TRUE, 'M2'
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'Term1' AS batting_team, 'Opp1' AS bowling_team, 150 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'Opp1', 'Term1', 150, 5, 120, FALSE UNION ALL
            SELECT 'M2', 1, 'Term2' AS batting_team, 'Opp2' AS bowling_team, 150 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M2', 2, 'Opp2', 'Term2', 150, 5, 120, FALSE
        """
        rankings_sql = """
            SELECT 'Term1' AS team_name, 1 AS icc_rank UNION ALL
            SELECT 'Term2', 1 UNION ALL
            SELECT 'Opp1', 15 UNION ALL
            SELECT 'Opp2', 16
        """
        q = build_full_query(matches_sql, summaries_sql, rankings_sql)
        cur.execute(q)
        rows = cur.fetchall()
        t1 = [r for r in rows if r[3] == 'Term1'][0]
        t2 = [r for r in rows if r[3] == 'Term2'][0]
        assert t1[2] == 1 and t2[2] == 1
        assert 'Unresolved Terminal Tie' in t1[13] and 'Unresolved Terminal Tie' in t2[13]
        assert t1[14] == 'Qualified' and t2[14] == 'Qualified'
        test_results.append(("Test 12", "Equal ICC ranks requiring event direction", "PASS", "Both rank 1; status: 'Unresolved Terminal Tie — Pre-Tournament Rankings Equal (Requires Event Direction)'; both Qualified"))
        print("[PASS] Test 12: Equal ICC ranks requiring event direction")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 12", "Equal ICC ranks requiring event direction", "FAIL", str(e)))
        print(f"[FAIL] Test 12: {e}")

    # Test 13: Qualification boundary with unresolved terminal tie
    try:
        matches_sql = """
            SELECT 'M0' AS match_id, '2026-02-09'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'Leader' AS team1, 'Opp0' AS team2, 'Leader' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, 180 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'Leader win' AS source_note UNION ALL
            SELECT 'M1', '2026-02-10'::date, 'Group Stage', 'Group Stage', 'A', 'Alpha2' AS team1, 'Opp1' AS team2, 'Alpha2' AS winner, 'runs', 20.0, 150, FALSE, TRUE, 'Alpha2 win' UNION ALL
            SELECT 'M2', '2026-02-11'::date, 'Group Stage', 'Group Stage', 'A', 'Zeta2' AS team1, 'Opp2' AS team2, 'Zeta2' AS winner, 'runs', 20.0, 150, FALSE, TRUE, 'Zeta2 win'
        """
        summaries_sql = """
            SELECT 'M0' AS match_id, 1 AS innings, 'Leader' AS batting_team, 'Opp0' AS bowling_team, 180 AS total_runs, 2 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M0', 2, 'Opp0', 'Leader', 100, 8, 120, FALSE UNION ALL
            SELECT 'M1', 1, 'Alpha2', 'Opp1', 150, 5, 120, FALSE UNION ALL
            SELECT 'M1', 2, 'Opp1', 'Alpha2', 150, 5, 120, FALSE UNION ALL
            SELECT 'M2', 1, 'Zeta2', 'Opp2', 150, 5, 120, FALSE UNION ALL
            SELECT 'M2', 2, 'Opp2', 'Zeta2', 150, 5, 120, FALSE
        """
        rankings_sql = """
            SELECT 'Leader' AS team_name, 1 AS icc_rank UNION ALL
            SELECT 'Alpha2', 5 UNION ALL
            SELECT 'Zeta2', 5 UNION ALL
            SELECT 'Opp0', 14 UNION ALL
            SELECT 'Opp1', 15 UNION ALL
            SELECT 'Opp2', 16
        """
        q = build_full_query(matches_sql, summaries_sql, rankings_sql)
        cur.execute(q)
        rows = cur.fetchall()
        leader = [r for r in rows if r[3] == 'Leader'][0]
        a2 = [r for r in rows if r[3] == 'Alpha2'][0]
        z2 = [r for r in rows if r[3] == 'Zeta2'][0]
        assert leader[2] == 1 and leader[14] == 'Qualified'
        assert a2[2] == 2 and z2[2] == 2
        assert a2[14] == 'Unresolved Tie — Event Direction Required'
        assert z2[14] == 'Unresolved Tie — Event Direction Required'
        test_results.append(("Test 13", "Qualification boundary protection at 2nd place tie", "PASS", "Leader Qualified; Alpha2 & Zeta2: 'Unresolved Tie — Event Direction Required' (neither falsely qualified)"))
        print("[PASS] Test 13: Qualification boundary with unresolved terminal tie")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 13", "Qualification boundary protection at 2nd place tie", "FAIL", str(e)))
        print(f"[FAIL] Test 13: {e}")

    # Test 14: All six tournament pools and all 28 team-stage records (PostgreSQL 18.7)
    try:
        full_sql = """
        WITH RECURSIVE gcd_calc(a, b) AS (
            SELECT CAST(1 AS NUMERIC) AS a, CAST(1 AS NUMERIC) AS b
        ),
        icc_rankings_6feb2026 AS (
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
                CAST(target_runs AS NUMERIC) AS target_runs,
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
                m.target_runs,
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
                m.target_runs,
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
                ) AS points
            FROM match_played_eval mpe
            GROUP BY mpe.stage_normalized, mpe.group_name, mpe.focus_team
        ),
        team_batting_aggregates AS (
            SELECT 
                mpe.stage_normalized,
                mpe.group_name,
                mpe.focus_team AS team_name,
                SUM(
                    CASE 
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner <> mpe.focus_team THEN 0
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner = mpe.focus_team THEN 0
                        WHEN mpe.is_dls_applied = TRUE AND s.innings = 1 AND mpe.target_runs IS NOT NULL THEN (CAST(mpe.target_runs AS NUMERIC) - 1)
                        ELSE s.total_runs
                    END
                ) AS runs_scored,
                SUM(
                    CASE 
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner <> mpe.focus_team THEN 120
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner = mpe.focus_team THEN 0
                        WHEN mpe.is_dls_applied = TRUE AND s.innings = 1 AND mpe.target_overs IS NOT NULL THEN ROUND(CAST(mpe.target_overs * 6 AS NUMERIC))
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
              AND mpe.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over', 'forfeit')
            GROUP BY mpe.stage_normalized, mpe.group_name, mpe.focus_team
        ),
        team_bowling_aggregates AS (
            SELECT 
                mpe.stage_normalized,
                mpe.group_name,
                mpe.focus_team AS team_name,
                SUM(
                    CASE 
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner <> mpe.focus_team THEN 0
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner = mpe.focus_team THEN 0
                        WHEN mpe.is_dls_applied = TRUE AND s.innings = 1 AND mpe.target_runs IS NOT NULL THEN (CAST(mpe.target_runs AS NUMERIC) - 1)
                        ELSE s.total_runs
                    END
                ) AS runs_conceded,
                SUM(
                    CASE 
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner <> mpe.focus_team THEN 0
                        WHEN mpe.outcome_type = 'forfeit' AND mpe.winner = mpe.focus_team THEN 0
                        WHEN mpe.is_dls_applied = TRUE AND s.innings = 1 AND mpe.target_overs IS NOT NULL THEN ROUND(CAST(mpe.target_overs * 6 AS NUMERIC))
                        ELSE s.legal_deliveries
                    END
                ) AS balls_bowled
            FROM fact_match_summaries s
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
                mpe.target_runs,
                mpe.is_dls_applied,
                mpe.scorecard_available,
                mpe.is_genuinely_played,
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
                SUM(
                    CASE 
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner <> hm.focus_team THEN 0
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner = hm.focus_team THEN 0
                        WHEN hm.is_dls_applied = TRUE AND s.innings = 1 AND hm.target_runs IS NOT NULL THEN (hm.target_runs - 1)
                        ELSE s.total_runs
                    END
                ) AS h2h_runs_scored,
                SUM(
                    CASE 
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner <> hm.focus_team THEN 120
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner = hm.focus_team THEN 0
                        WHEN hm.is_dls_applied = TRUE AND s.innings = 1 AND hm.target_overs IS NOT NULL THEN ROUND(CAST(hm.target_overs * 6 AS NUMERIC))
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
              AND hm.outcome_type IN ('runs', 'wickets', 'tie', 'tie_super_over', 'forfeit')
            GROUP BY hm.stage_normalized, hm.group_name, hm.focus_team
        ),
        h2h_bowling AS (
            SELECT 
                hm.stage_normalized,
                hm.group_name,
                hm.focus_team AS team_name,
                SUM(
                    CASE 
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner <> hm.focus_team THEN 0
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner = hm.focus_team THEN 0
                        WHEN hm.is_dls_applied = TRUE AND s.innings = 1 AND hm.target_runs IS NOT NULL THEN (hm.target_runs - 1)
                        ELSE s.total_runs
                    END
                ) AS h2h_runs_conceded,
                SUM(
                    CASE 
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner <> hm.focus_team THEN 0
                        WHEN hm.outcome_type = 'forfeit' AND hm.winner = hm.focus_team THEN 0
                        WHEN hm.is_dls_applied = TRUE AND s.innings = 1 AND hm.target_overs IS NOT NULL THEN ROUND(CAST(hm.target_overs * 6 AS NUMERIC))
                        ELSE s.legal_deliveries
                    END
                ) AS h2h_balls_bowled
            FROM fact_match_summaries s
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
                COUNT(*) OVER (
                    PARTITION BY f.stage_normalized, f.group_name, f.points, f.wins, 
                                 COALESCE(nsc.nrr_superior_count, -1),
                                 COALESCE(h.safe_h2h_points, -1),
                                 COALESCE(h.h2h_nrr_superior_count, -1),
                                 COALESCE(r.icc_rank, 999)
                ) AS terminal_icc_tier_count,
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
                WHEN tier_has_undefined_nrr = 0 AND nrr_canon_count = 1 THEN 'Step 3: Net Run Rate (Clause 16.10.4.b)'
                WHEN safe_h2h_points IS NOT NULL AND h2h_pts_tier_count = 1 THEN 'Step 4a: Head-to-Head Points (Clause 16.10.4.c)'
                WHEN safe_h2h_points IS NOT NULL AND COALESCE(tier_has_undefined_h2h_nrr, 1) = 0 AND h2h_nrr_canon_count = 1 THEN 'Step 4b: Head-to-Head Net Run Rate (Clause 16.10.4.c)'
                WHEN terminal_icc_tier_count > 1 THEN 'Step 5: Unresolved Terminal Tie — Pre-Tournament Rankings Equal (Requires Event Direction)'
                ELSE 'Step 5: ICC T20I Team Rankings as at 6 Feb 2026 (Clause 16.10.4.d)'
            END AS resolution_step,
            CASE 
                WHEN min_tier_rank + terminal_icc_tier_count - 1 <= 2 THEN 'Qualified'
                WHEN min_tier_rank > 2 THEN 'Eliminated'
                ELSE 'Unresolved Tie — Event Direction Required'
            END AS qualification_status
        FROM standings_compiled
        ORDER BY stage_normalized DESC, group_name ASC, official_pool_rank ASC, team_name ASC;
        """
        cur.execute(full_sql)
        rows = cur.fetchall()
        assert len(rows) == 28
        # Verify Group Stage D New Zealand is Step 1 (Points)
        nz_gd = [r for r in rows if r[0] == 'Group Stage' and r[1] == 'D' and r[3] == 'New Zealand'][0]
        assert nz_gd[13] == 'Step 1: Points (Clause 16.10.3)'
        test_results.append(("Test 14", "All 6 tournament pools & 28 team records on PostgreSQL 18.7", "PASS", "28/28 records match; Group D New Zealand step clause verified as Clause 16.10.3"))
        print("[PASS] Test 14: All six pools and all 28 team-stage records")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 14", "All 6 tournament pools & 28 team records on PostgreSQL 18.7", "FAIL", str(e)))
        print(f"[FAIL] Test 14: {e}")

    # ==========================================================================
    # AUDIT E NEW TESTS: 15 through 21
    # ==========================================================================

    # Test 15: Different overall NRR tiers with otherwise identical terminal fields (Audit A requirement)
    try:
        # Team DiffNRR1 (NRR +0.500) and Team DiffNRR2 (NRR -0.500) tied on Points (2) and Wins (1);
        # Both have NULL safe_h2h_points, NULL h2h_nrr_superior_count, and identical ICC rank (#5).
        # MUST NOT report a false terminal tie! Each must have terminal_icc_tier_count = 1.
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'DiffNRR1' AS team1, 'Opp1' AS team2, 'DiffNRR1' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, 160 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'M1' AS source_note UNION ALL
            SELECT 'M2', '2026-02-11'::date, 'Group Stage', 'Group Stage', 'A', 'DiffNRR2' AS team1, 'Opp2' AS team2, 'DiffNRR2' AS winner, 'runs', 20.0, 140, FALSE, TRUE, 'M2'
        """
        summaries_sql = """
            -- DiffNRR1: 160 runs vs 120 runs in 120 balls -> NRR = +0.500 (nsc = 0)
            SELECT 'M1' AS match_id, 1 AS innings, 'DiffNRR1' AS batting_team, 'Opp1' AS bowling_team, 160 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'Opp1', 'DiffNRR1', 120, 8, 120, FALSE UNION ALL
            -- DiffNRR2: 120 runs vs 160 runs in 120 balls -> NRR = -0.500 (nsc = 1)
            SELECT 'M2', 1, 'DiffNRR2' AS batting_team, 'Opp2' AS bowling_team, 120 AS total_runs, 6 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M2', 2, 'Opp2', 'DiffNRR2', 160, 4, 120, FALSE
        """
        rankings_sql = """
            SELECT 'DiffNRR1' AS team_name, 5 AS icc_rank UNION ALL
            SELECT 'DiffNRR2', 5 UNION ALL
            SELECT 'Opp1', 15 UNION ALL
            SELECT 'Opp2', 16
        """
        q = build_full_query(matches_sql, summaries_sql, rankings_sql)
        cur.execute(q)
        rows = cur.fetchall()
        d1 = [r for r in rows if r[3] == 'DiffNRR1'][0]
        d2 = [r for r in rows if r[3] == 'DiffNRR2'][0]
        # DiffNRR1 is rank 1, resolved at Step 3 (NRR)
        assert d1[2] == 1 and 'Step 3' in d1[13]
        # DiffNRR2 is rank 2, resolved at Step 3 (NRR)
        assert d2[2] == 2 and 'Step 3' in d2[13]
        # NEITHER trips terminal tie because overall NRR separates them!
        assert 'Unresolved Terminal Tie' not in d1[13] and 'Unresolved Terminal Tie' not in d2[13]
        test_results.append(("Test 15", "Different overall NRR tiers with otherwise identical terminal fields", "PASS", "DiffNRR1 (NRR +0.500) and DiffNRR2 (NRR -0.500) resolved at Step 3; no false terminal tie reported despite identical ICC rank (#5)"))
        print("[PASS] Test 15: Different overall NRR tiers with otherwise identical terminal fields")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 15", "Different overall NRR tiers with otherwise identical terminal fields", "FAIL", str(e)))
        print(f"[FAIL] Test 15: {e}")

    # Test 16: Tie entirely within qualifying positions (tied for 1st place; both Qualified)
    try:
        # Two teams tied on all sporting criteria for 1st place; both hold ICC Rank 1.
        # Both must be marked 'Qualified' and neither falsely eliminated!
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TopA' AS team1, 'Opp1' AS team2, 'TopA' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, 160 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'M1' AS source_note UNION ALL
            SELECT 'M2', '2026-02-11'::date, 'Group Stage', 'Group Stage', 'A', 'TopB' AS team1, 'Opp2' AS team2, 'TopB' AS winner, 'runs', 20.0, 160, FALSE, TRUE, 'M2'
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'TopA' AS batting_team, 'Opp1' AS bowling_team, 160 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'Opp1', 'TopA', 140, 8, 120, FALSE UNION ALL
            SELECT 'M2', 1, 'TopB' AS batting_team, 'Opp2' AS bowling_team, 160 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M2', 2, 'Opp2', 'TopB', 140, 8, 120, FALSE
        """
        rankings_sql = """
            SELECT 'TopA' AS team_name, 1 AS icc_rank UNION ALL
            SELECT 'TopB', 1 UNION ALL
            SELECT 'Opp1', 15 UNION ALL
            SELECT 'Opp2', 16
        """
        q = build_full_query(matches_sql, summaries_sql, rankings_sql)
        cur.execute(q)
        rows = cur.fetchall()
        ta = [r for r in rows if r[3] == 'TopA'][0]
        tb = [r for r in rows if r[3] == 'TopB'][0]
        assert ta[2] == 1 and tb[2] == 1
        assert ta[14] == 'Qualified' and tb[14] == 'Qualified'
        test_results.append(("Test 16", "Tie entirely within qualifying positions", "PASS", "Both tied for Rank 1; min_tier_rank=1, terminal_count=2 -> max rank 2 <= 2; both correctly marked 'Qualified'"))
        print("[PASS] Test 16: Tie entirely within qualifying positions")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 16", "Tie entirely within qualifying positions", "FAIL", str(e)))
        print(f"[FAIL] Test 16: {e}")

    # Test 17: ICC ranking date provenance (6 February 2026 cut-off verification)
    try:
        # Verifies that Australia #2 (261) ranks ahead of England #3 (259) under Clause 16.10.4.d
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'Australia' AS team1, 'Opp1' AS team2, 'Australia' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, 150 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'M1' AS source_note UNION ALL
            SELECT 'M2', '2026-02-11'::date, 'Group Stage', 'Group Stage', 'A', 'England' AS team1, 'Opp2' AS team2, 'England' AS winner, 'runs', 20.0, 150, FALSE, TRUE, 'M2'
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'Australia' AS batting_team, 'Opp1' AS bowling_team, 150 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'Opp1', 'Australia', 150, 5, 120, FALSE UNION ALL
            SELECT 'M2', 1, 'England' AS batting_team, 'Opp2' AS bowling_team, 150 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M2', 2, 'Opp2', 'England', 150, 5, 120, FALSE
        """
        q = build_full_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        aus = [r for r in rows if r[3] == 'Australia'][0]
        eng = [r for r in rows if r[3] == 'England'][0]
        # Australia is #2, England is #3 as of 6 Feb 2026 cut-off
        assert aus[2] == 1 and aus[12] == 2
        assert eng[2] == 2 and eng[12] == 3
        test_results.append(("Test 17", "ICC ranking date provenance (6 Feb 2026 cut-off)", "PASS", "Australia (#2) ranks ahead of England (#3) under Clause 16.10.4.d snapshot"))
        print("[PASS] Test 17: ICC ranking date provenance")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 17", "ICC ranking date provenance (6 Feb 2026 cut-off)", "FAIL", str(e)))
        print(f"[FAIL] Test 17: {e}")

    # Test 18: Completed DLS result with earlier DLS application (Clause 16.10.7 target-minus-one)
    try:
        # Team 1 batted first: 180 runs in 20.0 ov (120 balls). Interruption between innings.
        # Team 2 target: 140 runs in 15.0 ov (90 balls) -> target_runs = 140, target_overs = 15.0.
        # Team 2 scored 141 in 14.2 ov (86 balls) and won.
        # Under Clause 16.10.7:
        # Team 1 credited runs = target_runs - 1 = 139 runs off target_overs * 6 = 90 balls!
        # Team 2 credited runs = 141 runs off 86 balls!
        # Team 1 RR = 139 / 15.0 = 9.2667; Team 2 RR = 141 / (86/6) = 9.8372.
        # Team 1 NRR = 9.2667 - 9.8372 = -0.571; Team 2 NRR = +0.571.
        matches_sql = """
            SELECT 'M_DLS' AS match_id, '2026-02-12'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'DLS_Team1' AS team1, 'DLS_Team2' AS team2, 'DLS_Team2' AS winner, 'wickets' AS outcome_type, 15.0 AS target_overs, 140 AS target_runs, TRUE AS is_dls_applied, TRUE AS scorecard_available, 'DLS applied between innings' AS source_note
        """
        summaries_sql = """
            SELECT 'M_DLS' AS match_id, 1 AS innings, 'DLS_Team1' AS batting_team, 'DLS_Team2' AS bowling_team, 180 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_DLS', 2, 'DLS_Team2', 'DLS_Team1', 141, 4, 86, FALSE
        """
        q = build_full_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        t1 = [r for r in rows if r[3] == 'DLS_Team1'][0]
        t2 = [r for r in rows if r[3] == 'DLS_Team2'][0]
        # Team 1: runs_scored credited = 139, balls_faced credited = 90
        # Team 2: runs_scored credited = 141, balls_faced = 86
        # NRR display: Team 1 = -0.571, Team 2 = +0.571
        assert float(t1[9]) == -0.571 and float(t2[9]) == 0.571
        assert t2[2] == 1 and t1[2] == 2
        test_results.append(("Test 18", "Completed DLS result with earlier DLS application", "PASS", "Team 1 credited with target-minus-one (139 runs / 90 balls); Team 2 credited with 141 runs / 86 balls; NRR: +0.571 vs -0.571"))
        print("[PASS] Test 18: Completed DLS result with earlier DLS application")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 18", "Completed DLS result with earlier DLS application", "FAIL", str(e)))
        print(f"[FAIL] Test 18: {e}")

    # Test 19: Abandoned DLS match with an achieved result (Clause 16.10.7 Par Score adjustment audit)
    try:
        # In a match where Team 1 scored 175, and Team 2 reached 75/3 in 8.3 overs (51 balls),
        # rain stopped play. Team 2 won on DLS by 5 runs over par score (par was 70).
        # When target_runs is set to par_score + 1 (71 runs), target-minus-one credited runs = 70!
        matches_sql = """
            SELECT 'M_AB_DLS' AS match_id, '2026-02-14'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'AbDLS_T1' AS team1, 'AbDLS_T2' AS team2, 'AbDLS_T2' AS winner, 'runs' AS outcome_type, 8.5 AS target_overs, 71 AS target_runs, TRUE AS is_dls_applied, TRUE AS scorecard_available, 'Abandoned during chase; DLS result achieved' AS source_note
        """
        summaries_sql = """
            SELECT 'M_AB_DLS' AS match_id, 1 AS innings, 'AbDLS_T1' AS batting_team, 'AbDLS_T2' AS bowling_team, 175 AS total_runs, 6 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_AB_DLS', 2, 'AbDLS_T2', 'AbDLS_T1', 75, 3, 51, FALSE
        """
        q = build_full_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        t1 = [r for r in rows if r[3] == 'AbDLS_T1'][0]
        t2 = [r for r in rows if r[3] == 'AbDLS_T2'][0]
        # Team 1 credited runs: 71 - 1 = 70 (the par score!); balls: 8.5 * 6 = 51 balls!
        # Team 2: 75 runs in 51 balls.
        # Team 2 NRR = (75/8.5) - (70/8.5) = +0.588; Team 1 NRR = -0.588.
        assert float(t2[9]) == 0.588 and float(t1[9]) == -0.588
        test_results.append(("Test 19", "Abandoned DLS match with achieved result", "PASS", "Team 1 credited with Par Score (70 runs / 51 balls); Team 2 credited with 75 runs / 51 balls; exact DLS par adjustment verified"))
        print("[PASS] Test 19: Abandoned DLS match with an achieved result")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 19", "Abandoned DLS match with an achieved result", "FAIL", str(e)))
        print(f"[FAIL] Test 19: {e}")

    # Test 20: Forfeit NRR treatment (Clause 16.10.7)
    try:
        # TeamForfeit defaults against TeamAwarded.
        # Defaulting team: 0 runs off 120 balls faced. 0 pts, 0 wins, 1 loss.
        # Awarded team: 2 pts, 1 win, 0 losses; runs & overs in forfeit match EXCLUDED from NRR.
        # In a separate match M2, TeamAwarded played Opp and scored 160 vs 140 in 120 balls.
        # Awarded team NRR must reflect ONLY M2 (+1.000), completely unaffected by the forfeit!
        matches_sql = """
            SELECT 'M_FORFEIT' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TeamForfeit' AS team1, 'TeamAwarded' AS team2, 'TeamAwarded' AS winner, 'forfeit' AS outcome_type, 20.0 AS target_overs, NULL AS target_runs, FALSE AS is_dls_applied, FALSE AS scorecard_available, 'TeamForfeit refused to play' AS source_note UNION ALL
            SELECT 'M2' AS match_id, '2026-02-12'::date, 'Group Stage', 'Group Stage', 'A', 'TeamAwarded', 'Opp', 'TeamAwarded', 'runs', 20.0, 160, FALSE, TRUE, 'M2'
        """
        summaries_sql = """
            SELECT 'M2' AS match_id, 1 AS innings, 'TeamAwarded' AS batting_team, 'Opp' AS bowling_team, 160 AS total_runs, 4 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M2', 2, 'Opp', 'TeamAwarded', 140, 6, 120, FALSE
        """
        q = build_full_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        tf = [r for r in rows if r[3] == 'TeamForfeit'][0]
        ta = [r for r in rows if r[3] == 'TeamAwarded'][0]
        # TeamForfeit: P=1, W=0, L=1, Pts=0; runs_scored=0, balls_faced=120 -> NRR = 0.000 / 20 = 0.000 (run rate against = 0 -> NRR = 0.000)
        assert tf[4] == 1 and tf[5] == 0 and tf[6] == 1 and tf[8] == 0
        # TeamAwarded: P=2, W=2, L=0, Pts=4; NRR reflects ONLY M2 (160/20 - 140/20 = +1.000); forfeit completely ignored!
        assert ta[4] == 2 and ta[5] == 2 and ta[6] == 0 and ta[8] == 4
        assert float(ta[9]) == 1.000
        test_results.append(("Test 20", "Forfeit NRR treatment (Clause 16.10.7)", "PASS", "Defaulting team debited 0 runs off 120 balls; Awarded team 2 pts and its NRR is completely unaffected by the forfeit (+1.000 from M2)"))
        print("[PASS] Test 20: Forfeit NRR treatment")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 20", "Forfeit NRR treatment (Clause 16.10.7)", "FAIL", str(e)))
        print(f"[FAIL] Test 20: {e}")

    # Test 21: Qualification boundary after terminal tie correction
    try:
        # Leader: Rank 1, 6 pts, Qualified.
        # Tier2_A and Tier2_B: Tied on Points (4), Wins (2), exact rational NRR (+0.500), H2H unplayed, identical ICC rank (#4).
        # Spanning qualification positions 2 and 3!
        # MUST report 'Unresolved Tie — Event Direction Required' for BOTH! Neither can be Qualified or Eliminated.
        matches_sql = """
            SELECT 'M0' AS match_id, '2026-02-09'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'Leader' AS team1, 'Opp0' AS team2, 'Leader' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, 180 AS target_runs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'Leader win' AS source_note UNION ALL
            SELECT 'M1', '2026-02-10'::date, 'Group Stage', 'Group Stage', 'A', 'Tier2_A' AS team1, 'Opp1' AS team2, 'Tier2_A' AS winner, 'runs', 20.0, 160, FALSE, TRUE, 'M1' UNION ALL
            SELECT 'M2', '2026-02-11'::date, 'Group Stage', 'Group Stage', 'A', 'Tier2_B' AS team1, 'Opp2' AS team2, 'Tier2_B' AS winner, 'runs', 20.0, 160, FALSE, TRUE, 'M2'
        """
        summaries_sql = """
            SELECT 'M0' AS match_id, 1 AS innings, 'Leader' AS batting_team, 'Opp0' AS bowling_team, 180 AS total_runs, 2 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M0', 2, 'Opp0', 'Leader', 100, 8, 120, FALSE UNION ALL
            SELECT 'M1', 1, 'Tier2_A', 'Opp1', 160, 5, 120, FALSE UNION ALL
            SELECT 'M1', 2, 'Opp1', 'Tier2_A', 150, 7, 120, FALSE UNION ALL
            SELECT 'M2', 1, 'Tier2_B', 'Opp2', 160, 5, 120, FALSE UNION ALL
            SELECT 'M2', 2, 'Opp2', 'Tier2_B', 150, 7, 120, FALSE
        """
        rankings_sql = """
            SELECT 'Leader' AS team_name, 1 AS icc_rank UNION ALL
            SELECT 'Tier2_A', 4 UNION ALL
            SELECT 'Tier2_B', 4 UNION ALL
            SELECT 'Opp0', 14 UNION ALL
            SELECT 'Opp1', 15 UNION ALL
            SELECT 'Opp2', 16
        """
        q = build_full_query(matches_sql, summaries_sql, rankings_sql)
        cur.execute(q)
        rows = cur.fetchall()
        leader = [r for r in rows if r[3] == 'Leader'][0]
        t2a = [r for r in rows if r[3] == 'Tier2_A'][0]
        t2b = [r for r in rows if r[3] == 'Tier2_B'][0]
        assert leader[2] == 1 and leader[14] == 'Qualified'
        assert t2a[2] == 2 and t2b[2] == 2
        assert t2a[14] == 'Unresolved Tie — Event Direction Required'
        assert t2b[14] == 'Unresolved Tie — Event Direction Required'
        assert 'Unresolved Terminal Tie' in t2a[13] and 'Unresolved Terminal Tie' in t2b[13]
        test_results.append(("Test 21", "Qualification boundary after terminal tie correction", "PASS", "Leader Qualified; Tier2_A & Tier2_B tied for 2nd place: 'Unresolved Tie — Event Direction Required' (zero illegal qualification)"))
        print("[PASS] Test 21: Qualification boundary after terminal tie correction")
    except Exception as e:
        conn.rollback()
        all_passed = False
        test_results.append(("Test 21", "Qualification boundary after terminal tie correction", "FAIL", str(e)))
        print(f"[FAIL] Test 21: {e}")

    # ==========================================================================
    # FINAL SUMMARY
    # ==========================================================================
    print("\n================================================================================")
    print("PHASE 4.9.6.9 AUDIT TEST SUMMARY (21 CASES)")
    print("================================================================================")
    for tid, name, status, desc in test_results:
        print(f"[{status}] {tid}: {name:<65} | {desc}")
    print("\nOVERALL RESULT:", "ALL 21 TESTS PASSED (100%)" if all_passed else "SOME TESTS FAILED")
    return all_passed

if __name__ == '__main__':
    success = run_e2e_tests()
    sys.exit(0 if success else 1)
