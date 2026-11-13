# ETL Architecture & Ingestion Runbook

## 1. Overview & Data Pipeline Architecture

The ETL pipeline transforms raw semi-structured JSON match files and official ICC records into a dimensional star-schema relational data warehouse.

```mermaid
flowchart TD
    subgraph Data Sources
        S1["Cricsheet Open Data (49 Match JSONs)"]
        S2["Official ICC Tournament Match Centre (6 Non-Cricsheet Fixtures)"]
    end

    subgraph Data Extraction & Processing (Python)
        P1["MatchParser (Metadata & Dimensions)"]
        P2["DeliveryParser (Ball-by-Ball & Phases)"]
        P3["ScorecardParser (Batting & Bowling Metrics)"]
        VAL["Reconciliation Engine (Runs & Wickets Balancing)"]
    end

    subgraph Processed Storage Layer
        CSV["Processed CSV Datasets (data/processed/)"]
    end

    subgraph Relational Database Warehouse
        TBL["Star Schema Tables (dim_teams, dim_venues, dim_players, dim_matches, facts)"]
        VW["10 Analytical Views (sql/analytics/)"]
    end

    S1 --> P1 & P2 & P3
    S2 --> P1 & P3
    P1 & P2 & P3 --> VAL
    VAL --> CSV
    CSV -->|Transactional Bulk Load| TBL
    TBL --> VW
```

---

## 2. Ingestion Order & Foreign Key Dependency Chain

To enforce referential integrity and prevent constraint violations, tables are loaded in strict topological order:

1. **`dim_teams`**: Master list of all 20 participating nations.
2. **`dim_venues`**: 8 tournament stadiums across India and Sri Lanka.
3. **`dim_players`**: 282 registered tournament players mapped to `dim_teams`.
4. **`dim_matches`**: 55 scheduled fixtures referencing `dim_teams` (team1, team2) and `dim_venues` (venue).
5. **`fact_deliveries`**: 11,555 ball-by-ball events referencing `dim_matches`, `dim_teams`, and `dim_players`.
6. **`fact_batting_scorecards`**: 811 batting records referencing `dim_matches`, `dim_teams`, and `dim_players`.
7. **`fact_bowling_scorecards`**: 598 bowling records referencing `dim_matches`, `dim_teams`, and `dim_players`.
8. **`fact_match_summaries`**: 106 innings records referencing `dim_matches` and `dim_teams`.

---

## 3. Idempotency & Transactional Guarantees

- **Single Atomic Transaction**: Ingestion executes within `engine.begin()`. If any table fails insertion, the entire batch rolls back automatically.
- **Idempotent Deletion**: Prior to ingestion, existing fact and dimension records are deleted in reverse dependency order (`DELETE FROM facts` then `DELETE FROM dimensions`), guaranteeing that repeated executions produce identical row counts with zero duplicate records.
- **Bulk Loading Performance**: Ingestion utilizes chunked batches (`chunksize=1000`) via SQLAlchemy and Pandas, optimized for PostgreSQL bulk load throughput.

---

## 4. Multi-Tier Source Coverage Governance

The database preserves explicit source coverage flags on `dim_matches`:
- `metadata_available` (55/55): Match date, teams, venue, toss, outcome, margin, player of match.
- `scorecard_available` (53/55): Official innings scorecards. Matches 32 and 41 were abandoned due to rain without play, hence `scorecard_available = False`.
- `ball_by_ball_available` (49/55): Granular delivery feeds from Cricsheet. Matches 4, 13, 28, 39 were withheld by Cricsheet policy, hence `ball_by_ball_available = False`.
- **Zero Fabrication Rule**: No artificial deliveries or simulated statistics are inserted for matches where telemetry was unavailable.

---

## 5. Execution Instructions

```bash
# Set environment variables in .env (if using external PostgreSQL)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=t20_worldcup_2026
DB_USER=postgres
DB_PASSWORD=your_password

# Execute the complete database pipeline
python -m src.database.loader

# Run automated tests
python -m unittest discover -s tests -p "test_*.py"
```

