-- ==============================================================================
-- ICC Men's T20 World Cup 2026 - PostgreSQL Relational Data Warehouse Schema
-- 01_create_dimensions.sql: Dimension Tables DDL
-- ==============================================================================

-- 1. Dimension: Teams (All 20 Participating Nations)
CREATE TABLE IF NOT EXISTS dim_teams (
    team_id VARCHAR(10) PRIMARY KEY,
    team_name VARCHAR(50) NOT NULL UNIQUE,
    icc_status VARCHAR(30) NOT NULL,
    group_2026 VARCHAR(20) NOT NULL,
    is_host BOOLEAN NOT NULL DEFAULT FALSE
);

-- 2. Dimension: Venues (8 Host Stadiums)
CREATE TABLE IF NOT EXISTS dim_venues (
    venue_name VARCHAR(100) PRIMARY KEY,
    city VARCHAR(50),
    country VARCHAR(50) NOT NULL
);

-- 3. Dimension: Players (Master Registry across 20 Teams)
CREATE TABLE IF NOT EXISTS dim_players (
    player_id VARCHAR(32) PRIMARY KEY,
    player_name VARCHAR(100) NOT NULL,
    team VARCHAR(50) NOT NULL REFERENCES dim_teams(team_name) ON DELETE RESTRICT
);

-- 4. Dimension: Matches (All 55 Scheduled Fixtures with Provenance Flags)
CREATE TABLE IF NOT EXISTS dim_matches (
    match_id VARCHAR(32) PRIMARY KEY,
    match_date DATE NOT NULL,
    tournament_name VARCHAR(100) NOT NULL DEFAULT 'ICC Men''s T20 World Cup',
    match_number INTEGER,
    stage VARCHAR(50),
    group_name VARCHAR(20),
    team1 VARCHAR(50) NOT NULL REFERENCES dim_teams(team_name) ON DELETE RESTRICT,
    team2 VARCHAR(50) NOT NULL REFERENCES dim_teams(team_name) ON DELETE RESTRICT,
    toss_winner VARCHAR(50),
    toss_decision VARCHAR(10),
    venue VARCHAR(100) NOT NULL REFERENCES dim_venues(venue_name) ON DELETE RESTRICT,
    city VARCHAR(50),
    winner VARCHAR(50) NOT NULL,
    outcome_type VARCHAR(30) NOT NULL,
    win_margin INTEGER NOT NULL DEFAULT 0,
    player_of_match VARCHAR(100),
    target_runs INTEGER,
    target_overs NUMERIC(4,1),
    is_dls_applied BOOLEAN NOT NULL DEFAULT FALSE,
    umpire1 VARCHAR(100),
    umpire2 VARCHAR(100),
    tv_umpire VARCHAR(100),
    match_referee VARCHAR(100),
    metadata_available BOOLEAN NOT NULL DEFAULT TRUE,
    scorecard_available BOOLEAN NOT NULL DEFAULT FALSE,
    ball_by_ball_available BOOLEAN NOT NULL DEFAULT FALSE,
    source_note VARCHAR(255) NOT NULL
);

-- Create Indexes for Query Optimization & Joins
CREATE INDEX IF NOT EXISTS idx_dim_matches_date ON dim_matches(match_date);
CREATE INDEX IF NOT EXISTS idx_dim_matches_stage ON dim_matches(stage);
CREATE INDEX IF NOT EXISTS idx_dim_matches_teams ON dim_matches(team1, team2);
CREATE INDEX IF NOT EXISTS idx_dim_players_team ON dim_players(team);

