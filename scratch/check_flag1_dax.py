with open('power_bi/dax_measures.dax', 'r', encoding='utf-8') as f:
    content = f.read()

target_measures = [
    'Player Strike Rate',
    'Player Strike Rate (Min 100 Runs)',
    'Player Economy Rate',
    'Player Economy Rate (Min 10 Overs)',
    'Team Win Pct',
    'Venue Avg First Innings Score',
    'Venue Avg Second Innings Score'
]

for m in target_measures:
    print(f"=== MEASURE: {m} ===")
    pattern = f"// Measure: {m}\n"
    if pattern in content:
        start = content.index(pattern)
        # find next measure or end
        next_m = content.find("// Measure:", start + len(pattern))
        if next_m != -1:
            print(content[start:next_m].strip())
        else:
            print(content[start:].strip())
    else:
        print("NOT FOUND")
    print()
