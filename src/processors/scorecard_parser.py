"""
Scorecard parser calculating batting and bowling performance metrics
in strict accordance with official ICC cricket scoring rules.
"""

from typing import Dict, Any, List
from collections import defaultdict


class ScorecardParser:
    """Computes individual batting and bowling scorecards from ball-by-ball deliveries."""

    BOWLER_CREDITED_WICKETS = {
        "bowled",
        "caught",
        "caught and bowled",
        "lbw",
        "stumped",
        "hit wicket",
    }

    @classmethod
    def parse_scorecards(
        cls, match_id: str, deliveries: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Calculates official batting and bowling scorecards from parsed delivery records.

        Returns:
            Dictionary containing 'batting' and 'bowling' lists of records.
        """
        # Group deliveries by innings
        innings_deliveries = defaultdict(list)
        for d in deliveries:
            innings_deliveries[d["innings"]].append(d)

        batting_records = []
        bowling_records = []

        for inn_num, delivs in sorted(innings_deliveries.items()):
            # 1. Batting Scorecard Calculation
            batter_order = []
            batter_stats = defaultdict(
                lambda: {
                    "player_id": "",
                    "runs": 0,
                    "balls_faced": 0,
                    "fours": 0,
                    "sixes": 0,
                    "is_out": False,
                    "dismissal_kind": "not out",
                    "bowler": None,
                    "fielder": None,
                }
            )

            # 2. Bowling Scorecard Calculation
            bowler_order = []
            bowler_stats = defaultdict(
                lambda: {
                    "player_id": "",
                    "legal_balls": 0,
                    "runs_conceded": 0,
                    "wickets": 0,
                    "dots": 0,
                    "wides": 0,
                    "no_balls": 0,
                    "fours_conceded": 0,
                    "sixes_conceded": 0,
                    "over_runs": defaultdict(int),
                    "over_balls": defaultdict(int),
                }
            )

            batting_team = delivs[0]["batting_team"] if delivs else ""
            bowling_team = delivs[0]["bowling_team"] if delivs else ""

            for d in delivs:
                b_name = d["batter"]
                b_id = d["batter_id"]
                bw_name = d["bowler"]
                bw_id = d["bowler_id"]
                ns_name = d["non_striker"]
                ns_id = d["non_striker_id"]

                # Track batting order
                if b_name not in batter_order:
                    batter_order.append(b_name)
                    batter_stats[b_name]["player_id"] = b_id
                if ns_name not in batter_order:
                    batter_order.append(ns_name)
                    batter_stats[ns_name]["player_id"] = ns_id

                # Track bowling order
                if bw_name not in bowler_order:
                    bowler_order.append(bw_name)
                    bowler_stats[bw_name]["player_id"] = bw_id

                # Batting metrics
                extra_str = str(d.get("extra_type") or "")
                is_wide = "wide" in extra_str.lower()
                is_noball = "noball" in extra_str.lower()

                # A wide is NOT counted as a ball faced by the batter
                if not is_wide:
                    batter_stats[b_name]["balls_faced"] += 1

                b_runs = d["batter_runs"]
                batter_stats[b_name]["runs"] += b_runs
                if d["is_boundary_four"]:
                    batter_stats[b_name]["fours"] += 1
                if d["is_boundary_six"]:
                    batter_stats[b_name]["sixes"] += 1

                # Wicket for batter
                if d["is_wicket"]:
                    dismissed = d["player_dismissed"] or b_name
                    if dismissed in batter_stats:
                        batter_stats[dismissed]["is_out"] = True
                        batter_stats[dismissed]["dismissal_kind"] = d["wicket_kind"]
                        batter_stats[dismissed]["bowler"] = bw_name
                        batter_stats[dismissed]["fielder"] = d["fielder_involved"]

                # Bowling metrics
                # Bowler runs conceded = batter_runs + wides + noballs
                # (Byes and legbyes are NOT charged to bowler)
                bowler_charge = b_runs
                if is_wide or is_noball:
                    bowler_charge += d["extra_runs"]

                over_no = d["over_number"]
                bowler_stats[bw_name]["runs_conceded"] += bowler_charge
                bowler_stats[bw_name]["over_runs"][over_no] += bowler_charge

                if d["is_legal_delivery"]:
                    bowler_stats[bw_name]["legal_balls"] += 1
                    bowler_stats[bw_name]["over_balls"][over_no] += 1
                    if bowler_charge == 0:
                        bowler_stats[bw_name]["dots"] += 1

                if is_wide:
                    bowler_stats[bw_name]["wides"] += 1
                if is_noball:
                    bowler_stats[bw_name]["no_balls"] += 1
                if d["is_boundary_four"]:
                    bowler_stats[bw_name]["fours_conceded"] += 1
                if d["is_boundary_six"]:
                    bowler_stats[bw_name]["sixes_conceded"] += 1

                # Wicket credited to bowler
                if (
                    d["is_wicket"]
                    and str(d["wicket_kind"]).lower() in cls.BOWLER_CREDITED_WICKETS
                ):
                    bowler_stats[bw_name]["wickets"] += 1

            # Compile batting records
            for pos, b_name in enumerate(batter_order, start=1):
                b_data = batter_stats[b_name]
                bf = b_data["balls_faced"]
                runs = b_data["runs"]
                sr = round((runs / bf) * 100.0, 2) if bf > 0 else 0.0

                batting_records.append(
                    {
                        "match_id": str(match_id),
                        "innings": inn_num,
                        "team": batting_team,
                        "player_name": b_name,
                        "player_id": b_data["player_id"],
                        "batting_position": pos,
                        "runs": runs,
                        "balls_faced": bf,
                        "fours": b_data["fours"],
                        "sixes": b_data["sixes"],
                        "strike_rate": sr,
                        "is_out": b_data["is_out"],
                        "dismissal_kind": b_data["dismissal_kind"],
                        "bowler": b_data["bowler"],
                        "fielder": b_data["fielder"],
                    }
                )

            # Compile bowling records
            for bw_name in bowler_order:
                bw_data = bowler_stats[bw_name]
                lb = bw_data["legal_balls"]
                comp_overs = lb // 6
                rem_balls = lb % 6
                overs_formatted = round(comp_overs + (rem_balls / 10.0), 1)

                # Maiden calculation: completed 6-ball over with 0 runs conceded
                maidens = 0
                for ov, balls in bw_data["over_balls"].items():
                    if balls == 6 and bw_data["over_runs"][ov] == 0:
                        maidens += 1

                decimal_overs = lb / 6.0 if lb > 0 else 0.0
                econ = (
                    round(bw_data["runs_conceded"] / decimal_overs, 2)
                    if decimal_overs > 0
                    else 0.0
                )

                bowling_records.append(
                    {
                        "match_id": str(match_id),
                        "innings": inn_num,
                        "team": bowling_team,
                        "player_name": bw_name,
                        "player_id": bw_data["player_id"],
                        "overs": overs_formatted,
                        "legal_balls": lb,
                        "maidens": maidens,
                        "runs_conceded": bw_data["runs_conceded"],
                        "wickets": bw_data["wickets"],
                        "economy_rate": econ,
                        "dots": bw_data["dots"],
                        "wides": bw_data["wides"],
                        "no_balls": bw_data["no_balls"],
                        "fours_conceded": bw_data["fours_conceded"],
                        "sixes_conceded": bw_data["sixes_conceded"],
                    }
                )

        return {"batting": batting_records, "bowling": bowling_records}

