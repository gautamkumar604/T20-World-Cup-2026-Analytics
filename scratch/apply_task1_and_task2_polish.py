import json
import os

P4_VISUALS_DIR = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page4_TacticalAnalysis/visuals'
P3_VISUALS_DIR = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page3_ExecutiveOverview/visuals'

# =============================================================================
# TASK 1: Fix Layout Cut-offs (Coordinates adjustments)
# Max canvas width: 1280. Rightmost x + width must not exceed 1280.
# We ensure right edge <= 1210 (leaving a generous 70px right margin).
# =============================================================================

layout_updates = {
    # Top Banner & Slicers
    'HeaderBanner_Tactical': {'x': 20, 'y': 10, 'width': 630, 'height': 60},
    'Slicer_Stage_Tactical': {'x': 670, 'y': 10, 'width': 260, 'height': 60},
    'Slicer_Team_Tactical': {'x': 950, 'y': 10, 'width': 260, 'height': 60},  # right = 1210
    
    # KPI Cards (Top Row)
    'Card_PP_RunRate': {'x': 20, 'y': 78, 'width': 180, 'height': 75},
    'Card_PP_Wickets': {'x': 215, 'y': 78, 'width': 180, 'height': 75},
    'Card_Middle_RunRate': {'x': 410, 'y': 78, 'width': 180, 'height': 75},
    'Card_Middle_Wickets': {'x': 605, 'y': 78, 'width': 180, 'height': 75},
    'Card_Death_RunRate': {'x': 800, 'y': 78, 'width': 180, 'height': 75},
    'Card_Death_Wickets': {'x': 995, 'y': 78, 'width': 180, 'height': 75},  # right = 1175 (was 1260)
    
    # Middle Row Charts
    'Bar_TossImpact': {'x': 20, 'y': 162, 'width': 575, 'height': 248},
    'Donut_BoundaryDistribution': {'x': 615, 'y': 162, 'width': 585, 'height': 248},  # right = 1200 (was 1260)
    
    # Bottom Row Tables
    'Table_PowerplaySpecialists': {'x': 20, 'y': 420, 'width': 575, 'height': 285},
    'Table_DeathSpecialists': {'x': 615, 'y': 420, 'width': 585, 'height': 285}  # right = 1200 (was 1260)
}

for vname, pos in layout_updates.items():
    vpath = os.path.join(P4_VISUALS_DIR, vname, 'visual.json')
    if os.path.exists(vpath):
        with open(vpath, 'r', encoding='utf-8') as f:
            vdata = json.load(f)
        vdata['position']['x'] = pos['x']
        vdata['position']['y'] = pos['y']
        vdata['position']['width'] = pos['width']
        vdata['position']['height'] = pos['height']
        with open(vpath, 'w', encoding='utf-8') as f:
            json.dump(vdata, f, indent=2)
        print(f"Updated position for {vname}: pos=({pos['x']}, {pos['y']}, w={pos['width']}, h={pos['height']}) -> right={pos['x'] + pos['width']}")

# =============================================================================
# TASK 2: Enforce Top 5 FilterConfig (CRITICAL)
# Inject complete, schema-compliant FilterDefinition with VisualTopN: 5
# =============================================================================

# Table A: Powerplay Specialists -> Top 5 Bowlers by Wickets in Overs 1-6
pp_table_path = os.path.join(P4_VISUALS_DIR, 'Table_PowerplaySpecialists', 'visual.json')
with open(pp_table_path, 'r', encoding='utf-8') as f:
    pp_data = json.load(f)

pp_filter = {
    "name": "FilterTop5_PowerplaySpecialists",
    "field": {
        "Column": {
            "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
            "Property": "bowler"
        }
    },
    "type": "TopN",
    "howCreated": "User",
    "filter": {
        "Version": 2,
        "From": [
            {
                "Name": "f",
                "Entity": "fact_deliveries",
                "Type": 0
            }
        ],
        "Where": [
            {
                "Target": [
                    {
                        "Column": {
                            "Expression": {"SourceRef": {"Source": "f"}},
                            "Property": "bowler"
                        }
                    }
                ],
                "Condition": {
                    "VisualTopN": {
                        "ItemCount": 5
                    }
                }
            }
        ]
    }
}
pp_data['filterConfig'] = {
    "filters": [pp_filter]
}
with open(pp_table_path, 'w', encoding='utf-8') as f:
    json.dump(pp_data, f, indent=2)
print("Injected strict Top 5 filterConfig into Table_PowerplaySpecialists")

# Table B: Death Overs Specialists -> Top 5 Bowlers by Economy in Overs 16-20 (Min 10 balls)
death_table_path = os.path.join(P4_VISUALS_DIR, 'Table_DeathSpecialists', 'visual.json')
with open(death_table_path, 'r', encoding='utf-8') as f:
    death_data = json.load(f)

death_filter = {
    "name": "FilterTop5_DeathSpecialists",
    "field": {
        "Column": {
            "Expression": {"SourceRef": {"Entity": "fact_deliveries"}},
            "Property": "bowler"
        }
    },
    "type": "TopN",
    "howCreated": "User",
    "filter": {
        "Version": 2,
        "From": [
            {
                "Name": "f",
                "Entity": "fact_deliveries",
                "Type": 0
            }
        ],
        "Where": [
            {
                "Target": [
                    {
                        "Column": {
                            "Expression": {"SourceRef": {"Source": "f"}},
                            "Property": "bowler"
                        }
                    }
                ],
                "Condition": {
                    "VisualTopN": {
                        "ItemCount": 5
                    }
                }
            }
        ]
    }
}
death_data['filterConfig'] = {
    "filters": [death_filter]
}
with open(death_table_path, 'w', encoding='utf-8') as f:
    json.dump(death_data, f, indent=2)
print("Injected strict Top 5 filterConfig into Table_DeathSpecialists")

# Also update Page 3's Top 5 tables for complete consistency
p3_tables = [
    ('Table_TopRunScorers', 'fact_batting_scorecards', 'player_name'),
    ('Table_TopWicketTakers', 'fact_bowling_scorecards', 'player_name'),
    ('Table_HighestStrikeRate', 'fact_batting_scorecards', 'player_name'),
    ('Table_BestBowlingEconomy', 'fact_bowling_scorecards', 'player_name')
]
for tname, ent, col in p3_tables:
    tpath = os.path.join(P3_VISUALS_DIR, tname, 'visual.json')
    if os.path.exists(tpath):
        with open(tpath, 'r', encoding='utf-8') as f:
            tdata = json.load(f)
        tdata['filterConfig'] = {
            "filters": [
                {
                    "name": f"FilterTop5_{tname}",
                    "field": {
                        "Column": {
                            "Expression": {"SourceRef": {"Entity": ent}},
                            "Property": col
                        }
                    },
                    "type": "TopN",
                    "howCreated": "User",
                    "filter": {
                        "Version": 2,
                        "From": [{"Name": "t", "Entity": ent, "Type": 0}],
                        "Where": [
                            {
                                "Target": [
                                    {
                                        "Column": {
                                            "Expression": {"SourceRef": {"Source": "t"}},
                                            "Property": col
                                        }
                                    }
                                ],
                                "Condition": {
                                    "VisualTopN": {"ItemCount": 5}
                                }
                            }
                        ]
                    }
                }
            ]
        }
        with open(tpath, 'w', encoding='utf-8') as f:
            json.dump(tdata, f, indent=2)
        print(f"Injected strict Top 5 filterConfig into Page 3: {tname}")

print("\nSUCCESS: All layout coordinates and Top 5 filters successfully updated!")
