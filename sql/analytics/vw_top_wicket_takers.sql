-- ==============================================================================
-- View: vw_top_wicket_takers
-- Top wicket takers with legal overs, maidens, economy rates, and bowling averages
-- ==============================================================================

CREATE OR REPLACE VIEW vw_top_wicket_takers AS
SELECT 
    bw.player_id,
    bw.player_name,
    bw.team,
    COUNT(DISTINCT bw.match_id) AS matches_played,
    COUNT(bw.match_id) AS innings_bowled,
    SUM(bw.legal_balls) AS total_legal_balls,
    ROUND((SUM(bw.legal_balls) / 6) + ((SUM(bw.legal_balls) % 6) / 10.0), 1) AS total_overs_bowled,
    SUM(bw.maidens) AS total_maidens,
    SUM(bw.runs_conceded) AS total_runs_conceded,
    SUM(bw.wickets) AS total_wickets,
    ROUND(
        CASE 
            WHEN SUM(bw.wickets) > 0 
            THEN SUM(bw.runs_conceded)::NUMERIC / SUM(bw.wickets)
            ELSE NULL 
        END, 2
    ) AS bowling_average,
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
            THEN SUM(bw.legal_balls)::NUMERIC / SUM(bw.wickets)
            ELSE NULL 
        END, 2
    ) AS strike_rate_balls_per_wicket,
    SUM(bw.dots) AS total_dot_balls
FROM fact_bowling_scorecards bw
GROUP BY bw.player_id, bw.player_name, bw.team
ORDER BY total_wickets DESC, economy_rate ASC;

