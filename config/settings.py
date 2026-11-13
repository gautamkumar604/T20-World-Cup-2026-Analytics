"""
Configuration and settings module for the ICC Men's T20 World Cup 2026 Analytics project.
"""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DOCS_DIR = BASE_DIR / "docs"
REPORTS_DIR = BASE_DIR / "reports"

# Data Directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# SQL and Tests
SQL_DIR = BASE_DIR / "sql"
TESTS_DIR = BASE_DIR / "tests"

# Cricsheet Data Sources
# Cricsheet provides bulk archives for Men's T20 Internationals (IT20s) and all T20s
CRICSHEET_T20_MALE_URL = "https://cricsheet.org/downloads/t20s_male_json.zip"
CRICSHEET_T20_ALL_URL = "https://cricsheet.org/downloads/t20s_json.zip"
RAW_ARCHIVE_NAME = "t20s_male_json.zip"

# Tournament Identification Rules
TARGET_TOURNAMENT_NAME = "ICC Men's T20 World Cup"
TARGET_GENDER = "male"
TARGET_YEAR = "2026"

# Ensure essential directories exist
for directory in [
    CONFIG_DIR,
    DOCS_DIR,
    REPORTS_DIR,
    RAW_DATA_DIR,
    INTERIM_DATA_DIR,
    PROCESSED_DATA_DIR,
    SQL_DIR / "schema",
    SQL_DIR / "staging",
    SQL_DIR / "analytics",
    TESTS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

