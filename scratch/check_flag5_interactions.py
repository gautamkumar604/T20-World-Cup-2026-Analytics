import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', 'r', encoding='utf-8') as f:
    rep = json.load(f)

for s in rep['sections']:
    print(f"Section {s.get('displayName')}:")
    for k in s.keys():
        if k != 'visualContainers':
            print(f"  {k}: {s[k]}")
    # check visual container configs for interaction / cross
    for vc in s.get('visualContainers', []):
        cfg = json.loads(vc['config'])
        if 'Matrix_TeamWinRate' in cfg.get('name', ''):
            print("  Found Matrix_TeamWinRate container:")
            print(json.dumps(cfg, indent=2))
        for k in cfg.keys():
            if 'interact' in k.lower() or 'cross' in k.lower():
                print(f"  Visual {cfg.get('name')} has interaction key: {k}")

# Check top level for visualInteractions
print("Top-level keys in report.json:", list(rep.keys()))
if 'visualInteractions' in rep:
    print("Found visualInteractions in root report.json!")
    print(rep['visualInteractions'])
for s in rep['sections']:
    if 'visualInteractions' in s:
        print(f"Found visualInteractions in section {s.get('displayName')}!")
