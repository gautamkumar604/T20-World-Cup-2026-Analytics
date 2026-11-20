import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

for t in bim['model']['tables']:
    if t['name'] in ('fact_batting_scorecards', 'fact_bowling_scorecards', 'dim_players'):
        print(f"\nTable {t['name']}:")
        for c in t.get('columns', []):
            print(f" - {c['name']} ({c.get('dataType')})")
