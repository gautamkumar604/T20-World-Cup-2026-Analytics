import os, json

p_root = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages'
for root, dirs, files in os.walk(p_root):
    if 'mobile.json' in files:
        p = os.path.join(root, 'mobile.json')
        with open(p, 'r', encoding='utf-8') as f:
            d = json.load(f)
        print(p, '->', d.get('$schema'))
