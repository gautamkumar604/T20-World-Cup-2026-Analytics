import os
import json

p_root = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages'
schema_1_0_0 = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainerMobileState/1.0.0/schema.json"

for root, dirs, files in os.walk(p_root):
    if 'mobile.json' in files:
        p = os.path.join(root, 'mobile.json')
        with open(p, 'r', encoding='utf-8') as f:
            d = json.load(f)
        d['$schema'] = schema_1_0_0
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(d, f, indent=2)

print("Standardized all mobile.json schemas to 1.0.0!")
