"""
Processing and normalization pipeline for ICC Men's T20 World Cup 2026.

Parses all interim JSON files, executes mathematical reconciliation audits,
and exports clean normalized tabular datasets to data/processed/.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

from config.settings import INTERIM_DATA_DIR, PROCESSED_DATA_DIR, REPORTS_DIR
from src.utils.logger import get_logger
from src.processors.match_parser import MatchParser
from src.processors.delivery_parser import DeliveryParser
from src.processors.scorecard_parser import ScorecardParser

logger = get_logger("processing_pipeline")


class ProcessingPipeline:
    """Orchestrates parsing, reconciliation, and export of normalized datasets."""

    def __init__(
        self,
        interim_dir: Path = INTERIM_DATA_DIR,
        processed_dir: Path = PROCESSED_DATA_DIR,
        reports_dir: Path = REPORTS_DIR,
    ):
        self.interim_dir = interim_dir
        self.processed_dir = processed_dir
        self.reports_dir = reports_dir

        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        """Executes full normalization across all interim match JSON files."""
        json_files = sorted(list(self.interim_dir.glob("*.json")))
        logger.info("Found %d match files in %s", len(json_files), self.interim_dir)

        if not json_files:
            raise FileNotFoundError(f"No JSON match files found in {self.interim_dir}")

        all_matches = []
        all_venues = {}
        all_players = {}
        all_summaries = []
        all_deliveries = []
        all_batting = []
        all_bowling = []

        audit_results = {
            "total_matches_processed": 0,
            "total_deliveries_processed": 0,
            "total_batting_records": 0,
            "total_bowling_records": 0,
            "reconciliation_discrepancies": [],
        }

        for file_path in json_files:
            match_id = file_path.stem
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 1. Parse Match Metadata
            match_record = MatchParser.parse_match(match_id, data)
            all_matches.append(match_record)

            # 2. Parse Venues & Players
            venue_rec, player_recs = MatchParser.parse_venues_and_players(match_id, data)
            all_venues[venue_rec["venue_name"]] = venue_rec
            for p in player_recs:
                all_players[p["player_id"]] = p

            # 3. Parse Innings Summaries
            summaries = MatchParser.parse_innings_summaries(match_id, data)
            all_summaries.extend(summaries)

            # 4. Parse Ball-by-Ball Deliveries
            deliveries = DeliveryParser.parse_deliveries(match_id, data)
            all_deliveries.extend(deliveries)

            # 5. Parse Batting & Bowling Scorecards
            scorecards = ScorecardParser.parse_scorecards(match_id, deliveries)
            batting_recs = scorecards["batting"]
            bowling_recs = scorecards["bowling"]
            all_batting.extend(batting_recs)
            all_bowling.extend(bowling_recs)

            # 6. Mathematical Reconciliation Audits
            self._reconcile_match(
                match_id=match_id,
                summaries=summaries,
                deliveries=deliveries,
                batting_recs=batting_recs,
                bowling_recs=bowling_recs,
                audit_results=audit_results,
            )

            audit_results["total_matches_processed"] += 1

        audit_results["total_deliveries_processed"] = len(all_deliveries)
        audit_results["total_batting_records"] = len(all_batting)
        audit_results["total_bowling_records"] = len(all_bowling)

        logger.info(
            "Reconciliation complete. Processed %d matches, %d deliveries. Discrepancies found: %d",
            audit_results["total_matches_processed"],
            audit_results["total_deliveries_processed"],
            len(audit_results["reconciliation_discrepancies"]),
        )

        # 7. Convert to DataFrames and Export
        self._export_datasets(
            matches=all_matches,
            venues=list(all_venues.values()),
            players=list(all_players.values()),
            summaries=all_summaries,
            deliveries=all_deliveries,
            batting=all_batting,
            bowling=all_bowling,
        )

        # 8. Save Audit Summary
        audit_path = self.reports_dir / "reconciliation_audit.json"
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit_results, f, indent=2)
        logger.info("Saved reconciliation audit report to %s", audit_path)

        return audit_results

    def _reconcile_match(
        self,
        match_id: str,
        summaries: List[Dict[str, Any]],
        deliveries: List[Dict[str, Any]],
        batting_recs: List[Dict[str, Any]],
        bowling_recs: List[Dict[str, Any]],
        audit_results: Dict[str, Any],
    ) -> None:
        """Verifies mathematical identities across innings."""
        for summ in summaries:
            inn = summ["innings"]
            inn_runs = summ["total_runs"]
            inn_extras = summ["extras_total"]
            inn_fielding_extras = (
                summ["extras_byes"] + summ["extras_legbyes"] + summ["extras_penalty"]
            )

            # 1. Delivery total runs sum
            inn_deliveries = [
                d for d in deliveries if d["match_id"] == match_id and d["innings"] == inn
            ]
            deliv_sum = sum(d["total_runs"] for d in inn_deliveries)
            if deliv_sum != inn_runs:
                audit_results["reconciliation_discrepancies"].append(
                    {
                        "match_id": match_id,
                        "innings": inn,
                        "type": "delivery_vs_innings_runs",
                        "expected": inn_runs,
                        "computed": deliv_sum,
                    }
                )

            # 2. Batting scorecard sum + extras == innings total
            inn_batting = [
                b for b in batting_recs if b["match_id"] == match_id and b["innings"] == inn
            ]
            bat_runs_sum = sum(b["runs"] for b in inn_batting)
            if (bat_runs_sum + inn_extras) != inn_runs:
                audit_results["reconciliation_discrepancies"].append(
                    {
                        "match_id": match_id,
                        "innings": inn,
                        "type": "batting_runs_plus_extras_vs_total",
                        "expected": inn_runs,
                        "computed": bat_runs_sum + inn_extras,
                    }
                )

            # 3. Bowling runs conceded + fielding extras == innings total
            inn_bowling = [
                bw for bw in bowling_recs if bw["match_id"] == match_id and bw["innings"] == inn
            ]
            bowl_conceded_sum = sum(bw["runs_conceded"] for bw in inn_bowling)
            if (bowl_conceded_sum + inn_fielding_extras) != inn_runs:
                audit_results["reconciliation_discrepancies"].append(
                    {
                        "match_id": match_id,
                        "innings": inn,
                        "type": "bowling_conceded_plus_fielding_extras_vs_total",
                        "expected": inn_runs,
                        "computed": bowl_conceded_sum + inn_fielding_extras,
                    }
                )

    def _export_datasets(
        self,
        matches: List[Dict[str, Any]],
        venues: List[Dict[str, Any]],
        players: List[Dict[str, Any]],
        summaries: List[Dict[str, Any]],
        deliveries: List[Dict[str, Any]],
        batting: List[Dict[str, Any]],
        bowling: List[Dict[str, Any]],
    ) -> None:
        """Exports datasets to CSV and Parquet formats."""
        export_map = {
            "matches": pd.DataFrame(matches),
            "dim_venues": pd.DataFrame(venues),
            "dim_players": pd.DataFrame(players),
            "match_summaries": pd.DataFrame(summaries),
            "deliveries": pd.DataFrame(deliveries),
            "batting_scorecards": pd.DataFrame(batting),
            "bowling_scorecards": pd.DataFrame(bowling),
        }

        for table_name, df in export_map.items():
            csv_path = self.processed_dir / f"{table_name}.csv"
            df.to_csv(csv_path, index=False, encoding="utf-8")
            logger.info("Saved %s (%d rows) to %s", table_name, len(df), csv_path)

            try:
                parquet_path = self.processed_dir / f"{table_name}.parquet"
                df.to_parquet(parquet_path, index=False)
                logger.info("Saved %s to %s", table_name, parquet_path)
            except Exception:
                # pyarrow/fastparquet not installed; CSV is primary
                pass


if __name__ == "__main__":
    pipeline = ProcessingPipeline()
    results = pipeline.run()
    print("Pipeline completed successfully:")
    print(f"Matches: {results['total_matches_processed']}")
    print(f"Deliveries: {results['total_deliveries_processed']}")
    print(f"Discrepancies: {len(results['reconciliation_discrepancies'])}")
