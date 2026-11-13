"""
Database connection manager supporting PostgreSQL with SQLite fallback for local testing.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.exc import OperationalError

from config.settings import BASE_DIR, DATA_DIR
from src.utils.logger import get_logger

logger = get_logger("db_connection")

# Load environment variables
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv(BASE_DIR / ".env.example")


def get_db_url(use_sqlite_fallback: bool = True) -> str:
    """
    Constructs the database connection URL from environment variables.
    If PostgreSQL host is unavailable or unreachable and use_sqlite_fallback is True,
    returns a local SQLite warehouse URL.
    """
    db_type = os.getenv("DB_TYPE", "postgres").lower()
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASSWORD", "postgres")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "t20_worldcup_2026")

    pg_url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    if db_type == "sqlite":
        sqlite_path = DATA_DIR / "t20_worldcup_2026.db"
        return f"sqlite:///{sqlite_path.as_posix()}"

    # Test PostgreSQL availability
    try:
        test_engine = create_engine(pg_url, connect_args={"connect_timeout": 3})
        with test_engine.connect():
            logger.info("Successfully connected to PostgreSQL at %s:%s/%s", db_host, db_port, db_name)
            return pg_url
    except Exception as e:
        if use_sqlite_fallback:
            sqlite_path = DATA_DIR / "t20_worldcup_2026.db"
            logger.warning(
                "PostgreSQL connection to %s:%s failed (%s). Falling back to SQLite warehouse at %s.",
                db_host,
                db_port,
                str(e),
                sqlite_path,
            )
            return f"sqlite:///{sqlite_path.as_posix()}"
        else:
            raise OperationalError(
                f"Could not connect to PostgreSQL at {db_host}:{db_port}/{db_name}: {str(e)}",
                params=None,
                orig=e,
            )


def create_postgres_database_if_not_exists() -> bool:
    """Attempts to create the target PostgreSQL database if connected to PostgreSQL server."""
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASSWORD", "postgres")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "t20_worldcup_2026")

    # Connect to the default maintenance database 'postgres'
    admin_url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/postgres"
    try:
        admin_engine = create_engine(
            admin_url,
            isolation_level="AUTOCOMMIT",
            connect_args={"connect_timeout": 3},
        )
        with admin_engine.connect() as conn:
            check_sql = text("SELECT 1 FROM pg_database WHERE datname = :dbname")
            exists = conn.execute(check_sql, {"dbname": db_name}).scalar()
            if not exists:
                logger.info("Database '%s' does not exist. Creating...", db_name)
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                logger.info("Database '%s' created successfully.", db_name)
            else:
                logger.info("Database '%s' already exists.", db_name)
        return True
    except Exception as e:
        logger.warning("Could not create database via maintenance connection: %s", str(e))
        return False


def get_db_engine(db_url: Optional[str] = None) -> Engine:
    """Returns an engine with foreign key pragmas enabled if SQLite."""
    if db_url is None:
        db_url = get_db_url()

    if db_url.startswith("sqlite"):
        engine = create_engine(db_url, echo=False)
        with engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys = ON;"))
        return engine
    else:
        return create_engine(db_url, pool_pre_ping=True, echo=False)


def get_db_connection(engine: Optional[Engine] = None):
    """Context-friendly connection generator."""
    if engine is None:
        engine = get_db_engine()
    return engine.connect()
