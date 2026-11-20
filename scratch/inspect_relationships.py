import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

print('Relationships:')
for r in bim['model'].get('relationships', []):
    print(f" - {r['fromTable']}[{r['fromColumn']}] -> {r['toTable']}[{r['toColumn']}] (crossFilteringBehavior: {r.get('crossFilteringBehavior', 'oneDirection')}, isActive: {r.get('isActive', True)})")
