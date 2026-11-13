-- ==============================================================================
-- View: vw_bowling_statistics
-- Granular bowling efficiency metrics including dot ball percentage and boundary concession
-- ==============================================================================

CREATE OR REPLACE VIEW vw_bowling_statistics AS
SELECT 
    bw.player_id,
    bw.player_name,
    bw.team,
    COUNT(bw.match_id) AS innings_bowled,
    SUM(bw.legal_balls) AS legal_balls,
    ROUND((SUM(bw.legal_balls) / 6) + ((SUM(bw.legal_balls) % 6) / 10.0), 1) AS overs,
    SUM(bw.runs_conceded) AS runs_conceded,
    SUM(bw.wickets) AS wickets,
    SUM(bw.dots) AS dot_balls,
    ROUND(
        CASE 
            WHEN SUM(bw.legal_balls) > 0 
            THEN (SUM(bw.dots)::NUMERIC / SUM(bw.legal_balls)) * 100.0
            ELSE 0.00 
        END, 2
    ) AS dot_ball_percentage,
    SUM(bw.fours_conceded) AS fours_conceded,
    SUM(bw.sixes_conceded) AS sixes_conceded,
    ROUND(
        CASE 
            WHEN SUM(bw.legal_balls) > 0 
            THEN (SUM(bw.runs_conceded)::NUMERIC / (SUM(bw.legal_balls)::NUMERIC / 6.0))
            ELSE 0.00 
        END, 2
    ) AS economy_rate,
    ROUND(
        CASE 
            WHEN SUM(bw.wickets) > 0 
            THEN SUM(bw.runs_conceded)::NUMERIC / SUM(bw.wickets)
            ELSE NULL 
        END, 2
    ) AS bowling_average
FROM fact_bowling_scorecards bw
GROUP BY bw.player_id, bw.player_name, bw.team
HAVING SUM(bw.legal_balls) >= 24
ORDER BY wickets DESC, economy_rate ASC;
