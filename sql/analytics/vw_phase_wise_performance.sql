-- ==============================================================================
-- View: vw_phase_wise_performance
-- Team scoring and wicket rates segmented by Powerplay (0-5), Middle (6-14), and Death (15-19)
-- ==============================================================================

CREATE OR REPLACE VIEW vw_phase_wise_performance AS
SELECT 
    d.batting_team,
    d.phase,
    COUNT(DISTINCT d.match_id) AS matches_batted,
    SUM(d.total_runs) AS phase_runs,
    SUM(CASE WHEN d.is_legal_delivery THEN 1 ELSE 0 END) AS phase_legal_balls,
    SUM(CASE WHEN d.is_wicket THEN 1 ELSE 0 END) AS phase_wickets_lost,
    SUM(CASE WHEN d.is_boundary_four THEN 1 ELSE 0 END) AS phase_fours,
    SUM(CASE WHEN d.is_boundary_six THEN 1 ELSE 0 END) AS phase_sixes,
    SUM(CASE WHEN d.is_dot_ball THEN 1 ELSE 0 END) AS phase_dot_balls,
    ROUND(
        CASE 
            WHEN SUM(CASE WHEN d.is_legal_delivery THEN 1 ELSE 0 END) > 0 
            THEN (SUM(d.total_runs)::NUMERIC / (SUM(CASE WHEN d.is_legal_delivery THEN 1 ELSE 0 END)::NUMERIC / 6.0))
            ELSE 0.00 
        END, 2
    ) AS phase_run_rate,
    ROUND(
        CASE 
            WHEN SUM(d.total_runs) > 0 
            THEN (SUM(CASE WHEN d.is_boundary_four THEN 4 ELSE 0 END + CASE WHEN d.is_boundary_six THEN 6 ELSE 0 END)::NUMERIC / SUM(d.total_runs)) * 100.0
            ELSE 0.00 
        END, 2
    ) AS boundary_run_percentage
FROM fact_deliveries d
GROUP BY d.batting_team, d.phase
ORDER BY d.batting_team, 
    CASE d.phase 
        WHEN 'Powerplay' THEN 1 
        WHEN 'Middle' THEN 2 
        WHEN 'Death' THEN 3 
        ELSE 4 
    END;
