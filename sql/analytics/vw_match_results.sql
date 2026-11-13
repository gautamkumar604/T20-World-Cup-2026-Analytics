-- ==============================================================================
-- View: vw_match_results
-- Match-by-match executive summary with scores, outcome details, and data coverage indicators
-- ==============================================================================

CREATE OR REPLACE VIEW vw_match_results AS
SELECT 
    m.match_number,
    m.match_id,
    m.match_date,
    m.stage,
    m.group_name,
    m.team1,
    m.team2,
    m.venue,
    m.city,
    m.toss_winner,
    m.toss_decision,
    m.winner,
    m.outcome_type,
    m.win_margin,
    m.player_of_match,
    m.metadata_available,
    m.scorecard_available,
    m.ball_by_ball_available,
    m.source_note
FROM dim_matches m
ORDER BY m.match_date ASC, m.match_number ASC;
