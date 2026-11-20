import json
import os

P3_DIR = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page3_ExecutiveOverview/visuals'

tables = [
    'Table_BestBowlingEconomy',
    'Table_HighestStrikeRate',
    'Table_TopRunScorers',
    'Table_TopWicketTakers'
]

for t in tables:
    vpath = os.path.join(P3_DIR, t, 'visual.json')
    with open(vpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'filterConfig' in data and 'filters' in data['filterConfig']:
        for filt in data['filterConfig']['filters']:
            # Remove properties that violate PBIR FilterContainer schema
            for invalid_prop in ['operator', 'itemCount', 'orderBy']:
                if invalid_prop in filt:
                    del filt[invalid_prop]
            filt['howCreated'] = 'User'
    
    with open(vpath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Cleaned {t}/visual.json successfully.")
