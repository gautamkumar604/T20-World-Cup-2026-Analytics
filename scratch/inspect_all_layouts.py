import json

REPORT_PATH = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(REPORT_PATH, 'r', encoding='utf-8') as f:
    rep = json.load(f)

for s_idx, sec in enumerate(rep['sections']):
    s_name = sec.get('name')
    s_disp = sec.get('displayName')
    print(f"\n==================================================================")
    print(f"SECTION {s_idx + 1}: {s_disp} ({s_name})")
    print(f"==================================================================")
    for v_idx, vc in enumerate(sec.get('visualContainers', [])):
        cfg = json.loads(vc['config'])
        vname = cfg.get('name')
        sv = cfg.get('singleVisual', {})
        vtype = sv.get('visualType')
        x, y, w, h = vc.get('x'), vc.get('y'), vc.get('width'), vc.get('height')
        z = vc.get('z')
        print(f"Visual {v_idx+1:02d}: {vname:<30} | Type: {vtype:<15} | x={x:>4}, y={y:>4}, w={w:>4}, h={h:>4}, z={z}")
