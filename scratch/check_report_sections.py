import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', 'r', encoding='utf-8') as f:
    rep = json.load(f)

print(f"Total sections: {len(rep.get('sections', []))}")
for i, s in enumerate(rep.get('sections', [])):
    print(f"Section {i}: name='{s.get('name')}', displayName='{s.get('displayName')}'")
    containers = s.get('visualContainers', [])
    print(f"   Visual containers count: {len(containers)}")
    for vc in containers:
        cfg = json.loads(vc.get('config', '{}'))
        vname = cfg.get('name', 'unnamed')
        vtype = cfg.get('singleVisual', {}).get('visualType', 'unknown')
        print(f"     - {vname} ({vtype})")
