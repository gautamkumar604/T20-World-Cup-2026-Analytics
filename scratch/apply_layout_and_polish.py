import json
import shutil

REPORT_PATH = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
BIM_PATH = 'power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim'

with open(REPORT_PATH, 'r', encoding='utf-8') as f:
    report = json.load(f)

with open(BIM_PATH, 'r', encoding='utf-8') as f:
    bim = json.load(f)

# Helper function to generate prototypeQuery
def make_prototype_query(from_entities, select_items, order_by=None, take=None):
    from_clause = [{"Name": alias, "Entity": entity, "Type": 0} for alias, entity in from_entities]
    select_clause = []
    for alias, entity, prop, is_measure in select_items:
        key = "Measure" if is_measure else "Column"
        item = {
            key: {
                "Expression": {"SourceRef": {"Source": alias}},
                "Property": prop
            },
            "Name": f"{entity}.{prop}",
            "NativeReferenceName": prop
        }
        select_clause.append(item)
    
    pq = {
        "Version": 2,
        "From": from_clause,
        "Select": select_clause
    }
    if order_by:
        pq["OrderBy"] = order_by
    if take is not None:
        pq["Take"] = take
    return pq

# =========================================================================
# TASK 1: Ensure DAX Measure formatString in model.bim
# =========================================================================
for t in bim['model']['tables']:
    for m in t.get('measures', []):
        if m['name'] == 'Total Tournament Runs':
            m['formatString'] = '#,##0'
            print(f"Verified {m['name']} formatString = '#,##0' in model.bim")

with open(BIM_PATH, 'w', encoding='utf-8') as f:
    json.dump(bim, f, indent=2, ensure_ascii=False)

# =========================================================================
# TASK 2: Page 1 Layout & Overlap Fix (Tournament Overview & Standings)
# =========================================================================
s0 = None
for s in report['sections']:
    if s.get('name') == 'ReportSection_Page1_Overview':
        s0 = s
        break

if not s0:
    raise ValueError("ReportSection_Page1_Overview not found")

# Page 1 Visuals coordinate mapping
# Header & Slicers at y=10
# Cards at y=78
# Data Visuals at y=158
p1_coords = {
    'HeaderBanner': {'x': 20, 'y': 10, 'w': 550, 'h': 60, 'z': 10},
    'Slicer_Stage': {'x': 585, 'y': 10, 'w': 215, 'h': 60, 'z': 20},
    'Slicer_Group': {'x': 810, 'y': 10, 'w': 215, 'h': 60, 'z': 21},
    'Slicer_Country': {'x': 1035, 'y': 10, 'w': 225, 'h': 60, 'z': 22},
    'Card_TotalMatches': {'x': 20, 'y': 78, 'w': 180, 'h': 72, 'z': 30},
    'Card_CompletedMatches': {'x': 210, 'y': 78, 'w': 180, 'h': 72, 'z': 31},
    'Card_TotalRuns': {'x': 400, 'y': 78, 'w': 185, 'h': 72, 'z': 32},
    'Card_TotalWickets': {'x': 595, 'y': 78, 'w': 180, 'h': 72, 'z': 33},
    'Card_TournamentRunRate': {'x': 785, 'y': 78, 'w': 185, 'h': 72, 'z': 34},
    'Card_HighestScore': {'x': 980, 'y': 78, 'w': 280, 'h': 72, 'z': 35},
    'Table_GroupStandings': {'x': 20, 'y': 158, 'w': 640, 'h': 548, 'z': 40},
    'Donut_MatchOutcomes': {'x': 680, 'y': 158, 'w': 580, 'h': 265, 'z': 41},
    'Table_VenueAverages': {'x': 680, 'y': 433, 'w': 580, 'h': 273, 'z': 42}
}

for vc in s0['visualContainers']:
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    if vname in p1_coords:
        c = p1_coords[vname]
        vc['x'] = c['x']
        vc['y'] = c['y']
        vc['width'] = c['w']
        vc['height'] = c['h']
        vc['z'] = c['z']
    
    sv = cfg.get('singleVisual', {})
    
    # Polish Card_TotalRuns
    if vname == 'Card_TotalRuns':
        objs = sv.setdefault('objects', {})
        labels = objs.setdefault('labels', [{}])
        labels[0].setdefault('properties', {})['displayUnits'] = {'expr': {'Literal': {'Value': '1D'}}}
        labels[0]['properties']['fontSize'] = {'expr': {'Literal': {'Value': '18D'}}}

    # Polish Card_HighestScore - ensure font size fits without truncation
    elif vname == 'Card_HighestScore':
        objs = sv.setdefault('objects', {})
        labels = objs.setdefault('labels', [{}])
        labels[0].setdefault('properties', {})['fontSize'] = {'expr': {'Literal': {'Value': '12D'}}}
        labels[0]['properties']['labelTitle'] = 'Highest Match Total'

    # Slicers on Page 1: set dropdown mode
    elif vname in ('Slicer_Stage', 'Slicer_Group', 'Slicer_Country'):
        objs = sv.setdefault('objects', {})
        data = objs.setdefault('data', [{}])
        data[0].setdefault('properties', {})['mode'] = {'expr': {'Literal': {'Value': "'Dropdown'"}}}
        sel = objs.setdefault('selection', [{}])
        sel[0].setdefault('properties', {})['selectAllCheckbox'] = {'expr': {'Literal': {'Value': 'true'}}}

    vc['config'] = json.dumps(cfg)

print("TASK 2 (Page 1) complete: Slicers moved to header bar, layout updated, 0 overlap.")

# =========================================================================
# TASK 2 & 3: Page 3 Layout, Card width & Top 5 Filters (Executive Overview)
# =========================================================================
s2 = None
for s in report['sections']:
    if s.get('name') == 'ReportSection_Page3_ExecutiveOverview':
        s2 = s
        break

if not s2:
    raise ValueError("ReportSection_Page3_ExecutiveOverview not found")

p3_coords = {
    'HeaderBanner_Executive': {'x': 20, 'y': 10, 'w': 650, 'h': 60, 'z': 10},
    'Slicer_Stage_Exec': {'x': 685, 'y': 10, 'w': 275, 'h': 60, 'z': 20},
    'Slicer_Team_Exec': {'x': 975, 'y': 10, 'w': 285, 'h': 60, 'z': 21},
    'Card_Exec_TotalMatches': {'x': 20, 'y': 78, 'w': 175, 'h': 72, 'z': 30},
    'Card_Exec_CompletedMatches': {'x': 205, 'y': 78, 'w': 175, 'h': 72, 'z': 31},
    'Card_Exec_TotalRuns': {'x': 390, 'y': 78, 'w': 180, 'h': 72, 'z': 32},
    'Card_Exec_TotalWickets': {'x': 580, 'y': 78, 'w': 175, 'h': 72, 'z': 33},
    'Card_Exec_HighestScore': {'x': 765, 'y': 78, 'w': 245, 'h': 72, 'z': 34},
    'Card_Exec_LowestScore': {'x': 1020, 'y': 78, 'w': 240, 'h': 72, 'z': 35},
    'Bar_TournamentProgress': {'x': 20, 'y': 158, 'w': 380, 'h': 205, 'z': 40},
    'Matrix_TeamWinRate': {'x': 415, 'y': 158, 'w': 440, 'h': 205, 'z': 41},
    'Bar_VenuePerformance': {'x': 870, 'y': 158, 'w': 390, 'h': 205, 'z': 42},
    'Table_TopRunScorers': {'x': 20, 'y': 372, 'w': 300, 'h': 335, 'z': 50},
    'Table_TopWicketTakers': {'x': 330, 'y': 372, 'w': 300, 'h': 335, 'z': 51},
    'Table_HighestStrikeRate': {'x': 640, 'y': 372, 'w': 300, 'h': 335, 'z': 52},
    'Table_BestBowlingEconomy': {'x': 950, 'y': 372, 'w': 310, 'h': 335, 'z': 53}
}

# Top 5 Filter Definitions
top5_filters = {
    'Table_TopRunScorers': {
        "name": "FilterTop5RunScorers",
        "type": "TopN",
        "howCreated": 0,
        "expression": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": "fact_batting_scorecards"}},
                "Property": "player_name"
            }
        },
        "operator": "Top",
        "itemCount": 5,
        "orderBy": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": "fact_batting_scorecards"}},
                "Property": "Player Total Runs"
            }
        }
    },
    'Table_TopWicketTakers': {
        "name": "FilterTop5WicketTakers",
        "type": "TopN",
        "howCreated": 0,
        "expression": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": "fact_bowling_scorecards"}},
                "Property": "player_name"
            }
        },
        "operator": "Top",
        "itemCount": 5,
        "orderBy": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": "fact_bowling_scorecards"}},
                "Property": "Player Total Wickets"
            }
        }
    },
    'Table_HighestStrikeRate': {
        "name": "FilterTop5StrikeRate",
        "type": "TopN",
        "howCreated": 0,
        "expression": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": "fact_batting_scorecards"}},
                "Property": "player_name"
            }
        },
        "operator": "Top",
        "itemCount": 5,
        "orderBy": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": "fact_batting_scorecards"}},
                "Property": "Player Strike Rate (Min 100 Runs)"
            }
        }
    },
    'Table_BestBowlingEconomy': {
        "name": "FilterTop5EconomyRate",
        "type": "TopN",
        "howCreated": 0,
        "expression": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": "fact_bowling_scorecards"}},
                "Property": "player_name"
            }
        },
        "operator": "Bottom",
        "itemCount": 5,
        "orderBy": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": "fact_bowling_scorecards"}},
                "Property": "Player Economy Rate (Min 10 Overs)"
            }
        }
    }
}

for vc in s2['visualContainers']:
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    if vname in p3_coords:
        c = p3_coords[vname]
        vc['x'] = c['x']
        vc['y'] = c['y']
        vc['width'] = c['w']
        vc['height'] = c['h']
        vc['z'] = c['z']
    
    sv = cfg.get('singleVisual', {})

    # Card_Exec_TotalRuns displayUnits
    if vname == 'Card_Exec_TotalRuns':
        objs = sv.setdefault('objects', {})
        labels = objs.setdefault('labels', [{}])
        labels[0].setdefault('properties', {})['displayUnits'] = {'expr': {'Literal': {'Value': '1D'}}}
        labels[0]['properties']['fontSize'] = {'expr': {'Literal': {'Value': '18D'}}}

    # Card_Exec_HighestScore font size
    elif vname == 'Card_Exec_HighestScore':
        objs = sv.setdefault('objects', {})
        labels = objs.setdefault('labels', [{}])
        labels[0].setdefault('properties', {})['fontSize'] = {'expr': {'Literal': {'Value': '12D'}}}

    # Card_Exec_LowestScore font size
    elif vname == 'Card_Exec_LowestScore':
        objs = sv.setdefault('objects', {})
        labels = objs.setdefault('labels', [{}])
        labels[0].setdefault('properties', {})['fontSize'] = {'expr': {'Literal': {'Value': '12D'}}}

    # Slicers dropdown mode
    elif vname in ('Slicer_Stage_Exec', 'Slicer_Team_Exec'):
        objs = sv.setdefault('objects', {})
        data = objs.setdefault('data', [{}])
        data[0].setdefault('properties', {})['mode'] = {'expr': {'Literal': {'Value': "'Dropdown'"}}}
        sel = objs.setdefault('selection', [{}])
        sel[0].setdefault('properties', {})['selectAllCheckbox'] = {'expr': {'Literal': {'Value': 'true'}}}

    # Table Top 5 filters
    if vname in top5_filters:
        filt = top5_filters[vname]
        vc['filters'] = json.dumps([filt])
        cfg['filterConfig'] = [filt]
        cfg['filters'] = [filt]
        sv['prototypeQuery']['Take'] = 5

    vc['config'] = json.dumps(cfg)

print("TASK 2 & 3 (Page 3) complete: Table height increased to 335, Top 5 filters injected.")

# =========================================================================
# TASK 4: Page 2 (Standings) Matrix Stepped Layout & Conditional Formatting
# =========================================================================
s1 = None
for s in report['sections']:
    if s.get('name') == 'ReportSection_Page2_Standings':
        s1 = s
        break

if not s1:
    raise ValueError("ReportSection_Page2_Standings not found")

for vc in s1['visualContainers']:
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    sv = cfg.get('singleVisual', {})

    if vname == 'Matrix_TournamentStandings':
        objs = sv.setdefault('objects', {})
        # 1. Stepped layout
        row_headers = objs.setdefault('rowHeaders', [{}])
        row_headers[0].setdefault('properties', {})['stepped'] = {'expr': {'Literal': {'Value': 'true'}}}
        row_headers[0]['properties']['steppedLayoutIndentation'] = {'expr': {'Literal': {'Value': '15D'}}}

        # 2. Conditional formatting rules for Qualified and Eliminated
        objs['conditionalFormatting'] = [
            {
                "properties": {
                    "rules": [
                        {"value": "Qualified", "color": "#D4EDDA"},
                        {"value": "Eliminated", "color": "#E9ECEF"}
                    ]
                }
            },
            {
                "selector": {
                    "data": [
                        {
                            "dataViewWildcard": {
                                "matchingOption": 1
                            }
                        }
                    ]
                },
                "properties": {
                    "backColor": {
                        "rules": {
                            "input": {
                                "Column": {
                                    "Expression": {
                                        "SourceRef": {
                                            "Entity": "view_tournament_standings"
                                        }
                                    },
                                    "Property": "qualification_status"
                                }
                            },
                            "rules": [
                                {
                                    "value": "Qualified",
                                    "color": {
                                        "solid": {
                                            "color": "#D4EDDA"
                                        }
                                    }
                                },
                                {
                                    "value": "Eliminated",
                                    "color": {
                                        "solid": {
                                            "color": "#E9ECEF"
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        ]

    elif vname == 'Slicer_Group_Standings':
        objs = sv.setdefault('objects', {})
        data = objs.setdefault('data', [{}])
        data[0].setdefault('properties', {})['mode'] = {'expr': {'Literal': {'Value': "'Dropdown'"}}}
        sel = objs.setdefault('selection', [{}])
        sel[0].setdefault('properties', {})['selectAllCheckbox'] = {'expr': {'Literal': {'Value': 'true'}}}
        sel[0]['properties']['singleSelect'] = {'expr': {'Literal': {'Value': 'false'}}}

    vc['config'] = json.dumps(cfg)

print("TASK 4 (Page 2) complete: Matrix Stepped Layout, conditional formatting & hierarchical slicer formatted.")

# Save modified report.json
with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("SUCCESS: report.json and model.bim successfully updated!")
