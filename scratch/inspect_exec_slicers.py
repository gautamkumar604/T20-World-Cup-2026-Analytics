import json

report_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(report_path, 'r', encoding='utf-8') as f:
    rep = json.load(f)

s2 = rep['sections'][2]
for idx in [1, 2]:
    vc = s2['visualContainers'][idx]
    cfg = json.loads(vc['config'])
    print(f"=== {cfg.get('name')} ===")
    print(json.dumps(cfg, indent=2))
