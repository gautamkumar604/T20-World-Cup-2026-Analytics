import json
import os

BASE_DIR = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages'
BIM_PATH = 'power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim'

# =========================================================================
# TASK 1: Fix "18K" KPI Card Format
# =========================================================================
with open(BIM_PATH, 'r', encoding='utf-8') as f:
    bim = json.load(f)

for t in bim['model']['tables']:
    for m in t.get('measures', []):
        if m['name'] == 'Total Tournament Runs':
            m['formatString'] = '#,##0'
            print("Verified model.bim Total Tournament Runs formatString = '#,##0'")

with open(BIM_PATH, 'w', encoding='utf-8') as f:
    json.dump(bim, f, indent=2, ensure_ascii=False)

# Update Card_Exec_TotalRuns (Page 3)
p3_card_path = os.path.join(BASE_DIR, 'ReportSection_Page3_ExecutiveOverview/visuals/Card_Exec_TotalRuns/visual.json')
with open(p3_card_path, 'r', encoding='utf-8') as f:
    c3 = json.load(f)

c3_objs = c3['visual'].setdefault('objects', {})
c3_labels = c3_objs.setdefault('labels', [{}])
c3_labels[0].setdefault('properties', {})['displayUnits'] = {'expr': {'Literal': {'Value': '1D'}}}
c3_labels[0]['properties']['fontSize'] = {'expr': {'Literal': {'Value': '18D'}}}
c3_labels[0]['properties']['color'] = {'solid': {'color': {'expr': {'Literal': {'Value': "'#1A365D'"}}}}}

with open(p3_card_path, 'w', encoding='utf-8') as f:
    json.dump(c3, f, indent=2, ensure_ascii=False)
print("Updated Card_Exec_TotalRuns visual.json with displayUnits: 1D")

# Update Card_TotalRuns (Page 1)
p1_card_path = os.path.join(BASE_DIR, 'ReportSection_Page1_Overview/visuals/Card_TotalRuns/visual.json')
with open(p1_card_path, 'r', encoding='utf-8') as f:
    c1 = json.load(f)

c1_objs = c1['visual'].setdefault('objects', {})
c1_labels = c1_objs.setdefault('labels', [{}])
c1_labels[0].setdefault('properties', {})['displayUnits'] = {'expr': {'Literal': {'Value': '1D'}}}
c1_labels[0]['properties']['fontSize'] = {'expr': {'Literal': {'Value': '18D'}}}

with open(p1_card_path, 'w', encoding='utf-8') as f:
    json.dump(c1, f, indent=2, ensure_ascii=False)
print("Updated Card_TotalRuns (Page 1) visual.json with displayUnits: 1D")

# =========================================================================
# TASK 2: Enforce Strict Top 5 Filter on Page 3 Player Tables
# =========================================================================
p3_visuals_dir = os.path.join(BASE_DIR, 'ReportSection_Page3_ExecutiveOverview/visuals')

top5_specs = {
    'Table_TopRunScorers': {
        'entity': 'fact_batting_scorecards',
        'column': 'player_name',
        'measure': 'Player Total Runs',
        'operator': 'Top',
        'count': 5
    },
    'Table_TopWicketTakers': {
        'entity': 'fact_bowling_scorecards',
        'column': 'player_name',
        'measure': 'Player Total Wickets',
        'operator': 'Top',
        'count': 5
    },
    'Table_HighestStrikeRate': {
        'entity': 'fact_batting_scorecards',
        'column': 'player_name',
        'measure': 'Player Strike Rate (Min 100 Runs)',
        'operator': 'Top',
        'count': 5
    },
    'Table_BestBowlingEconomy': {
        'entity': 'fact_bowling_scorecards',
        'column': 'player_name',
        'measure': 'Player Economy Rate (Min 10 Overs)',
        'operator': 'Bottom',
        'count': 5
    }
}

for tname, spec in top5_specs.items():
    vpath = os.path.join(p3_visuals_dir, tname, 'visual.json')
    with open(vpath, 'r', encoding='utf-8') as f:
        vjson = json.load(f)
    
    filter_obj = {
        "name": f"FilterTop5_{tname}",
        "field": {
            "Column": {
                "Expression": {
                    "SourceRef": {
                        "Entity": spec['entity']
                    }
                },
                "Property": spec['column']
            }
        },
        "type": "TopN",
        "operator": spec['operator'],
        "itemCount": spec['count'],
        "orderBy": {
            "Measure": {
                "Expression": {
                    "SourceRef": {
                        "Entity": spec['entity']
                    }
                },
                "Property": spec['measure']
            }
        }
    }
    
    # Inject filterConfig
    vjson['filterConfig'] = {
        "filters": [filter_obj]
    }
    
    with open(vpath, 'w', encoding='utf-8') as f:
        json.dump(vjson, f, indent=2, ensure_ascii=False)
    print(f"Updated {tname} with strict Top 5 filterConfig ({spec['operator']} 5 by {spec['measure']})")

# =========================================================================
# TASK 3: Apply Conditional Formatting on Page 2 Matrix
# =========================================================================
matrix_path = os.path.join(BASE_DIR, 'ReportSection_Page2_Standings/visuals/Matrix_TournamentStandings/visual.json')
with open(matrix_path, 'r', encoding='utf-8') as f:
    mjson = json.load(f)

mobjs = mjson['visual'].setdefault('objects', {})

# Define conditional formatting rule for qualification_status
cond_rules = {
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

# Apply to values -> backColor
mobjs['values'] = [
    {
        "properties": {
            "backColor": {
                "rules": cond_rules
            },
            "backColorSecondary": {
                "solid": {
                    "color": {
                        "expr": {
                            "Literal": {
                                "Value": "'#F8F9FA'"
                            }
                        }
                    }
                }
            }
        }
    },
    {
        "selector": {
            "metadata": "view_tournament_standings.points"
        },
        "properties": {
            "backColor": {
                "rules": cond_rules
            }
        }
    },
    {
        "selector": {
            "metadata": "view_tournament_standings.team_name"
        },
        "properties": {
            "backColor": {
                "rules": cond_rules
            }
        }
    }
]

with open(matrix_path, 'w', encoding='utf-8') as f:
    json.dump(mjson, f, indent=2, ensure_ascii=False)
print("Updated Matrix_TournamentStandings visual.json with values -> backColor conditional formatting rules")

# Also update monolithic report.json if present
rep_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
if os.path.exists(rep_path):
    with open(rep_path, 'r', encoding='utf-8') as f:
        rep = json.load(f)
    
    # Update Page 2 Matrix in rep
    for vc in rep['sections'][1]['visualContainers']:
        cfg = json.loads(vc['config'])
        if cfg.get('name') == 'Matrix_TournamentStandings':
            cfg['singleVisual']['objects']['values'] = mobjs['values']
            vc['config'] = json.dumps(cfg)
    
    # Update Page 3 Cards & Tables in rep
    for vc in rep['sections'][2]['visualContainers']:
        cfg = json.loads(vc['config'])
        vname = cfg.get('name')
        if vname == 'Card_Exec_TotalRuns':
            cfg['singleVisual']['objects']['labels'][0]['properties']['displayUnits'] = {'expr': {'Literal': {'Value': '1D'}}}
            vc['config'] = json.dumps(cfg)
        elif vname in top5_specs:
            spec = top5_specs[vname]
            f_obj = {
                "name": f"FilterTop5_{vname}",
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": spec['entity']}},
                        "Property": spec['column']
                    }
                },
                "type": "TopN",
                "operator": spec['operator'],
                "itemCount": spec['count'],
                "orderBy": {
                    "Measure": {
                        "Expression": {"SourceRef": {"Entity": spec['entity']}},
                        "Property": spec['measure']
                    }
                }
            }
            vc['filters'] = json.dumps([f_obj])
            cfg['filterConfig'] = [f_obj]
            vc['config'] = json.dumps(cfg)
    
    with open(rep_path, 'w', encoding='utf-8') as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)
    print("Updated monolithic report.json as well for backward compatibility.")

print("SUCCESS: All tasks applied cleanly!")
