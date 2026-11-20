import json
import os

page_name = "ReportSection_Page4_TacticalAnalysis"
base_dir = f"power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/{page_name}"
visuals_dir = f"{base_dir}/visuals"

os.makedirs(visuals_dir, exist_ok=True)

# 1. Update pages.json
pages_json_path = "power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/pages.json"
with open(pages_json_path, 'r', encoding='utf-8') as f:
    pages_meta = json.load(f)

if page_name not in pages_meta.get("pageOrder", []):
    pages_meta["pageOrder"].append(page_name)
    with open(pages_json_path, 'w', encoding='utf-8') as f:
        json.dump(pages_meta, f, indent=2)
    print(f"Added {page_name} to pages.json")

# 2. Create page.json
page_json = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
    "name": page_name,
    "displayName": "Tactical Analysis",
    "displayOption": "DeprecatedDynamic"
}
with open(f"{base_dir}/page.json", 'w', encoding='utf-8') as f:
    json.dump(page_json, f, indent=2)
print("Created page.json")

# Helper function to save a visual
def save_visual(vis_name, vis_dict):
    v_folder = f"{visuals_dir}/{vis_name}"
    os.makedirs(v_folder, exist_ok=True)
    with open(f"{v_folder}/visual.json", 'w', encoding='utf-8') as f:
        json.dump(vis_dict, f, indent=2)
    print(f"Created visual: {vis_name}")

# --- VISUALS ---

# 1. Header Banner
header_banner = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json",
    "name": "HeaderBanner_Tactical",
    "position": {"x": 20, "y": 10, "z": 0, "height": 60, "width": 650},
    "visual": {
        "visualType": "textbox",
        "objects": {
            "general": [{
                "properties": {
                    "paragraphs": [{
                        "textRuns": [
                            {
                                "value": "ICC Men's T20 World Cup 2026 — Tactical Analysis\n",
                                "textStyle": {
                                    "fontSize": "17pt",
                                    "fontWeight": "bold",
                                    "color": "#1A365D"
                                }
                            },
                            {
                                "value": "Phase Dynamics (Powerplay, Middle, Death), Toss Match Impact & Phase Specialists",
                                "textStyle": {
                                    "fontSize": "9pt",
                                    "color": "#4A5568"
                                }
                            }
                        ]
                    }]
                }
            }]
        }
    }
}
save_visual("HeaderBanner_Tactical", header_banner)

# 2. Slicer Stage
slicer_stage = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json",
    "name": "Slicer_Stage_Tactical",
    "position": {"x": 685, "y": 10, "z": 1000, "height": 60, "width": 275},
    "visual": {
        "visualType": "slicer",
        "query": {
            "queryState": {
                "Values": {
                    "projections": [{
                        "field": {
                            "Column": {
                                "Expression": {"SourceRef": {"Entity": "dim_matches"}},
                                "Property": "Stage_Normalized"
                            }
                        },
                        "queryRef": "dim_matches.Stage_Normalized",
                        "nativeQueryRef": "Stage_Normalized",
                        "active": True
                    }]
                }
            }
        },
        "objects": {
            "general": [{"properties": {"orientation": {"expr": {"Literal": {"Value": "'horizontal'"}}}}}],
            "header": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}],
            "data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Dropdown'"}}}}}],
            "selection": [{"properties": {}}]
        }
    }
}
save_visual("Slicer_Stage_Tactical", slicer_stage)

# 3. Slicer Team
slicer_team = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json",
    "name": "Slicer_Team_Tactical",
    "position": {"x": 975, "y": 10, "z": 2000, "height": 60, "width": 285},
    "visual": {
        "visualType": "slicer",
        "query": {
            "queryState": {
                "Values": {
                    "projections": [{
                        "field": {
                            "Column": {
                                "Expression": {"SourceRef": {"Entity": "dim_teams"}},
                                "Property": "team_name"
                            }
                        },
                        "queryRef": "dim_teams.team_name",
                        "nativeQueryRef": "team_name",
                        "active": True
                    }]
                }
            }
        },
        "objects": {
            "general": [{"properties": {"orientation": {"expr": {"Literal": {"Value": "'horizontal'"}}}}}],
            "header": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}],
            "data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Dropdown'"}}}}}],
            "selection": [{"properties": {}}]
        }
    }
}
save_visual("Slicer_Team_Tactical", slicer_team)

# Helper for KPI cards
def make_card(name, x, y, w, h, z, measure_prop, title_text, is_int=False):
    props = {
        "fontSize": {"expr": {"Literal": {"Value": "18D"}}},
        "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#1A365D'"}}}}}
    }
    if is_int:
        props["displayUnits"] = {"expr": {"Literal": {"Value": "1D"}}}
    
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": z, "height": h, "width": w},
        "visual": {
            "visualType": "card",
            "query": {
                "queryState": {
                    "Values": {
                        "projections": [{
                            "field": {
                                "Measure": {
                                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                    "Property": measure_prop
                                }
                            },
                            "queryRef": f"fact_deliveries.{measure_prop}",
                            "nativeQueryRef": measure_prop
                        }]
                    }
                }
            },
            "objects": {
                "labels": [{"properties": props}],
                "categoryLabels": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}],
                "title": [{
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{title_text}'"}}}
                    }
                }]
            }
        }
    }

# 6 KPI Cards
cards_meta = [
    ("Card_PP_RunRate", 20, 78, 195, 75, 3000, "Powerplay Run Rate", "Powerplay Run Rate", False),
    ("Card_PP_Wickets", 230, 78, 195, 75, 4000, "Powerplay Wickets", "Powerplay Wickets", True),
    ("Card_Middle_RunRate", 440, 78, 195, 75, 5000, "Middle Overs Run Rate", "Middle Overs Run Rate", False),
    ("Card_Middle_Wickets", 650, 78, 195, 75, 6000, "Middle Overs Wickets", "Middle Overs Wickets", True),
    ("Card_Death_RunRate", 860, 78, 195, 75, 7000, "Death Overs Run Rate", "Death Overs Run Rate", False),
    ("Card_Death_Wickets", 1070, 78, 190, 75, 8000, "Death Overs Wickets", "Death Overs Wickets", True)
]
for c_name, cx, cy, cw, ch, cz, m_prop, t_text, is_int in cards_meta:
    save_visual(c_name, make_card(c_name, cx, cy, cw, ch, cz, m_prop, t_text, is_int))

# 4. Toss Impact (100% Stacked Bar Chart)
bar_toss_impact = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json",
    "name": "Bar_TossImpact",
    "position": {"x": 20, "y": 162, "z": 9000, "height": 248, "width": 605},
    "visual": {
        "visualType": "hundredPercentStackedBarChart",
        "query": {
            "queryState": {
                "Category": {
                    "projections": [{
                        "field": {
                            "Column": {
                                "Expression": {"SourceRef": {"Entity": "dim_matches"}},
                                "Property": "Toss Decision Label"
                            }
                        },
                        "queryRef": "dim_matches.Toss Decision Label",
                        "nativeQueryRef": "Toss Decision Label",
                        "active": True
                    }]
                },
                "Series": {
                    "projections": [{
                        "field": {
                            "Column": {
                                "Expression": {"SourceRef": {"Entity": "dim_matches"}},
                                "Property": "Toss Match Result"
                            }
                        },
                        "queryRef": "dim_matches.Toss Match Result",
                        "nativeQueryRef": "Toss Match Result"
                    }]
                },
                "Y": {
                    "projections": [{
                        "field": {
                            "Measure": {
                                "Expression": {"SourceRef": {"Entity": "dim_matches"}},
                                "Property": "Toss Completed Matches"
                            }
                        },
                        "queryRef": "dim_matches.Toss Completed Matches",
                        "nativeQueryRef": "Toss Completed Matches"
                    }]
                }
            }
        },
        "objects": {
            "title": [{
                "properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "text": {"expr": {"Literal": {"Value": "'Toss Impact: Win % When Batting First vs Chasing'"}}}
                }
            }],
            "legend": [{
                "properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "position": {"expr": {"Literal": {"Value": "'Top'"}}}
                }
            }]
        }
    }
}
save_visual("Bar_TossImpact", bar_toss_impact)

# 5. Boundary Distribution by Phase (Donut Chart)
donut_boundaries = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json",
    "name": "Donut_BoundaryDistribution",
    "position": {"x": 645, "y": 162, "z": 10000, "height": 248, "width": 615},
    "visual": {
        "visualType": "donutChart",
        "query": {
            "queryState": {
                "Category": {
                    "projections": [{
                        "field": {
                            "Column": {
                                "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                "Property": "phase"
                            }
                        },
                        "queryRef": "fact_deliveries.phase",
                        "nativeQueryRef": "phase",
                        "active": True
                    }]
                },
                "Y": {
                    "projections": [{
                        "field": {
                            "Measure": {
                                "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                "Property": "Phase Total Boundaries"
                            }
                        },
                        "queryRef": "fact_deliveries.Phase Total Boundaries",
                        "nativeQueryRef": "Phase Total Boundaries"
                    }]
                },
                "Tooltips": {
                    "projections": [
                        {
                            "field": {
                                "Measure": {
                                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                    "Property": "Phase Total Fours"
                                }
                            },
                            "queryRef": "fact_deliveries.Phase Total Fours",
                            "nativeQueryRef": "Phase Total Fours"
                        },
                        {
                            "field": {
                                "Measure": {
                                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                    "Property": "Phase Total Sixes"
                                }
                            },
                            "queryRef": "fact_deliveries.Phase Total Sixes",
                            "nativeQueryRef": "Phase Total Sixes"
                        }
                    ]
                }
            }
        },
        "objects": {
            "title": [{
                "properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "text": {"expr": {"Literal": {"Value": "'Boundary Distribution by Phase (Fours & Sixes)'"}}}
                }
            }],
            "legend": [{
                "properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "position": {"expr": {"Literal": {"Value": "'Right'"}}}
                }
            }]
        }
    }
}
save_visual("Donut_BoundaryDistribution", donut_boundaries)

# 6. Table A: Powerplay Specialists (Top 5)
table_powerplay = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json",
    "name": "Table_PowerplaySpecialists",
    "position": {"x": 20, "y": 420, "z": 11000, "height": 285, "width": 605},
    "visual": {
        "visualType": "tableEx",
        "query": {
            "queryState": {
                "Values": {
                    "projections": [
                        {
                            "field": {
                                "Column": {
                                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                    "Property": "bowler"
                                }
                            },
                            "queryRef": "fact_deliveries.bowler",
                            "nativeQueryRef": "bowler"
                        },
                        {
                            "field": {
                                "Column": {
                                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                    "Property": "bowling_team"
                                }
                            },
                            "queryRef": "fact_deliveries.bowling_team",
                            "nativeQueryRef": "bowling_team"
                        },
                        {
                            "field": {
                                "Measure": {
                                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                    "Property": "Bowler Powerplay Wickets"
                                }
                            },
                            "queryRef": "fact_deliveries.Bowler Powerplay Wickets",
                            "nativeQueryRef": "Bowler Powerplay Wickets"
                        },
                        {
                            "field": {
                                "Measure": {
                                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                    "Property": "Bowler Powerplay Economy"
                                }
                            },
                            "queryRef": "fact_deliveries.Bowler Powerplay Economy",
                            "nativeQueryRef": "Bowler Powerplay Economy"
                        },
                        {
                            "field": {
                                "Measure": {
                                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                    "Property": "Bowler Powerplay Overs"
                                }
                            },
                            "queryRef": "fact_deliveries.Bowler Powerplay Overs",
                            "nativeQueryRef": "Bowler Powerplay Overs"
                        }
                    ]
                }
            },
            "sortDefinition": {
                "sort": [{
                    "field": {
                        "Measure": {
                            "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                            "Property": "Bowler Powerplay Wickets"
                        }
                    },
                    "direction": "Descending"
                }]
            }
        },
        "objects": {
            "title": [{
                "properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "text": {"expr": {"Literal": {"Value": "'Powerplay Specialists (Top 5 Bowlers by Wickets in Overs 1-6)'"}}}
                }
            }]
        }
    },
    "filterConfig": {
        "filters": [{
            "name": "FilterTop5_PowerplaySpecialists",
            "field": {
                "Column": {
                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                    "Property": "bowler"
                }
            },
            "type": "TopN",
            "howCreated": "User"
        }]
    }
}
save_visual("Table_PowerplaySpecialists", table_powerplay)

# 7. Table B: Death Specialists (Top 5)
table_death = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json",
    "name": "Table_DeathSpecialists",
    "position": {"x": 645, "y": 420, "z": 12000, "height": 285, "width": 615},
    "visual": {
        "visualType": "tableEx",
        "query": {
            "queryState": {
                "Values": {
                    "projections": [
                        {
                            "field": {
                                "Column": {
                                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                    "Property": "bowler"
                                }
                            },
                            "queryRef": "fact_deliveries.bowler",
                            "nativeQueryRef": "bowler"
                        },
                        {
                            "field": {
                                "Column": {
                                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                    "Property": "bowling_team"
                                }
                            },
                            "queryRef": "fact_deliveries.bowling_team",
                            "nativeQueryRef": "bowling_team"
                        },
                        {
                            "field": {
                                "Measure": {
                                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                    "Property": "Bowler Death Overs Economy (Min 10 Balls)"
                                }
                            },
                            "queryRef": "fact_deliveries.Bowler Death Overs Economy (Min 10 Balls)",
                            "nativeQueryRef": "Bowler Death Overs Economy (Min 10 Balls)"
                        },
                        {
                            "field": {
                                "Measure": {
                                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                    "Property": "Bowler Death Overs Wickets"
                                }
                            },
                            "queryRef": "fact_deliveries.Bowler Death Overs Wickets",
                            "nativeQueryRef": "Bowler Death Overs Wickets"
                        },
                        {
                            "field": {
                                "Measure": {
                                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                                    "Property": "Bowler Death Overs Balls"
                                }
                            },
                            "queryRef": "fact_deliveries.Bowler Death Overs Balls",
                            "nativeQueryRef": "Bowler Death Overs Balls"
                        }
                    ]
                }
            },
            "sortDefinition": {
                "sort": [{
                    "field": {
                        "Measure": {
                            "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                            "Property": "Bowler Death Overs Economy (Min 10 Balls)"
                        }
                    },
                    "direction": "Ascending"
                }]
            }
        },
        "objects": {
            "title": [{
                "properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "text": {"expr": {"Literal": {"Value": "'Death Overs Specialists (Top 5 by Economy, Overs 16-20, Min 10 Balls)'"}}}
                }
            }]
        }
    },
    "filterConfig": {
        "filters": [{
            "name": "FilterTop5_DeathSpecialists",
            "field": {
                "Column": {
                    "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
                    "Property": "bowler"
                }
            },
            "type": "TopN",
            "howCreated": "User"
        }]
    }
}
save_visual("Table_DeathSpecialists", table_death)

print("\nAll visuals created successfully for Page 4 (Tactical Analysis)!")
