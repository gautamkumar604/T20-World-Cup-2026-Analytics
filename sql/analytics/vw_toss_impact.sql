-- ==============================================================================
-- View: vw_toss_impact
-- Evaluates the correlation between winning the coin toss and winning the match
-- ==============================================================================

CREATE OR REPLACE VIEW vw_toss_impact AS
SELECT 
    m.toss_decision,
    COUNT(m.match_id) AS total_decisions,
    SUM(CASE WHEN m.toss_winner = m.winner THEN 1 ELSE 0 END) AS toss_and_match_wins,
    SUM(CASE WHEN m.toss_winner != m.winner AND m.outcome_type NOT IN ('no result') THEN 1 ELSE 0 END) AS toss_won_match_lost,
    SUM(CASE WHEN m.outcome_type = 'no result' THEN 1 ELSE 0 END) AS no_results,
    ROUND(
        CASE 
            WHEN (COUNT(m.match_id) - SUM(CASE WHEN m.outcome_type = 'no result' THEN 1 ELSE 0 END)) > 0 
            THEN (SUM(CASE WHEN m.toss_winner = m.winner THEN 1.0 ELSE 0.0 END) / 
                  (COUNT(m.match_id) - SUM(CASE WHEN m.outcome_type = 'no result' THEN 1 ELSE 0 END))) * 100.0
            ELSE 0.00 
        END, 2
    ) AS toss_win_to_match_win_pct
FROM dim_matches m
WHERE m.toss_decision IS NOT NULL
GROUP BY m.toss_decision;

