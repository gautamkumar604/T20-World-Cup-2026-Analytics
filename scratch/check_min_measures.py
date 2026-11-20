import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

for t in bim['model']['tables']:
    for m in t.get('measures', []):
        if 'Min 10' in m['name']:
            print(f"=== {m['name']} ({t['name']}) ===")
            print(m['expression'])
