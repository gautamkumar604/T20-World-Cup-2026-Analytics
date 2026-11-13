"""
Production ETL database loader for ICC Men's T20 World Cup 2026.

Supports transactional, idempotent loading of dimensional models and fact tables
with automated constraint validation, referential integrity verification,
and deployment of analytical SQL views.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy import Engine, text

from config.settings import PROCESSED_DATA_DIR, SQL_DIR, REPORTS_DIR, DOCS_DIR
from src.utils.logger import get_logger
from src.database.db_connection import get_db_engine, create_postgres_database_if_not_exists

logger = get_logger("database_loader")


class DatabaseLoader:
    """Manages DDL execution, data ingestion, referential integrity, and view deployments."""

    INGESTION_ORDER = [
        "dim_teams",
        "dim_venues",
        "dim_players",
        "dim_matches",
        "fact_deliveries",
        "fact_batting_scorecards",
        "fact_bowling_scorecards",
        "fact_match_summaries",
    ]

    CSV_TO_TABLE_MAP = {
        "dim_teams": "dim_teams",
        "dim_venues": "dim_venues",
        "dim_players": "dim_players",
        "matches": "dim_matches",
        "deliveries": "fact_deliveries",
        "batting_scorecards": "fact_batting_scorecards",
        "bowling_scorecards": "fact_bowling_scorecards",
        "match_summaries": "fact_match_summaries",
    }

    def __init__(self, engine: Engine = None):
        if engine is None:
            # Attempt to create Postgres DB first if available
            create_postgres_database_if_not_exists()
            self.engine = get_db_engine()
        else:
            self.engine = engine

        self.reports_dir = REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.is_sqlite = str(self.engine.url).startswith("sqlite")
        logger.info("DatabaseLoader initialized using engine: %s (is_sqlite=%s)", self.engine.url, self.is_sqlite)

    def deploy_schema(self) -> None:
        """Executes DDL statements to create dimension and fact tables."""
        logger.info("Deploying relational database schema...")
        dim_sql_file = SQL_DIR / "schema" / "01_create_dimensions.sql"
        fact_sql_file = SQL_DIR / "schema" / "02_create_facts.sql"

        ddl_scripts = [dim_sql_file, fact_sql_file]

        with self.engine.begin() as conn:
            if self.is_sqlite:
                conn.execute(text("PRAGMA foreign_keys = OFF;"))

            for script_path in ddl_scripts:
                if not script_path.exists():
                    raise FileNotFoundError(f"Schema script missing: {script_path}")
                content = script_path.read_text(encoding="utf-8")
                
                # Split commands safely for SQLite/Postgres compatibility
                statements = [s.strip() for s in content.split(";") if s.strip()]
                for stmt in statements:
                    # In SQLite, replace SERIAL with INTEGER and adjust type syntax if needed
                    clean_stmt = stmt
                    if self.is_sqlite:
                        clean_stmt = clean_stmt.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                    try:
                        conn.execute(text(clean_stmt))
                    except Exception as e:
                        logger.error("Error executing DDL statement: %s\nError: %s", clean_stmt[:80], str(e))
                        raise

            if self.is_sqlite:
                conn.execute(text("PRAGMA foreign_keys = ON;"))

        logger.info("Schema tables and indexes created successfully.")

    def load_data(self) -> Dict[str, Any]:
        """Loads all processed CSV files into corresponding relational tables idempotently."""
        logger.info("Beginning transactional data ingestion...")
        ingestion_audit = {
            "database_url": str(self.engine.url),
            "tables_loaded": {},
            "record_counts_csv_vs_db": {},
            "status": "IN_PROGRESS",
        }

        # Read CSV dataframes
        dfs = {}
        for csv_name, table_name in self.CSV_TO_TABLE_MAP.items():
            csv_path = PROCESSED_DATA_DIR / f"{csv_name}.csv"
            if not csv_path.exists():
                raise FileNotFoundError(f"Required processed CSV missing: {csv_path}")
            df = pd.read_csv(csv_path)
            dfs[table_name] = df

        # Transactional loading: delete from facts then dimensions, then insert in order
        with self.engine.begin() as conn:
            if self.is_sqlite:
                conn.execute(text("PRAGMA foreign_keys = OFF;"))

            # Idempotent cleanup: truncate/delete in reverse order
            for table in reversed(self.INGESTION_ORDER):
                conn.execute(text(f"DELETE FROM {table};"))

            # Ingest in forward foreign-key order
            for table in self.INGESTION_ORDER:
                df = dfs[table]
                row_count = len(df)
                logger.info("Ingesting %d rows into %s...", row_count, table)
                
                # Use pandas to_sql with append mode
                df.to_sql(table, conn, if_exists="append", index=False, chunksize=1000)
                ingestion_audit["tables_loaded"][table] = row_count

            if self.is_sqlite:
                conn.execute(text("PRAGMA foreign_keys = ON;"))

        # Verify record counts in DB
        logger.info("Verifying database record counts...")
        with self.engine.connect() as conn:
            for table in self.INGESTION_ORDER:
                csv_count = len(dfs[table])
                db_count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                ingestion_audit["record_counts_csv_vs_db"][table] = {
                    "csv_records": csv_count,
                    "db_records": db_count,
                    "matches": csv_count == db_count,
                }
                assert csv_count == db_count, f"Count mismatch in {table}: CSV={csv_count}, DB={db_count}"

        ingestion_audit["status"] = "SUCCESS"
        logger.info("All tables loaded successfully with 100% record parity.")
        return ingestion_audit

    def deploy_views(self) -> List[str]:
        """Deploys all analytical SQL views from sql/analytics/."""
        logger.info("Deploying analytical SQL views...")
        analytics_dir = SQL_DIR / "analytics"
        view_files = sorted(list(analytics_dir.glob("*.sql")))
        deployed = []

        with self.engine.begin() as conn:
            for vf in view_files:
                sql_content = vf.read_text(encoding="utf-8")
                # SQLite view compatibility adjustments
                if self.is_sqlite:
                    sql_content = sql_content.replace("CREATE OR REPLACE VIEW", "CREATE VIEW IF NOT EXISTS")
                    sql_content = sql_content.replace("::NUMERIC", "")
                    sql_content = sql_content.replace("::FLOAT", "")
                    # In SQLite, drop if exists first to allow re-creation
                    view_name = vf.stem
                    conn.execute(text(f"DROP VIEW IF EXISTS {view_name};"))

                conn.execute(text(sql_content))
                deployed.append(vf.stem)
                logger.info("Deployed view: %s", vf.stem)

        logger.info("Successfully deployed %d analytical views.", len(deployed))
        return deployed

    def verify_referential_integrity(self) -> Dict[str, Any]:
        """Runs referential integrity audits to ensure foreign keys resolve properly."""
        logger.info("Running referential integrity tests...")
        checks = {}

        with self.engine.connect() as conn:
            # 1. Matches -> Teams
            m_teams_orphan = conn.execute(text("""
                SELECT COUNT(*) FROM dim_matches m
                WHERE m.team1 NOT IN (SELECT team_name FROM dim_teams)
                   OR m.team2 NOT IN (SELECT team_name FROM dim_teams)
            """)).scalar()
            checks["matches_to_teams_orphans"] = m_teams_orphan

            # 2. Matches -> Venues
            m_venues_orphan = conn.execute(text("""
                SELECT COUNT(*) FROM dim_matches m
                WHERE m.venue NOT IN (SELECT venue_name FROM dim_venues)
            """)).scalar()
            checks["matches_to_venues_orphans"] = m_venues_orphan

            # 3. Deliveries -> Matches
            d_matches_orphan = conn.execute(text("""
                SELECT COUNT(*) FROM fact_deliveries d
                WHERE d.match_id NOT IN (SELECT match_id FROM dim_matches)
            """)).scalar()
            checks["deliveries_to_matches_orphans"] = d_matches_orphan

            # 4. Scorecards -> Matches
            bat_matches_orphan = conn.execute(text("""
                SELECT COUNT(*) FROM fact_batting_scorecards b
                WHERE b.match_id NOT IN (SELECT match_id FROM dim_matches)
            """)).scalar()
            checks["batting_to_matches_orphans"] = bat_matches_orphan

            bowl_matches_orphan = conn.execute(text("""
                SELECT COUNT(*) FROM fact_bowling_scorecards bw
                WHERE bw.match_id NOT IN (SELECT match_id FROM dim_matches)
            """)).scalar()
            checks["bowling_to_matches_orphans"] = bowl_matches_orphan

            # 5. Summaries -> Matches
            sum_matches_orphan = conn.execute(text("""
                SELECT COUNT(*) FROM fact_match_summaries s
                WHERE s.match_id NOT IN (SELECT match_id FROM dim_matches)
            """)).scalar()
            checks["summaries_to_matches_orphans"] = sum_matches_orphan

        checks["all_referential_checks_passed"] = all(v == 0 for v in checks.values())
        logger.info("Referential integrity verification: %s", checks)
        return checks

    def run_pipeline(self) -> Dict[str, Any]:
        """Runs the complete database pipeline: DDL -> Ingestion -> Views -> Verification."""
        self.deploy_schema()
        ingestion_results = self.load_data()
        views = self.deploy_views()
        ref_integrity = self.verify_referential_integrity()

        report = {
            "ingestion": ingestion_results,
            "views_deployed": views,
            "referential_integrity": ref_integrity,
        }

        # Save JSON Report
        report_path = self.reports_dir / "database_ingestion_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info("Saved database ingestion report to %s", report_path)

        # Generate Markdown Report
        self._write_markdown_report(report)

        return report

    def _write_markdown_report(self, report: Dict[str, Any]) -> None:
        """Writes the formal database validation report in reports/database_validation_report.md."""
        md_path = self.reports_dir / "database_validation_report.md"
        rec_data = report["ingestion"]["record_counts_csv_vs_db"]
        ref_data = report["referential_integrity"]

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# PostgreSQL Relational Data Warehouse — Ingestion & Validation Report\n\n")
            f.write(f"**Database URL**: `{report['ingestion']['database_url']}`  \n")
            f.write(f"**Status**: `{report['ingestion']['status']}`  \n\n")
            f.write("---\n\n")

            f.write("## 1. Table Inventory & Record Parity Verification\n\n")
            f.write("| Table Name | Type | CSV Records | Database Records | Record Parity |\n")
            f.write("| :--- | :---: | :---: | :---: | :---: |\n")

            total_records = 0
            for table, stats in rec_data.items():
                t_type = "Dimension" if table.startswith("dim_") else "Fact"
                parity = "✅ 100% Match" if stats["matches"] else "❌ Mismatch"
                total_records += stats["db_records"]
                f.write(f"| `{table}` | {t_type} | {stats['csv_records']:,} | {stats['db_records']:,} | {parity} |\n")

            f.write(f"\n**Total Warehouse Records Loaded**: **{total_records:,}**\n\n")
            f.write("---\n\n")

            f.write("## 2. Referential Integrity & Foreign Key Audit\n\n")
            f.write("| Foreign Key Relationship | Orphan Records | Audit Result |\n")
            f.write("| :--- | :---: | :---: |\n")
            f.write(f"| `dim_matches(team1, team2)` -> `dim_teams(team_name)` | {ref_data['matches_to_teams_orphans']} | {'✅ Valid' if ref_data['matches_to_teams_orphans'] == 0 else '❌ Invalid'} |\n")
            f.write(f"| `dim_matches(venue)` -> `dim_venues(venue_name)` | {ref_data['matches_to_venues_orphans']} | {'✅ Valid' if ref_data['matches_to_venues_orphans'] == 0 else '❌ Invalid'} |\n")
            f.write(f"| `fact_deliveries(match_id)` -> `dim_matches(match_id)` | {ref_data['deliveries_to_matches_orphans']} | {'✅ Valid' if ref_data['deliveries_to_matches_orphans'] == 0 else '❌ Invalid'} |\n")
            f.write(f"| `fact_batting_scorecards(match_id)` -> `dim_matches(match_id)` | {ref_data['batting_to_matches_orphans']} | {'✅ Valid' if ref_data['batting_to_matches_orphans'] == 0 else '❌ Invalid'} |\n")
            f.write(f"| `fact_bowling_scorecards(match_id)` -> `dim_matches(match_id)` | {ref_data['bowling_to_matches_orphans']} | {'✅ Valid' if ref_data['bowling_to_matches_orphans'] == 0 else '❌ Invalid'} |\n")
            f.write(f"| `fact_match_summaries(match_id)` -> `dim_matches(match_id)` | {ref_data['summaries_to_matches_orphans']} | {'✅ Valid' if ref_data['summaries_to_matches_orphans'] == 0 else '❌ Invalid'} |\n")
            f.write("\n---\n\n")

            f.write("## 3. Analytical Views Deployed (10 Views)\n\n")
            for v in report["views_deployed"]:
                f.write(f"- ✅ `{v}`\n")
            f.write("\n")

        logger.info("Saved validation report markdown to %s", md_path)


if __name__ == "__main__":
    loader = DatabaseLoader()
    results = loader.run_pipeline()
    print("Database loader executed successfully:")
    for t, s in results["ingestion"]["record_counts_csv_vs_db"].items():
        print(f"  {t}: {s['db_records']} rows")
