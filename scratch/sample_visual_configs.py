import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', 'r', encoding='utf-8') as f:
    rep = json.load(f)

for vc in rep['sections'][0]['visualContainers']:
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    vtype = cfg.get('singleVisual', {}).get('visualType')
    if vtype in ('textbox', 'card', 'slicer', 'tableEx', 'donutChart'):
        print(f"\n=================== {vname} ({vtype}) ===================")
        print(json.dumps(cfg, indent=2))
