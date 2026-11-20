import os, json

p_root = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages'
pages_json = os.path.join(p_root, 'pages.json')
with open(pages_json, 'r', encoding='utf-8') as f:
    meta = json.load(f)
print('Page Order in PBIR:', meta.get('pageOrder'))

for p in meta.get('pageOrder', []):
    pdir = os.path.join(p_root, p)
    with open(os.path.join(pdir, 'page.json'), 'r', encoding='utf-8') as f:
        pj = json.load(f)
    vdir = os.path.join(pdir, 'visuals')
    vcount = len(os.listdir(vdir)) if os.path.exists(vdir) else 0
    print(f" - {p}: displayName='{pj.get('displayName')}', visuals={vcount}")

print("\nChecking file counts in power_bi directory:")
count = 0
for root, dirs, files in os.walk('power_bi'):
    for f in files:
        if f.endswith(('.json', '.bim', '.pbip', '.pbir', '.pbism')):
            p = os.path.join(root, f)
            with open(p, 'r', encoding='utf-8') as fp:
                json.load(fp)
            count += 1
print(f"Validated all {count} files in power_bi: 0 syntax errors!")
