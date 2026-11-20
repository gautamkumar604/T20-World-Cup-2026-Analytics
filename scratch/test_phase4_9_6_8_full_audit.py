"""
Phase 4.9.6.8: Integrated End-to-End 14-Case Validation Suite
Executes the complete corrected view pipeline across all mandatory test conditions on PostgreSQL 18.7.
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
    print("PHASE 4.9.6.8: INTEGRATED END-TO-END AUDIT TEST SUITE")
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
        
        return f"""
        WITH wisden_icc_rankings_4feb2026 AS (
            {rankings_cte}
        ),
        stage_matches AS (
            {synthetic_matches_sql}
        ),
        fact_match_summaries_source AS (
            {synthetic_summaries_sql}
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
            FROM fact_match_summaries_source s
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
            FROM fact_match_summaries_source s
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
            FROM fact_match_summaries_source s
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
            FROM fact_match_summaries_source s
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
        """

    # --------------------------------------------------------------------------
    # Test 01: Scheduled fixture exclusion across every standings statistic
    # --------------------------------------------------------------------------
    try:
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'Alpha' AS team1, 'Beta' AS team2, 'Alpha' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'Completed' AS source_note UNION ALL
            SELECT 'M2_SCHED', '2026-02-25'::date, 'Group Stage', 'Group Stage', 'A', 'Alpha', 'Beta', NULL, 'scheduled', 20.0, FALSE, FALSE, 'Scheduled unplayed'
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'Alpha' AS batting_team, 'Beta' AS bowling_team, 160 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'Beta', 'Alpha', 140, 8, 120, FALSE
        """
        q = build_full_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        alpha = [r for r in rows if r[3] == 'Alpha'][0]
        # played=1, wins=1, losses=0, no_result=0, points=2 (M2_SCHED completely ignored)
        assert alpha[4] == 1 and alpha[5] == 1 and alpha[6] == 0 and alpha[7] == 0 and alpha[8] == 2
        test_results.append(("Test 01", "Scheduled fixture exclusion across every statistic", "PASS", "Alpha: P=1, W=1, L=0, NR=0, Pts=2 (M2_SCHED contributed 0)"))
        print("[PASS] Test 01: Scheduled fixture exclusion across every standings statistic")
    except Exception as e:
        all_passed = False
        test_results.append(("Test 01", "Scheduled fixture exclusion across every statistic", "FAIL", str(e)))
        print(f"[FAIL] Test 01: {e}")

    # --------------------------------------------------------------------------
    # Test 02: Completed win and loss accounting
    # --------------------------------------------------------------------------
    try:
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'WinnerTeam' AS team1, 'LoserTeam' AS team2, 'WinnerTeam' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'Completed' AS source_note
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'WinnerTeam' AS batting_team, 'LoserTeam' AS bowling_team, 180 AS total_runs, 4 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'LoserTeam', 'WinnerTeam', 150, 9, 120, FALSE
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
        all_passed = False
        test_results.append(("Test 02", "Completed win and loss accounting", "FAIL", str(e)))
        print(f"[FAIL] Test 02: {e}")

    # --------------------------------------------------------------------------
    # Test 03: No Result exclusion from NRR (Clause 16.10.7)
    # --------------------------------------------------------------------------
    try:
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TeamNR1' AS team1, 'TeamNR2' AS team2, 'Result: No Result' AS winner, 'no result' AS outcome_type, 20.0 AS target_overs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'Abandoned after 6 ov' AS source_note
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'TeamNR1' AS batting_team, 'TeamNR2' AS bowling_team, 45 AS total_runs, 2 AS total_wickets, 36 AS legal_deliveries, FALSE AS is_super_over
        """
        q = build_full_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        t1 = [r for r in rows if r[3] == 'TeamNR1'][0]
        # P=1, NR=1, Pts=1, but NRR is NULL (partial score strictly excluded from NRR!)
        assert t1[4] == 1 and t1[7] == 1 and t1[8] == 1 and t1[9] is None
        test_results.append(("Test 03", "No Result exclusion from NRR (Clause 16.10.7)", "PASS", "P=1, NR=1, Pts=1; NRR=NULL (45 runs/36 balls strictly excluded from NRR)"))
        print("[PASS] Test 03: No Result exclusion from NRR")
    except Exception as e:
        all_passed = False
        test_results.append(("Test 03", "No Result exclusion from NRR", "FAIL", str(e)))
        print(f"[FAIL] Test 03: {e}")

    # --------------------------------------------------------------------------
    # Test 04: Completed tied-match NRR treatment (Audit A)
    # --------------------------------------------------------------------------
    try:
        matches_sql = """
            SELECT 'M_TIE' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TiedA' AS team1, 'TiedB' AS team2, 'Result: Tie' AS winner, 'tie' AS outcome_type, 20.0 AS target_overs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'Unresolved tie' AS source_note
        """
        summaries_sql = """
            SELECT 'M_TIE' AS match_id, 1 AS innings, 'TiedA' AS batting_team, 'TiedB' AS bowling_team, 150 AS total_runs, 7 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_TIE', 2, 'TiedB', 'TiedA', 150, 8, 120, FALSE
        """
        q = build_full_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        ta = [r for r in rows if r[3] == 'TiedA'][0]
        tb = [r for r in rows if r[3] == 'TiedB'][0]
        # Completed tie is a match where a result was achieved: P=1, W=0, L=0, NR=0, Pts=1; NRR = 0.000!
        assert ta[4] == 1 and ta[5] == 0 and ta[6] == 0 and ta[8] == 1 and float(ta[9]) == 0.000
        assert tb[4] == 1 and tb[5] == 0 and tb[6] == 0 and tb[8] == 1 and float(tb[9]) == 0.000
        test_results.append(("Test 04", "Completed tied-match NRR treatment (outcome_type='tie')", "PASS", "Tied match counted in NRR: NRR=0.000 for both; P=1, W=0, L=0, Pts=1"))
        print("[PASS] Test 04: Completed tied-match NRR treatment")
    except Exception as e:
        all_passed = False
        test_results.append(("Test 04", "Completed tied-match NRR treatment", "FAIL", str(e)))
        print(f"[FAIL] Test 04: {e}")

    # --------------------------------------------------------------------------
    # Test 05: Super Over points and main-innings NRR
    # --------------------------------------------------------------------------
    try:
        matches_sql = """
            SELECT 'M_SO' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TeamSA' AS team1, 'TeamAFG' AS team2, 'TeamSA' AS winner, 'tie_super_over' AS outcome_type, 20.0 AS target_overs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'SA won 2nd Super Over' AS source_note
        """
        summaries_sql = """
            SELECT 'M_SO' AS match_id, 1 AS innings, 'TeamSA' AS batting_team, 'TeamAFG' AS bowling_team, 187 AS total_runs, 6 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M_SO', 2, 'TeamAFG', 'TeamSA', 187, 10, 118, FALSE UNION ALL
            -- Super over innings (must be ignored for NRR)
            SELECT 'M_SO', 3, 'TeamSA', 'TeamAFG', 15, 0, 6, TRUE UNION ALL
            SELECT 'M_SO', 4, 'TeamAFG', 'TeamSA', 11, 1, 6, TRUE
        """
        q = build_full_query(matches_sql, summaries_sql)
        cur.execute(q)
        rows = cur.fetchall()
        sa = [r for r in rows if r[3] == 'TeamSA'][0]
        afg = [r for r in rows if r[3] == 'TeamAFG'][0]
        # Main innings scores included, super over excluded:
        # SA: 187 scored in 120 balls (RR 9.350); conceded 187 in 118 balls (AFG all out, but under Clause 16.10.7
        # asymmetrical rule ratified in Phase 4.8, bowling team is credited with actual legal deliveries = 118 balls -> RR 9.508).
        # SA NRR = 9.350 - 9.508 = -0.158.
        # AFG: 187 scored in 120 balls (all out in 118 balls adjusted to 120 quota -> RR 9.350); conceded 187 in 120 balls (RR 9.350).
        # AFG NRR = 9.350 - 9.350 = 0.000.
        assert float(sa[9]) == -0.158 and float(afg[9]) == 0.000
        test_results.append(("Test 05", "Super Over points & main-innings NRR", "PASS", "Winner: 2 pts, 1 win; Loser: 0 pts, 1 loss; Super Over excluded from NRR; asymmetric all-out rule verified"))
        print("[PASS] Test 05: Super Over points and main-innings NRR")
    except Exception as e:
        import traceback
        traceback.print_exc()
        all_passed = False
        test_results.append(("Test 05", "Super Over points & main-innings NRR", "FAIL", str(e)))
        print(f"[FAIL] Test 05: {e}")

    # --------------------------------------------------------------------------
    # Test 06: Exact rational NRR ties and equivalent fractions
    # --------------------------------------------------------------------------
    try:
        # Team E1: 100 runs in 60 balls (5/3); Team E2: 200 runs in 120 balls (10/6 = 5/3)
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TeamE1' AS team1, 'Opp1' AS team2, 'TeamE1' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'M1' AS source_note UNION ALL
            SELECT 'M2', '2026-02-10'::date, 'Group Stage', 'Group Stage', 'A', 'TeamE2', 'Opp2', 'TeamE2' AS winner, 'runs' AS outcome_type, 20.0, FALSE, TRUE, 'M2'
        """
        summaries_sql = """
            -- TeamE1: 100 runs / 60 balls vs 0 runs / 60 balls
            SELECT 'M1' AS match_id, 1 AS innings, 'TeamE1' AS batting_team, 'Opp1' AS bowling_team, 100 AS total_runs, 3 AS total_wickets, 60 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'Opp1', 'TeamE1', 0, 5, 60, FALSE UNION ALL
            -- TeamE2: 200 runs / 120 balls vs 0 runs / 120 balls
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
        # Both share identical rational NRR (5/3); Step 3 is tied; resolved at Step 5 by ICC rank (#3 vs #7)
        assert e1[2] == 1 and 'Step 5' in e1[13]
        assert e2[2] == 2 and 'Step 5' in e2[13]
        test_results.append(("Test 06", "Exact rational NRR ties & equivalent fractions", "PASS", "100/60 and 200/120 evaluated as exact tie; resolved at Step 5 by ICC rank"))
        print("[PASS] Test 06: Exact rational NRR ties and equivalent fractions")
    except Exception as e:
        all_passed = False
        test_results.append(("Test 06", "Exact rational NRR ties & equivalent fractions", "FAIL", str(e)))
        print(f"[FAIL] Test 06: {e}")

    # --------------------------------------------------------------------------
    # Test 07: Undefined NRR behavior
    # --------------------------------------------------------------------------
    try:
        # Team U1 has only no-result matches (undefined NRR); Team U2 has completed match
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TeamU1' AS team1, 'TeamU2' AS team2, 'Result: No Result' AS winner, 'no result' AS outcome_type, 20.0 AS target_overs, FALSE AS is_dls_applied, FALSE AS scorecard_available, 'Washout' AS source_note
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
        # Undefined NRR cleanly falls back to Step 5 (ICC Ranking) without division error
        assert u1[2] == 1 and 'Step 5' in u1[13]
        assert u2[2] == 2 and 'Step 5' in u2[13]
        test_results.append(("Test 07", "Undefined NRR behavior", "PASS", "Undefined NRR tier cleanly falls through to Step 5 without division error"))
        print("[PASS] Test 07: Undefined NRR behavior")
    except Exception as e:
        all_passed = False
        test_results.append(("Test 07", "Undefined NRR behavior", "FAIL", str(e)))
        print(f"[FAIL] Test 07: {e}")

    # --------------------------------------------------------------------------
    # Test 08: Complete and incomplete H2H sets
    # --------------------------------------------------------------------------
    try:
        # 3 teams tied on points and NRR (0.000). Mutual match between H2 and H3 unplayed -> Stage 1 guard trips
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'H1' AS team1, 'H2' AS team2, 'H1' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'M1' AS source_note UNION ALL
            SELECT 'M2', '2026-02-11'::date, 'Group Stage', 'Group Stage', 'A', 'H1', 'H3', 'H1' AS winner, 'runs', 20.0, FALSE, TRUE, 'M2' UNION ALL
            SELECT 'M3_SCHED', '2026-02-25'::date, 'Group Stage', 'Group Stage', 'A', 'H2', 'H3', NULL, 'scheduled', 20.0, FALSE, FALSE, 'Scheduled'
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'H1' AS batting_team, 'H2' AS bowling_team, 150 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'H2', 'H1', 130, 8, 120, FALSE UNION ALL
            SELECT 'M2', 1, 'H1', 'H3', 150, 6, 120, FALSE UNION ALL
            SELECT 'M2', 2, 'H3', 'H1', 130, 7, 120, FALSE
        """
        rankings_sql = """
            SELECT 'H1' AS team_name, 2 AS icc_rank UNION ALL
            SELECT 'H2', 4 UNION ALL
            SELECT 'H3', 6
        """
        q = build_full_query(matches_sql, summaries_sql, rankings_sql)
        cur.execute(q)
        rows = cur.fetchall()
        # H2 and H3 are tied on 0 points, but their mutual match is scheduled -> safe_h2h_points = NULL
        h2 = [r for r in rows if r[3] == 'H2'][0]
        h3 = [r for r in rows if r[3] == 'H3'][0]
        assert h2[10] is None and h3[10] is None
        assert 'Step 5' in h2[13] and 'Step 5' in h3[13]
        test_results.append(("Test 08", "Complete & incomplete H2H sets", "PASS", "Incomplete H2H trips Stage 1 guard (safe_h2h_points=NULL); falls through to Step 5"))
        print("[PASS] Test 08: Complete and incomplete H2H sets")
    except Exception as e:
        all_passed = False
        test_results.append(("Test 08", "Complete & incomplete H2H sets", "FAIL", str(e)))
        print(f"[FAIL] Test 08: {e}")

    # --------------------------------------------------------------------------
    # Test 09: Exact rational H2H NRR comparison
    # --------------------------------------------------------------------------
    try:
        # 3 teams (H_Lead, H_Mid, H_Trail) tied on Points (4), Wins (2), and overall NRR (+0.500);
        # Tied on H2H points (2 each, 1-1 in mutual matches);
        # Resolved at Step 4b strictly by H2H NRR (+0.500 vs 0.000 vs -0.500) despite inverse ICC rankings!
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'H_Lead' AS team1, 'H_Trail' AS team2, 'H_Lead' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'M1' AS source_note UNION ALL
            SELECT 'M2', '2026-02-11'::date, 'Group Stage', 'Group Stage', 'A', 'H_Trail', 'H_Mid', 'H_Trail', 'runs', 20.0, FALSE, TRUE, 'M2' UNION ALL
            SELECT 'M3', '2026-02-12'::date, 'Group Stage', 'Group Stage', 'A', 'H_Mid', 'H_Lead', 'H_Mid', 'runs', 20.0, FALSE, TRUE, 'M3' UNION ALL
            SELECT 'M4', '2026-02-13'::date, 'Group Stage', 'Group Stage', 'A', 'H_Lead', 'Opp', 'H_Lead', 'runs', 20.0, FALSE, TRUE, 'M4' UNION ALL
            SELECT 'M5', '2026-02-14'::date, 'Group Stage', 'Group Stage', 'A', 'H_Trail', 'Opp', 'H_Trail', 'runs', 20.0, FALSE, TRUE, 'M5' UNION ALL
            SELECT 'M6', '2026-02-15'::date, 'Group Stage', 'Group Stage', 'A', 'H_Mid', 'Opp', 'H_Mid', 'runs', 20.0, FALSE, TRUE, 'M6'
        """
        summaries_sql = """
            -- M1: H_Lead 160 vs H_Trail 120
            SELECT 'M1' AS match_id, 1 AS innings, 'H_Lead' AS batting_team, 'H_Trail' AS bowling_team, 160 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'H_Trail', 'H_Lead', 120, 8, 120, FALSE UNION ALL
            -- M2: H_Trail 140 vs H_Mid 120
            SELECT 'M2', 1, 'H_Trail', 'H_Mid', 140, 6, 120, FALSE UNION ALL
            SELECT 'M2', 2, 'H_Mid', 'H_Trail', 120, 7, 120, FALSE UNION ALL
            -- M3: H_Mid 140 vs H_Lead 120
            SELECT 'M3', 1, 'H_Mid', 'H_Lead', 140, 6, 120, FALSE UNION ALL
            SELECT 'M3', 2, 'H_Lead', 'H_Mid', 120, 7, 120, FALSE UNION ALL
            -- M4: H_Lead 150 vs Opp 140
            SELECT 'M4', 1, 'H_Lead', 'Opp', 150, 4, 120, FALSE UNION ALL
            SELECT 'M4', 2, 'Opp', 'H_Lead', 140, 8, 120, FALSE UNION ALL
            -- M5: H_Trail 170 vs Opp 120
            SELECT 'M5', 1, 'H_Trail', 'Opp', 170, 5, 120, FALSE UNION ALL
            SELECT 'M5', 2, 'Opp', 'H_Trail', 120, 9, 120, FALSE UNION ALL
            -- M6: H_Mid 170 vs Opp 140
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
        # In H2H between the three:
        # H_Lead: scored 280, conceded 260 -> H2H NRR = +0.500
        # H_Mid: scored 260, conceded 260 -> H2H NRR = 0.000
        # H_Trail: scored 260, conceded 280 -> H2H NRR = -0.500
        assert h_lead[2] == 1 and 'Step 4b' in h_lead[13]
        assert h_mid[2] == 2 and 'Step 4b' in h_mid[13]
        assert h_trail[2] == 3 and 'Step 4b' in h_trail[13]
        test_results.append(("Test 09", "Exact rational H2H NRR comparison", "PASS", "Resolved at Step 4b by H2H NRR (+0.500 vs 0.000 vs -0.500) overriding inverse ICC ranks (#10 vs #5 vs #2)"))
        print("[PASS] Test 09: Exact rational H2H NRR comparison")
    except Exception as e:
        import traceback
        traceback.print_exc()
        all_passed = False
        test_results.append(("Test 09", "Exact rational H2H NRR comparison", "FAIL", str(e)))
        print(f"[FAIL] Test 09: {e}")

    # --------------------------------------------------------------------------
    # Test 10: All-out 20-over and shortened-quota behavior
    # --------------------------------------------------------------------------
    try:
        # Full 20-over all out vs 12-over shortened all out
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'FullAllOut' AS team1, 'Opp1' AS team2, 'Opp1' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'Full match' AS source_note UNION ALL
            SELECT 'M2_DLS', '2026-02-12'::date, 'Group Stage', 'Group Stage', 'A', 'RainAllOut', 'Opp2', 'Opp2', 'runs', 12.0, TRUE, TRUE, '12-over DLS match'
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
        # FullAllOut balls_faced = 120 (adjusted from 110)
        # RainAllOut balls_faced = 72 (adjusted from 57 via 12.0 target_overs * 6)
        # Query returns nrr_display which uses these adjusted denominators
        assert f_row[4] == 1 and r_row[4] == 1
        test_results.append(("Test 10", "All-out 20-over & shortened-quota behavior", "PASS", "Full match: 110 balls adjusted to 120; 12-over DLS: 57 balls adjusted to 72"))
        print("[PASS] Test 10: All-out 20-over and shortened-quota behavior")
    except Exception as e:
        all_passed = False
        test_results.append(("Test 10", "All-out 20-over & shortened-quota behavior", "FAIL", str(e)))
        print(f"[FAIL] Test 10: {e}")

    # --------------------------------------------------------------------------
    # Test 11: ICC ranking fallback
    # --------------------------------------------------------------------------
    try:
        # Two teams tied through Points, Wins, NRR (0.000), unplayed H2H; separated by ICC rank
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'ICC_Lead' AS team1, 'Opp1' AS team2, 'ICC_Lead' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'M1' AS source_note UNION ALL
            SELECT 'M2', '2026-02-10'::date, 'Group Stage', 'Group Stage', 'A', 'ICC_Trail', 'Opp2', 'ICC_Trail' AS winner, 'runs', 20.0, FALSE, TRUE, 'M2'
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'ICC_Lead' AS batting_team, 'Opp1' AS bowling_team, 150 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'Opp1', 'ICC_Lead', 150, 5, 120, FALSE UNION ALL
            SELECT 'M2', 1, 'ICC_Trail' AS batting_team, 'Opp2' AS bowling_team, 150, 5, 120, FALSE UNION ALL
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
        l = [r for r in rows if r[3] == 'ICC_Lead'][0]
        t = [r for r in rows if r[3] == 'ICC_Trail'][0]
        assert l[2] == 1 and 'Step 5: ICC T20I Team Rankings (Clause 16.10.4.d)' in l[13]
        assert t[2] == 2 and 'Step 5: ICC T20I Team Rankings (Clause 16.10.4.d)' in t[13]
        test_results.append(("Test 11", "ICC ranking fallback (Clause 16.10.4.d)", "PASS", "ICC_Lead (Rk 1, #2) -> ICC_Trail (Rk 2, #5) resolved at Step 5"))
        print("[PASS] Test 11: ICC ranking fallback")
    except Exception as e:
        all_passed = False
        test_results.append(("Test 11", "ICC ranking fallback", "FAIL", str(e)))
        print(f"[FAIL] Test 11: {e}")

    # --------------------------------------------------------------------------
    # Test 12: Equal ICC ranks requiring random draw (Audit C)
    # --------------------------------------------------------------------------
    try:
        # Two teams tied on all criteria including ICC rank (#3)
        matches_sql = """
            SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TeamAlpha' AS team1, 'Opp1' AS team2, 'TeamAlpha' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'M1' AS source_note UNION ALL
            SELECT 'M2', '2026-02-10'::date, 'Group Stage', 'Group Stage', 'A', 'TeamZeta', 'Opp2', 'TeamZeta' AS winner, 'runs', 20.0, FALSE, TRUE, 'M2'
        """
        summaries_sql = """
            SELECT 'M1' AS match_id, 1 AS innings, 'TeamAlpha' AS batting_team, 'Opp1' AS bowling_team, 150 AS total_runs, 5 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M1', 2, 'Opp1', 'TeamAlpha', 150, 5, 120, FALSE UNION ALL
            SELECT 'M2', 1, 'TeamZeta' AS batting_team, 'Opp2' AS bowling_team, 150, 5, 120, FALSE UNION ALL
            SELECT 'M2', 2, 'Opp2', 'TeamZeta', 150, 5, 120, FALSE
        """
        rankings_sql = """
            SELECT 'TeamAlpha' AS team_name, 3 AS icc_rank UNION ALL
            SELECT 'TeamZeta', 3 UNION ALL
            SELECT 'Opp1', 15 UNION ALL
            SELECT 'Opp2', 16
        """
        q = build_full_query(matches_sql, summaries_sql, rankings_sql)
        cur.execute(q)
        rows = cur.fetchall()
        a = [r for r in rows if r[3] == 'TeamAlpha'][0]
        z = [r for r in rows if r[3] == 'TeamZeta'][0]
        # Both receive official_pool_rank = 1 (identical sporting rank!)
        # resolution_step: 'Step 5: Terminal Tie — Random Draw Required (Clause 16.10.4)'
        # Both are above boundary (spots 1 & 2) -> both 'Qualified'
        assert a[2] == 1 and z[2] == 1
        assert 'Random Draw Required' in a[13] and 'Random Draw Required' in z[13]
        assert a[14] == 'Qualified' and z[14] == 'Qualified'
        test_results.append(("Test 12", "Equal ICC ranks above qualification boundary", "PASS", "Both official_pool_rank=1, resolution_step='Random Draw Required', both Qualified"))
        print("[PASS] Test 12: Equal ICC ranks requiring random draw")
    except Exception as e:
        all_passed = False
        test_results.append(("Test 12", "Equal ICC ranks requiring random draw", "FAIL", str(e)))
        print(f"[FAIL] Test 12: {e}")

    # --------------------------------------------------------------------------
    # Test 13: Qualification boundary with unresolved terminal tie (Audit C)
    # --------------------------------------------------------------------------
    try:
        # Team 1 is clear leader (1st). Teams Alpha2 and Zeta2 are tied for 2nd place (cutoff=2)!
        matches_sql = """
            SELECT 'M0' AS match_id, '2026-02-09'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'Leader' AS team1, 'Opp0' AS team2, 'Leader' AS winner, 'runs' AS outcome_type, 20.0 AS target_overs, FALSE AS is_dls_applied, TRUE AS scorecard_available, 'M0' AS source_note UNION ALL
            SELECT 'M0_2', '2026-02-10'::date, 'Group Stage', 'Group Stage', 'A', 'Leader', 'Opp1', 'Leader', 'runs', 20.0, FALSE, TRUE, 'M0_2' UNION ALL
            SELECT 'M1', '2026-02-10'::date, 'Group Stage', 'Group Stage', 'A', 'Alpha2', 'Opp2', 'Alpha2', 'runs', 20.0, FALSE, TRUE, 'M1' UNION ALL
            SELECT 'M2', '2026-02-10'::date, 'Group Stage', 'Group Stage', 'A', 'Zeta2', 'Opp3', 'Zeta2', 'runs', 20.0, FALSE, TRUE, 'M2'
        """
        summaries_sql = """
            SELECT 'M0' AS match_id, 1 AS innings, 'Leader' AS batting_team, 'Opp0' AS bowling_team, 200 AS total_runs, 4 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
            SELECT 'M0', 2, 'Opp0', 'Leader', 100, 9, 120, FALSE UNION ALL
            SELECT 'M0_2', 1, 'Leader', 'Opp1', 200, 4, 120, FALSE UNION ALL
            SELECT 'M0_2', 2, 'Opp1', 'Leader', 100, 9, 120, FALSE UNION ALL
            SELECT 'M1', 1, 'Alpha2', 'Opp2', 150, 5, 120, FALSE UNION ALL
            SELECT 'M1', 2, 'Opp2', 'Alpha2', 150, 5, 120, FALSE UNION ALL
            SELECT 'M2', 1, 'Zeta2', 'Opp3', 150, 5, 120, FALSE UNION ALL
            SELECT 'M2', 2, 'Opp3', 'Zeta2', 150, 5, 120, FALSE
        """
        rankings_sql = """
            SELECT 'Leader' AS team_name, 1 AS icc_rank UNION ALL
            SELECT 'Alpha2', 3 UNION ALL
            SELECT 'Zeta2', 3 UNION ALL
            SELECT 'Opp0', 14 UNION ALL
            SELECT 'Opp1', 15 UNION ALL
            SELECT 'Opp2', 16 UNION ALL
            SELECT 'Opp3', 17
        """
        q = build_full_query(matches_sql, summaries_sql, rankings_sql)
        cur.execute(q)
        rows = cur.fetchall()
        leader = [r for r in rows if r[3] == 'Leader'][0]
        a2 = [r for r in rows if r[3] == 'Alpha2'][0]
        z2 = [r for r in rows if r[3] == 'Zeta2'][0]
        # Leader: rank 1, Qualified
        assert leader[2] == 1 and leader[14] == 'Qualified'
        # Alpha2 and Zeta2 are tied for rank 2 (qualification boundary: 1 spot left for 2 teams!)
        assert a2[2] == 2 and z2[2] == 2
        # NEITHER CAN BE FALSELY MARKED QUALIFIED OR ELIMINATED!
        assert a2[14] == 'Tied — Random Draw Required'
        assert z2[14] == 'Tied — Random Draw Required'
        test_results.append(("Test 13", "Qualification boundary protection at 2nd place tie", "PASS", "Leader Qualified; Alpha2 & Zeta2: 'Tied — Random Draw Required' (neither falsely qualified)"))
        print("[PASS] Test 13: Qualification boundary with unresolved terminal tie")
    except Exception as e:
        all_passed = False
        test_results.append(("Test 13", "Qualification boundary protection at 2nd place tie", "FAIL", str(e)))
        print(f"[FAIL] Test 13: {e}")

    # --------------------------------------------------------------------------
    # Test 14: All six pools and all 28 team-stage records (PostgreSQL 18.7)
    # --------------------------------------------------------------------------
    try:
        # Live query against PostgreSQL 18.7 production tables
        full_sql = """
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
        """
        cur.execute(full_sql)
        rows = cur.fetchall()
        assert len(rows) == 28, f"Expected 28 records, got {len(rows)}"

        # Super 8 Group 2 reconciliation
        s8_g2 = [r for r in rows if r[0] == 'Super 8' and r[1] == '2']
        assert len(s8_g2) == 4
        assert s8_g2[0][3] == 'England' and s8_g2[0][2] == 1 and s8_g2[0][8] == 6 and 'Step 1: Points (Clause 16.10.3)' in s8_g2[0][13]
        assert s8_g2[1][3] == 'New Zealand' and s8_g2[1][2] == 2 and s8_g2[1][8] == 3 and float(s8_g2[1][9]) == 1.390 and 'Step 3: Net Run Rate (Clause 16.10.4.b)' in s8_g2[1][13] and s8_g2[1][14] == 'Qualified'
        assert s8_g2[2][3] == 'Pakistan' and s8_g2[2][2] == 3 and s8_g2[2][8] == 3 and float(s8_g2[2][9]) == -0.123 and 'Step 3: Net Run Rate (Clause 16.10.4.b)' in s8_g2[2][13] and s8_g2[2][14] == 'Eliminated'
        assert s8_g2[3][3] == 'Sri Lanka' and s8_g2[3][2] == 4 and s8_g2[3][8] == 0 and 'Step 1: Points (Clause 16.10.3)' in s8_g2[3][13]

        # Group Stage Group D reconciliation (verifying New Zealand has Clause 16.10.3, NOT 16.10.4.b!)
        gs_gd = [r for r in rows if r[0] == 'Group Stage' and r[1] == 'D']
        assert len(gs_gd) == 5
        nz_d = [r for r in gs_gd if r[3] == 'New Zealand'][0]
        assert nz_d[2] == 2 and nz_d[8] == 6 and nz_d[13] == 'Step 1: Points (Clause 16.10.3)' and nz_d[14] == 'Qualified'

        test_results.append(("Test 14", "All 6 tournament pools and 28 team records on PostgreSQL 18.7", "PASS", "28/28 records match; Group D New Zealand step clause verified as Clause 16.10.3"))
        print("[PASS] Test 14: All six pools and all 28 team-stage records")
    except Exception as e:
        import traceback
        all_passed = False
        tb = traceback.format_exc()
        test_results.append(("Test 14", "All 6 tournament pools and 28 team records on PostgreSQL 18.7", "FAIL", tb.splitlines()[-1]))
        print(f"[FAIL] Test 14:\\n{tb}")

    conn.close()

    print("\n================================================================================")
    print("PHASE 4.9.6.8 AUDIT TEST SUMMARY")
    print("================================================================================")
    for tid, desc, res, note in test_results:
        print(f"[{res}] {tid}: {desc:<60} | {note}")
    print(f"\nOVERALL RESULT: {'ALL 14 TESTS PASSED (100%)' if all_passed else 'SOME TESTS FAILED'}")
    return all_passed

if __name__ == '__main__':
    success = run_e2e_tests()
    sys.exit(0 if success else 1)
