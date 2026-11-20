import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page1_Overview/visuals/Donut_MatchOutcomes/visual.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

print(json.dumps(d, indent=2))
