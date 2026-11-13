-- ==============================================================================
-- View: vw_team_performance
-- Team standings, match outcomes, win percentages, and run rates
-- ==============================================================================

CREATE OR REPLACE VIEW vw_team_performance AS
WITH match_outcomes AS (
    SELECT 
        t.team_name,
        t.group_2026,
        m.match_id,
        CASE 
            WHEN m.winner = t.team_name THEN 'WIN'
            WHEN m.winner LIKE 'Result:%' OR m.outcome_type = 'no result' THEN 'NO_RESULT'
            WHEN m.outcome_type = 'tie' THEN 'TIE'
            ELSE 'LOSS'
        END AS outcome
    FROM dim_teams t
    JOIN dim_matches m ON t.team_name = m.team1 OR t.team_name = m.team2
),
team_runs AS (
    SELECT 
        s.batting_team AS team_name,
        SUM(s.total_runs) AS total_runs_scored,
        SUM(s.legal_deliveries) AS total_balls_batted,
        SUM(s.total_wickets) AS total_wickets_lost
    FROM fact_match_summaries s
    GROUP BY s.batting_team
)
SELECT 
    mo.team_name,
    mo.group_2026,
    COUNT(mo.match_id) AS matches_played,
    SUM(CASE WHEN mo.outcome = 'WIN' THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN mo.outcome = 'LOSS' THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN mo.outcome = 'TIE' THEN 1 ELSE 0 END) AS ties,
    SUM(CASE WHEN mo.outcome = 'NO_RESULT' THEN 1 ELSE 0 END) AS no_results,
    ROUND(
        CASE 
            WHEN COUNT(mo.match_id) - SUM(CASE WHEN mo.outcome = 'NO_RESULT' THEN 1 ELSE 0 END) > 0 
            THEN (SUM(CASE WHEN mo.outcome = 'WIN' THEN 1.0 ELSE 0.0 END) / 
                  (COUNT(mo.match_id) - SUM(CASE WHEN mo.outcome = 'NO_RESULT' THEN 1 ELSE 0 END))) * 100.0
            ELSE 0.00 
        END, 2
    ) AS win_percentage,
    COALESCE(tr.total_runs_scored, 0) AS total_runs_scored,
    COALESCE(tr.total_wickets_lost, 0) AS total_wickets_lost,
    ROUND(
        CASE 
            WHEN COALESCE(tr.total_balls_batted, 0) > 0 
            THEN (tr.total_runs_scored::NUMERIC / (tr.total_balls_batted::NUMERIC / 6.0))
            ELSE 0.00 
        END, 2
    ) AS tournament_run_rate
FROM match_outcomes mo
LEFT JOIN team_runs tr ON mo.team_name = tr.team_name
GROUP BY mo.team_name, mo.group_2026, tr.total_runs_scored, tr.total_balls_batted, tr.total_wickets_lost
ORDER BY wins DESC, win_percentage DESC;
