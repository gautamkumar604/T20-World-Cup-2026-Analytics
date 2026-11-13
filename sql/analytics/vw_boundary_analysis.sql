-- ==============================================================================
-- View: vw_boundary_analysis
-- Distribution of 4s and 6s across teams, boundary frequencies, and boundary runs
-- ==============================================================================

CREATE OR REPLACE VIEW vw_boundary_analysis AS
SELECT 
    d.batting_team,
    COUNT(DISTINCT d.match_id) AS matches_played,
    SUM(d.total_runs) AS total_runs,
    SUM(CASE WHEN d.is_boundary_four THEN 1 ELSE 0 END) AS total_fours,
    SUM(CASE WHEN d.is_boundary_six THEN 1 ELSE 0 END) AS total_sixes,
    SUM(CASE WHEN d.is_boundary_four THEN 4 ELSE 0 END + CASE WHEN d.is_boundary_six THEN 6 ELSE 0 END) AS total_boundary_runs,
    ROUND(
        CASE 
            WHEN SUM(d.total_runs) > 0 
            THEN (SUM(CASE WHEN d.is_boundary_four THEN 4 ELSE 0 END + CASE WHEN d.is_boundary_six THEN 6 ELSE 0 END)::NUMERIC / SUM(d.total_runs)) * 100.0
            ELSE 0.00 
        END, 2
    ) AS boundary_percentage,
    ROUND(
        CASE 
            WHEN (SUM(CASE WHEN d.is_boundary_four THEN 1 ELSE 0 END) + SUM(CASE WHEN d.is_boundary_six THEN 1 ELSE 0 END)) > 0 
            THEN SUM(CASE WHEN d.is_legal_delivery THEN 1 ELSE 0 END)::NUMERIC / 
                 (SUM(CASE WHEN d.is_boundary_four THEN 1 ELSE 0 END) + SUM(CASE WHEN d.is_boundary_six THEN 1 ELSE 0 END))
            ELSE 0.00 
        END, 1
    ) AS balls_per_boundary
FROM fact_deliveries d
GROUP BY d.batting_team
ORDER BY total_boundary_runs DESC;

