import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', 'r', encoding='utf-8') as f:
    rep = json.load(f)

s1 = rep['sections'][1]
s2 = rep['sections'][2]

print("Section 1 keys:", list(s1.keys()))
print("Section 2 keys:", list(s2.keys()))

print("\nSection 1 visual types:")
for vc in s1['visualContainers']:
    cfg = json.loads(vc['config'])
    print(cfg.get('name'), cfg.get('singleVisual', {}).get('visualType'))

print("\nSection 2 visual types:")
for vc in s2['visualContainers']:
    cfg = json.loads(vc['config'])
    print(cfg.get('name'), cfg.get('singleVisual', {}).get('visualType'))
