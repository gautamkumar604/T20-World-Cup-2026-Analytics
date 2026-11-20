import json

REPORT_PATH = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(REPORT_PATH, 'r', encoding='utf-8') as f:
    rep = json.load(f)

s1 = rep['sections'][1]
for vc in s1['visualContainers']:
    cfg = json.loads(vc['config'])
    if cfg.get('name') == 'Matrix_TournamentStandings':
        print("=== Matrix_TournamentStandings config ===")
        print(json.dumps(cfg, indent=2))
