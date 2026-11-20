import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', 'r', encoding='utf-8') as f:
    rep = json.load(f)

for vc in rep['sections'][2]['visualContainers']:
    cfg = json.loads(vc['config'])
    if cfg.get('name') == 'Card_Exec_HighestScore':
        print(json.dumps(cfg, indent=2))
