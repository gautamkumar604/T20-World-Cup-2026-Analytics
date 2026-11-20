import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', 'r', encoding='utf-8') as f:
    rep = json.load(f)

s2 = rep['sections'][2]
for vc in s2['visualContainers']:
    cfg = json.loads(vc['config'])
    if cfg.get('name') in ('Card_Exec_HighestScore', 'Card_Exec_LowestScore'):
        print(f"=== {cfg.get('name')} ===")
        print(json.dumps(cfg, indent=2))
        sv = cfg.get('singleVisual', {})
        proj = sv.get('projections', {})
        print("projections:", proj)
        print("has prototypeQuery:", 'prototypeQuery' in sv)
        if 'prototypeQuery' in sv:
            print("Select array:", sv['prototypeQuery'].get('Select'))
        else:
            print("Select array: MISSING (prototypeQuery is absent)")
        print()

print("Checking visualInteractions or filterConfig on Section 2:")
print("Section 2 filters:", s2.get('filters'))
print("Section 2 visualInteractions:", s2.get('visualInteractions'))
for vc in s2['visualContainers']:
    if 'filters' in vc:
        print(f"Visual {json.loads(vc['config']).get('name')} has visual-level filters: {vc['filters']}")
