-- ==============================================================================
-- View: vw_top_run_scorers
-- Top run scorers across the tournament with innings, boundaries, and strike rates
-- ==============================================================================

CREATE OR REPLACE VIEW vw_top_run_scorers AS
SELECT 
    b.player_id,
    b.player_name,
    b.team,
    COUNT(DISTINCT b.match_id) AS matches_played,
    COUNT(b.match_id) AS innings_batted,
    SUM(CASE WHEN b.is_out = FALSE THEN 1 ELSE 0 END) AS not_outs,
    SUM(b.runs) AS total_runs,
    SUM(b.balls_faced) AS total_balls_faced,
    SUM(b.fours) AS total_fours,
    SUM(b.sixes) AS total_sixes,
    MAX(b.runs) AS highest_score,
    ROUND(
        CASE 
            WHEN (COUNT(b.match_id) - SUM(CASE WHEN b.is_out = FALSE THEN 1 ELSE 0 END)) > 0 
            THEN SUM(b.runs)::NUMERIC / (COUNT(b.match_id) - SUM(CASE WHEN b.is_out = FALSE THEN 1 ELSE 0 END))
            ELSE SUM(b.runs)::NUMERIC 
        END, 2
    ) AS batting_average,
    ROUND(
        CASE 
            WHEN SUM(b.balls_faced) > 0 
            THEN (SUM(b.runs)::NUMERIC / SUM(b.balls_faced)) * 100.0 
            ELSE 0.00 
        END, 2
    ) AS strike_rate,
    SUM(CASE WHEN b.runs >= 50 AND b.runs < 100 THEN 1 ELSE 0 END) AS fifties,
    SUM(CASE WHEN b.runs >= 100 THEN 1 ELSE 0 END) AS hundreds
FROM fact_batting_scorecards b
GROUP BY b.player_id, b.player_name, b.team
ORDER BY total_runs DESC, strike_rate DESC;
