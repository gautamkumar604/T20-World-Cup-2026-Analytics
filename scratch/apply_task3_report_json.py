import json

REPORT_PATH = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'

with open(REPORT_PATH, 'r', encoding='utf-8') as f:
    rep = json.load(f)

# Visual 1: Header Banner Textbox
vc_header = {
    "x": 20,
    "y": 15,
    "z": 10,
    "width": 1240,
    "height": 65,
    "config": json.dumps({
        "name": "HeaderBanner_Standings",
        "singleVisual": {
            "visualType": "textbox",
            "objects": {
                "general": [{
                    "properties": {
                        "paragraphs": [{
                            "textRuns": [
                                {
                                    "value": "ICC Men's T20 World Cup 2026 — Official Tournament Standings & Qualification\n",
                                    "textStyle": {
                                        "fontFamily": "Segoe UI Semibold",
                                        "fontSize": "16pt",
                                        "color": "#1A365D"
                                    }
                                },
                                {
                                    "value": "Official Clause 16.10 Net Run Rate | Exact Rational Tie-Breaking Engine | Super 8 Qualification Pathway",
                                    "textStyle": {
                                        "fontFamily": "Segoe UI",
                                        "fontSize": "10pt",
                                        "color": "#4A5568"
                                    }
                                }
                            ]
                        }]
                    }
                }]
            }
        }
    })
}

# Visual 2: Stage Slicer (horizontal buttons)
vc_slicer_stage = {
    "x": 20,
    "y": 88,
    "z": 20,
    "width": 300,
    "height": 65,
    "config": json.dumps({
        "name": "Slicer_Stage_Standings",
        "singleVisual": {
            "visualType": "slicer",
            "projections": {
                "Values": [{"queryRef": "view_tournament_standings.stage_normalized"}]
            },
            "objects": {
                "general": [{
                    "properties": {
                        "orientation": {"expr": {"Literal": {"Value": "'horizontal'"}}}
                    }
                }],
                "header": [{
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "title": {"expr": {"Literal": {"Value": "'Tournament Stage'"}}}
                    }
                }]
            }
        }
    })
}

# Visual 3: Group Slicer (horizontal buttons)
vc_slicer_group = {
    "x": 330,
    "y": 88,
    "z": 30,
    "width": 420,
    "height": 65,
    "config": json.dumps({
        "name": "Slicer_Group_Standings",
        "singleVisual": {
            "visualType": "slicer",
            "projections": {
                "Values": [{"queryRef": "view_tournament_standings.group_name"}]
            },
            "objects": {
                "general": [{
                    "properties": {
                        "orientation": {"expr": {"Literal": {"Value": "'horizontal'"}}}
                    }
                }],
                "header": [{
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "title": {"expr": {"Literal": {"Value": "'Group / Pool'"}}}
                    }
                }]
            }
        }
    })
}

# Visual 4: Card - Active Teams
vc_card_teams = {
    "x": 765,
    "y": 88,
    "z": 40,
    "width": 235,
    "height": 65,
    "config": json.dumps({
        "name": "Card_Standings_TeamsCount",
        "singleVisual": {
            "visualType": "card",
            "projections": {
                "Values": [{"queryRef": "view_tournament_standings.team_name"}]
            },
            "objects": {
                "labels": [{
                    "properties": {
                        "fontSize": {"expr": {"Literal": {"Value": "16D"}}},
                        "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#1A365D'"}}}}}
                    }
                }],
                "categoryLabels": [{
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}}
                    }
                }]
            }
        }
    })
}

# Visual 5: Card - Qualification Certification
vc_card_cert = {
    "x": 1015,
    "y": 88,
    "z": 50,
    "width": 245,
    "height": 65,
    "config": json.dumps({
        "name": "Card_Standings_Certification",
        "singleVisual": {
            "visualType": "card",
            "projections": {
                "Values": [{"queryRef": "view_tournament_standings.resolution_step"}]
            },
            "objects": {
                "labels": [{
                    "properties": {
                        "fontSize": {"expr": {"Literal": {"Value": "12D"}}},
                        "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#2E7D32'"}}}}}
                    }
                }],
                "categoryLabels": [{
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}}
                    }
                }]
            }
        }
    })
}

# Visual 6: Matrix Visual (pivotTable)
vc_matrix_standings = {
    "x": 20,
    "y": 165,
    "z": 60,
    "width": 1240,
    "height": 535,
    "config": json.dumps({
        "name": "Matrix_TournamentStandings",
        "singleVisual": {
            "visualType": "pivotTable",
            "projections": {
                "Rows": [
                    {"queryRef": "view_tournament_standings.stage_normalized", "active": True},
                    {"queryRef": "view_tournament_standings.group_name", "active": True},
                    {"queryRef": "view_tournament_standings.team_name", "active": True}
                ],
                "Values": [
                    {"queryRef": "view_tournament_standings.pool_rank"},
                    {"queryRef": "view_tournament_standings.played"},
                    {"queryRef": "view_tournament_standings.wins"},
                    {"queryRef": "view_tournament_standings.losses"},
                    {"queryRef": "view_tournament_standings.no_result"},
                    {"queryRef": "view_tournament_standings.points"},
                    {"queryRef": "view_tournament_standings.nrr_display"}
                ],
                "Tooltips": [
                    {"queryRef": "view_tournament_standings.resolution_step"},
                    {"queryRef": "view_tournament_standings.qualification_status"}
                ]
            },
            "objects": {
                "general": [{
                    "properties": {
                        "title": {"expr": {"Literal": {"Value": "'Official Pool Standings (Ranked by Points, Rational NRR & Clause 16.10 Tie-Breaks)'"}}}
                    }
                }],
                "columnHeaders": [{
                    "properties": {
                        "fontColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#FFFFFF'"}}}}},
                        "backColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#1A365D'"}}}}},
                        "autoSizeColumnWidth": {"expr": {"Literal": {"Value": "true"}}}
                    }
                }],
                "values": [{
                    "properties": {
                        "backColorSecondary": {"solid": {"color": {"expr": {"Literal": {"Value": "'#F8F9FA'"}}}}}
                    }
                }],
                "conditionalFormatting": [{
                    "properties": {
                        "rules": [
                            {"value": "Qualified", "color": "#D4EDDA"},
                            {"value": "Eliminated", "color": "#E9ECEF"}
                        ]
                    }
                }]
            },
            "sortDefinition": {
                "sort": [
                    {"field": {"queryRef": "view_tournament_standings.points"}, "direction": "Descending"},
                    {"field": {"queryRef": "view_tournament_standings.pool_rank"}, "direction": "Ascending"},
                    {"field": {"queryRef": "view_tournament_standings.team_name"}, "direction": "Ascending"}
                ]
            }
        }
    })
}

# Build Section 2
new_section = {
    "id": 1,
    "name": "ReportSection_Page2_Standings",
    "displayName": "Tournament Standings",
    "filters": [],
    "ordinal": 1,
    "visualContainers": [
        vc_header,
        vc_slicer_stage,
        vc_slicer_group,
        vc_card_teams,
        vc_card_cert,
        vc_matrix_standings
    ],
    "width": 1280.0,
    "height": 720.0
}

# Check if section already exists
existing_names = [s['name'] for s in rep['sections']]
if 'ReportSection_Page2_Standings' in existing_names:
    idx = existing_names.index('ReportSection_Page2_Standings')
    rep['sections'][idx] = new_section
    print("Updated existing ReportSection_Page2_Standings in report.json")
else:
    rep['sections'].append(new_section)
    print("Added ReportSection_Page2_Standings to report.json")

with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    json.dump(rep, f, indent=2)

print(f"Saved report.json. Total sections: {len(rep['sections'])}")
