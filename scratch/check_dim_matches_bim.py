import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

for t in bim['model']['tables']:
    if t['name'] == 'dim_matches':
        print('dim_matches columns in model.bim:')
        for c in t.get('columns', []):
            print(f" - {c['name']} ({c.get('type', 'data')}, {c.get('dataType')})")
