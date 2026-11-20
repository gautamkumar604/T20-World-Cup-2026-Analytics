import zipfile
import json

with zipfile.ZipFile('power_bi/T20_World_Cup_2026_Analytics.pbit', 'r') as z:
    layout_bytes = z.read('Layout')
    # Layout is typically UTF-16-LE
    try:
        layout_str = layout_bytes.decode('utf-16-le')
    except Exception:
        layout_str = layout_bytes.decode('utf-8')
    layout_json = json.loads(layout_str)

print("Layout keys:", list(layout_json.keys()))
print("Sections count:", len(layout_json.get('sections', [])))
for s in layout_json.get('sections', []):
    print(f"Section: {s.get('displayName')}, visuals: {len(s.get('visualContainers', []))}")
    for vc in s.get('visualContainers', [])[:3]:
        cfg = json.loads(vc['config'])
        print(f"  Visual: {cfg.get('name')}")
        sv = cfg.get('singleVisual', {})
        print("    singleVisual keys:", list(sv.keys()))
        if 'prototypeQuery' in sv:
            print("    prototypeQuery:", json.dumps(sv['prototypeQuery'], indent=2))
        if 'projections' in sv:
            print("    projections:", json.dumps(sv['projections'], indent=2))
