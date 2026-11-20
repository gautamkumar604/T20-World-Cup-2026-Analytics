import json

report_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(report_path, 'r', encoding='utf-8') as f:
    rep = json.load(f)

for s_idx, sec in enumerate(rep['sections']):
    print(f"\nSection {s_idx}: {sec['displayName']}")
    for v_idx, vc in enumerate(sec['visualContainers']):
        print(f"  VC {v_idx+1} keys: {list(vc.keys())}")
        if 'filters' in vc:
            print(f"    filters: {vc['filters']}")
