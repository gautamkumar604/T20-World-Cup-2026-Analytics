import json
import os

BASE_DIR = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages'

for root, dirs, files in os.walk(BASE_DIR):
    for f in files:
        if f == 'visual.json':
            vpath = os.path.join(root, f)
            with open(vpath, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
            if 'filterConfig' in data:
                print(f"=== {data.get('name')} ===")
                print(json.dumps(data.get('filterConfig'), indent=2))
