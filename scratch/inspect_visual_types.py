import os, json

p_root = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages'
for root, dirs, files in os.walk(p_root):
    for f in files:
        if f == 'visual.json':
            with open(os.path.join(root, f), 'r', encoding='utf-8') as fp:
                v = json.load(fp)
                vt = v.get('visual', {}).get('visualType')
                qs = v.get('visual', {}).get('query', {}).get('queryState', {})
                print(f"{v.get('name')}: {vt} -> channels: {list(qs.keys())}")
