import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

for t in bim['model']['tables']:
    if t['name'] == 'fact_deliveries':
        print('fact_deliveries columns in model.bim:')
        for c in t.get('columns', []):
            print(f" - {c['name']} ({c.get('dataType')})")
