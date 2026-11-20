import os, json

p3_visuals = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page3_ExecutiveOverview/visuals'
for v in os.listdir(p3_visuals):
    if 'Header' in v or 'Banner' in v or 'Title' in v:
        with open(os.path.join(p3_visuals, v, 'visual.json'), 'r', encoding='utf-8') as f:
            d = json.load(f)
        print(v, json.dumps(d, indent=2))
