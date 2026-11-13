"""
Automated database validation, referential integrity, and view testing suite.

Executes non-destructive read-only audits against the database and tests
loading idempotency in an isolated temporary test database to guarantee
zero modification or deletion of production warehouse files.
"""

import unittest
import tempfile
from pathlib import Path
from sqlalchemy import text, create_engine

from config.settings import DATA_DIR
from src.database.db_connection import get_db_engine
from src.database.loader import DatabaseLoader


class TestDatabaseIntegrity(unittest.TestCase):
    """Test suite verifying existing warehouse record parity, foreign keys, and SQL views."""

    @classmethod
    def setUpClass(cls):
        """Connects strictly read-only to the existing SQLite warehouse."""
        sqlite_file = DATA_DIR / "t20_worldcup_2026.db"
        if not sqlite_file.exists():
            raise unittest.SkipTest(f"Warehouse database missing at {sqlite_file}")
        
        cls.engine = get_db_engine(f"sqlite:///{sqlite_file.as_posix()}")
        cls.loader = DatabaseLoader(engine=cls.engine)

    def test_record_counts_parity(self):
        """Verifies that database counts match CSV counts exactly across all tables."""
        expected_counts = {
            "dim_teams": 20,
            "dim_venues": 8,
            "dim_players": 282,
            "dim_matches": 55,
            "fact_deliveries": 11555,
            "fact_batting_scorecards": 811,
            "fact_bowling_scorecards": 598,
            "fact_match_summaries": 106,
        }
        with self.engine.connect() as conn:
            for table, expected in expected_counts.items():
                db_count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                self.assertEqual(
                    db_count,
                    expected,
                    f"Count mismatch in {table}: expected {expected}, got {db_count}",
                )

    def test_referential_integrity(self):
        """Verifies that all foreign key relationships have zero orphan records."""
        checks = self.loader.verify_referential_integrity()
        self.assertTrue(checks["all_referential_checks_passed"])
        for check_name, count in checks.items():
            if check_name != "all_referential_checks_passed":
                self.assertEqual(count, 0, f"Orphan records found for {check_name}: {count}")

    def test_idempotent_reloading_in_temp_database(self):
        """
        Verifies idempotency in an isolated temporary database.
        Guarantees existing production data/t20_worldcup_2026.db is NOT modified.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_db = Path(tmp_dir) / "temp_warehouse.db"
            temp_url = f"sqlite:///{temp_db.as_posix()}"
            temp_engine = create_engine(temp_url)
            temp_loader = DatabaseLoader(engine=temp_engine)

            # First load
            temp_loader.deploy_schema()
            temp_loader.load_data()

            initial_counts = {}
            with temp_engine.connect() as conn:
                for table in temp_loader.INGESTION_ORDER:
                    initial_counts[table] = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

            # Second load (idempotency check)
            temp_loader.load_data()

            with temp_engine.connect() as conn:
                for table in temp_loader.INGESTION_ORDER:
                    post_count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    self.assertEqual(
                        post_count,
                        initial_counts[table],
                        f"Duplicate records introduced in {table} after reloading!",
                    )
            temp_engine.dispose()

    def test_analytical_views_execution(self):
        """Verifies that all 10 analytical SQL views can be queried without errors."""
        views_to_test = [
            "vw_top_run_scorers",
            "vw_top_wicket_takers",
            "vw_team_performance",
            "vw_batting_statistics",
            "vw_bowling_statistics",
            "vw_phase_wise_performance",
            "vw_venue_analysis",
            "vw_toss_impact",
            "vw_boundary_analysis",
            "vw_match_results",
        ]
        with self.engine.connect() as conn:
            for view_name in views_to_test:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {view_name}")).scalar()
                self.assertGreater(
                    result,
                    0,
                    f"View {view_name} returned zero rows!",
                )

    def test_source_coverage_flags(self):
        """Verifies that source coverage flags accurately reflect tournament availability."""
        with self.engine.connect() as conn:
            total_matches = conn.execute(text("SELECT COUNT(*) FROM dim_matches")).scalar()
            metadata_matches = conn.execute(
                text("SELECT COUNT(*) FROM dim_matches WHERE metadata_available = 1 OR metadata_available = TRUE")
            ).scalar()
            scorecard_matches = conn.execute(
                text("SELECT COUNT(*) FROM dim_matches WHERE scorecard_available = 1 OR scorecard_available = TRUE")
            ).scalar()
            bbb_matches = conn.execute(
                text("SELECT COUNT(*) FROM dim_matches WHERE ball_by_ball_available = 1 OR ball_by_ball_available = TRUE")
            ).scalar()

            self.assertEqual(total_matches, 55)
            self.assertEqual(metadata_matches, 55)
            self.assertEqual(scorecard_matches, 53)
            self.assertEqual(bbb_matches, 49)


if __name__ == "__main__":
    unittest.main()
