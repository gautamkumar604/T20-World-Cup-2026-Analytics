import json

report_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(report_path, 'r', encoding='utf-8') as f:
    rep = json.load(f)

s2 = rep['sections'][2]
for idx in [12, 13, 14, 15]:
    vc = s2['visualContainers'][idx]
    cfg = json.loads(vc['config'])
    print(f"=== Visual {idx+1}: {cfg.get('name')} ===")
    sv = cfg.get('singleVisual', {})
    print("projections:", json.dumps(sv.get('projections'), indent=2))
    print("prototypeQuery:", json.dumps(sv.get('prototypeQuery'), indent=2))
    print("sortDefinition:", json.dumps(sv.get('sortDefinition'), indent=2))
    print("filters in vc:", vc.get('filters'))
    print("filters in config:", cfg.get('filters'))
