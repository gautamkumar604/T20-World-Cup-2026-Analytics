# Data Source Documentation: ICC Men's T20 World Cup 2026

## 1. Overview
This document outlines the official data sources, schema contracts, attribution requirements, and extraction mechanics utilized for the **ICC Men's T20 World Cup 2026 Data Analytics** platform.

---

## 2. Primary Source: Cricsheet

* **Provider**: [Cricsheet](https://cricsheet.org/)
* **Format**: Structured JSON (Schema Version 1.3.0+)
* **Licensing**: [Open Data Commons Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/) / [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/)
* **Attribution Requirement**: *"Data provided by Cricsheet (cricsheet.org), licensed under CC BY-SA 4.0 / ODbL."*
* **Download Endpoint**: `https://cricsheet.org/downloads/t20s_male_json.zip` or `https://cricsheet.org/downloads/t20s_json.zip`

### Cricsheet JSON File Schema (v1.3.0)

Each match is represented as a single standalone JSON file named by its unique match ID (e.g., `1411123.json`). The schema contains two primary top-level keys:

```
{
  "meta": {
    "data_version": "1.3.0",
    "created": "2026-03-09",
    "revision": 1
  },
  "info": { ... },
  "innings": [ ... ]
}
```

#### A. `info` Object (Match Metadata)
Contains complete situational, environmental, and outcome metadata:
- `balls_per_over`: Standard `6` for T20.
- `dates`: Array of match dates in ISO format (`["YYYY-MM-DD"]`).
- `event`:
  - `name`: Tournament designation (e.g., `"ICC Men's T20 World Cup"`).
  - `match_number`: Sequential match number in the tournament.
  - `stage`: Tournament phase (e.g., `"Group"`, `"Super 8"`, `"Semi Final"`, `"Final"`).
  - `group`: Group assignment (e.g., `"Group A"`).
- `gender`: `"male"` for the Men's World Cup.
- `match_type`: `"T20"`.
- `teams`: Array containing `[Team 1, Team 2]`.
- `toss`:
  - `winner`: Team name winning the toss.
  - `decision`: `"bat"` or `"field"`.
- `venue`: Stadium name and city.
- `city`: City where the venue is located.
- `outcome`:
  - `winner`: Winning team.
  - `by`: Margin of victory (`{"runs": 24}` or `{"wickets": 7}`).
  - `result`: `"tie"`, `"no result"` (if abandoned).
  - `method`: `"D/L"` (if Duckworth-Lewis-Stern was applied).
- `player_of_match`: Array of awarded players.
- `players`: Dictionary mapping each team to its 11-player lineup.
- `registry`: Dictionary mapping player names to unique international IDs (`people` dictionary containing identifiers like `cricinfo` ID, `cricsheet` UUID).
- `officials`: Match referees, on-field umpires, and TV umpires.

#### B. `innings` Array (Ball-by-Ball Telemetry)
Each element represents one team's batting innings:
- `team`: Name of the batting team.
- `overs`: Array of completed or partial overs:
  - `over`: Zero-indexed over number (0 to 19).
  - `deliveries`: Array of delivery objects:
    - `batter`: Striker facing the ball.
    - `bowler`: Delivery bowler.
    - `non_striker`: Batter at the non-striker's end.
    - `runs`:
      - `batter`: Runs scored off the bat.
      - `extras`: Extra runs conceded.
      - `total`: Sum of batter runs + extras on that delivery.
    - `extras`: Sub-classification object if extras occurred:
      - `wides`, `noballs`, `byes`, `legbyes`, `penalty`.
    - `wickets`: Array of dismissals occurring on the delivery:
      - `kind`: Dismissal type (`"bowled"`, `"caught"`, `"lbw"`, `"run out"`, `"stumped"`, `"hit wicket"`).
      - `player_out`: Dismissed batter.
      - `fielders`: Array of fielders involved.
    - `review`: Details of DRS referrals if requested.
- `powerplays`: Over spans designated as Powerplay.
- `target`: Target runs and overs set for the chasing team.
- `super_over`: Boolean flag (`true`/`false`) if an innings was a tiebreaker super over.

---

## 3. Secondary & Scorecard Verification Sources

| Source | Role | Usage Constraints |
| :--- | :--- | :--- |
| **ICC Official Match Centre** (`icc-cricket.com`) | Official Scorecards & DLS Targets | Manual reference and cross-validation of match numbers and official outcomes. |
| **ESPNcricinfo** (`espncricinfo.com`) | Scorecard Cross-Audit | External statistical validation for boundary counts, strike rates, and fall-of-wicket sequences. Strictly no web-scraping to respect ToS and robots.txt. |

---

## 4. Ingestion & Storage Architecture

1. **`data/raw/`**: Stores downloaded source ZIP archives and calculated SHA-256 hash files (`checksums.sha256`). This directory is strictly read-only and immutable.
2. **`data/interim/`**: Contains unpacked JSON match files that passed strict tournament isolation criteria (`info.event.name == "ICC Men's T20 World Cup"`, `info.gender == "male"`, and `dates` in 2026).
3. **`data/processed/`**: Will store normalized relational tables in Parquet/CSV format ready for PostgreSQL staging.

---

## 5. Rate Limits & Terms Compliance Policy
- **Bulk Download Model**: Cricsheet encourages bulk archive downloading rather than scraping thousands of web pages. Our collector fetches the complete archive once using standard HTTP `User-Agent` headers.
- **Local Isolation**: All tournament extraction and filtering operations are performed locally in-memory on the downloaded archive without placing ongoing network load on Cricsheet servers.

