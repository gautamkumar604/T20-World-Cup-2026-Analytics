import os, json

p4_dir = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page4_TacticalAnalysis/visuals'
for vf in os.listdir(p4_dir):
    with open(os.path.join(p4_dir, vf, 'visual.json'), 'r', encoding='utf-8') as f:
        v = json.load(f)
    p = v['position']
    print(f"{vf:30} x={p['x']:4}, y={p['y']:4}, w={p['width']:4}, h={p['height']:4} -> right={p['x']+p['width']}")
