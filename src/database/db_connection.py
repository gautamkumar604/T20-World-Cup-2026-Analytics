"""
Database connection manager with strict dialect enforcement and secure credential handling.

Guarantees:
1. Strict PostgreSQL mode: connection failures raise clear, actionable OperationalErrors.
2. Zero silent fallback to SQLite.
3. Explicit SQLite support only when DB_TYPE=sqlite.
4. Unsupported DB_TYPE values are rejected with ValueError.
5. Separation of URL construction from connection validation.
6. Proper disposal of temporary engines to prevent resource/connection leaks.
7. Complete masking of passwords in logs, URLs, and exception messages.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.exc import OperationalError

from config.settings import BASE_DIR, DATA_DIR
from src.utils.logger import get_logger

logger = get_logger("db_connection")

# Load environment configuration from .env if present, otherwise .env.example
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv(BASE_DIR / ".env.example")

SUPPORTED_DB_TYPES = {"postgres", "postgresql", "sqlite"}


def get_db_config() -> Dict[str, Any]:
    """Retrieves and validates database configuration parameters from environment."""
    raw_type = os.getenv("DB_TYPE", "postgres").strip().lower()
    if raw_type not in SUPPORTED_DB_TYPES:
        raise ValueError(
            f"Unsupported DB_TYPE '{raw_type}'. Supported dialects are: 'postgres' or 'sqlite'."
        )

    return {
        "db_type": raw_type,
        "db_user": os.getenv("DB_USER", "postgres").strip(),
        "db_pass": os.getenv("DB_PASSWORD", "").strip(),
        "db_host": os.getenv("DB_HOST", "localhost").strip(),
        "db_port": os.getenv("DB_PORT", "5432").strip(),
        "db_name": os.getenv("DB_NAME", "t20_worldcup_2026").strip(),
    }


def build_db_url(config: Optional[Dict[str, Any]] = None, mask_password: bool = False) -> str:
    """
    Constructs a database connection URL without initiating any network connection.

    Args:
        config: Optional configuration dictionary. If None, reads from get_db_config().
        mask_password: If True, replaces password with '***' for safe logging.

    Returns:
        Formatted database connection string.
    """
    if config is None:
        config = get_db_config()

    db_type = config["db_type"]

    if db_type == "sqlite":
        sqlite_path = DATA_DIR / f"{config['db_name']}.db"
        return f"sqlite:///{sqlite_path.as_posix()}"

    # PostgreSQL URL construction
    db_user = config["db_user"]
    db_host = config["db_host"]
    db_port = config["db_port"]
    db_name = config["db_name"]

    if mask_password:
        password_repr = "***" if config["db_pass"] else ""
    else:
        # URL-encode password in case of special characters
        password_repr = quote_plus(config["db_pass"]) if config["db_pass"] else ""

    auth_part = f"{db_user}:{password_repr}" if password_repr else db_user
    return f"postgresql+psycopg2://{auth_part}@{db_host}:{db_port}/{db_name}"


def get_masked_db_url(config: Optional[Dict[str, Any]] = None) -> str:
    """Convenience helper returning the sanitized connection string with masked password."""
    return build_db_url(config=config, mask_password=True)


def test_db_connection(engine: Optional[Engine] = None, timeout_seconds: int = 4) -> bool:
    """
    Tests live database connectivity. In PostgreSQL mode, failures raise an explicit,
    actionable OperationalError with masked credentials and zero silent fallback.

    Args:
        engine: Optional existing SQLAlchemy engine. If None, creates a temporary engine.
        timeout_seconds: Connection timeout in seconds.

    Returns:
        True if connection succeeded.

    Raises:
        OperationalError: If connection to PostgreSQL fails.
    """
    config = get_db_config()
    db_type = config["db_type"]
    masked_url = get_masked_db_url(config)

    temp_engine = None
    target_engine = engine

    try:
        if target_engine is None:
            full_url = build_db_url(config, mask_password=False)
            connect_args = {"connect_timeout": timeout_seconds} if db_type != "sqlite" else {}
            temp_engine = create_engine(full_url, connect_args=connect_args)
            target_engine = temp_engine

        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1;"))

        logger.info("Successfully established connection to %s", masked_url)
        return True

    except Exception as e:
        error_msg = (
            f"Failed to connect to database at {masked_url}. "
            f"Host='{config['db_host']}', Port={config['db_port']}, User='{config['db_user']}', "
            f"Database='{config['db_name']}'. Error details: {str(e)}"
        )
        logger.error(error_msg)
        raise OperationalError(error_msg, params=None, orig=e) from e

    finally:
        if temp_engine is not None:
            temp_engine.dispose()


def get_db_engine(custom_url: Optional[str] = None) -> Engine:
    """
    Initializes and returns a production SQLAlchemy engine.
    Strictly follows DB_TYPE without silent fallback.
    """
    if custom_url is not None:
        target_url = custom_url
        is_sqlite = target_url.startswith("sqlite")
    else:
        config = get_db_config()
        target_url = build_db_url(config, mask_password=False)
        is_sqlite = config["db_type"] == "sqlite"

    if is_sqlite:
        engine = create_engine(target_url, echo=False)
        with engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys = ON;"))
        return engine
    else:
        # PostgreSQL Engine with pre-ping validation and connection pool management
        return create_engine(
            target_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=False,
        )


def create_postgres_database_if_not_exists(timeout_seconds: int = 4) -> bool:
    """
    Connects to the default PostgreSQL maintenance database ('postgres')
    and creates the target database if it does not already exist.
    Guarantees proper disposal of the maintenance engine and masked logging.
    """
    config = get_db_config()
    if config["db_type"] == "sqlite":
        return True

    db_name = config["db_name"]
    maintenance_config = config.copy()
    maintenance_config["db_name"] = "postgres"

    maintenance_url = build_db_url(maintenance_config, mask_password=False)
    masked_maint_url = get_masked_db_url(maintenance_config)

    admin_engine = None
    try:
        admin_engine = create_engine(
            maintenance_url,
            isolation_level="AUTOCOMMIT",
            connect_args={"connect_timeout": timeout_seconds},
        )
        with admin_engine.connect() as conn:
            check_sql = text("SELECT 1 FROM pg_database WHERE datname = :dbname")
            exists = conn.execute(check_sql, {"dbname": db_name}).scalar()
            if not exists:
                logger.info("Database '%s' does not exist on %s. Creating...", db_name, masked_maint_url)
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                logger.info("Database '%s' created successfully.", db_name)
            else:
                logger.info("Database '%s' already exists on %s.", db_name, masked_maint_url)
        return True
    except Exception as e:
        logger.warning(
            "Could not verify/create database '%s' via maintenance connection (%s): %s",
            db_name,
            masked_maint_url,
            str(e),
        )
        return False
    finally:
        if admin_engine is not None:
            admin_engine.dispose()


def get_db_connection(engine: Optional[Engine] = None):
    """Context-friendly connection generator."""
    if engine is None:
        engine = get_db_engine()
    return engine.connect()
