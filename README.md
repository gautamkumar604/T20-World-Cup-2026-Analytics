# ICC Men's T20 World Cup 2026 Data Analytics

A production-grade, end-to-end data engineering and analytics solution analyzing the complete **ICC Men's T20 World Cup 2026** tournament using ball-by-ball delivery telemetry and match scorecards.

---

## 📌 Project Objectives

1. **End-to-End Analytics Pipeline**: Collect, sanitize, validate, and store all ball-by-ball deliveries and official scorecards from the 2026 ICC Men's T20 World Cup.
2. **Relational Modeling & Warehousing**: Design and populate a dimensional PostgreSQL star schema (`Dim_Match`, `Dim_Player`, `Dim_Venue`, `Fact_Deliveries`, `Fact_Scorecards`).
3. **Reproducibility & Integrity**: Guarantee 100% data fidelity with strict source attribution, zero data fabrication, mathematical reconciliation between ball-by-ball runs and official scorecards, and cryptographic checksum validation.
4. **Business Intelligence**: Provide robust SQL analytical marts serving as the semantic layer for Power BI executive dashboards and granular performance reports.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Language & Runtimes** | Python 3.10+ |
| **Data Manipulation** | Pandas, NumPy |
| **Relational Database** | PostgreSQL, SQLAlchemy, psycopg2 |
| **Validation & Schemas** | Pydantic, Python Standard Library |
| **Testing & CI** | Pytest |
| **Business Intelligence** | Power BI, SQL Analytical Marts |

---

## 📂 Project Structure

```text
T20-World-Cup-2026-Analytics/
├── .env.example                  # Environment configuration template
├── .gitignore                    # Version control ignore rules
├── README.md                     # Project overview and runbook
├── requirements.txt              # Production Python dependencies
├── config/
│   └── settings.py               # Path configurations, settings, constants
├── docs/
│   ├── data_sources.md           # Dataset sources, licensing, and schema definitions
│   ├── metadata_report.md        # Audit of matches, teams, venues, and completeness
│   └── data_dictionary.md        # Entity attributes, types, and primary/foreign keys
├── data/
│   ├── raw/                      # Read-only untouched archives and SHA-256 checksums
│   ├── interim/                  # Filtered 2026 World Cup match JSON files
│   └── processed/                # Clean tabular normalized datasets (Parquet / CSV)
├── sql/
│   ├── schema/                   # PostgreSQL DDL tables & constraints
│   ├── staging/                  # Staging tables & bulk ingestion queries
│   └── analytics/                # SQL analytical views & marts for Power BI
├── src/
│   ├── __init__.py
│   ├── collectors/               # Data collection & tournament isolation
│   │   ├── __init__.py
│   │   ├── cricsheet_downloader.py
│   │   └── tournament_filter.py
│   ├── processors/               # JSON parsers & feature extractors
│   │   ├── __init__.py
│   │   ├── match_parser.py
│   │   ├── delivery_parser.py
│   │   └── scorecard_parser.py
│   ├── database/                 # PostgreSQL ETL & connection managers
│   │   ├── __init__.py
│   │   ├── db_connection.py
│   │   └── loader.py
│   └── utils/                    # Shared utilities
│       ├── __init__.py
│       ├── logger.py
│       └── validator.py
├── tests/
│   ├── __init__.py
│   ├── test_data_integrity.py
│   └── test_parsers.py
└── reports/                      # Execution logs and audit summaries
```

---

## 🔒 Data Integrity & Governance Principles

- **No Data Fabrication**: Cricket records are never fabricated or estimated. If a match was abandoned without a ball bowled, it is recorded accurately as abandoned.
- **Strict Tournament Isolation**: Only matches belonging to the `ICC Men's T20 World Cup` in the 2026 edition are processed. Other tournaments, bilateral series, and domestic leagues (IPL, BBL, PSL) are strictly isolated and excluded.
- **Cryptographic Preservation**: Downloaded raw archives are verified using SHA-256 hashes and stored read-only in `data/raw/`.
- **Ball-to-Scorecard Reconciliation**: Ball-by-ball delivery sums are verified mathematically against official team scorecard totals.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10 or higher
- PostgreSQL 14+ (for Phase 2 database warehousing)

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/your-username/T20-World-Cup-2026-Analytics.git
cd T20-World-Cup-2026-Analytics

# Setup virtual environment
python -m venv venv
venv\Scripts\activate   # On Windows
source venv/bin/activate # On Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### 3. Running Data Collection & Isolation (Phase 1)
```bash
# Download raw Cricsheet data and compute checksums
python -m src.collectors.cricsheet_downloader

# Isolate 2026 T20 World Cup matches and generate metadata report
python -m src.collectors.tournament_filter
```

---

## 📊 Roadmap

- [x] **Phase 1: Project Initialization & Data Collection**
  - Modular project structure
  - Raw dataset download & SHA-256 verification
  - 2026 Men's T20 World Cup isolation & metadata audit
- [x] **Phase 2: Data Extraction, Normalization & Cleansing**
  - Delivery-level, match-level, and scorecard tabular parsing
  - 100% mathematical reconciliation between deliveries, scorecards, and match totals
  - Normalized tabular datasets generated in `data/processed/`
  - Comprehensive Data Dictionary (`docs/data_dictionary.md`)
- [ ] **Phase 3: Relational Data Warehousing (PostgreSQL)**
  - Star schema DDL deployment (`Dim_Match`, `Dim_Player`, `Dim_Venue`, `Fact_Deliveries`, `Fact_Scorecards`)
  - Automated PostgreSQL ingestion pipeline and staging tables
  - SQL Analytical Marts & views for BI reporting
- [ ] **Phase 4: Power BI Semantic Modeling & Dashboards**
  - Star-schema relationships and DAX KPIs
  - Tournament executive dashboard & phase-by-phase tactical analysis

---

## 📜 License & Attribution
Data sourced from [Cricsheet](https://cricsheet.org/) under the Open Data Commons Open Database License (ODbL) / Creative Commons Attribution-ShareAlike (CC BY-SA 4.0).

