import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

for t in bim['model']['tables']:
    if t['name'] == 'dim_matches':
        for c in t.get('columns', []):
            if c['name'] in ('Stage_Normalized', 'Tournament_Group'):
                print(c)
        print('Partition M code for dim_matches:')
        for p in t.get('partitions', []):
            print(p.get('source', {}).get('expression'))
