import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

for t in bim['model']['tables']:
    if 'LocalDateTable' in t['name']:
        for c in t.get('columns', []):
            print(json.dumps(c, indent=2))
