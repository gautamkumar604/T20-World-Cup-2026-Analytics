import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

for t in bim['model']['tables']:
    if t['name'] == 'fact_match_summaries':
        for m in t.get('measures', []):
            if 'Selected Team' in m['name'] or 'Tournament Points' in m['name']:
                print(f"=== {m['name']} ===")
                print(f"  Description: {m.get('description')}")
                print(f"  DAX: {m.get('expression')}")
