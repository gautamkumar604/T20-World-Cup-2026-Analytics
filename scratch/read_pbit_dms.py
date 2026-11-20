import zipfile
import json

with zipfile.ZipFile('power_bi/T20_World_Cup_2026_Analytics.pbit', 'r') as z:
    dms_bytes = z.read('DataModelSchema')
    try:
        dms_str = dms_bytes.decode('utf-16-le')
    except Exception:
        dms_str = dms_bytes.decode('utf-8')
    dms_json = json.loads(dms_str)

for t in dms_json.get('model', {}).get('tables', []):
    meas = [m['name'] for m in t.get('measures', [])]
    if meas:
        print(f"Table: {t['name']}")
        for m in meas:
            print(f"  - '{m}'")
