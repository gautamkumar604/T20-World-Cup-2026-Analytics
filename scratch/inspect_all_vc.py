import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', encoding='utf-8') as f:
    rep = json.load(f)

for i, vc in enumerate(rep['sections'][0]['visualContainers']):
    cfg = json.loads(vc['config'])
    sv = cfg.get('singleVisual', {})
    print(f"Visual {i+1}:")
    print(f"  name: {cfg.get('name')}")
    print(f"  type: {sv.get('visualType')}")
    print(f"  projections: {sv.get('projections')}")
    print(f"  objects keys: {list(sv.get('objects', {}).keys())}")
    print(f"  vc keys: {list(vc.keys())}")
    print("-" * 40)
