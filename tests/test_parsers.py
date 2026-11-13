"""
Unit tests for match, delivery, and scorecard parsing pipelines.
"""

import unittest
import json
from pathlib import Path

from config.settings import INTERIM_DATA_DIR
from src.processors.match_parser import MatchParser
from src.processors.delivery_parser import DeliveryParser
from src.processors.scorecard_parser import ScorecardParser


class TestParsers(unittest.TestCase):
    """Test suite for parsing and statistical calculations."""

    @classmethod
    def setUpClass(cls):
        """Loads a real tournament match JSON file for testing."""
        sample_files = list(INTERIM_DATA_DIR.glob("*.json"))
        if not sample_files:
            raise unittest.SkipTest("No sample interim JSON files available for testing.")
        cls.sample_path = sample_files[0]
        with open(cls.sample_path, "r", encoding="utf-8") as f:
            cls.match_data = json.load(f)
        cls.match_id = cls.sample_path.stem

    def test_match_parser(self):
        """Verifies extraction of match metadata."""
        match_record = MatchParser.parse_match(self.match_id, self.match_data)
        self.assertEqual(match_record["match_id"], self.match_id)
        self.assertIn("tournament_name", match_record)
        self.assertIsNotNone(match_record["team1"])
        self.assertIsNotNone(match_record["team2"])
        self.assertIsNotNone(match_record["winner"])

    def test_venue_and_players_parser(self):
        """Verifies venue and player dimension extraction."""
        venue, players = MatchParser.parse_venues_and_players(
            self.match_id, self.match_data
        )
        self.assertIn("venue_name", venue)
        self.assertIn(venue["country"], ["India", "Sri Lanka"])
        self.assertGreater(len(players), 20)  # At least 22 players (11 per team)

    def test_delivery_parser_and_phases(self):
        """Verifies delivery telemetry and phase tagging."""
        deliveries = DeliveryParser.parse_deliveries(self.match_id, self.match_data)
        self.assertGreater(len(deliveries), 200)

        # Verify phase mapping
        for d in deliveries:
            over = d["over_number"]
            if over < 6:
                self.assertEqual(d["phase"], "Powerplay")
            elif over < 15:
                self.assertEqual(d["phase"], "Middle")
            else:
                self.assertEqual(d["phase"], "Death")

            # Mathematical runs consistency per ball
            self.assertEqual(d["total_runs"], d["batter_runs"] + d["extra_runs"])

    def test_scorecard_reconciliation(self):
        """Verifies that scorecard totals balance with ball-by-ball delivery sums."""
        deliveries = DeliveryParser.parse_deliveries(self.match_id, self.match_data)
        scorecards = ScorecardParser.parse_scorecards(self.match_id, deliveries)
        summaries = MatchParser.parse_innings_summaries(self.match_id, self.match_data)

        batting = scorecards["batting"]
        bowling = scorecards["bowling"]

        for summ in summaries:
            inn = summ["innings"]
            inn_runs = summ["total_runs"]
            inn_extras = summ["extras_total"]
            fielding_extras = (
                summ["extras_byes"] + summ["extras_legbyes"] + summ["extras_penalty"]
            )

            # Batting runs + extras must balance with total runs
            inn_bat = [b for b in batting if b["innings"] == inn]
            self.assertEqual(sum(b["runs"] for b in inn_bat) + inn_extras, inn_runs)

            # Bowling runs conceded + fielding extras must balance with total runs
            inn_bowl = [bw for bw in bowling if bw["innings"] == inn]
            self.assertEqual(
                sum(bw["runs_conceded"] for bw in inn_bowl) + fielding_extras, inn_runs
            )


if __name__ == "__main__":
    unittest.main()
