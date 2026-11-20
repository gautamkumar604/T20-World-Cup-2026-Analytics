import psycopg2, os, json

conn = psycopg2.connect(
    dbname='t20_worldcup_2026',
    user='postgres',
    password=os.environ.get('DB_PASSWORD', 'Gautam@101'),
    host='localhost',
    port=5432
)
cur = conn.cursor()

results = {}

# 1. Phase KPIs
print("--- 1. Phase Breakdown KPIs ---")
cur.execute('''
    SELECT 
        phase,
        SUM(total_runs) AS runs,
        SUM(CASE WHEN is_legal_delivery THEN 1 ELSE 0 END) AS legal_balls,
        ROUND((SUM(total_runs)::numeric / NULLIF(SUM(CASE WHEN is_legal_delivery THEN 1 ELSE 0 END), 0)) * 6.0, 2) AS run_rate,
        SUM(CASE WHEN is_wicket THEN 1 ELSE 0 END) AS total_wickets,
        SUM(CASE WHEN is_wicket AND wicket_kind NOT IN ('run out', 'retired hurt', 'retired out') THEN 1 ELSE 0 END) AS bowler_wickets
    FROM fact_deliveries
    WHERE is_super_over = FALSE
    GROUP BY phase
    ORDER BY CASE phase WHEN 'Powerplay' THEN 1 WHEN 'Middle' THEN 2 WHEN 'Death' THEN 3 ELSE 4 END;
''')
phase_kpis = []
for r in cur.fetchall():
    row = {
        'phase': r[0],
        'runs': int(r[1]),
        'legal_balls': int(r[2]),
        'run_rate': float(r[3]),
        'total_wickets': int(r[4]),
        'bowler_wickets': int(r[5])
    }
    phase_kpis.append(row)
    print(row)
results['phase_kpis'] = phase_kpis

# 2. Toss Impact
print("\n--- 2. Toss Impact ---")
cur.execute('''
    SELECT 
        toss_decision,
        COUNT(*) AS total_matches,
        SUM(CASE WHEN toss_winner = winner THEN 1 ELSE 0 END) AS toss_winner_won,
        SUM(CASE WHEN toss_winner != winner AND outcome_type != 'no result' THEN 1 ELSE 0 END) AS toss_loser_won,
        ROUND(SUM(CASE WHEN toss_winner = winner THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100.0, 2) AS toss_win_pct
    FROM dim_matches
    WHERE toss_decision IS NOT NULL AND outcome_type != 'no result'
    GROUP BY toss_decision;
''')
toss_impact = []
for r in cur.fetchall():
    row = {
        'toss_decision': r[0],
        'total_matches': int(r[1]),
        'toss_winner_won': int(r[2]),
        'toss_loser_won': int(r[3]),
        'toss_win_pct': float(r[4])
    }
    toss_impact.append(row)
    print(row)
results['toss_impact'] = toss_impact

# 3. Boundary Distribution by Phase
print("\n--- 3. Boundary Distribution by Phase ---")
cur.execute('''
    SELECT 
        phase,
        SUM(CASE WHEN is_boundary_four THEN 1 ELSE 0 END) AS total_fours,
        SUM(CASE WHEN is_boundary_six THEN 1 ELSE 0 END) AS total_sixes,
        SUM(CASE WHEN is_boundary_four OR is_boundary_six THEN 1 ELSE 0 END) AS total_boundaries,
        SUM(CASE WHEN is_boundary_four THEN 4 WHEN is_boundary_six THEN 6 ELSE 0 END) AS boundary_runs,
        ROUND(SUM(CASE WHEN is_boundary_four THEN 4 WHEN is_boundary_six THEN 6 ELSE 0 END)::numeric / NULLIF(SUM(total_runs), 0) * 100.0, 2) AS boundary_run_pct
    FROM fact_deliveries
    WHERE is_super_over = FALSE
    GROUP BY phase
    ORDER BY CASE phase WHEN 'Powerplay' THEN 1 WHEN 'Middle' THEN 2 WHEN 'Death' THEN 3 ELSE 4 END;
''')
boundary_dist = []
for r in cur.fetchall():
    row = {
        'phase': r[0],
        'total_fours': int(r[1]),
        'total_sixes': int(r[2]),
        'total_boundaries': int(r[3]),
        'boundary_runs': int(r[4]),
        'boundary_run_pct': float(r[5])
    }
    boundary_dist.append(row)
    print(row)
results['boundary_dist'] = boundary_dist

# 4. Top Bowlers - Powerplay Specialists (Top 5)
print("\n--- 4. Powerplay Specialists (Top 5) ---")
cur.execute('''
    SELECT 
        bowler,
        bowling_team,
        COUNT(DISTINCT match_id) AS matches,
        SUM(CASE WHEN is_legal_delivery THEN 1 ELSE 0 END) AS legal_balls,
        SUM(total_runs) AS runs_conceded,
        SUM(CASE WHEN is_wicket AND wicket_kind NOT IN ('run out', 'retired hurt', 'retired out') THEN 1 ELSE 0 END) AS wickets,
        ROUND((SUM(total_runs)::numeric / NULLIF(SUM(CASE WHEN is_legal_delivery THEN 1 ELSE 0 END), 0)) * 6.0, 2) AS economy
    FROM fact_deliveries
    WHERE phase = 'Powerplay' AND is_super_over = FALSE
    GROUP BY bowler, bowling_team
    ORDER BY wickets DESC, economy ASC, bowler ASC
    LIMIT 5;
''')
pp_bowlers = []
for r in cur.fetchall():
    row = {
        'bowler': r[0],
        'team': r[1],
        'matches': int(r[2]),
        'balls': int(r[3]),
        'runs': int(r[4]),
        'wickets': int(r[5]),
        'economy': float(r[6])
    }
    pp_bowlers.append(row)
    print(row)
results['pp_bowlers'] = pp_bowlers

# 5. Top Bowlers - Death Overs Specialists (Top 5, Min 10 balls)
print("\n--- 5. Death Overs Specialists (Top 5, Min 10 balls) ---")
cur.execute('''
    SELECT 
        bowler,
        bowling_team,
        COUNT(DISTINCT match_id) AS matches,
        SUM(CASE WHEN is_legal_delivery THEN 1 ELSE 0 END) AS legal_balls,
        SUM(total_runs) AS runs_conceded,
        SUM(CASE WHEN is_wicket AND wicket_kind NOT IN ('run out', 'retired hurt', 'retired out') THEN 1 ELSE 0 END) AS wickets,
        ROUND((SUM(total_runs)::numeric / NULLIF(SUM(CASE WHEN is_legal_delivery THEN 1 ELSE 0 END), 0)) * 6.0, 2) AS economy
    FROM fact_deliveries
    WHERE phase = 'Death' AND is_super_over = FALSE
    GROUP BY bowler, bowling_team
    HAVING SUM(CASE WHEN is_legal_delivery THEN 1 ELSE 0 END) >= 10
    ORDER BY economy ASC, wickets DESC, bowler ASC
    LIMIT 5;
''')
death_bowlers = []
for r in cur.fetchall():
    row = {
        'bowler': r[0],
        'team': r[1],
        'matches': int(r[2]),
        'balls': int(r[3]),
        'runs': int(r[4]),
        'wickets': int(r[5]),
        'economy': float(r[6])
    }
    death_bowlers.append(row)
    print(row)
results['death_bowlers'] = death_bowlers

with open('scratch/phase_4_3_pg_baseline.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

conn.close()
