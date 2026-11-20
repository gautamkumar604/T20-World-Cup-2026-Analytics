import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

for t in bim['model']['tables']:
    for m in t.get('measures', []):
        if 'team' in m['name'].lower() or 'count' in m['name'].lower() or 'cert' in m['name'].lower() or 'stand' in m['name'].lower():
            print(f"{t['name']}: {m['name']}")
