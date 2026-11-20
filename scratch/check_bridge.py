import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

for t in bim['model']['tables']:
    if t['name'] == 'bridge_match_teams':
        print('bridge_match_teams partitions:')
        print(json.dumps(t.get('partitions', []), indent=2))
        print('columns:')
        for c in t.get('columns', []):
            print(c)
