"""
Match metadata and dimension parser for ICC Men's T20 World Cup 2026.
"""

from typing import Dict, Any, List, Tuple
from config.settings import TARGET_TOURNAMENT_NAME


class MatchParser:
    """Parses match-level metadata, dimension records (players, venues), and innings summaries."""

    @staticmethod
    def parse_match(match_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts the top-level match entity attributes."""
        info = data.get("info", {})
        dates = info.get("dates", [])
        match_date = dates[0] if dates else None

        event = info.get("event", {})
        match_number = event.get("match_number") if isinstance(event, dict) else None
        stage = event.get("stage") if isinstance(event, dict) else None
        group_name = event.get("group") if isinstance(event, dict) else None

        teams = info.get("teams", [])
        team1 = teams[0] if len(teams) > 0 else None
        team2 = teams[1] if len(teams) > 1 else None

        toss = info.get("toss", {})
        toss_winner = toss.get("winner")
        toss_decision = toss.get("decision")

        venue = info.get("venue")
        city = info.get("city")

        outcome = info.get("outcome", {})
        winner = outcome.get("winner")
        outcome_by = outcome.get("by", {})

        if "runs" in outcome_by:
            outcome_type = "runs"
            win_margin = outcome_by["runs"]
        elif "wickets" in outcome_by:
            outcome_type = "wickets"
            win_margin = outcome_by["wickets"]
        elif "result" in outcome:
            outcome_type = outcome["result"]
            win_margin = 0
            if not winner:
                winner = f"Result: {outcome_type}"
        else:
            outcome_type = "unknown"
            win_margin = 0

        is_dls = outcome.get("method") == "D/L"

        pom = info.get("player_of_match", [])
        player_of_match = ", ".join(pom) if pom else None

        # Officials
        officials = info.get("officials", {})
        umpires = officials.get("umpires", [])
        umpire1 = umpires[0] if len(umpires) > 0 else None
        umpire2 = umpires[1] if len(umpires) > 1 else None
        tv_umpires = officials.get("tv_umpires", [])
        tv_umpire = tv_umpires[0] if tv_umpires else None
        referees = officials.get("match_referees", [])
        match_referee = referees[0] if referees else None

        # Target runs/overs from 2nd innings
        target_runs = None
        target_overs = None
        innings = data.get("innings", [])
        if len(innings) > 1:
            target = innings[1].get("target", {})
            if target:
                target_runs = target.get("runs")
                target_overs = target.get("overs")

        return {
            "match_id": str(match_id),
            "match_date": match_date,
            "tournament_name": TARGET_TOURNAMENT_NAME,
            "match_number": match_number,
            "stage": stage,
            "group_name": group_name,
            "team1": team1,
            "team2": team2,
            "toss_winner": toss_winner,
            "toss_decision": toss_decision,
            "venue": venue,
            "city": city,
            "winner": winner,
            "outcome_type": outcome_type,
            "win_margin": win_margin,
            "player_of_match": player_of_match,
            "target_runs": target_runs,
            "target_overs": target_overs,
            "is_dls_applied": is_dls,
            "umpire1": umpire1,
            "umpire2": umpire2,
            "tv_umpire": tv_umpire,
            "match_referee": match_referee,
            "metadata_available": True,
            "scorecard_available": True,
            "ball_by_ball_available": True,
            "source_note": "Cricsheet Open Data (Ball-by-Ball & Scorecard complete)",
        }

    @staticmethod
    def parse_venues_and_players(
        match_id: str, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Extracts venue dimension record and player dimension records."""
        info = data.get("info", {})
        venue_name = info.get("venue", "Unknown")
        city = info.get("city", "Unknown")

        # Country determination based on known host venues
        sri_lankan_venues = [
            "Pallekele International Cricket Stadium",
            "R Premadasa Stadium",
            "Sinhalese Sports Club Ground",
        ]
        country = (
            "Sri Lanka"
            if any(sv.lower() in venue_name.lower() for sv in sri_lankan_venues)
            else "India"
        )

        venue_record = {
            "venue_name": venue_name,
            "city": city,
            "country": country,
        }

        # Players
        registry = info.get("registry", {}).get("people", {})
        players_dict = info.get("players", {})
        player_records = []

        for team, player_list in players_dict.items():
            for p_name in player_list:
                p_id = registry.get(p_name, p_name)
                player_records.append(
                    {
                        "player_id": str(p_id),
                        "player_name": p_name,
                        "team": team,
                    }
                )

        return venue_record, player_records

    @staticmethod
    def parse_innings_summaries(match_id: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculates team innings summaries (runs, wickets, overs, extras)."""
        summaries = []
        innings = data.get("innings", [])
        teams = data.get("info", {}).get("teams", [])

        for idx, inn in enumerate(innings):
            batting_team = inn.get("team")
            bowling_team = [t for t in teams if t != batting_team]
            bowling_team_name = bowling_team[0] if bowling_team else "Opposition"

            overs = inn.get("overs", [])
            total_runs = 0
            total_wickets = 0
            extras_total = 0
            extras_wides = 0
            extras_noballs = 0
            extras_byes = 0
            extras_legbyes = 0
            extras_penalty = 0
            legal_deliveries = 0

            for over_obj in overs:
                deliveries = over_obj.get("deliveries", [])
                for d in deliveries:
                    runs = d.get("runs", {})
                    total_runs += runs.get("total", 0)
                    extra_sub = d.get("extras", {})
                    if extra_sub:
                        extras_total += runs.get("extras", 0)
                        extras_wides += extra_sub.get("wides", 0)
                        extras_noballs += extra_sub.get("noballs", 0)
                        extras_byes += extra_sub.get("byes", 0)
                        extras_legbyes += extra_sub.get("legbyes", 0)
                        extras_penalty += extra_sub.get("penalty", 0)
                        if "wides" not in extra_sub and "noballs" not in extra_sub:
                            legal_deliveries += 1
                    else:
                        legal_deliveries += 1

                    if "wickets" in d:
                        total_wickets += len(d["wickets"])

            completed_overs = legal_deliveries // 6
            remainder_balls = legal_deliveries % 6
            overs_formatted = round(completed_overs + (remainder_balls / 10.0), 1)
            decimal_overs = legal_deliveries / 6.0 if legal_deliveries > 0 else 0
            run_rate = round(total_runs / decimal_overs, 2) if decimal_overs > 0 else 0.0

            summaries.append(
                {
                    "match_id": str(match_id),
                    "innings": idx + 1,
                    "batting_team": batting_team,
                    "bowling_team": bowling_team_name,
                    "total_runs": total_runs,
                    "total_wickets": total_wickets,
                    "legal_deliveries": legal_deliveries,
                    "total_overs": overs_formatted,
                    "extras_total": extras_total,
                    "extras_wides": extras_wides,
                    "extras_noballs": extras_noballs,
                    "extras_byes": extras_byes,
                    "extras_legbyes": extras_legbyes,
                    "extras_penalty": extras_penalty,
                    "run_rate": run_rate,
                    "is_super_over": inn.get("super_over", False),
                }
            )

        return summaries

