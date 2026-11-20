import json

with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

print('Tables in model.bim:')
for t in bim['model']['tables']:
    cols = [c['name'] for c in t.get('columns', [])]
    measures = [m['name'] for m in t.get('measures', [])]
    print(f" - {t['name']}: {len(cols)} cols, {len(measures)} measures")
    if t['name'] in ['fact_deliveries', 'dim_matches', 'vw_toss_impact', 'vw_boundary_analysis', 'vw_phase_wise_performance']:
        print(f"    Columns: {cols[:15]}...")
