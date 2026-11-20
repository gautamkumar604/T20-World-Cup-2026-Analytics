import subprocess, json

raw = subprocess.check_output(['git', '-C', 'D:/my_projects/GGV_projects/T20-World-Cup-2026-Analytics', 'show', 'HEAD:power_bi/T20_World_Cup_2026_Analytics.Report/report.json'], encoding='utf-8')
data = json.loads(raw)
print('Sections in HEAD report.json:')
for s in data.get('sections', []):
    vcount = len(s.get('visualContainers', []))
    print(f" - id={s.get('id')}, name={s.get('name')}, title={s.get('displayName')}, visuals={vcount}")
