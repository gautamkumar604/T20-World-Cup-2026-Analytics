"""
Unit and data integrity tests for the ICC Men's T20 World Cup 2026 data pipeline.
"""

import unittest
import tempfile
from pathlib import Path
from src.utils.validator import compute_sha256, verify_sha256, validate_cricsheet_json_structure
from src.collectors.tournament_filter import TournamentFilter


class TestDataIntegrity(unittest.TestCase):
    """Test suite verifying validation functions and tournament filter criteria."""

    def test_sha256_computation(self):
        """Verifies SHA-256 calculation on known input."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.txt"
            test_file.write_text("T20 World Cup 2026 Data Analytics", encoding="utf-8")

            hash_val = compute_sha256(test_file)
            self.assertEqual(len(hash_val), 64)
            self.assertTrue(verify_sha256(test_file, hash_val))
            self.assertFalse(verify_sha256(test_file, "0" * 64))

    def test_validate_cricsheet_json_structure(self):
        """Verifies schema validation on valid and invalid payloads."""
        valid_payload = {
            "meta": {"data_version": "1.3.0"},
            "info": {
                "dates": ["2026-02-15"],
                "teams": ["India", "Australia"],
                "gender": "male",
            },
        }
        self.assertTrue(validate_cricsheet_json_structure(valid_payload))

        invalid_payload = {"meta": {}}
        self.assertFalse(validate_cricsheet_json_structure(invalid_payload))

        invalid_payload_2 = {"meta": {}, "info": {"teams": []}}
        self.assertFalse(validate_cricsheet_json_structure(invalid_payload_2))

    def test_tournament_filter_matching(self):
        """Verifies that only 2026 Men's T20 World Cup main tournament matches are matched."""
        t_filter = TournamentFilter()

        # Target: 2026 Men's T20 World Cup main event
        match_2026_main = {
            "info": {
                "event": {"name": "ICC Men's T20 World Cup", "match_number": 1},
                "gender": "male",
                "dates": ["2026-02-10"],
                "season": "2026",
            }
        }
        self.assertTrue(t_filter.is_target_tournament_match(match_2026_main))

        # Rejection 1: 2026 Qualifier (Must NOT mix)
        match_2026_qualifier = {
            "info": {
                "event": {
                    "name": "ICC Men's T20 World Cup Sub Regional Asia Qualifier A",
                    "match_number": 1,
                },
                "gender": "male",
                "dates": ["2026-10-05"],
                "season": "2026",
            }
        }
        self.assertFalse(t_filter.is_target_tournament_match(match_2026_qualifier))

        # Rejection 2: 2026 Regional Final (Must NOT mix)
        match_2026_region_final = {
            "info": {
                "event": {"name": "ICC Men's T20 World Cup Europe Region Final"},
                "gender": "male",
                "dates": ["2026-07-15"],
                "season": "2026",
            }
        }
        self.assertFalse(t_filter.is_target_tournament_match(match_2026_region_final))

        # Rejection 3: 2024 Men's T20 World Cup (Earlier edition - Must NOT mix)
        match_2024 = {
            "info": {
                "event": {"name": "ICC Men's T20 World Cup", "match_number": 1},
                "gender": "male",
                "dates": ["2024-06-05"],
                "season": "2024",
            }
        }
        self.assertFalse(t_filter.is_target_tournament_match(match_2024))

        # Rejection 4: Domestic league in 2026 (IPL)
        match_ipl = {
            "info": {
                "event": {"name": "Indian Premier League"},
                "gender": "male",
                "dates": ["2026-04-10"],
                "season": "2026",
            }
        }
        self.assertFalse(t_filter.is_target_tournament_match(match_ipl))

        # Rejection 5: Women's T20 World Cup
        match_women = {
            "info": {
                "event": {"name": "ICC Women's T20 World Cup"},
                "gender": "female",
                "dates": ["2026-02-10"],
                "season": "2026",
            }
        }
        self.assertFalse(t_filter.is_target_tournament_match(match_women))


if __name__ == "__main__":
    unittest.main()
