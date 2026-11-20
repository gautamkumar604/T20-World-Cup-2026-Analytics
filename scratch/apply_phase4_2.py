import json
import os

# 1. Update model.bim
model_path = 'power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim'
with open(model_path, 'r', encoding='utf-8') as f:
    bim = json.load(f)

# Find tables
tables = {t['name']: t for t in bim['model']['tables']}

new_summary_measures = [
    {
        "name": "Lowest Match Score",
        "expression": "VAR MinRuns = CALCULATE(MIN(fact_match_summaries[total_runs]), fact_match_summaries[is_super_over] = FALSE())\nVAR TopRow = TOPN(1, FILTER(fact_match_summaries, fact_match_summaries[total_runs] = MinRuns && fact_match_summaries[is_super_over] = FALSE()), fact_match_summaries[total_runs], ASC)\nVAR TeamName = MAXX(TopRow, fact_match_summaries[batting_team])\nVAR Opponent = MAXX(TopRow, fact_match_summaries[bowling_team])\nVAR Wickets = MAXX(TopRow, fact_match_summaries[total_wickets])\nRETURN\n    IF(NOT ISBLANK(MinRuns), FORMAT(MinRuns, \"#,##0\") & \"/\" & FORMAT(Wickets, \"0\") & \" (\" & TeamName & \" vs \" & Opponent & \")\", BLANK())",
        "displayFolder": "Phase 4.2 Measures"
    },
    {
        "name": "Lowest Team Score",
        "expression": "CALCULATE(MIN(fact_match_summaries[total_runs]), fact_match_summaries[is_super_over] = FALSE())",
        "formatString": "#,##0",
        "displayFolder": "Phase 4.2 Measures"
    },
    {
        "name": "Highest Team Score",
        "expression": "CALCULATE(MAX(fact_match_summaries[total_runs]), fact_match_summaries[is_super_over] = FALSE())",
        "formatString": "#,##0",
        "displayFolder": "Phase 4.2 Measures"
    },
    {
        "name": "Team Win Pct",
        "expression": "VAR MatchesWon = [Selected Team Matches Won]\nVAR MatchesCompleted = [Selected Team Matches Completed]\nRETURN\n    IF(MatchesCompleted > 0, DIVIDE(MatchesWon, MatchesCompleted, BLANK()) * 100, BLANK())",
        "formatString": "0.0\"%\"",
        "displayFolder": "Phase 4.2 Measures"
    },
    {
        "name": "Venue Avg First Innings Score",
        "expression": "CALCULATE(\n    AVERAGE(fact_match_summaries[total_runs]),\n    fact_match_summaries[innings] = 1,\n    fact_match_summaries[is_super_over] = FALSE()\n)",
        "formatString": "0.0",
        "displayFolder": "Phase 4.2 Measures"
    },
    {
        "name": "Venue Avg Second Innings Score",
        "expression": "CALCULATE(\n    AVERAGE(fact_match_summaries[total_runs]),\n    fact_match_summaries[innings] = 2,\n    fact_match_summaries[is_super_over] = FALSE()\n)",
        "formatString": "0.0",
        "displayFolder": "Phase 4.2 Measures"
    }
]

new_batting_measures = [
    {
        "name": "Player Total Runs",
        "expression": "SUM(fact_batting_scorecards[runs])",
        "formatString": "#,##0",
        "displayFolder": "Phase 4.2 Measures"
    },
    {
        "name": "Player Balls Faced",
        "expression": "SUM(fact_batting_scorecards[balls_faced])",
        "formatString": "#,##0",
        "displayFolder": "Phase 4.2 Measures"
    },
    {
        "name": "Player Strike Rate",
        "expression": "DIVIDE(SUM(fact_batting_scorecards[runs]), SUM(fact_batting_scorecards[balls_faced]), BLANK()) * 100",
        "formatString": "0.00",
        "displayFolder": "Phase 4.2 Measures"
    },
    {
        "name": "Player Strike Rate (Min 100 Runs)",
        "expression": "VAR RunsScored = SUM(fact_batting_scorecards[runs])\nVAR BallsFaced = SUM(fact_batting_scorecards[balls_faced])\nRETURN\n    IF(RunsScored >= 100, DIVIDE(RunsScored, BallsFaced, BLANK()) * 100, BLANK())",
        "formatString": "0.00",
        "displayFolder": "Phase 4.2 Measures"
    }
]

new_bowling_measures = [
    {
        "name": "Player Total Wickets",
        "expression": "SUM(fact_bowling_scorecards[wickets])",
        "formatString": "#,##0",
        "displayFolder": "Phase 4.2 Measures"
    },
    {
        "name": "Player Legal Balls",
        "expression": "SUM(fact_bowling_scorecards[legal_balls])",
        "formatString": "#,##0",
        "displayFolder": "Phase 4.2 Measures"
    },
    {
        "name": "Player Overs Bowled",
        "expression": "DIVIDE(SUM(fact_bowling_scorecards[legal_balls]), 6, 0)",
        "formatString": "0.0",
        "displayFolder": "Phase 4.2 Measures"
    },
    {
        "name": "Player Runs Conceded",
        "expression": "SUM(fact_bowling_scorecards[runs_conceded])",
        "formatString": "#,##0",
        "displayFolder": "Phase 4.2 Measures"
    },
    {
        "name": "Player Economy Rate",
        "expression": "VAR RunsConc = SUM(fact_bowling_scorecards[runs_conceded])\nVAR LegalBalls = SUM(fact_bowling_scorecards[legal_balls])\nRETURN\n    IF(LegalBalls > 0, DIVIDE(RunsConc, (LegalBalls / 6.0), BLANK()), BLANK())",
        "formatString": "0.00",
        "displayFolder": "Phase 4.2 Measures"
    },
    {
        "name": "Player Economy Rate (Min 10 Overs)",
        "expression": "VAR RunsConc = SUM(fact_bowling_scorecards[runs_conceded])\nVAR LegalBalls = SUM(fact_bowling_scorecards[legal_balls])\nRETURN\n    IF(LegalBalls >= 60, DIVIDE(RunsConc, (LegalBalls / 6.0), BLANK()), BLANK())",
        "formatString": "0.00",
        "displayFolder": "Phase 4.2 Measures"
    }
]

# Append measures safely (avoiding duplicates)
def add_measures(tbl, new_meas):
    if 'measures' not in tbl:
        tbl['measures'] = []
    existing_names = {m['name'] for m in tbl['measures']}
    added = 0
    for m in new_meas:
        if m['name'] not in existing_names:
            tbl['measures'].append(m)
            added += 1
        else:
            # Update existing
            for idx, em in enumerate(tbl['measures']):
                if em['name'] == m['name']:
                    tbl['measures'][idx] = m
    return added

add_measures(tables['fact_match_summaries'], new_summary_measures)
add_measures(tables['fact_batting_scorecards'], new_batting_measures)
add_measures(tables['fact_bowling_scorecards'], new_bowling_measures)

with open(model_path, 'w', encoding='utf-8') as f:
    json.dump(bim, f, indent=2, ensure_ascii=False)
print("Updated model.bim with Phase 4.2 measures!")

# 2. Update report.json
report_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(report_path, 'r', encoding='utf-8') as f:
    rep = json.load(f)

# Define Section 3 (Executive Overview)
page3_containers = [
    # Visual 1: Header Banner
    {
        "x": 20, "y": 10, "z": 10, "width": 740, "height": 60,
        "config": json.dumps({
            "name": "HeaderBanner_Executive",
            "singleVisual": {
                "visualType": "textbox",
                "objects": {
                    "general": [{
                        "properties": {
                            "paragraphs": [
                                {
                                    "textRuns": [{
                                        "value": "ICC Men's T20 World Cup 2026 — Executive Dashboard\n",
                                        "textStyle": {"fontSize": "17pt", "fontWeight": "bold", "color": "#1A365D"}
                                    }, {
                                        "value": "Authoritative Tournament Intelligence: Stage Progression, Player Leaders & Venue Analytics",
                                        "textStyle": {"fontSize": "9pt", "color": "#4A5568"}
                                    }]
                                }
                            ]
                        }
                    }]
                }
            }
        })
    },
    # Visual 2: Stage Slicer
    {
        "x": 770, "y": 10, "z": 20, "width": 235, "height": 60,
        "config": json.dumps({
            "name": "Slicer_Stage_Exec",
            "singleVisual": {
                "visualType": "slicer",
                "projections": {
                    "Values": [{"queryRef": "dim_matches.Stage_Normalized"}]
                },
                "objects": {
                    "general": [{"properties": {"orientation": {"expr": {"Literal": {"Value": "'horizontal'"}}}}}],
                    "header": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}, "title": {"expr": {"Literal": {"Value": "'Stage Filter'"}}}}}]
                }
            }
        })
    },
    # Visual 3: Team Slicer
    {
        "x": 1015, "y": 10, "z": 30, "width": 245, "height": 60,
        "config": json.dumps({
            "name": "Slicer_Team_Exec",
            "singleVisual": {
                "visualType": "slicer",
                "projections": {
                    "Values": [{"queryRef": "dim_teams.team_name"}]
                },
                "objects": {
                    "general": [{"properties": {"orientation": {"expr": {"Literal": {"Value": "'vertical'"}}}}}],
                    "header": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}, "title": {"expr": {"Literal": {"Value": "'Team Filter'"}}}}}]
                }
            }
        })
    },
    # Visual 4: Card Total Matches
    {
        "x": 20, "y": 78, "z": 40, "width": 195, "height": 72,
        "config": json.dumps({
            "name": "Card_Exec_TotalMatches",
            "singleVisual": {
                "visualType": "card",
                "projections": {
                    "Values": [{"queryRef": "fact_match_summaries.Tournament Matches Scheduled"}]
                },
                "objects": {
                    "labels": [{"properties": {"fontSize": {"expr": {"Literal": {"Value": "18D"}}}, "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#1A365D'"}}}}}}}],
                    "categoryLabels": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}]
                }
            }
        })
    },
    # Visual 5: Card Completed Matches
    {
        "x": 225, "y": 78, "z": 50, "width": 195, "height": 72,
        "config": json.dumps({
            "name": "Card_Exec_CompletedMatches",
            "singleVisual": {
                "visualType": "card",
                "projections": {
                    "Values": [{"queryRef": "fact_match_summaries.Tournament Matches Completed"}]
                },
                "objects": {
                    "labels": [{"properties": {"fontSize": {"expr": {"Literal": {"Value": "18D"}}}, "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#1A365D'"}}}}}}}],
                    "categoryLabels": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}]
                }
            }
        })
    },
    # Visual 6: Card Total Runs
    {
        "x": 430, "y": 78, "z": 60, "width": 195, "height": 72,
        "config": json.dumps({
            "name": "Card_Exec_TotalRuns",
            "singleVisual": {
                "visualType": "card",
                "projections": {
                    "Values": [{"queryRef": "fact_match_summaries.Total Tournament Runs"}]
                },
                "objects": {
                    "labels": [{"properties": {"fontSize": {"expr": {"Literal": {"Value": "18D"}}}, "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#1A365D'"}}}}}}}],
                    "categoryLabels": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}]
                }
            }
        })
    },
    # Visual 7: Card Total Wickets
    {
        "x": 635, "y": 78, "z": 70, "width": 195, "height": 72,
        "config": json.dumps({
            "name": "Card_Exec_TotalWickets",
            "singleVisual": {
                "visualType": "card",
                "projections": {
                    "Values": [{"queryRef": "fact_match_summaries.Total Tournament Wickets"}]
                },
                "objects": {
                    "labels": [{"properties": {"fontSize": {"expr": {"Literal": {"Value": "18D"}}}, "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#1A365D'"}}}}}}}],
                    "categoryLabels": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}]
                }
            }
        })
    },
    # Visual 8: Card Highest Match Score
    {
        "x": 840, "y": 78, "z": 80, "width": 205, "height": 72,
        "config": json.dumps({
            "name": "Card_Exec_HighestScore",
            "singleVisual": {
                "visualType": "card",
                "projections": {
                    "Values": [{"queryRef": "fact_match_summaries.Highest Match Score"}]
                },
                "objects": {
                    "labels": [{"properties": {"fontSize": {"expr": {"Literal": {"Value": "14D"}}}, "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#2E7D32'"}}}}}}}],
                    "categoryLabels": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}]
                }
            }
        })
    },
    # Visual 9: Card Lowest Match Score
    {
        "x": 1055, "y": 78, "z": 90, "width": 205, "height": 72,
        "config": json.dumps({
            "name": "Card_Exec_LowestScore",
            "singleVisual": {
                "visualType": "card",
                "projections": {
                    "Values": [{"queryRef": "fact_match_summaries.Lowest Match Score"}]
                },
                "objects": {
                    "labels": [{"properties": {"fontSize": {"expr": {"Literal": {"Value": "14D"}}}, "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#C53030'"}}}}}}}],
                    "categoryLabels": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}]
                }
            }
        })
    },
    # Visual 10: Tournament Progress Visual (clusteredColumnChart)
    {
        "x": 20, "y": 158, "z": 100, "width": 380, "height": 255,
        "config": json.dumps({
            "name": "Bar_TournamentProgress",
            "singleVisual": {
                "visualType": "clusteredColumnChart",
                "projections": {
                    "Category": [{"queryRef": "dim_matches.Stage_Normalized"}],
                    "Y": [{"queryRef": "fact_match_summaries.Selected Team Matches Completed"}]
                },
                "objects": {
                    "general": [{"properties": {"title": {"expr": {"Literal": {"Value": "'Tournament Progress by Stage (Matches Completed)'"}}}}}]
                }
            }
        })
    },
    # Visual 11: Team Win Rate Heatmap Matrix (pivotTable)
    {
        "x": 415, "y": 158, "z": 110, "width": 440, "height": 255,
        "config": json.dumps({
            "name": "Matrix_TeamWinRate",
            "singleVisual": {
                "visualType": "pivotTable",
                "projections": {
                    "Rows": [{"queryRef": "dim_teams.team_name", "active": True}],
                    "Columns": [{"queryRef": "dim_matches.Stage_Normalized", "active": True}],
                    "Values": [{"queryRef": "fact_match_summaries.Team Win Pct"}]
                },
                "objects": {
                    "general": [{"properties": {"title": {"expr": {"Literal": {"Value": "'Team Win Rate % by Stage (≥1 Win)'"}}}}}],
                    "conditionalFormatting": [{"properties": {"rules": [{"value": "100%", "color": "#2E7D32"}, {"value": "50%", "color": "#FFFFFF"}, {"value": "0%", "color": "#D32F2F"}]}}]
                }
            }
        })
    },
    # Visual 12: Venue Performance Bar Chart (clusteredBarChart)
    {
        "x": 870, "y": 158, "z": 120, "width": 390, "height": 255,
        "config": json.dumps({
            "name": "Bar_VenuePerformance",
            "singleVisual": {
                "visualType": "clusteredBarChart",
                "projections": {
                    "Category": [{"queryRef": "dim_venues.venue_name"}],
                    "Y": [{"queryRef": "fact_match_summaries.Venue Avg First Innings Score"}]
                },
                "objects": {
                    "general": [{"properties": {"title": {"expr": {"Literal": {"Value": "'Venue Scoring Pace (Avg 1st Innings Runs)'"}}}}}]
                }
            }
        })
    },
    # Visual 13: Top 5 Run Scorers Table (tableEx)
    {
        "x": 20, "y": 420, "z": 130, "width": 300, "height": 290,
        "config": json.dumps({
            "name": "Table_TopRunScorers",
            "singleVisual": {
                "visualType": "tableEx",
                "projections": {
                    "Values": [
                        {"queryRef": "fact_batting_scorecards.player_name"},
                        {"queryRef": "fact_batting_scorecards.team"},
                        {"queryRef": "fact_batting_scorecards.Player Total Runs"},
                        {"queryRef": "fact_batting_scorecards.Player Strike Rate"}
                    ]
                },
                "objects": {
                    "general": [{"properties": {"title": {"expr": {"Literal": {"Value": "'Top 5 Run Scorers'"}}}}}]
                },
                "sortDefinition": {
                    "sort": [{"field": {"queryRef": "fact_batting_scorecards.Player Total Runs"}, "direction": "Descending"}]
                }
            }
        })
    },
    # Visual 14: Top 5 Wicket Takers Table (tableEx)
    {
        "x": 330, "y": 420, "z": 140, "width": 300, "height": 290,
        "config": json.dumps({
            "name": "Table_TopWicketTakers",
            "singleVisual": {
                "visualType": "tableEx",
                "projections": {
                    "Values": [
                        {"queryRef": "fact_bowling_scorecards.player_name"},
                        {"queryRef": "fact_bowling_scorecards.team"},
                        {"queryRef": "fact_bowling_scorecards.Player Total Wickets"},
                        {"queryRef": "fact_bowling_scorecards.Player Economy Rate"}
                    ]
                },
                "objects": {
                    "general": [{"properties": {"title": {"expr": {"Literal": {"Value": "'Top 5 Wicket Takers'"}}}}}]
                },
                "sortDefinition": {
                    "sort": [{"field": {"queryRef": "fact_bowling_scorecards.Player Total Wickets"}, "direction": "Descending"}]
                }
            }
        })
    },
    # Visual 15: Highest Strike Rate Table (tableEx)
    {
        "x": 640, "y": 420, "z": 150, "width": 300, "height": 290,
        "config": json.dumps({
            "name": "Table_HighestStrikeRate",
            "singleVisual": {
                "visualType": "tableEx",
                "projections": {
                    "Values": [
                        {"queryRef": "fact_batting_scorecards.player_name"},
                        {"queryRef": "fact_batting_scorecards.team"},
                        {"queryRef": "fact_batting_scorecards.Player Strike Rate (Min 100 Runs)"},
                        {"queryRef": "fact_batting_scorecards.Player Total Runs"}
                    ]
                },
                "objects": {
                    "general": [{"properties": {"title": {"expr": {"Literal": {"Value": "'Highest Strike Rate (min 100 runs)'"}}}}}]
                },
                "sortDefinition": {
                    "sort": [{"field": {"queryRef": "fact_batting_scorecards.Player Strike Rate (Min 100 Runs)"}, "direction": "Descending"}]
                }
            }
        })
    },
    # Visual 16: Best Bowling Economy Table (tableEx)
    {
        "x": 950, "y": 420, "z": 160, "width": 310, "height": 290,
        "config": json.dumps({
            "name": "Table_BestBowlingEconomy",
            "singleVisual": {
                "visualType": "tableEx",
                "projections": {
                    "Values": [
                        {"queryRef": "fact_bowling_scorecards.player_name"},
                        {"queryRef": "fact_bowling_scorecards.team"},
                        {"queryRef": "fact_bowling_scorecards.Player Economy Rate (Min 10 Overs)"},
                        {"queryRef": "fact_bowling_scorecards.Player Total Wickets"}
                    ]
                },
                "objects": {
                    "general": [{"properties": {"title": {"expr": {"Literal": {"Value": "'Best Bowling Economy (min 10 ov)'"}}}}}]
                },
                "sortDefinition": {
                    "sort": [{"field": {"queryRef": "fact_bowling_scorecards.Player Economy Rate (Min 10 Overs)"}, "direction": "Ascending"}]
                }
            }
        })
    }
]

# Check if section 2 already exists
sec_names = [s['name'] for s in rep['sections']]
if "ReportSection_Page3_ExecutiveOverview" in sec_names:
    for idx, s in enumerate(rep['sections']):
        if s['name'] == "ReportSection_Page3_ExecutiveOverview":
            rep['sections'][idx]['visualContainers'] = page3_containers
            print("Replaced existing ReportSection_Page3_ExecutiveOverview visual containers!")
else:
    new_section = {
        "id": len(rep['sections']),
        "name": "ReportSection_Page3_ExecutiveOverview",
        "displayName": "Executive Overview",
        "filters": "[]",
        "ordinal": len(rep['sections']),
        "visualContainers": page3_containers,
        "width": 1280.0,
        "height": 720.0
    }
    rep['sections'].append(new_section)
    print("Appended new ReportSection_Page3_ExecutiveOverview!")

with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(rep, f, indent=2, ensure_ascii=False)
print("Updated report.json successfully!")
