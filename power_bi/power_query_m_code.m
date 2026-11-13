// ==============================================================================
// ICC Men's T20 World Cup 2026 — Power Query M Extraction Scripts (PostgreSQL)
// Server: localhost | Port: 5432 | Database: t20_worldcup_2026 | Mode: Import
// ==============================================================================

// Table: dim_teams
let
    Source = PostgreSQL.Database("localhost", "t20_worldcup_2026"),
    public_dim_teams = Source{[Schema="public",Item="dim_teams"]}[Data]
in
    public_dim_teams

// Table: dim_venues
let
    Source = PostgreSQL.Database("localhost", "t20_worldcup_2026"),
    public_dim_venues = Source{[Schema="public",Item="dim_venues"]}[Data]
in
    public_dim_venues

// Table: dim_players
let
    Source = PostgreSQL.Database("localhost", "t20_worldcup_2026"),
    public_dim_players = Source{[Schema="public",Item="dim_players"]}[Data]
in
    public_dim_players

// Table: dim_matches
let
    Source = PostgreSQL.Database("localhost", "t20_worldcup_2026"),
    public_dim_matches = Source{[Schema="public",Item="dim_matches"]}[Data]
in
    public_dim_matches

// Table: fact_match_summaries
let
    Source = PostgreSQL.Database("localhost", "t20_worldcup_2026"),
    public_fact_match_summaries = Source{[Schema="public",Item="fact_match_summaries"]}[Data]
in
    public_fact_match_summaries

// Table: fact_batting_scorecards
let
    Source = PostgreSQL.Database("localhost", "t20_worldcup_2026"),
    public_fact_batting_scorecards = Source{[Schema="public",Item="fact_batting_scorecards"]}[Data]
in
    public_fact_batting_scorecards

// Table: fact_bowling_scorecards
let
    Source = PostgreSQL.Database("localhost", "t20_worldcup_2026"),
    public_fact_bowling_scorecards = Source{[Schema="public",Item="fact_bowling_scorecards"]}[Data]
in
    public_fact_bowling_scorecards

// Table: fact_deliveries
let
    Source = PostgreSQL.Database("localhost", "t20_worldcup_2026"),
    public_fact_deliveries = Source{[Schema="public",Item="fact_deliveries"]}[Data]
in
    public_fact_deliveries

