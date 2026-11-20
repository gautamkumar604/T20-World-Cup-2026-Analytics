import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', encoding='utf-8') as f:
    rep = json.load(f)

for s in rep.get('sections', []):
    print(f"Section: {s.get('displayName')}")
    for i, vc in enumerate(s.get('visualContainers', [])):
        config_str = vc.get('config', '{}')
        config = json.loads(config_str) if isinstance(config_str, str) else config_str
        single_visual = config.get('singleVisual', {})
        vis_type = single_visual.get('visualType')
        print(f"  Visual {i+1}: type={vis_type}, x={vc.get('x')}, y={vc.get('y')}, width={vc.get('width')}, height={vc.get('height')}")
