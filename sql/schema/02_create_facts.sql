-- ==============================================================================
-- ICC Men's T20 World Cup 2026 - PostgreSQL Relational Data Warehouse Schema
-- 02_create_facts.sql: Fact Tables DDL
-- ==============================================================================

-- 1. Fact Table: Ball-by-Ball Deliveries (11,555 Records across 49 Matches)
CREATE TABLE IF NOT EXISTS fact_deliveries (
    delivery_id VARCHAR(64) PRIMARY KEY,
    match_id VARCHAR(32) NOT NULL REFERENCES dim_matches(match_id) ON DELETE CASCADE,
    innings INTEGER NOT NULL,
    batting_team VARCHAR(50) NOT NULL REFERENCES dim_teams(team_name) ON DELETE RESTRICT,
    bowling_team VARCHAR(50) NOT NULL REFERENCES dim_teams(team_name) ON DELETE RESTRICT,
    over_number INTEGER NOT NULL,
    ball_in_over INTEGER NOT NULL,
    actual_delivery_str VARCHAR(10) NOT NULL,
    phase VARCHAR(20) NOT NULL,
    batter VARCHAR(100) NOT NULL,
    batter_id VARCHAR(32) NOT NULL REFERENCES dim_players(player_id) ON DELETE RESTRICT,
    bowler VARCHAR(100) NOT NULL,
    bowler_id VARCHAR(32) NOT NULL REFERENCES dim_players(player_id) ON DELETE RESTRICT,
    non_striker VARCHAR(100) NOT NULL,
    non_striker_id VARCHAR(32) NOT NULL REFERENCES dim_players(player_id) ON DELETE RESTRICT,
    batter_runs INTEGER NOT NULL DEFAULT 0,
    extra_runs INTEGER NOT NULL DEFAULT 0,
    total_runs INTEGER NOT NULL DEFAULT 0,
    is_legal_delivery BOOLEAN NOT NULL DEFAULT TRUE,
    extra_type VARCHAR(50),
    is_boundary_four BOOLEAN NOT NULL DEFAULT FALSE,
    is_boundary_six BOOLEAN NOT NULL DEFAULT FALSE,
    is_dot_ball BOOLEAN NOT NULL DEFAULT FALSE,
    is_wicket BOOLEAN NOT NULL DEFAULT FALSE,
    wicket_kind VARCHAR(50),
    player_dismissed VARCHAR(100),
    fielder_involved VARCHAR(100),
    is_super_over BOOLEAN NOT NULL DEFAULT FALSE
);

-- Indexes on Deliveries for Star-Schema Querying & Power BI Drill-through
CREATE INDEX IF NOT EXISTS idx_deliveries_match ON fact_deliveries(match_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_batter ON fact_deliveries(batter_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_bowler ON fact_deliveries(bowler_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_phase ON fact_deliveries(phase);
CREATE INDEX IF NOT EXISTS idx_deliveries_innings ON fact_deliveries(match_id, innings);

-- 2. Fact Table: Batting Scorecards
CREATE TABLE IF NOT EXISTS fact_batting_scorecards (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(32) NOT NULL REFERENCES dim_matches(match_id) ON DELETE CASCADE,
    innings INTEGER NOT NULL,
    team VARCHAR(50) NOT NULL REFERENCES dim_teams(team_name) ON DELETE RESTRICT,
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(32) NOT NULL REFERENCES dim_players(player_id) ON DELETE RESTRICT,
    batting_position INTEGER NOT NULL,
    runs INTEGER NOT NULL DEFAULT 0,
    balls_faced INTEGER NOT NULL DEFAULT 0,
    fours INTEGER NOT NULL DEFAULT 0,
    sixes INTEGER NOT NULL DEFAULT 0,
    strike_rate NUMERIC(6,2) NOT NULL DEFAULT 0.00,
    is_out BOOLEAN NOT NULL DEFAULT FALSE,
    dismissal_kind VARCHAR(50) NOT NULL,
    bowler VARCHAR(100),
    fielder VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_batting_match_inn ON fact_batting_scorecards(match_id, innings);
CREATE INDEX IF NOT EXISTS idx_batting_player ON fact_batting_scorecards(player_id);

-- 3. Fact Table: Bowling Scorecards
CREATE TABLE IF NOT EXISTS fact_bowling_scorecards (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(32) NOT NULL REFERENCES dim_matches(match_id) ON DELETE CASCADE,
    innings INTEGER NOT NULL,
    team VARCHAR(50) NOT NULL REFERENCES dim_teams(team_name) ON DELETE RESTRICT,
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(32) NOT NULL REFERENCES dim_players(player_id) ON DELETE RESTRICT,
    overs NUMERIC(4,1) NOT NULL DEFAULT 0.0,
    legal_balls INTEGER NOT NULL DEFAULT 0,
    maidens INTEGER NOT NULL DEFAULT 0,
    runs_conceded INTEGER NOT NULL DEFAULT 0,
    wickets INTEGER NOT NULL DEFAULT 0,
    economy_rate NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    dots INTEGER NOT NULL DEFAULT 0,
    wides INTEGER NOT NULL DEFAULT 0,
    no_balls INTEGER NOT NULL DEFAULT 0,
    fours_conceded INTEGER NOT NULL DEFAULT 0,
    sixes_conceded INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_bowling_match_inn ON fact_bowling_scorecards(match_id, innings);
CREATE INDEX IF NOT EXISTS idx_bowling_player ON fact_bowling_scorecards(player_id);

-- 4. Fact Table: Match Summaries (106 Innings)
CREATE TABLE IF NOT EXISTS fact_match_summaries (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(32) NOT NULL REFERENCES dim_matches(match_id) ON DELETE CASCADE,
    innings INTEGER NOT NULL,
    batting_team VARCHAR(50) NOT NULL REFERENCES dim_teams(team_name) ON DELETE RESTRICT,
    bowling_team VARCHAR(50) NOT NULL REFERENCES dim_teams(team_name) ON DELETE RESTRICT,
    total_runs INTEGER NOT NULL,
    total_wickets INTEGER NOT NULL,
    legal_deliveries INTEGER NOT NULL,
    total_overs NUMERIC(4,1) NOT NULL,
    extras_total INTEGER NOT NULL DEFAULT 0,
    extras_wides INTEGER NOT NULL DEFAULT 0,
    extras_noballs INTEGER NOT NULL DEFAULT 0,
    extras_byes INTEGER NOT NULL DEFAULT 0,
    extras_legbyes INTEGER NOT NULL DEFAULT 0,
    extras_penalty INTEGER NOT NULL DEFAULT 0,
    run_rate NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    is_super_over BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_summaries_match ON fact_match_summaries(match_id);

