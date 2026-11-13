-- ==============================================================================
-- View: vw_venue_analysis
-- Venue characteristics: matches played, batting 1st vs 2nd wins, average scores
-- ==============================================================================

CREATE OR REPLACE VIEW vw_venue_analysis AS
WITH innings_scores AS (
    SELECT 
        m.venue,
        s.match_id,
        s.innings,
        s.total_runs
    FROM fact_match_summaries s
    JOIN dim_matches m ON s.match_id = m.match_id
    WHERE s.is_super_over = FALSE
)
SELECT 
    v.venue_name,
    v.city,
    v.country,
    COUNT(DISTINCT m.match_id) AS total_matches_scheduled,
    SUM(CASE WHEN m.outcome_type NOT IN ('no result') AND m.winner NOT LIKE 'Result:%' THEN 1 ELSE 0 END) AS matches_completed,
    SUM(CASE WHEN m.outcome_type = 'runs' THEN 1 ELSE 0 END) AS bat_first_wins,
    SUM(CASE WHEN m.outcome_type = 'wickets' THEN 1 ELSE 0 END) AS bat_second_wins,
    SUM(CASE WHEN m.outcome_type LIKE '%super_over%' OR m.outcome_type = 'tie' THEN 1 ELSE 0 END) AS tied_matches,
    ROUND(AVG(CASE WHEN i.innings = 1 THEN i.total_runs ELSE NULL END), 1) AS avg_first_innings_score,
    ROUND(AVG(CASE WHEN i.innings = 2 THEN i.total_runs ELSE NULL END), 1) AS avg_second_innings_score,
    MAX(CASE WHEN i.innings = 1 THEN i.total_runs ELSE NULL END) AS highest_innings_score,
    MIN(CASE WHEN i.innings = 1 THEN i.total_runs ELSE NULL END) AS lowest_defended_score
FROM dim_venues v
LEFT JOIN dim_matches m ON v.venue_name = m.venue
LEFT JOIN innings_scores i ON m.match_id = i.match_id
GROUP BY v.venue_name, v.city, v.country
ORDER BY total_matches_scheduled DESC;
