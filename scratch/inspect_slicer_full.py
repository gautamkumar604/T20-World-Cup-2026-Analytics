import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page3_ExecutiveOverview/visuals/Slicer_Stage_Exec/visual.json', 'r', encoding='utf-8') as f:
    s = json.load(f)

print(json.dumps(s, indent=2))
