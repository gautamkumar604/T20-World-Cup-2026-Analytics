import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', 'r', encoding='utf-8') as f:
    rep = json.load(f)

# Build map of table -> {'columns': set, 'measures': set}
model_entities = {}
for t in bim['model']['tables']:
    tname = t['name']
    cols = {c['name']: c for c in t.get('columns', [])}
    meas = {m['name']: m for m in t.get('measures', [])}
    model_entities[tname] = {'columns': cols, 'measures': meas}

print("=== CHECKING SECTION 2 VISUALS BINDINGS ===")
s2 = rep['sections'][2]
for idx, vc in enumerate(s2['visualContainers']):
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    sv = cfg.get('singleVisual', {})
    vtype = sv.get('visualType')
    projections = sv.get('projections', {})
    print(f"\nVisual {idx+1}: {vname} ({vtype})")
    for role, items in projections.items():
        print(f"  Role '{role}':")
        for item in items:
            qref = item.get('queryRef')
            if not qref:
                print(f"    [!] Item has NO queryRef: {item}")
                continue
            parts = qref.split('.', 1)
            if len(parts) != 2:
                print(f"    [FAIL] Bad format: {qref}")
                continue
            tbl, fld = parts
            if tbl not in model_entities:
                print(f"    [FAIL] Table '{tbl}' NOT in model.bim! Available: {list(model_entities.keys())}")
            elif fld in model_entities[tbl]['columns']:
                print(f"    [OK-COL] {tbl}.{fld} is a COLUMN")
            elif fld in model_entities[tbl]['measures']:
                print(f"    [OK-MEAS] {tbl}.{fld} is a MEASURE")
            else:
                # check case-insensitive match
                col_ci = {k.lower(): k for k in model_entities[tbl]['columns']}
                meas_ci = {k.lower(): k for k in model_entities[tbl]['measures']}
                if fld.lower() in col_ci:
                    print(f"    [CASE-MISMATCH-COL] {tbl}.{fld} -> actual: {col_ci[fld.lower()]}")
                elif fld.lower() in meas_ci:
                    print(f"    [CASE-MISMATCH-MEAS] {tbl}.{fld} -> actual: {meas_ci[fld.lower()]}")
                else:
                    print(f"    [NOT-FOUND] {tbl}.{fld} NOT FOUND in table '{tbl}'!")
                    print(f"      Available cols: {list(model_entities[tbl]['columns'].keys())[:5]}...")
                    print(f"      Available meas: {list(model_entities[tbl]['measures'].keys())}")
