import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

print("=== RELATIONSHIPS IN MODEL.BIM ===")
for r in bim['model'].get('relationships', []):
    from_t = r.get('fromTable')
    from_c = r.get('fromColumn')
    to_t = r.get('toTable')
    to_c = r.get('toColumn')
    active = r.get('isActive', True)
    cross_filter = r.get('crossFilteringBehavior', 'oneDirection')
    print(f"{from_t}[{from_c}] -> {to_t}[{to_c}] (active={active}, crossFiltering={cross_filter})")
