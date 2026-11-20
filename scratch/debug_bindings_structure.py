import json

report_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(report_path, 'r', encoding='utf-8') as f:
    rep = json.load(f)

for s_idx, s in enumerate(rep['sections']):
    print(f"=== Section {s_idx}: {s.get('displayName')} ===")
    for vc_idx, vc in enumerate(s.get('visualContainers', [])):
        cfg = json.loads(vc['config'])
        print(f"  Visual {vc_idx}: name={cfg.get('name')}")
        # check top-level keys of vc
        vc_keys = [k for k in vc.keys() if k != 'config']
        print(f"    VC keys: {vc_keys}")
        # check if filters exist
        if 'filters' in vc:
            print(f"    VC filters: {vc['filters'][:100]}")
        # check query in vc if any
        if 'query' in vc:
            print(f"    VC query: {vc['query'][:100]}")
        if 'dataTransforms' in vc:
            print(f"    VC dataTransforms: exists")
        
        # inside config:
        cfg_keys = list(cfg.keys())
        print(f"    config keys: {cfg_keys}")
        sv = cfg.get('singleVisual', {})
        print(f"    singleVisual keys: {list(sv.keys())}")
        if 'prototypeQuery' in sv:
            print(f"    singleVisual prototypeQuery: exists")
        if 'projections' in sv:
            print(f"    singleVisual projections: {sv['projections']}")
        if vc_idx >= 2 and s_idx == 0:
            break
