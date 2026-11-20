import json

model_path = 'power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim'
with open(model_path, 'r', encoding='utf-8') as f:
    bim = json.load(f)

report_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(report_path, 'r', encoding='utf-8') as f:
    rep = json.load(f)

# Build entity map from model.bim
model_tables = {}
for t in bim['model']['tables']:
    tname = t['name']
    cols = {c['name']: c for c in t.get('columns', [])}
    meas = {m['name']: m for m in t.get('measures', [])}
    model_tables[tname] = {'columns': cols, 'measures': meas}

s2 = rep['sections'][2]
print(f"=== VERIFYING SECTION 2 ({s2['displayName']}) VISUAL CONTAINERS ===")
errors = 0
total_bindings = 0

for idx, vc in enumerate(s2['visualContainers']):
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    sv = cfg.get('singleVisual', {})
    vtype = sv.get('visualType')
    
    if vname == 'HeaderBanner_Executive':
        print(f"[{idx+1}] {vname} ({vtype}): Banner header - PASS")
        continue
    
    proj = sv.get('projections', {})
    proto = sv.get('prototypeQuery', {})
    
    if not proto:
        print(f"[{idx+1}] [FAIL] {vname} ({vtype}): MISSING prototypeQuery!")
        errors += 1
        continue
    
    from_clause = proto.get('From', [])
    select_clause = proto.get('Select', [])
    from_map = {f['Name']: f['Entity'] for f in from_clause}
    
    select_names = {s['Name']: s for s in select_clause}
    
    # Check that all projections have matching select items
    proj_refs = []
    for role, items in proj.items():
        for item in items:
            qref = item.get('queryRef')
            proj_refs.append((role, qref))
            total_bindings += 1
            if qref not in select_names:
                print(f"[{idx+1}] [FAIL] {vname}: queryRef '{qref}' in role '{role}' NOT in prototypeQuery Select!")
                errors += 1
            else:
                s_item = select_names[qref]
                is_meas = 'Measure' in s_item
                is_col = 'Column' in s_item
                kind = 'Measure' if is_meas else 'Column'
                prop = s_item[kind]['Property']
                src = s_item[kind]['Expression']['SourceRef']['Source']
                entity = from_map.get(src)
                
                # Check entity and property in model.bim
                if entity not in model_tables:
                    print(f"[{idx+1}] [FAIL] {vname}: Entity '{entity}' not in model.bim!")
                    errors += 1
                elif is_meas and prop not in model_tables[entity]['measures']:
                    print(f"[{idx+1}] [FAIL] {vname}: Measure '{prop}' not in table '{entity}' in model.bim!")
                    errors += 1
                elif is_col and prop not in model_tables[entity]['columns']:
                    print(f"[{idx+1}] [FAIL] {vname}: Column '{prop}' not in table '{entity}' in model.bim!")
                    errors += 1

    print(f"[{idx+1}] [PASS] {vname} ({vtype}): {len(proj_refs)} bindings, prototypeQuery verified!")

print(f"\n=======================================================")
print(f"TOTAL VISUAL CONTAINERS VERIFIED: {len(s2['visualContainers'])}")
print(f"TOTAL PROJECTED BINDINGS: {total_bindings}")
print(f"ERRORS DETECTED: {errors}")
print(f"=======================================================")
