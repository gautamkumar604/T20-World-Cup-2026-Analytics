import re
import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', 'r', encoding='utf-8') as f:
    rep = json.load(f)

for s in rep['sections']:
    print(f"\n================ SECTION: {s['displayName']} ================")
    for vc in s.get('visualContainers', []):
        cfg = json.loads(vc['config'])
        sv = cfg.get('singleVisual', {})
        proj = sv.get('projections', {})
        if proj:
            print(f"Visual {cfg.get('name')} ({sv.get('visualType')}):")
            for role, items in proj.items():
                refs = [item.get('queryRef') for item in items if isinstance(item, dict)]
                print(f"  {role}: {refs}")
