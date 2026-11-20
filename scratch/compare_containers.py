import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', 'r', encoding='utf-8') as f:
    rep = json.load(f)

print("=== SECTION 1 VISUAL 3 (Card_Standings_TeamsCount) ===")
print(json.dumps(rep['sections'][1]['visualContainers'][3], indent=2))

print("\n=== SECTION 2 VISUAL 3 (Card_Exec_TotalMatches) ===")
print(json.dumps(rep['sections'][2]['visualContainers'][3], indent=2))

print("\n=== SECTION 1 VISUAL 5 (Matrix_TournamentStandings) ===")
print(json.dumps(rep['sections'][1]['visualContainers'][5], indent=2))

print("\n=== SECTION 2 VISUAL 10 (Matrix_TeamWinRate) ===")
print(json.dumps(rep['sections'][2]['visualContainers'][10], indent=2))
