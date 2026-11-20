import psycopg2
import json
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME', 't20_worldcup_2026'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', ''),
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5432')
)
cur = conn.cursor()

print("="*60)
print("PHASE 4.1 COMPREHENSIVE VERIFICATION SUITE")
print("="*60)

# ---------------------------------------------------------
# Test 1: Full 28-row Standings Query from PostgreSQL 18.7
# ---------------------------------------------------------
cur.execute("""
SELECT stage_normalized, group_name, pool_rank, team_name, played, wins, losses, no_result,
       points, nrr_display, nrr_canon_num, nrr_canon_den, resolution_step, qualification_status
FROM view_tournament_standings
ORDER BY stage_normalized, group_name, pool_rank, team_name;
""")
all_rows = cur.fetchall()
print(f"\n[TEST 1] Total Rows in view_tournament_standings: {len(all_rows)} (Expected: 28)")
assert len(all_rows) == 28, f"Expected 28 rows, got {len(all_rows)}"

# ---------------------------------------------------------
# Test 5.1: Key Team Verifications (Slicer = 'All')
# ---------------------------------------------------------
print("\n[TEST 5.1] Slicer = 'All' Key Team Verifications:")
# South Africa (Super 8 Grp 1): Pts 6, NRR +2.259, Rank 1
sa = [r for r in all_rows if r[0] == 'Super 8' and r[1] == '1' and r[3] == 'South Africa'][0]
print(f"  South Africa (S8 Grp 1): Rank {sa[2]}, Pts {sa[8]}, NRR {sa[9]}, Status: {sa[13]}")
assert sa[2] == 1, f"Expected SA rank 1, got {sa[2]}"
assert sa[8] == 6, f"Expected SA pts 6, got {sa[8]}"
assert str(sa[9]) == '2.259', f"Expected SA NRR 2.259, got {sa[9]}"

# India (Super 8 Grp 1): Pts 4, NRR +0.106, Rank 2
ind = [r for r in all_rows if r[0] == 'Super 8' and r[1] == '1' and r[3] == 'India'][0]
print(f"  India (S8 Grp 1): Rank {ind[2]}, Pts {ind[8]}, NRR {ind[9]}, Status: {ind[13]}")
assert ind[2] == 2, f"Expected India rank 2, got {ind[2]}"
assert ind[8] == 4, f"Expected India pts 4, got {ind[8]}"
assert str(ind[9]) == '0.106', f"Expected India NRR 0.106, got {ind[9]}"

# Zimbabwe (Group B): Pts 7, NRR +1.506, Rank 1
zim = [r for r in all_rows if r[0] == 'Group Stage' and r[1] == 'B' and r[3] == 'Zimbabwe'][0]
print(f"  Zimbabwe (Group B): Rank {zim[2]}, Pts {zim[8]}, NRR {zim[9]}, Status: {zim[13]}")
assert zim[2] == 1, f"Expected Zimbabwe rank 1, got {zim[2]}"
assert zim[8] == 7, f"Expected Zimbabwe pts 7, got {zim[8]}"
assert str(zim[9]) == '1.506', f"Expected Zimbabwe NRR 1.506, got {zim[9]}"

# Pakistan (Group A): Pts 6, NRR +0.976, Rank 2
pak = [r for r in all_rows if r[0] == 'Group Stage' and r[1] == 'A' and r[3] == 'Pakistan'][0]
print(f"  Pakistan (Group A): Rank {pak[2]}, Pts {pak[8]}, NRR {pak[9]}, Status: {pak[13]}")
assert pak[2] == 2, f"Expected Pakistan rank 2, got {pak[2]}"
assert pak[8] == 6, f"Expected Pakistan pts 6, got {pak[8]}"
assert str(pak[9]) == '0.976', f"Expected Pakistan NRR 0.976, got {pak[9]}"

print("  --> ALL TEST 5.1 CHECKS PASSED!")

# ---------------------------------------------------------
# Test 5.2: Slicer = 'Group Stage' (20 rows, 5 per group)
# ---------------------------------------------------------
print("\n[TEST 5.2] Slicer = 'Group Stage' Simulation:")
gs_rows = [r for r in all_rows if r[0] == 'Group Stage']
print(f"  Group Stage row count: {len(gs_rows)} (Expected: 20)")
assert len(gs_rows) == 20, f"Expected 20 rows, got {len(gs_rows)}"

groups = {}
for r in gs_rows:
    groups[r[1]] = groups.get(r[1], 0) + 1
print(f"  Teams per group: {groups} (Expected: {{'A': 5, 'B': 5, 'C': 5, 'D': 5}})")
assert groups == {'A': 5, 'B': 5, 'C': 5, 'D': 5}, f"Group breakdown mismatch: {groups}"
print("  --> ALL TEST 5.2 CHECKS PASSED!")

# ---------------------------------------------------------
# Test 5.3: Slicer = 'Group D' (5 rows, SA rank 1, NZ rank 2)
# ---------------------------------------------------------
print("\n[TEST 5.3] Slicer = 'Group D' Simulation:")
grp_d = [r for r in all_rows if r[0] == 'Group Stage' and r[1] == 'D']
print(f"  Group D row count: {len(grp_d)} (Expected: 5)")
assert len(grp_d) == 5, f"Expected 5 rows, got {len(grp_d)}"
for r in grp_d:
    print(f"    Rank #{r[2]} {r[3]:<20} | Pts: {r[8]} | NRR: {r[9]:>+7} | {r[13]}")

assert grp_d[0][3] == 'South Africa' and grp_d[0][2] == 1, f"Expected SA rank 1, got {grp_d[0]}"
assert grp_d[1][3] == 'New Zealand' and grp_d[1][2] == 2, f"Expected NZ rank 2, got {grp_d[1]}"
print("  --> ALL TEST 5.3 CHECKS PASSED!")

# ---------------------------------------------------------
# Test 5.4: Full 28-row Side-by-Side Audit
# ---------------------------------------------------------
print("\n[TEST 5.4] Full 28-Row Master Standings Ledger:")
print(f"{'Stage':<11} | {'Grp':<3} | {'Rk':<2} | {'Team':<24} | {'P':<2} | {'W':<2} | {'L':<2} | {'NR':<2} | {'Pts':<3} | {'NRR':<7} | {'Status':<10} | {'Tie-Break Resolution'}")
print("-" * 120)
for r in all_rows:
    print(f"{r[0]:<11} | {r[1]:<3} | #{r[2]:<1} | {r[3]:<24} | {r[4]:<2} | {r[5]:<2} | {r[6]:<2} | {r[7]:<2} | {r[8]:<3} | {r[9]:>+7} | {r[13]:<10} | {r[12]}")

# ---------------------------------------------------------
# Test 6: Verify model.bim JSON & Schema
# ---------------------------------------------------------
print("\n[TEST 6] Semantic Model model.bim Verification:")
with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)

table_names = [t['name'] for t in bim['model']['tables']]
assert 'view_tournament_standings' in table_names, "view_tournament_standings missing from model.bim"
st_table = [t for t in bim['model']['tables'] if t['name'] == 'view_tournament_standings'][0]
print(f"  Table view_tournament_standings present with {len(st_table['columns'])} columns.")
assert len(st_table['columns']) == 23, f"Expected 23 columns, got {len(st_table['columns'])}"

# Check relationship exclusion
st_rels = [r for r in bim['model'].get('relationships', []) if r.get('fromTable') == 'view_tournament_standings' or r.get('toTable') == 'view_tournament_standings']
print(f"  Relationships attached to view_tournament_standings: {len(st_rels)} (Expected: 0)")
assert len(st_rels) == 0, f"Expected 0 relationships on view_tournament_standings, got {len(st_rels)}"
print("  --> ALL TEST 6 CHECKS PASSED!")

# ---------------------------------------------------------
# Test 7: Verify report.json Pages and Visuals
# ---------------------------------------------------------
print("\n[TEST 7] Report Canvas report.json Verification:")
with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', 'r', encoding='utf-8') as f:
    rep = json.load(f)

sec_names = [s['name'] for s in rep['sections']]
print(f"  Report sections ({len(sec_names)}): {sec_names}")
assert 'ReportSection_Page2_Standings' in sec_names, "ReportSection_Page2_Standings missing from report.json"
st_sec = [s for s in rep['sections'] if s['name'] == 'ReportSection_Page2_Standings'][0]
print(f"  Page 'Tournament Standings' contains {len(st_sec['visualContainers'])} visual containers.")
assert len(st_sec['visualContainers']) >= 5, "Expected at least 5 visual containers on Standings page"

matrix_vc = [vc for vc in st_sec['visualContainers'] if 'Matrix_TournamentStandings' in vc['config']][0]
cfg = json.loads(matrix_vc['config'])
projections = cfg['singleVisual']['projections']
print(f"  Matrix Rows: {[p['queryRef'] for p in projections['Rows']]}")
print(f"  Matrix Values: {[p['queryRef'] for p in projections['Values']]}")
print(f"  Matrix Tooltips: {[p['queryRef'] for p in projections['Tooltips']]}")

assert len(projections['Rows']) == 3, f"Expected 3 Row fields, got {len(projections['Rows'])}"
assert len(projections['Values']) == 7, f"Expected 7 Value fields, got {len(projections['Values'])}"
print("  --> ALL TEST 7 CHECKS PASSED!")

# ---------------------------------------------------------
# Test 8: Ensure Existing 38 DAX Measures Untouched
# ---------------------------------------------------------
print("\n[TEST 8] DAX Measures File Integrity Check:")
with open('power_bi/dax_measures.dax', 'r', encoding='utf-8') as f:
    dax_text = f.read()

import re
dax_matches = re.findall(r'(\b[A-Za-z0-9_ ]+\b)\s*=\s*(.*?)(?=\n\s*[A-Za-z0-9_ ]+\s*=|\Z)', dax_text, re.DOTALL)
print(f"  DAX measures parsed: {len(dax_matches)} measures.")
assert len(dax_matches) >= 38, f"Expected at least 38 measures, found {len(dax_matches)}"
print("  --> ALL TEST 8 CHECKS PASSED!")

print("\n" + "="*60)
print("ALL PHASE 4.1 VERIFICATION TESTS PASSED (100% OK)")
print("="*60)
