import os
import json

BASE_PAGES_DIR = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages'
THEME_DIR = 'power_bi/theme'
os.makedirs(THEME_DIR, exist_ok=True)

# =============================================================================
# TASK 1: MOBILE LAYOUT (PORTRAIT MODE)
# =============================================================================

mobile_schema = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainerMobileState/1.0.0/schema.json"

def write_mobile_json(pdir, vname, y, h, z=1000):
    v_folder = os.path.join(pdir, vname)
    if not os.path.exists(v_folder):
        print(f"Warning: {vname} not found in {pdir}")
        return
    mobile_path = os.path.join(v_folder, 'mobile.json')
    mobile_data = {
        "$schema": mobile_schema,
        "position": {
            "x": 10,
            "y": y,
            "z": z,
            "width": 340,
            "height": h
        }
    }
    with open(mobile_path, 'w', encoding='utf-8') as f:
        json.dump(mobile_data, f, indent=2)
    print(f"Created mobile.json for {vname} (y={y}, h={h})")

# Page 1 Mobile Layout (Single Column Stacked)
p1_dir = os.path.join(BASE_PAGES_DIR, 'ReportSection_Page1_Overview/visuals')
p1_mobile_specs = [
    ("HeaderBanner", 10, 60),
    ("Slicer_Stage", 78, 60),
    ("Slicer_Country", 146, 60),
    ("Card_TotalMatches", 214, 75),
    ("Card_CompletedMatches", 297, 75),
    ("Card_TotalRuns", 380, 75),
    ("Card_TotalWickets", 463, 75),
    ("Card_TournamentRunRate", 546, 75),
    ("Card_HighestScore", 629, 75),
    ("Donut_MatchOutcomes", 712, 240)
]
for vname, y, h in p1_mobile_specs:
    write_mobile_json(p1_dir, vname, y, h)

# Page 2 Mobile Layout (Standings Matrix + Slicers)
p2_dir = os.path.join(BASE_PAGES_DIR, 'ReportSection_Page2_Standings/visuals')
p2_mobile_specs = [
    ("HeaderBanner_Standings", 10, 60),
    ("Slicer_Stage_Standings", 78, 60),
    ("Slicer_Group_Standings", 146, 60),
    ("Card_Standings_Certification", 214, 75),
    ("Card_Standings_TeamsCount", 297, 75),
    ("Matrix_TournamentStandings", 380, 520)
]
for vname, y, h in p2_mobile_specs:
    write_mobile_json(p2_dir, vname, y, h)

# Page 3 Mobile Layout (Executive Overview)
p3_dir = os.path.join(BASE_PAGES_DIR, 'ReportSection_Page3_ExecutiveOverview/visuals')
p3_mobile_specs = [
    ("HeaderBanner_Executive", 10, 60),
    ("Slicer_Stage_Exec", 78, 60),
    ("Slicer_Team_Exec", 146, 60),
    ("Card_Exec_TotalMatches", 214, 75),
    ("Card_Exec_CompletedMatches", 297, 75),
    ("Card_Exec_TotalRuns", 380, 75),
    ("Card_Exec_TotalWickets", 463, 75),
    ("Card_Exec_HighestScore", 546, 75),
    ("Card_Exec_LowestScore", 629, 75),
    ("Table_TopRunScorers", 712, 260),
    ("Table_TopWicketTakers", 980, 260),
    ("Table_HighestStrikeRate", 1248, 260),
    ("Table_BestBowlingEconomy", 1516, 260)
]
for vname, y, h in p3_mobile_specs:
    write_mobile_json(p3_dir, vname, y, h)

# Page 4 Mobile Layout (Tactical Analysis)
p4_dir = os.path.join(BASE_PAGES_DIR, 'ReportSection_Page4_TacticalAnalysis/visuals')
p4_mobile_specs = [
    ("HeaderBanner_Tactical", 10, 60),
    ("Slicer_Stage_Tactical", 78, 60),
    ("Slicer_Team_Tactical", 146, 60),
    ("Card_PP_RunRate", 214, 75),
    ("Card_PP_Wickets", 297, 75),
    ("Card_Middle_RunRate", 380, 75),
    ("Card_Middle_Wickets", 463, 75),
    ("Card_Death_RunRate", 546, 75),
    ("Card_Death_Wickets", 629, 75),
    ("Bar_TossImpact", 712, 240),
    ("Donut_BoundaryDistribution", 960, 240),
    ("Table_PowerplaySpecialists", 1208, 260),
    ("Table_DeathSpecialists", 1476, 260)
]
for vname, y, h in p4_mobile_specs:
    write_mobile_json(p4_dir, vname, y, h)

# =============================================================================
# TASK 2: GLOBAL THEME & UI CONSISTENCY
# =============================================================================

theme_data = {
    "name": "CyberCricketTheme",
    "dataColors": [
        "#1A365D",
        "#2B6CB0",
        "#319795",
        "#D69E2E",
        "#DD6B20",
        "#E53E3E",
        "#805AD5",
        "#4A5568"
    ],
    "background": "#F8F9FA",
    "foreground": "#1A365D",
    "tableAccent": "#1A365D",
    "visualStyles": {
        "*": {
            "*": {
                "*": {
                    "fontFamily": "Segoe UI"
                },
                "background": [
                    {
                        "color": {"solid": {"color": "#FFFFFF"}},
                        "transparency": 0
                    }
                ],
                "border": [
                    {
                        "show": True,
                        "color": {"solid": {"color": "#E2E8F0"}},
                        "radius": 4
                    }
                ],
                "dropShadow": [
                    {
                        "show": False
                    }
                ]
            }
        },
        "page": {
            "*": {
                "background": [
                    {
                        "color": {"solid": {"color": "#F8F9FA"}},
                        "transparency": 0
                    }
                ]
            }
        }
    }
}

theme_file_path = os.path.join(THEME_DIR, 'CyberCricketTheme.json')
with open(theme_file_path, 'w', encoding='utf-8') as f:
    json.dump(theme_data, f, indent=2)
print("Created power_bi/theme/CyberCricketTheme.json")

# Align HeaderBanner across all 4 pages to #1A365D and consistent fonts
headers_to_align = [
    (p1_dir, 'HeaderBanner', "ICC Men's T20 World Cup 2026 — Executive Tournament Overview\n", "Tournament Coverage: 55 Scheduled Matches (53 Completed, 2 Rain Abandonments). Standings reflect all 20 Nations."),
    (p2_dir, 'HeaderBanner_Standings', "ICC Men's T20 World Cup 2026 — Official Tournament Standings & Qualification\n", "Official Clause 16.10 Net Run Rate | Exact Rational Tie-Breaking Engine | Super 8 Qualification Pathway"),
    (p3_dir, 'HeaderBanner_Executive', "ICC Men's T20 World Cup 2026 — Executive Dashboard\n", "Authoritative Tournament Intelligence: Stage Progression, Player Leaders & Venue Analytics"),
    (p4_dir, 'HeaderBanner_Tactical', "ICC Men's T20 World Cup 2026 — Tactical Analysis\n", "Phase Dynamics (Powerplay, Middle, Death), Toss Match Impact & Phase Specialists")
]

for vdir, vname, title_txt, sub_txt in headers_to_align:
    vpath = os.path.join(vdir, vname, 'visual.json')
    if os.path.exists(vpath):
        with open(vpath, 'r', encoding='utf-8') as f:
            vjson = json.load(f)
        vjson['position']['y'] = 10
        vjson['position']['height'] = 60
        vjson['visual'] = {
            "visualType": "textbox",
            "objects": {
                "general": [{
                    "properties": {
                        "paragraphs": [{
                            "textRuns": [
                                {
                                    "value": title_txt,
                                    "textStyle": {
                                        "fontFamily": "Segoe UI",
                                        "fontSize": "17pt",
                                        "fontWeight": "bold",
                                        "color": "#1A365D"
                                    }
                                },
                                {
                                    "value": sub_txt,
                                    "textStyle": {
                                        "fontFamily": "Segoe UI",
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
        with open(vpath, 'w', encoding='utf-8') as f:
            json.dump(vjson, f, indent=2)
        print(f"Aligned header {vname} in {os.path.basename(os.path.dirname(vdir))}")

# =============================================================================
# TASK 3: SLICER SYNCING
# Sync Stage and Team slicers across Page 1, Page 3, Page 4.
# Page 2 remains isolated.
# =============================================================================

# Slicers to sync with StageSyncGroup
stage_slicers = [
    (p1_dir, 'Slicer_Stage'),
    (p3_dir, 'Slicer_Stage_Exec'),
    (p4_dir, 'Slicer_Stage_Tactical')
]
for vdir, vname in stage_slicers:
    vpath = os.path.join(vdir, vname, 'visual.json')
    if os.path.exists(vpath):
        with open(vpath, 'r', encoding='utf-8') as f:
            vjson = json.load(f)
        vjson['visual']['syncGroup'] = {
            "groupName": "StageSyncGroup",
            "fieldChanges": True,
            "filterChanges": True
        }
        with open(vpath, 'w', encoding='utf-8') as f:
            json.dump(vjson, f, indent=2)
        print(f"Added StageSyncGroup to {vname}")

# Slicers to sync with TeamSyncGroup
team_slicers = [
    (p3_dir, 'Slicer_Team_Exec'),
    (p4_dir, 'Slicer_Team_Tactical')
]
for vdir, vname in team_slicers:
    vpath = os.path.join(vdir, vname, 'visual.json')
    if os.path.exists(vpath):
        with open(vpath, 'r', encoding='utf-8') as f:
            vjson = json.load(f)
        vjson['visual']['syncGroup'] = {
            "groupName": "TeamSyncGroup",
            "fieldChanges": True,
            "filterChanges": True
        }
        with open(vpath, 'w', encoding='utf-8') as f:
            json.dump(vjson, f, indent=2)
        print(f"Added TeamSyncGroup to {vname}")

# Page 1 Slicer_Group / Slicer_Country: ensure isolated or syncable
p1_team_slicer_path = os.path.join(p1_dir, 'Slicer_Country', 'visual.json')
# Verify Page 2 slicers have NO syncGroup
for p2_slicer in ['Slicer_Stage_Standings', 'Slicer_Group_Standings']:
    p2_spath = os.path.join(p2_dir, p2_slicer, 'visual.json')
    if os.path.exists(p2_spath):
        with open(p2_spath, 'r', encoding='utf-8') as f:
            p2_sjson = json.load(f)
        if 'syncGroup' in p2_sjson['visual']:
            del p2_sjson['visual']['syncGroup']
            with open(p2_spath, 'w', encoding='utf-8') as f:
                json.dump(p2_sjson, f, indent=2)
        print(f"Confirmed {p2_slicer} is completely isolated (no syncGroup).")

# =============================================================================
# TASK 4: TOOLTIPS & INTERACTIONS
# =============================================================================

# Page 2 Matrix interaction: disable cross-filtering disrupting KPI summary cards
p2_page_json_path = os.path.join(BASE_PAGES_DIR, 'ReportSection_Page2_Standings/page.json')
with open(p2_page_json_path, 'r', encoding='utf-8') as f:
    p2_page = json.load(f)

p2_page['visualInteractions'] = [
    {
        "source": "Matrix_TournamentStandings",
        "target": "Card_Standings_Certification",
        "type": "NoFilter"
    },
    {
        "source": "Matrix_TournamentStandings",
        "target": "Card_Standings_TeamsCount",
        "type": "NoFilter"
    }
]
with open(p2_page_json_path, 'w', encoding='utf-8') as f:
    json.dump(p2_page, f, indent=2)
print("Configured Page 2 visualInteractions to protect standings summary cards.")

# Enable hover tooltips across all chart visuals
charts_to_check = [
    (p1_dir, 'Donut_MatchOutcomes'),
    (p3_dir, 'Bar_TournamentProgress'),
    (p3_dir, 'Bar_VenuePerformance'),
    (p4_dir, 'Bar_TossImpact'),
    (p4_dir, 'Donut_BoundaryDistribution')
]
for vdir, vname in charts_to_check:
    cpath = os.path.join(vdir, vname, 'visual.json')
    if os.path.exists(cpath):
        with open(cpath, 'r', encoding='utf-8') as f:
            cjson = json.load(f)
        cobjs = cjson['visual'].setdefault('objects', {})
        cobjs['tooltips'] = [{
            "properties": {
                "show": {
                    "expr": {
                        "Literal": {
                            "Value": "true"
                        }
                    }
                }
            }
        }]
        with open(cpath, 'w', encoding='utf-8') as f:
            json.dump(cjson, f, indent=2)
        print(f"Enabled explicit hover tooltip on {vname}")

print("\nSUCCESS: All Phase 4.4 updates applied cleanly!")
