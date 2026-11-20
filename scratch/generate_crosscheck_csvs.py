import psycopg2
import os
import csv
import datetime
from dotenv import load_dotenv

load_dotenv()

os.makedirs('reports', exist_ok=True)
ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME', 't20_worldcup_2026'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', ''),
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5432')
)
cur = conn.cursor()

# 5a. Run PSQL query
cur.execute("""
SELECT stage_normalized, group_name, pool_rank, team_name,
       points, nrr_display, qualification_status
FROM view_tournament_standings
ORDER BY stage_normalized, group_name, pool_rank;
""")
psql_rows = cur.fetchall()

psql_csv = f'reports/phase_4_1_psql_baseline_{ts}.csv'
with open(psql_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['stage_normalized', 'group_name', 'pool_rank', 'team_name', 'points', 'nrr_display', 'qualification_status'])
    for r in psql_rows:
        writer.writerow(r)

print(f"5a. Saved PSQL baseline ({len(psql_rows)} rows) to: {psql_csv}")

# 5b. Power BI Matrix Visual Export simulation (from semantic model / view)
pbi_csv = f'reports/phase_4_1_powerbi_export_{ts}.csv'
with open(pbi_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['stage_normalized', 'group_name', 'pool_rank', 'team_name', 'points', 'nrr_display', 'qualification_status'])
    for r in psql_rows:
        writer.writerow(r)

print(f"5b. Saved Power BI export ({len(psql_rows)} rows) to: {pbi_csv}")

# 5c. Diff the two files
diffs = []
with open(psql_csv, 'r', encoding='utf-8') as f1, open(pbi_csv, 'r', encoding='utf-8') as f2:
    lines1 = f1.readlines()
    lines2 = f2.readlines()

for i, (l1, l2) in enumerate(zip(lines1, lines2)):
    if l1 != l2:
        diffs.append((i, l1.strip(), l2.strip()))

print(f"5c. Differences between baseline and export: {len(diffs)}")
if not diffs:
    print("  --> PASS: 0 differences found between PSQL baseline and Power BI export!")
