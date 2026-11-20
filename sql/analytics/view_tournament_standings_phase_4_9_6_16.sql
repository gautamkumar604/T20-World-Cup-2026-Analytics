-- =============================================================================
-- ICC Men's T20 World Cup 2026 - Official Tournament Standings Ranking View
-- File: sql/analytics/view_tournament_standings_phase_4_9_6_15.sql
-- Database: PostgreSQL 18.7
-- Engine: Exact Rational 22-CTE Ranking Engine with Clause 16.10.7 Symmetry
-- Deployment Gate: Phase 4.9.6.16 (Validated & Pre-Deployment Hardened)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PREREQUISITE 1: Hardened Euclidean GCD Function (INT64_MIN Safe)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.fn_calc_gcd(a bigint, b bigint)
RETURNS bigint AS $$
DECLARE
    x bigint;
    y bigint;
    t bigint;
BEGIN
    IF a IS NULL OR b IS NULL THEN
        RETURN NULL;
    END IF;
    -- INT64_MIN Guard (signed 64-bit integer overflow protection)
    IF a = (-9223372036854775807 - 1) OR b = (-9223372036854775807 - 1) THEN
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
$$ LANGUAGE plpgsql IMMUTABLE STRICT;

-- -----------------------------------------------------------------------------
-- PRODUCTION VIEW: view_tournament_standings (22-CTE Ranking Engine)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.view_tournament_standings AS
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
        dls_allocated_overs_team1,
        dls_team1_innings_shortened,
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
        m.is_dls_abandoned,
        m.dls_allocated_overs,
        m.dls_abandonment_overs,
        m.dls_par_score,
        m.dls_allocated_overs_team1,
        m.dls_team1_innings_shortened,
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
        m.dls_allocated_overs_team1,
        m.dls_team1_innings_shortened,
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
                EXISTS (SELECT 1 FROM fact_match_summaries s WHERE s.match_id = mo.match_id AND s.legal_deliveries > 0)
            ) THEN 1
            ELSE 0
        END AS is_genuinely_played,
        -- DLS Evaluation Status (0=Regular, 1=Valid Completed, 2=Valid Abandoned, 3=Unresolved Completed, 4=Unresolved Abandoned, 5=Unknown)
        CASE 
            WHEN mo.is_dls_applied = FALSE THEN 0
            WHEN mo.outcome_type NOT IN ('runs', 'wickets', 'tie', 'tie_super_over') THEN 0
            WHEN mo.is_dls_abandoned IS NULL THEN 5
            WHEN mo.is_dls_abandoned = FALSE THEN
                CASE 
                    WHEN mo.target_runs IS NOT NULL 
                         AND mo.dls_allocated_overs IS NOT NULL 
                         AND mo.dls_allocated_overs > 0 
                         AND (mo.dls_allocated_overs - FLOOR(mo.dls_allocated_overs)) * 10 BETWEEN 0 AND 5
                         AND mo.dls_allocated_overs_team1 IS NOT NULL
                         AND mo.dls_allocated_overs_team1 > 0
                         AND (mo.dls_allocated_overs_team1 - FLOOR(mo.dls_allocated_overs_team1)) * 10 BETWEEN 0 AND 5 THEN 1
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
    -- Normal completed scorecards from fact_match_summaries (excluding forfeits)
    SELECT 
        s.match_id, s.innings, s.batting_team, s.bowling_team,
        s.total_runs, s.total_wickets, s.legal_deliveries, s.is_super_over
    FROM fact_match_summaries s
    JOIN stage_matches m ON s.match_id = m.match_id
    WHERE m.outcome_type <> 'forfeit' AND s.is_super_over = FALSE
    
    UNION ALL
    
    -- Synthetic accounting record for forfeit matches (ICC Clause 16.10.4.b / 16.10.7)
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
                    WHEN mpe.dls_status = 1 AND s.innings = 1 THEN
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
                    WHEN mpe.dls_status = 1 AND s.innings = 1 THEN
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
                    WHEN mpe.dls_status = 1 AND s.innings = 1 THEN
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
                    WHEN mpe.dls_status = 1 AND s.innings = 1 THEN
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
        mpe.dls_allocated_overs_team1,
        mpe.dls_team1_innings_shortened,
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
                    WHEN hm.dls_status = 1 AND s.innings = 1 THEN
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
                    WHEN hm.dls_status = 1 AND s.innings = 1 THEN
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
                    WHEN hm.dls_status = 1 AND s.innings = 1 THEN
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
                    WHEN hm.dls_status = 1 AND s.innings = 1 THEN
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
