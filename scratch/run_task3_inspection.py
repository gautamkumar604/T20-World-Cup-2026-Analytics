import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', 'r', encoding='utf-8') as f:
    rep = json.load(f)

for s in rep['sections'][:2]:
    print(f"\n================ SECTION: {s['displayName']} ================")
    for vc in s['visualContainers']:
        cfg = json.loads(vc['config'])
        vname = cfg.get('name')
        sv = cfg.get('singleVisual', {})
        proj = sv.get('projections', {})
        print(f"Visual: {vname} ({sv.get('visualType')})")
        print(f"  projections: {proj}")
        print(f"  has prototypeQuery: {'prototypeQuery' in sv}")
