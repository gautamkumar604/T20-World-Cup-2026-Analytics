import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

for t in bim['model']['tables']:
    meas = [m['name'] for m in t.get('measures', [])]
    if meas:
        print(f"Table: {t['name']} ({len(meas)} measures):")
        for m in meas:
            print(f"  - '{m}'")
