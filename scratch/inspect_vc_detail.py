import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', encoding='utf-8') as f:
    rep = json.load(f)

section = rep['sections'][0]
print("Visual 8 (slicer):")
print(json.dumps(section['visualContainers'][7], indent=2)[:800])
print("\n" + "="*50 + "\n")
print("Visual 11 (tableEx):")
print(json.dumps(section['visualContainers'][10], indent=2)[:1200])
