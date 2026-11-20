import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page3_ExecutiveOverview/visuals/Table_TopWicketTakers/visual.json', 'r', encoding='utf-8') as f:
    tw = json.load(f)
print('=== Table_TopWicketTakers ===')
print(json.dumps(tw, indent=2))

with open('power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page3_ExecutiveOverview/visuals/Table_BestBowlingEconomy/visual.json', 'r', encoding='utf-8') as f:
    be = json.load(f)
print('\n=== Table_BestBowlingEconomy ===')
print(json.dumps(be, indent=2))
