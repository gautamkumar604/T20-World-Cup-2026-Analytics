import json

report_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(report_path, 'r', encoding='utf-8') as f:
    rep = json.load(f)

s0 = rep['sections'][0]
print(f"=== SECTION: {s0['displayName']} ({s0['name']}) ===")
for idx, vc in enumerate(s0['visualContainers']):
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    sv = cfg.get('singleVisual', {})
    vtype = sv.get('visualType')
    has_pq = 'prototypeQuery' in sv
    print(f"\nVisual {idx+1}: {vname} ({vtype}), has_pq={has_pq}")
    print(f"  projections: {json.dumps(sv.get('projections', {}), indent=2)}")
