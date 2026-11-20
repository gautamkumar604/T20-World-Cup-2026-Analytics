import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

# Collect all tables, columns, measures in bim
entities = {}
for t in bim['model']['tables']:
    tname = t['name']
    entities[tname] = {'columns': set(), 'measures': set()}
    for c in t.get('columns', []):
        entities[tname]['columns'].add(c['name'])
    for m in t.get('measures', []):
        entities[tname]['measures'].add(m['name'])

# Check Page 1 queryRefs
with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', 'r', encoding='utf-8') as f:
    rep = json.load(f)

s0 = rep['sections'][0]
print(f"=== CHECKING PAGE 1 ({s0['displayName']}) QUERY REFS ===")
for idx, vc in enumerate(s0['visualContainers']):
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    sv = cfg.get('singleVisual', {})
    proj = sv.get('projections', {})
    print(f"\nVisual {idx+1}: {vname}")
    for k, p_list in proj.items():
        for p in p_list:
            qref = p.get('queryRef')
            parts = qref.split('.', 1)
            tname, prop = parts[0], parts[1]
            if tname not in entities:
                print(f"  [MISSING TABLE] {qref}")
            else:
                is_col = prop in entities[tname]['columns']
                is_meas = prop in entities[tname]['measures']
                if not is_col and not is_meas:
                    print(f"  [NOT FOUND IN BIM] {qref} (Table {tname} exists, but property {prop} not found!)")
                else:
                    kind = 'Measure' if is_meas else 'Column'
                    print(f"  [OK] {qref} -> {kind}")
