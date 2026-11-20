import json

report_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(report_path, 'r', encoding='utf-8') as f:
    rep = json.load(f)

# Find Section 2 (Executive Overview)
s2 = None
for s in rep['sections']:
    if s.get('name') == 'ReportSection_Page3_ExecutiveOverview':
        s2 = s
        break

if not s2:
    print("Error: ReportSection_Page3_ExecutiveOverview not found!")
    exit(1)

# Helper function to generate prototypeQuery
def make_prototype_query(from_entities, select_items):
    # from_entities: list of (alias, entity_name)
    # select_items: list of (alias, prop_name, is_measure)
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
    return {
        "Version": 2,
        "From": from_clause,
        "Select": select_clause
    }

# Update each visual container
for vc in s2['visualContainers']:
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    sv = cfg.get('singleVisual', {})
    vtype = sv.get('visualType')
    
    if vname == 'HeaderBanner_Executive':
        continue
    
    elif vname == 'Slicer_Stage_Exec':
        sv['projections'] = {'Values': [{'queryRef': 'dim_matches.Stage_Normalized'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('d', 'dim_matches')],
            [('d', 'dim_matches', 'Stage_Normalized', False)]
        )
    
    elif vname == 'Slicer_Team_Exec':
        sv['projections'] = {'Values': [{'queryRef': 'dim_teams.team_name'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('t', 'dim_teams')],
            [('t', 'dim_teams', 'team_name', False)]
        )
        
    elif vname == 'Card_Exec_TotalMatches':
        sv['projections'] = {'Values': [{'queryRef': 'fact_match_summaries.Tournament Matches Scheduled'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('f', 'fact_match_summaries')],
            [('f', 'fact_match_summaries', 'Tournament Matches Scheduled', True)]
        )
        
    elif vname == 'Card_Exec_CompletedMatches':
        sv['projections'] = {'Values': [{'queryRef': 'fact_match_summaries.Tournament Matches Completed'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('f', 'fact_match_summaries')],
            [('f', 'fact_match_summaries', 'Tournament Matches Completed', True)]
        )
        
    elif vname == 'Card_Exec_TotalRuns':
        sv['projections'] = {'Values': [{'queryRef': 'fact_match_summaries.Total Tournament Runs'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('f', 'fact_match_summaries')],
            [('f', 'fact_match_summaries', 'Total Tournament Runs', True)]
        )
        
    elif vname == 'Card_Exec_TotalWickets':
        sv['projections'] = {'Values': [{'queryRef': 'fact_match_summaries.Total Tournament Wickets'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('f', 'fact_match_summaries')],
            [('f', 'fact_match_summaries', 'Total Tournament Wickets', True)]
        )
        
    elif vname == 'Card_Exec_HighestScore':
        sv['projections'] = {'Values': [{'queryRef': 'fact_match_summaries.Highest Team Score'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('f', 'fact_match_summaries')],
            [('f', 'fact_match_summaries', 'Highest Team Score', True)]
        )
        
    elif vname == 'Card_Exec_LowestScore':
        sv['projections'] = {'Values': [{'queryRef': 'fact_match_summaries.Lowest Team Score'}]}
        sv['prototypeQuery'] = make_prototype_query(
            [('f', 'fact_match_summaries')],
            [('f', 'fact_match_summaries', 'Lowest Team Score', True)]
        )
        
    elif vname == 'Bar_TournamentProgress':
        sv['projections'] = {
            'Category': [{'queryRef': 'dim_matches.Stage_Normalized', 'active': True}],
            'Y': [{'queryRef': 'fact_match_summaries.Selected Team Matches Completed'}]
        }
        sv['prototypeQuery'] = make_prototype_query(
            [('d', 'dim_matches'), ('f', 'fact_match_summaries')],
            [
                ('d', 'dim_matches', 'Stage_Normalized', False),
                ('f', 'fact_match_summaries', 'Selected Team Matches Completed', True)
            ]
        )
        
    elif vname == 'Matrix_TeamWinRate':
        sv['projections'] = {
            'Rows': [{'queryRef': 'dim_teams.team_name', 'active': True}],
            'Columns': [{'queryRef': 'dim_matches.Stage_Normalized', 'active': True}],
            'Values': [{'queryRef': 'fact_match_summaries.Team Win Pct'}]
        }
        sv['prototypeQuery'] = make_prototype_query(
            [('t', 'dim_teams'), ('m', 'dim_matches'), ('f', 'fact_match_summaries')],
            [
                ('t', 'dim_teams', 'team_name', False),
                ('m', 'dim_matches', 'Stage_Normalized', False),
                ('f', 'fact_match_summaries', 'Team Win Pct', True)
            ]
        )
        
    elif vname == 'Bar_VenuePerformance':
        sv['projections'] = {
            'Category': [{'queryRef': 'dim_venues.venue_name', 'active': True}],
            'Y': [{'queryRef': 'fact_match_summaries.Venue Avg First Innings Score'}]
        }
        sv['prototypeQuery'] = make_prototype_query(
            [('v', 'dim_venues'), ('f', 'fact_match_summaries')],
            [
                ('v', 'dim_venues', 'venue_name', False),
                ('f', 'fact_match_summaries', 'Venue Avg First Innings Score', True)
            ]
        )
        
    elif vname == 'Table_TopRunScorers':
        sv['projections'] = {
            'Values': [
                {'queryRef': 'fact_batting_scorecards.player_name'},
                {'queryRef': 'fact_batting_scorecards.team'},
                {'queryRef': 'fact_batting_scorecards.Player Total Runs'},
                {'queryRef': 'fact_batting_scorecards.Player Strike Rate'}
            ]
        }
        sv['prototypeQuery'] = make_prototype_query(
            [('b', 'fact_batting_scorecards')],
            [
                ('b', 'fact_batting_scorecards', 'player_name', False),
                ('b', 'fact_batting_scorecards', 'team', False),
                ('b', 'fact_batting_scorecards', 'Player Total Runs', True),
                ('b', 'fact_batting_scorecards', 'Player Strike Rate', True)
            ]
        )
        
    elif vname == 'Table_TopWicketTakers':
        sv['projections'] = {
            'Values': [
                {'queryRef': 'fact_bowling_scorecards.player_name'},
                {'queryRef': 'fact_bowling_scorecards.team'},
                {'queryRef': 'fact_bowling_scorecards.Player Total Wickets'},
                {'queryRef': 'fact_bowling_scorecards.Player Economy Rate'}
            ]
        }
        sv['prototypeQuery'] = make_prototype_query(
            [('bw', 'fact_bowling_scorecards')],
            [
                ('bw', 'fact_bowling_scorecards', 'player_name', False),
                ('bw', 'fact_bowling_scorecards', 'team', False),
                ('bw', 'fact_bowling_scorecards', 'Player Total Wickets', True),
                ('bw', 'fact_bowling_scorecards', 'Player Economy Rate', True)
            ]
        )
        
    elif vname == 'Table_HighestStrikeRate':
        sv['projections'] = {
            'Values': [
                {'queryRef': 'fact_batting_scorecards.player_name'},
                {'queryRef': 'fact_batting_scorecards.team'},
                {'queryRef': 'fact_batting_scorecards.Player Strike Rate (Min 100 Runs)'},
                {'queryRef': 'fact_batting_scorecards.Player Total Runs'}
            ]
        }
        sv['prototypeQuery'] = make_prototype_query(
            [('b', 'fact_batting_scorecards')],
            [
                ('b', 'fact_batting_scorecards', 'player_name', False),
                ('b', 'fact_batting_scorecards', 'team', False),
                ('b', 'fact_batting_scorecards', 'Player Strike Rate (Min 100 Runs)', True),
                ('b', 'fact_batting_scorecards', 'Player Total Runs', True)
            ]
        )
        
    elif vname == 'Table_BestBowlingEconomy':
        sv['projections'] = {
            'Values': [
                {'queryRef': 'fact_bowling_scorecards.player_name'},
                {'queryRef': 'fact_bowling_scorecards.team'},
                {'queryRef': 'fact_bowling_scorecards.Player Economy Rate (Min 10 Overs)'},
                {'queryRef': 'fact_bowling_scorecards.Player Total Wickets'}
            ]
        }
        sv['prototypeQuery'] = make_prototype_query(
            [('bw', 'fact_bowling_scorecards')],
            [
                ('bw', 'fact_bowling_scorecards', 'player_name', False),
                ('bw', 'fact_bowling_scorecards', 'team', False),
                ('bw', 'fact_bowling_scorecards', 'Player Economy Rate (Min 10 Overs)', True),
                ('bw', 'fact_bowling_scorecards', 'Player Total Wickets', True)
            ]
        )
    
    vc['config'] = json.dumps(cfg)

with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(rep, f, indent=2, ensure_ascii=False)

print("SUCCESS: Injected prototypeQuery with From and Select clauses for all Executive Overview visuals in report.json!")
