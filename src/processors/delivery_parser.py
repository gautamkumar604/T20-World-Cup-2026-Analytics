"""
Ball-by-ball delivery telemetry parser for ICC Men's T20 World Cup 2026.
"""

from typing import Dict, Any, List


class DeliveryParser:
    """Parses granular ball-by-ball delivery events from match innings."""

    @staticmethod
    def get_phase(over_number: int) -> str:
        """Categorizes an over into standard T20 phases."""
        if over_number < 6:
            return "Powerplay"
        elif over_number < 15:
            return "Middle"
        else:
            return "Death"

    @classmethod
    def parse_deliveries(cls, match_id: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts complete delivery records for all innings in a match."""
        deliveries_list = []
        info = data.get("info", {})
        registry = info.get("registry", {}).get("people", {})
        teams = info.get("teams", [])
        innings = data.get("innings", [])

        for inn_idx, inn in enumerate(innings):
            innings_num = inn_idx + 1
            batting_team = inn.get("team")
            bowling_teams = [t for t in teams if t != batting_team]
            bowling_team = bowling_teams[0] if bowling_teams else "Opposition"
            is_super_over = inn.get("super_over", False)

            overs = inn.get("overs", [])
            for over_obj in overs:
                over_number = over_obj.get("over", 0)
                phase = cls.get_phase(over_number)
                deliveries = over_obj.get("deliveries", [])

                for ball_idx, deliv in enumerate(deliveries, start=1):
                    delivery_id = f"{match_id}_{innings_num}_{over_number}_{ball_idx}"
                    actual_delivery_str = str(
                        deliv.get("actual_delivery", f"{over_number}.{ball_idx}")
                    )

                    batter = deliv.get("batter", "")
                    bowler = deliv.get("bowler", "")
                    non_striker = deliv.get("non_striker", "")

                    batter_id = str(registry.get(batter, batter))
                    bowler_id = str(registry.get(bowler, bowler))
                    non_striker_id = str(registry.get(non_striker, non_striker))

                    runs = deliv.get("runs", {})
                    batter_runs = runs.get("batter", 0)
                    extra_runs = runs.get("extras", 0)
                    total_runs = runs.get("total", 0)

                    # Extras breakdown
                    extras_dict = deliv.get("extras", {})
                    extra_types = []
                    is_legal = True
                    if extras_dict:
                        for k in ["wides", "noballs", "byes", "legbyes", "penalty"]:
                            if k in extras_dict:
                                extra_types.append(k)
                        if "wides" in extras_dict or "noballs" in extras_dict:
                            is_legal = False

                    extra_type = ", ".join(extra_types) if extra_types else None

                    # Boundaries
                    is_boundary_four = batter_runs == 4
                    is_boundary_six = batter_runs == 6
                    is_dot_ball = total_runs == 0 and is_legal

                    # Wickets
                    wickets = deliv.get("wickets", [])
                    is_wicket = len(wickets) > 0
                    wicket_kind = None
                    player_dismissed = None
                    fielders_list = []

                    if is_wicket:
                        w_info = wickets[0]
                        wicket_kind = w_info.get("kind")
                        player_dismissed = w_info.get("player_out")
                        fielders = w_info.get("fielders", [])
                        for f in fielders:
                            if isinstance(f, dict) and "name" in f:
                                fielders_list.append(f["name"])
                            elif isinstance(f, str):
                                fielders_list.append(f)

                    fielder_involved = ", ".join(fielders_list) if fielders_list else None

                    deliveries_list.append(
                        {
                            "delivery_id": delivery_id,
                            "match_id": str(match_id),
                            "innings": innings_num,
                            "batting_team": batting_team,
                            "bowling_team": bowling_team,
                            "over_number": over_number,
                            "ball_in_over": ball_idx,
                            "actual_delivery_str": actual_delivery_str,
                            "phase": phase,
                            "batter": batter,
                            "batter_id": batter_id,
                            "bowler": bowler,
                            "bowler_id": bowler_id,
                            "non_striker": non_striker,
                            "non_striker_id": non_striker_id,
                            "batter_runs": batter_runs,
                            "extra_runs": extra_runs,
                            "total_runs": total_runs,
                            "is_legal_delivery": is_legal,
                            "extra_type": extra_type,
                            "is_boundary_four": is_boundary_four,
                            "is_boundary_six": is_boundary_six,
                            "is_dot_ball": is_dot_ball,
                            "is_wicket": is_wicket,
                            "wicket_kind": wicket_kind,
                            "player_dismissed": player_dismissed,
                            "fielder_involved": fielder_involved,
                            "is_super_over": is_super_over,
                        }
                    )

        return deliveries_list

