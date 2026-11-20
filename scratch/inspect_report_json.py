import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', encoding='utf-8') as f:
    rep = json.load(f)

print('Report keys:', list(rep.keys()))
sections = rep.get('sections', [])
print(f'Sections/Pages ({len(sections)}):')
for s in sections:
    print(f'  - name: {s.get("name")}, displayName: "{s.get("displayName")}"')
    visuals = s.get('visualContainers', [])
    print(f'    Visuals: {len(visuals)}')
