import json
import shutil
import os

REPORT_PATH = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
BIM_PATH = 'power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim'

# 1. Backup files
shutil.copy2(REPORT_PATH, REPORT_PATH + '.bak_patch')
shutil.copy2(BIM_PATH, BIM_PATH + '.bak_patch')
print(f"Backed up {REPORT_PATH} and {BIM_PATH}")

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

# ==========================================
# TASK 1: Page 2 (Tournament Standings)
# ==========================================
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
    vtype = sv.get('visualType')

    if vname == 'HeaderBanner_Standings':
        continue

    elif vname == 'Slicer_Stage_Standings':
        sv['projections'] = {'Values': [{'queryRef': 'view_tournament_standings.stage_normalized'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('v', 'view_tournament_standings')],
            [('v', 'view_tournament_standings', 'stage_normalized', False)]
        )

    elif vname == 'Slicer_Group_Standings':
        sv['projections'] = {
            'Values': [
                {'queryRef': 'view_tournament_standings.stage_normalized'},
                {'queryRef': 'view_tournament_standings.group_display'}
            ]
        }
        sv['prototypeQuery'] = make_prototype_query(
            [('v', 'view_tournament_standings')],
            [
                ('v', 'view_tournament_standings', 'stage_normalized', False),
                ('v', 'view_tournament_standings', 'group_display', False)
            ]
        )

    elif vname == 'Card_Standings_TeamsCount':
        sv['projections'] = {'Values': [{'queryRef': 'view_tournament_standings.team_name'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('v', 'view_tournament_standings')],
            [('v', 'view_tournament_standings', 'team_name', False)]
        )

    elif vname == 'Card_Standings_Certification':
        sv['projections'] = {'Values': [{'queryRef': 'view_tournament_standings.resolution_step'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('v', 'view_tournament_standings')],
            [('v', 'view_tournament_standings', 'resolution_step', False)]
        )

    elif vname == 'Matrix_TournamentStandings':
        sv['projections'] = {
            'Rows': [
                {'queryRef': 'view_tournament_standings.stage_normalized', 'active': True},
                {'queryRef': 'view_tournament_standings.group_name', 'active': True},
                {'queryRef': 'view_tournament_standings.team_name', 'active': True}
            ],
            'Values': [
                {'queryRef': 'view_tournament_standings.pool_rank'},
                {'queryRef': 'view_tournament_standings.played'},
                {'queryRef': 'view_tournament_standings.wins'},
                {'queryRef': 'view_tournament_standings.losses'},
                {'queryRef': 'view_tournament_standings.no_result'},
                {'queryRef': 'view_tournament_standings.points'},
                {'queryRef': 'view_tournament_standings.nrr_display'}
            ],
            'Tooltips': [
                {'queryRef': 'view_tournament_standings.resolution_step'},
                {'queryRef': 'view_tournament_standings.qualification_status'}
            ]
        }
        sv['prototypeQuery'] = make_prototype_query(
            [('v', 'view_tournament_standings')],
            [
                ('v', 'view_tournament_standings', 'stage_normalized', False),
                ('v', 'view_tournament_standings', 'group_name', False),
                ('v', 'view_tournament_standings', 'team_name', False),
                ('v', 'view_tournament_standings', 'pool_rank', False),
                ('v', 'view_tournament_standings', 'played', False),
                ('v', 'view_tournament_standings', 'wins', False),
                ('v', 'view_tournament_standings', 'losses', False),
                ('v', 'view_tournament_standings', 'no_result', False),
                ('v', 'view_tournament_standings', 'points', False),
                ('v', 'view_tournament_standings', 'nrr_display', False),
                ('v', 'view_tournament_standings', 'resolution_step', False),
                ('v', 'view_tournament_standings', 'qualification_status', False)
            ]
        )
        # sortDefinition is already set
    
    vc['config'] = json.dumps(cfg)

print("TASK 1 complete: Page 2 visuals patched.")

# ==========================================
# TASK 2: Page 3 Polish (Executive Overview)
# ==========================================
s2 = None
for s in report['sections']:
    if s.get('name') == 'ReportSection_Page3_ExecutiveOverview':
        s2 = s
        break

if not s2:
    raise ValueError("ReportSection_Page3_ExecutiveOverview not found")

for vc in s2['visualContainers']:
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    sv = cfg.get('singleVisual', {})
    vtype = sv.get('visualType')

    if vname == 'Card_Exec_TotalRuns':
        # Add displayUnits: 1D so it displays 17,582 instead of 18K
        objs = sv.setdefault('objects', {})
        labels = objs.setdefault('labels', [{}])
        if not labels:
            labels.append({})
        props = labels[0].setdefault('properties', {})
        props['displayUnits'] = {'expr': {'Literal': {'Value': '1D'}}}
        props['fontSize'] = {'expr': {'Literal': {'Value': '18D'}}}
        props['color'] = {'solid': {'color': {'expr': {'Literal': {'Value': "'#1A365D'"}}}}}

    elif vname == 'Table_TopRunScorers':
        sv['sortDefinition'] = {
            'sort': [
                {
                    'field': {'queryRef': 'fact_batting_scorecards.Player Total Runs'},
                    'direction': 'Descending'
                }
            ]
        }
        order_by = [
            {
                'Direction': 2,
                'Expression': {
                    'Measure': {
                        'Expression': {'SourceRef': {'Source': 'b'}},
                        'Property': 'Player Total Runs'
                    }
                }
            }
        ]
        sv['prototypeQuery'] = make_prototype_query(
            [('b', 'fact_batting_scorecards')],
            [
                ('b', 'fact_batting_scorecards', 'player_name', False),
                ('b', 'fact_batting_scorecards', 'team', False),
                ('b', 'fact_batting_scorecards', 'Player Total Runs', True),
                ('b', 'fact_batting_scorecards', 'Player Strike Rate', True)
            ],
            order_by=order_by,
            take=5
        )

    elif vname == 'Table_TopWicketTakers':
        sv['sortDefinition'] = {
            'sort': [
                {
                    'field': {'queryRef': 'fact_bowling_scorecards.Player Total Wickets'},
                    'direction': 'Descending'
                }
            ]
        }
        order_by = [
            {
                'Direction': 2,
                'Expression': {
                    'Measure': {
                        'Expression': {'SourceRef': {'Source': 'bw'}},
                        'Property': 'Player Total Wickets'
                    }
                }
            }
        ]
        sv['prototypeQuery'] = make_prototype_query(
            [('bw', 'fact_bowling_scorecards')],
            [
                ('bw', 'fact_bowling_scorecards', 'player_name', False),
                ('bw', 'fact_bowling_scorecards', 'team', False),
                ('bw', 'fact_bowling_scorecards', 'Player Total Wickets', True),
                ('bw', 'fact_bowling_scorecards', 'Player Economy Rate', True)
            ],
            order_by=order_by,
            take=5
        )

    elif vname == 'Table_HighestStrikeRate':
        sv['sortDefinition'] = {
            'sort': [
                {
                    'field': {'queryRef': 'fact_batting_scorecards.Player Strike Rate (Min 100 Runs)'},
                    'direction': 'Descending'
                }
            ]
        }
        order_by = [
            {
                'Direction': 2,
                'Expression': {
                    'Measure': {
                        'Expression': {'SourceRef': {'Source': 'b'}},
                        'Property': 'Player Strike Rate (Min 100 Runs)'
                    }
                }
            }
        ]
        sv['prototypeQuery'] = make_prototype_query(
            [('b', 'fact_batting_scorecards')],
            [
                ('b', 'fact_batting_scorecards', 'player_name', False),
                ('b', 'fact_batting_scorecards', 'team', False),
                ('b', 'fact_batting_scorecards', 'Player Strike Rate (Min 100 Runs)', True),
                ('b', 'fact_batting_scorecards', 'Player Total Runs', True)
            ],
            order_by=order_by,
            take=5
        )

    elif vname == 'Table_BestBowlingEconomy':
        sv['sortDefinition'] = {
            'sort': [
                {
                    'field': {'queryRef': 'fact_bowling_scorecards.Player Economy Rate (Min 10 Overs)'},
                    'direction': 'Ascending'
                }
            ]
        }
        order_by = [
            {
                'Direction': 1,
                'Expression': {
                    'Measure': {
                        'Expression': {'SourceRef': {'Source': 'bw'}},
                        'Property': 'Player Economy Rate (Min 10 Overs)'
                    }
                }
            }
        ]
        sv['prototypeQuery'] = make_prototype_query(
            [('bw', 'fact_bowling_scorecards')],
            [
                ('bw', 'fact_bowling_scorecards', 'player_name', False),
                ('bw', 'fact_bowling_scorecards', 'team', False),
                ('bw', 'fact_bowling_scorecards', 'Player Economy Rate (Min 10 Overs)', True),
                ('bw', 'fact_bowling_scorecards', 'Player Total Wickets', True)
            ],
            order_by=order_by,
            take=5
        )

    vc['config'] = json.dumps(cfg)

print("TASK 2 complete: Page 3 polish applied.")

# ==========================================
# TASK 3: Page 1 (Tournament Overview & Standings)
# ==========================================
s0 = None
for s in report['sections']:
    if s.get('name') == 'ReportSection_Page1_Overview':
        s0 = s
        break

if not s0:
    raise ValueError("ReportSection_Page1_Overview not found")

for vc in s0['visualContainers']:
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    sv = cfg.get('singleVisual', {})
    vtype = sv.get('visualType')

    if vname == 'HeaderBanner':
        continue

    elif vname == 'Card_TotalMatches':
        sv['projections'] = {'Values': [{'queryRef': 'fact_match_summaries.Tournament Matches Scheduled'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('f', 'fact_match_summaries')],
            [('f', 'fact_match_summaries', 'Tournament Matches Scheduled', True)]
        )

    elif vname == 'Card_CompletedMatches':
        sv['projections'] = {'Values': [{'queryRef': 'fact_match_summaries.Tournament Matches Completed'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('f', 'fact_match_summaries')],
            [('f', 'fact_match_summaries', 'Tournament Matches Completed', True)]
        )

    elif vname == 'Card_TotalRuns':
        sv['projections'] = {'Values': [{'queryRef': 'fact_match_summaries.Total Tournament Runs'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('f', 'fact_match_summaries')],
            [('f', 'fact_match_summaries', 'Total Tournament Runs', True)]
        )
        objs = sv.setdefault('objects', {})
        labels = objs.setdefault('labels', [{}])
        if not labels:
            labels.append({})
        props = labels[0].setdefault('properties', {})
        props['displayUnits'] = {'expr': {'Literal': {'Value': '1D'}}}

    elif vname == 'Card_TotalWickets':
        sv['projections'] = {'Values': [{'queryRef': 'fact_match_summaries.Total Tournament Wickets'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('f', 'fact_match_summaries')],
            [('f', 'fact_match_summaries', 'Total Tournament Wickets', True)]
        )

    elif vname == 'Card_TournamentRunRate':
        sv['projections'] = {'Values': [{'queryRef': 'fact_match_summaries.Tournament Run Rate'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('f', 'fact_match_summaries')],
            [('f', 'fact_match_summaries', 'Tournament Run Rate', True)]
        )

    elif vname == 'Card_HighestScore':
        sv['projections'] = {'Values': [{'queryRef': 'fact_match_summaries.Highest Match Score'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('f', 'fact_match_summaries')],
            [('f', 'fact_match_summaries', 'Highest Match Score', True)]
        )

    elif vname == 'Slicer_Stage':
        sv['projections'] = {'Values': [{'queryRef': 'dim_matches.Stage_Normalized'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('d', 'dim_matches')],
            [('d', 'dim_matches', 'Stage_Normalized', False)]
        )

    elif vname == 'Slicer_Group':
        sv['projections'] = {'Values': [{'queryRef': 'dim_teams.group_2026'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('t', 'dim_teams')],
            [('t', 'dim_teams', 'group_2026', False)]
        )

    elif vname == 'Slicer_Country':
        sv['projections'] = {'Values': [{'queryRef': 'dim_venues.country'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('v', 'dim_venues')],
            [('v', 'dim_venues', 'country', False)]
        )

    elif vname == 'Table_GroupStandings':
        sv['projections'] = {
            'Values': [
                {'queryRef': 'dim_teams.group_2026'},
                {'queryRef': 'dim_teams.team_name'},
                {'queryRef': 'fact_match_summaries.Selected Team Matches Scheduled'},
                {'queryRef': 'fact_match_summaries.Selected Team Matches Won'},
                {'queryRef': 'fact_match_summaries.Selected Team Losses'},
                {'queryRef': 'fact_match_summaries.Selected Team Matches Abandoned'},
                {'queryRef': 'fact_match_summaries.Tournament Points'},
                {'queryRef': 'fact_match_summaries.Net Run Rate (ICC)'}
            ]
        }
        sv['prototypeQuery'] = make_prototype_query(
            [('t', 'dim_teams'), ('f', 'fact_match_summaries')],
            [
                ('t', 'dim_teams', 'group_2026', False),
                ('t', 'dim_teams', 'team_name', False),
                ('f', 'fact_match_summaries', 'Selected Team Matches Scheduled', True),
                ('f', 'fact_match_summaries', 'Selected Team Matches Won', True),
                ('f', 'fact_match_summaries', 'Selected Team Losses', True),
                ('f', 'fact_match_summaries', 'Selected Team Matches Abandoned', True),
                ('f', 'fact_match_summaries', 'Tournament Points', True),
                ('f', 'fact_match_summaries', 'Net Run Rate (ICC)', True)
            ]
        )

    elif vname == 'Donut_MatchOutcomes':
        sv['projections'] = {
            'Category': [{'queryRef': 'dim_matches.outcome_type'}],
            'Y': [{'queryRef': 'fact_match_summaries.Tournament Matches Completed'}]
        }
        sv['prototypeQuery'] = make_prototype_query(
            [('d', 'dim_matches'), ('f', 'fact_match_summaries')],
            [
                ('d', 'dim_matches', 'outcome_type', False),
                ('f', 'fact_match_summaries', 'Tournament Matches Completed', True)
            ]
        )

    elif vname == 'Table_VenueAverages':
        sv['projections'] = {
            'Values': [
                {'queryRef': 'dim_venues.venue_name'},
                {'queryRef': 'dim_venues.city'},
                {'queryRef': 'fact_match_summaries.Total Tournament Runs'},
                {'queryRef': 'fact_match_summaries.Tournament Run Rate'}
            ]
        }
        sv['prototypeQuery'] = make_prototype_query(
            [('v', 'dim_venues'), ('f', 'fact_match_summaries')],
            [
                ('v', 'dim_venues', 'venue_name', False),
                ('v', 'dim_venues', 'city', False),
                ('f', 'fact_match_summaries', 'Total Tournament Runs', True),
                ('f', 'fact_match_summaries', 'Tournament Run Rate', True)
            ]
        )

    vc['config'] = json.dumps(cfg)

print("TASK 3 complete: Page 1 visuals patched.")

# Save modified report.json
with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("SUCCESS: report.json successfully written and formatted!")
