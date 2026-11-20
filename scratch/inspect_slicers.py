import os, json

p3_slicers = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page3_ExecutiveOverview/visuals'
for v in os.listdir(p3_slicers):
    if 'Slicer' in v:
        with open(os.path.join(p3_slicers, v, 'visual.json'), 'r', encoding='utf-8') as f:
            d = json.load(f)
        print(v, json.dumps(d['visual'].get('query'), indent=2))
