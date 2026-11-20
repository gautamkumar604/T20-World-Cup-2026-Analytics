import json

REPORT_PATH = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(REPORT_PATH, 'r', encoding='utf-8') as f:
    rep = json.load(f)

for s in rep['sections']:
    for vc in s['visualContainers']:
        cfg = json.loads(vc['config'])
        if 'Runs' in cfg.get('name', ''):
            print(f"Section {s['displayName']} - Visual {cfg['name']}:")
            print(json.dumps(cfg['singleVisual'].get('objects', {}), indent=2))
