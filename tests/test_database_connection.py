"""
Unit tests for database connection manager, strict dialect enforcement, and credential security.
"""

import os
import unittest
from unittest.mock import patch
from sqlalchemy.exc import OperationalError

from src.database.db_connection import (
    get_db_config,
    build_db_url,
    get_masked_db_url,
    test_db_connection,
    get_db_engine,
)


class TestDatabaseConnection(unittest.TestCase):
    """Test suite verifying strict PostgreSQL mode, explicit SQLite mode, and security."""

    def setUp(self):
        """Preserves original environment variables before each test."""
        self.original_env = os.environ.copy()

    def tearDown(self):
        """Restores original environment variables after each test."""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_unsupported_db_type_raises_value_error(self):
        """Verifies that invalid DB_TYPE values are rejected with ValueError."""
        invalid_types = ["oracle", "mysql", "mongodb", "invalid_dialect", ""]
        for bad_type in invalid_types:
            with self.subTest(bad_type=bad_type):
                os.environ["DB_TYPE"] = bad_type
                with self.assertRaises(ValueError) as ctx:
                    get_db_config()
                self.assertIn("Unsupported DB_TYPE", str(ctx.exception))

    def test_url_construction_without_connecting(self):
        """Verifies that build_db_url constructs strings purely in memory without network calls."""
        config = {
            "db_type": "postgres",
            "db_user": "test_user",
            "db_pass": "SecretPass123",
            "db_host": "db.production.local",
            "db_port": "5432",
            "db_name": "t20_warehouse",
        }
        raw_url = build_db_url(config, mask_password=False)
        self.assertEqual(
            raw_url,
            "postgresql+psycopg2://test_user:SecretPass123@db.production.local:5432/t20_warehouse",
        )

        masked_url = build_db_url(config, mask_password=True)
        self.assertEqual(
            masked_url,
            "postgresql+psycopg2://test_user:***@db.production.local:5432/t20_warehouse",
        )
        self.assertNotIn("SecretPass123", masked_url)

    def test_explicit_sqlite_mode(self):
        """Verifies that SQLite is used only when DB_TYPE=sqlite is explicitly set."""
        os.environ["DB_TYPE"] = "sqlite"
        os.environ["DB_NAME"] = "test_warehouse"

        config = get_db_config()
        self.assertEqual(config["db_type"], "sqlite")

        url = build_db_url(config)
        self.assertTrue(url.startswith("sqlite:///"))
        self.assertIn("test_warehouse.db", url)

        # In SQLite mode, test_db_connection connects without network calls
        self.assertTrue(test_db_connection(timeout_seconds=2))

    def test_strict_postgres_mode_fails_clearly_without_fallback(self):
        """Verifies that PostgreSQL connection failures raise an explicit OperationalError."""
        os.environ["DB_TYPE"] = "postgres"
        os.environ["DB_HOST"] = "192.0.2.1"  # Non-routable TEST-NET-1 IP to force timeout
        os.environ["DB_PORT"] = "5432"
        os.environ["DB_USER"] = "postgres"
        os.environ["DB_PASSWORD"] = "any_pass"
        os.environ["DB_NAME"] = "t20_worldcup_2026"

        with self.assertRaises(OperationalError) as ctx:
            test_db_connection(timeout_seconds=1)

        err_text = str(ctx.exception)
        # Verify clear diagnostic content
        self.assertIn("Failed to connect to database", err_text)
        self.assertIn("Host='192.0.2.1'", err_text)
        self.assertIn("Port=5432", err_text)
        self.assertIn("User='postgres'", err_text)
        # Verify it did NOT return or fallback to SQLite
        self.assertNotIn("sqlite", err_text.lower())

    def test_passwords_never_exposed_in_errors_or_masked_urls(self):
        """Verifies that plain-text passwords never leak into logs, URLs, or error strings."""
        sensitive_pass = "P@ssw0rd_Super_Secret_#999!"
        os.environ["DB_TYPE"] = "postgres"
        os.environ["DB_HOST"] = "127.0.0.1"
        os.environ["DB_PORT"] = "59999"  # Closed port
        os.environ["DB_USER"] = "postgres"
        os.environ["DB_PASSWORD"] = sensitive_pass
        os.environ["DB_NAME"] = "t20_worldcup_2026"

        masked = get_masked_db_url()
        self.assertNotIn(sensitive_pass, masked)
        self.assertIn("***", masked)

        with self.assertRaises(OperationalError) as ctx:
            test_db_connection(timeout_seconds=1)

        err_text = str(ctx.exception)
        self.assertNotIn(sensitive_pass, err_text)
        self.assertIn("***", err_text)


if __name__ == "__main__":
    unittest.main()

