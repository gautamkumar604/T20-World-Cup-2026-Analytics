import os
import json

print("=== 1. VERIFY NO LEGACY REPORT.JSON ===")
legacy_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
assert not os.path.exists(legacy_path), "Error: Legacy report.json exists! Must be removed."
print("[OK] No conflicting legacy report.json present.")

print("\n=== 2. VERIFY MOBILE LAYOUTS (PORTRAIT MODE) ===")
p_root = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages'
mobile_schema_const = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainerMobileState/1.0.0/schema.json"

mobile_count = 0
for p in sorted(os.listdir(p_root)):
    pdir = os.path.join(p_root, p)
    if not os.path.isdir(pdir): continue
    vdir = os.path.join(pdir, 'visuals')
    if not os.path.exists(vdir): continue
    print(f"\n--- {p} Mobile Visuals ---")
    for vf in sorted(os.listdir(vdir)):
        mpath = os.path.join(vdir, vf, 'mobile.json')
        if os.path.exists(mpath):
            with open(mpath, 'r', encoding='utf-8') as f:
                mdata = json.load(f)
            assert mdata.get("$schema") == mobile_schema_const, f"Invalid schema in {mpath}"
            pos = mdata.get("position", {})
            assert "x" in pos and "y" in pos and "width" in pos and "height" in pos, f"Incomplete position in {mpath}"
            assert pos["width"] <= 340, f"Width exceeds mobile container in {mpath}"
            print(f"  [OK] {vf:30}: y={pos['y']:4}, h={pos['height']:3}, w={pos['width']:3}")
            mobile_count += 1

print(f"\nTotal mobile visual definitions verified: {mobile_count}")

print("\n=== 3. VERIFY SLICER SYNCING ===")
# StageSyncGroup
for p, v in [
    ('ReportSection_Page1_Overview', 'Slicer_Stage'),
    ('ReportSection_Page3_ExecutiveOverview', 'Slicer_Stage_Exec'),
    ('ReportSection_Page4_TacticalAnalysis', 'Slicer_Stage_Tactical')
]:
    vpath = os.path.join(p_root, p, 'visuals', v, 'visual.json')
    with open(vpath, 'r', encoding='utf-8') as f:
        d = json.load(f)
    sg = d.get('visual', {}).get('syncGroup', {})
    assert sg.get('groupName') == 'StageSyncGroup', f"Missing StageSyncGroup in {p}/{v}"
    print(f"  [OK] Stage Slicer Sync: {p}/{v} -> {sg}")

# TeamSyncGroup
for p, v in [
    ('ReportSection_Page1_Overview', 'Slicer_Country'),
    ('ReportSection_Page3_ExecutiveOverview', 'Slicer_Team_Exec'),
    ('ReportSection_Page4_TacticalAnalysis', 'Slicer_Team_Tactical')
]:
    vpath = os.path.join(p_root, p, 'visuals', v, 'visual.json')
    with open(vpath, 'r', encoding='utf-8') as f:
        d = json.load(f)
    sg = d.get('visual', {}).get('syncGroup', {})
    assert sg.get('groupName') == 'TeamSyncGroup', f"Missing TeamSyncGroup in {p}/{v}"
    print(f"  [OK] Team Slicer Sync: {p}/{v} -> {sg}")

# Page 2 Isolation
for v in ['Slicer_Stage_Standings', 'Slicer_Group_Standings']:
    vpath = os.path.join(p_root, 'ReportSection_Page2_Standings', 'visuals', v, 'visual.json')
    with open(vpath, 'r', encoding='utf-8') as f:
        d = json.load(f)
    assert 'syncGroup' not in d.get('visual', {}), f"Page 2 slicer {v} must not have syncGroup!"
    print(f"  [OK] Page 2 Slicer Isolated: {v} (no syncGroup)")

print("\n=== 4. VERIFY HEADER BANNER ALIGNMENT & COLOR ===")
for p, v in [
    ('ReportSection_Page1_Overview', 'HeaderBanner'),
    ('ReportSection_Page2_Standings', 'HeaderBanner_Standings'),
    ('ReportSection_Page3_ExecutiveOverview', 'HeaderBanner_Executive'),
    ('ReportSection_Page4_TacticalAnalysis', 'HeaderBanner_Tactical')
]:
    vpath = os.path.join(p_root, p, 'visuals', v, 'visual.json')
    with open(vpath, 'r', encoding='utf-8') as f:
        d = json.load(f)
    pos = d.get('position', {})
    assert pos.get('y') == 10 and pos.get('height') == 60, f"Header misaligned in {p}/{v}"
    paras = d['visual']['objects']['general'][0]['properties']['paragraphs']
    color = paras[0]['textRuns'][0]['textStyle']['color']
    assert color.upper() == '#1A365D', f"Header color mismatch in {p}/{v}: {color}"
    print(f"  [OK] Header {p}/{v}: y=10, h=60, color={color}")

print("\n=== 5. VERIFY PAGE 2 VISUAL INTERACTIONS ===")
p2_page_path = os.path.join(p_root, 'ReportSection_Page2_Standings', 'page.json')
with open(p2_page_path, 'r', encoding='utf-8') as f:
    p2_page = json.load(f)
vi = p2_page.get('visualInteractions', [])
assert len(vi) >= 2, "Page 2 visualInteractions missing!"
print(f"  [OK] Page 2 visualInteractions configured: {vi}")

print("\n=== 6. VERIFY THEME FILE ===")
theme_path = 'power_bi/theme/CyberCricketTheme.json'
assert os.path.exists(theme_path), "Theme file missing!"
with open(theme_path, 'r', encoding='utf-8') as f:
    tdata = json.load(f)
assert tdata.get('name') == 'CyberCricketTheme', "Invalid theme name"
print(f"  [OK] Theme CyberCricketTheme.json verified: {list(tdata.keys())}")

print("\n=== 7. TOTAL FILE SYNTAX VALIDATION ===")
count = 0
for root, dirs, files in os.walk('power_bi'):
    for f in files:
        if f.endswith(('.json', '.bim', '.pbip', '.pbir', '.pbism')):
            p = os.path.join(root, f)
            with open(p, 'r', encoding='utf-8') as fp:
                json.load(fp)
            count += 1
print(f"Validated all {count} files in power_bi with 0 syntax errors!")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
