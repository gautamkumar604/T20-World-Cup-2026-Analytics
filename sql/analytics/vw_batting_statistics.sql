-- ==============================================================================
-- View: vw_batting_statistics
-- Granular batting metrics including boundary percentage, dot ball percentage, and conversion
-- ==============================================================================

CREATE OR REPLACE VIEW vw_batting_statistics AS
SELECT 
    b.player_id,
    b.player_name,
    b.team,
    COUNT(b.match_id) AS innings,
    SUM(b.runs) AS runs,
    SUM(b.balls_faced) AS balls_faced,
    SUM(b.fours) AS fours,
    SUM(b.sixes) AS sixes,
    SUM(b.fours * 4 + b.sixes * 6) AS boundary_runs,
    ROUND(
        CASE 
            WHEN SUM(b.runs) > 0 
            THEN (SUM(b.fours * 4 + b.sixes * 6)::NUMERIC / SUM(b.runs)) * 100.0
            ELSE 0.00 
        END, 2
    ) AS boundary_run_percentage,
    ROUND(
        CASE 
            WHEN SUM(b.balls_faced) > 0 
            THEN (SUM(b.runs)::NUMERIC / SUM(b.balls_faced)) * 100.0 
            ELSE 0.00 
        END, 2
    ) AS strike_rate,
    ROUND(
        CASE 
            WHEN (COUNT(b.match_id) - SUM(CASE WHEN b.is_out = FALSE THEN 1 ELSE 0 END)) > 0 
            THEN SUM(b.runs)::NUMERIC / (COUNT(b.match_id) - SUM(CASE WHEN b.is_out = FALSE THEN 1 ELSE 0 END))
            ELSE SUM(b.runs)::NUMERIC 
        END, 2
    ) AS batting_average
FROM fact_batting_scorecards b
GROUP BY b.player_id, b.player_name, b.team
HAVING SUM(b.balls_faced) >= 10
ORDER BY runs DESC;
