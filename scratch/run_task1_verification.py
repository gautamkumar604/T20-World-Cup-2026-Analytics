import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

tables_to_check = ['fact_match_summaries', 'fact_batting_scorecards', 'fact_bowling_scorecards']
table_measures = {}

for t in bim['model']['tables']:
    if t['name'] in tables_to_check:
        table_measures[t['name']] = [m['name'] for m in t.get('measures', [])]

print("=== TASK 1A: EXTRACT ALL MEASURES FROM THE 3 TABLES ===")
for tname, meas_list in table_measures.items():
    print(f"\nTable: {tname} ({len(meas_list)} measures):")
    for m in meas_list:
        print(f"  - {m}")

required_16 = [
    "Lowest Match Score",
    "Lowest Team Score",
    "Highest Team Score",
    "Team Win Pct",
    "Venue Avg First Innings Score",
    "Venue Avg Second Innings Score",
    "Player Total Runs",
    "Player Balls Faced",
    "Player Strike Rate",
    "Player Strike Rate (Min 100 Runs)",
    "Player Total Wickets",
    "Player Legal Balls",
    "Player Overs Bowled",
    "Player Runs Conceded",
    "Player Economy Rate",
    "Player Economy Rate (Min 10 Overs)"
]

all_bim_measures = set()
for mlist in table_measures.values():
    all_bim_measures.update(mlist)

print("\n=== TASK 1B: CONFIRM EXISTENCE OF THE 16 MEASURES ===")
missing = []
for m in required_16:
    exists = m in all_bim_measures
    print(f"  [{'EXISTS' if exists else 'MISSING'}] {m}")
    if not exists:
        missing.append(m)

print(f"\n=== TASK 1C: REPORT MISSING MEASURES ===")
print(f"Total missing measures: {len(missing)}")
if missing:
    print(f"Missing: {missing}")
else:
    print("ALL 16 MEASURES EXIST IN model.bim!")
