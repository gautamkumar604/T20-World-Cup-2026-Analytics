import json
import os
import uuid

# --- 1. UPDATE MODEL.BIM ---
bim_path = 'power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim'
with open(bim_path, 'r', encoding='utf-8') as f:
    bim = json.load(f)

# A. Add calculated columns and measure to dim_matches
for t in bim['model']['tables']:
    if t['name'] == 'dim_matches':
        existing_cols = {c['name'] for c in t.get('columns', [])}
        
        # Calculated column 1: Toss Decision Label
        if 'Toss Decision Label' not in existing_cols:
            t['columns'].append({
                "name": "Toss Decision Label",
                "dataType": "string",
                "type": "calculated",
                "expression": "IF(ISBLANK(dim_matches[toss_decision]), BLANK(), IF(dim_matches[toss_decision] = \"bat\", \"Bat First\", \"Bowl / Field First\"))",
                "isNullable": True,
                "summarizeBy": "none",
                "lineageTag": str(uuid.uuid4())
            })
            print("Added 'Toss Decision Label' calculated column to dim_matches.")
            
        # Calculated column 2: Toss Match Result
        if 'Toss Match Result' not in existing_cols:
            t['columns'].append({
                "name": "Toss Match Result",
                "dataType": "string",
                "type": "calculated",
                "expression": "IF(ISBLANK(dim_matches[toss_decision]) || dim_matches[outcome_type] = \"no result\", BLANK(), IF(dim_matches[toss_winner] = dim_matches[winner], \"Toss Winner Won\", \"Toss Loser Won\"))",
                "isNullable": True,
                "summarizeBy": "none",
                "lineageTag": str(uuid.uuid4())
            })
            print("Added 'Toss Match Result' calculated column to dim_matches.")
            
        # Measure in dim_matches: Toss Completed Matches
        existing_measures = {m['name'] for m in t.get('measures', [])}
        if 'Toss Completed Matches' not in existing_measures:
            if 'measures' not in t:
                t['measures'] = []
            t['measures'].append({
                "name": "Toss Completed Matches",
                "expression": "CALCULATE(COUNTROWS(dim_matches), NOT(ISBLANK(dim_matches[toss_decision])), dim_matches[outcome_type] <> \"no result\")",
                "formatString": "#,##0",
                "lineageTag": str(uuid.uuid4())
            })
            print("Added 'Toss Completed Matches' measure to dim_matches.")

    # B. Add measures to fact_deliveries
    if t['name'] == 'fact_deliveries':
        if 'measures' not in t:
            t['measures'] = []
        existing_measures = {m['name'] for m in t['measures']}
        
        deliveries_measures = [
            {
                "name": "Powerplay Run Rate",
                "expression": (
                    "VAR TotalRuns = CALCULATE(SUM(fact_deliveries[total_runs]), fact_deliveries[phase] = \"Powerplay\", fact_deliveries[is_super_over] = FALSE())\n"
                    "VAR LegalBalls = CALCULATE(COUNTROWS(fact_deliveries), fact_deliveries[phase] = \"Powerplay\", fact_deliveries[is_legal_delivery] = TRUE(), fact_deliveries[is_super_over] = FALSE())\n"
                    "RETURN DIVIDE(TotalRuns * 6.0, LegalBalls, BLANK())"
                ),
                "formatString": "0.00",
                "lineageTag": str(uuid.uuid4())
            },
            {
                "name": "Powerplay Wickets",
                "expression": "CALCULATE(COUNTROWS(fact_deliveries), fact_deliveries[phase] = \"Powerplay\", fact_deliveries[is_wicket] = TRUE(), fact_deliveries[is_super_over] = FALSE())",
                "formatString": "#,##0",
                "lineageTag": str(uuid.uuid4())
            },
            {
                "name": "Middle Overs Run Rate",
                "expression": (
                    "VAR TotalRuns = CALCULATE(SUM(fact_deliveries[total_runs]), fact_deliveries[phase] = \"Middle\", fact_deliveries[is_super_over] = FALSE())\n"
                    "VAR LegalBalls = CALCULATE(COUNTROWS(fact_deliveries), fact_deliveries[phase] = \"Middle\", fact_deliveries[is_legal_delivery] = TRUE(), fact_deliveries[is_super_over] = FALSE())\n"
                    "RETURN DIVIDE(TotalRuns * 6.0, LegalBalls, BLANK())"
                ),
                "formatString": "0.00",
                "lineageTag": str(uuid.uuid4())
            },
            {
                "name": "Middle Overs Wickets",
                "expression": "CALCULATE(COUNTROWS(fact_deliveries), fact_deliveries[phase] = \"Middle\", fact_deliveries[is_wicket] = TRUE(), fact_deliveries[is_super_over] = FALSE())",
                "formatString": "#,##0",
                "lineageTag": str(uuid.uuid4())
            },
            {
                "name": "Death Overs Run Rate",
                "expression": (
                    "VAR TotalRuns = CALCULATE(SUM(fact_deliveries[total_runs]), fact_deliveries[phase] = \"Death\", fact_deliveries[is_super_over] = FALSE())\n"
                    "VAR LegalBalls = CALCULATE(COUNTROWS(fact_deliveries), fact_deliveries[phase] = \"Death\", fact_deliveries[is_legal_delivery] = TRUE(), fact_deliveries[is_super_over] = FALSE())\n"
                    "RETURN DIVIDE(TotalRuns * 6.0, LegalBalls, BLANK())"
                ),
                "formatString": "0.00",
                "lineageTag": str(uuid.uuid4())
            },
            {
                "name": "Death Overs Wickets",
                "expression": "CALCULATE(COUNTROWS(fact_deliveries), fact_deliveries[phase] = \"Death\", fact_deliveries[is_wicket] = TRUE(), fact_deliveries[is_super_over] = FALSE())",
                "formatString": "#,##0",
                "lineageTag": str(uuid.uuid4())
            },
            {
                "name": "Phase Total Fours",
                "expression": "CALCULATE(COUNTROWS(fact_deliveries), fact_deliveries[is_boundary_four] = TRUE(), fact_deliveries[is_super_over] = FALSE())",
                "formatString": "#,##0",
                "lineageTag": str(uuid.uuid4())
            },
            {
                "name": "Phase Total Sixes",
                "expression": "CALCULATE(COUNTROWS(fact_deliveries), fact_deliveries[is_boundary_six] = TRUE(), fact_deliveries[is_super_over] = FALSE())",
                "formatString": "#,##0",
                "lineageTag": str(uuid.uuid4())
            },
            {
                "name": "Phase Total Boundaries",
                "expression": "CALCULATE(COUNTROWS(fact_deliveries), (fact_deliveries[is_boundary_four] = TRUE() || fact_deliveries[is_boundary_six] = TRUE()), fact_deliveries[is_super_over] = FALSE())",
                "formatString": "#,##0",
                "lineageTag": str(uuid.uuid4())
            },
            {
                "name": "Bowler Powerplay Wickets",
                "expression": (
                    "CALCULATE(\n"
                    "    COUNTROWS(fact_deliveries),\n"
                    "    fact_deliveries[phase] = \"Powerplay\",\n"
                    "    fact_deliveries[is_wicket] = TRUE(),\n"
                    "    fact_deliveries[wicket_kind] <> \"run out\",\n"
                    "    fact_deliveries[wicket_kind] <> \"retired hurt\",\n"
                    "    fact_deliveries[wicket_kind] <> \"retired out\",\n"
                    "    fact_deliveries[is_super_over] = FALSE()\n"
                    ")"
                ),
                "formatString": "#,##0",
                "lineageTag": str(uuid.uuid4())
            },
            {
                "name": "Bowler Powerplay Overs",
                "expression": (
                    "VAR LegalBalls = CALCULATE(\n"
                    "    COUNTROWS(fact_deliveries),\n"
                    "    fact_deliveries[phase] = \"Powerplay\",\n"
                    "    fact_deliveries[is_legal_delivery] = TRUE(),\n"
                    "    fact_deliveries[is_super_over] = FALSE()\n"
                    ")\n"
                    "VAR FullOvers = INT(DIVIDE(LegalBalls, 6, 0))\n"
                    "VAR RemBalls = MOD(LegalBalls, 6)\n"
                    "RETURN FullOvers + DIVIDE(RemBalls, 10, 0)"
                ),
                "formatString": "0.0",
                "lineageTag": str(uuid.uuid4())
            },
            {
                "name": "Bowler Powerplay Economy",
                "expression": (
                    "VAR RunsConc = CALCULATE(\n"
                    "    SUM(fact_deliveries[total_runs]),\n"
                    "    fact_deliveries[phase] = \"Powerplay\",\n"
                    "    fact_deliveries[is_super_over] = FALSE()\n"
                    ")\n"
                    "VAR LegalBalls = CALCULATE(\n"
                    "    COUNTROWS(fact_deliveries),\n"
                    "    fact_deliveries[phase] = \"Powerplay\",\n"
                    "    fact_deliveries[is_legal_delivery] = TRUE(),\n"
                    "    fact_deliveries[is_super_over] = FALSE()\n"
                    ")\n"
                    "RETURN DIVIDE(RunsConc * 6.0, LegalBalls, BLANK())"
                ),
                "formatString": "0.00",
                "lineageTag": str(uuid.uuid4())
            },
            {
                "name": "Bowler Death Overs Economy (Min 10 Balls)",
                "expression": (
                    "VAR RunsConc = CALCULATE(\n"
                    "    SUM(fact_deliveries[total_runs]),\n"
                    "    fact_deliveries[phase] = \"Death\",\n"
                    "    fact_deliveries[is_super_over] = FALSE()\n"
                    ")\n"
                    "VAR LegalBalls = CALCULATE(\n"
                    "    COUNTROWS(fact_deliveries),\n"
                    "    fact_deliveries[phase] = \"Death\",\n"
                    "    fact_deliveries[is_legal_delivery] = TRUE(),\n"
                    "    fact_deliveries[is_super_over] = FALSE()\n"
                    ")\n"
                    "RETURN IF(LegalBalls >= 10, DIVIDE(RunsConc * 6.0, LegalBalls, BLANK()), BLANK())"
                ),
                "formatString": "0.00",
                "lineageTag": str(uuid.uuid4())
            },
            {
                "name": "Bowler Death Overs Wickets",
                "expression": (
                    "CALCULATE(\n"
                    "    COUNTROWS(fact_deliveries),\n"
                    "    fact_deliveries[phase] = \"Death\",\n"
                    "    fact_deliveries[is_wicket] = TRUE(),\n"
                    "    fact_deliveries[wicket_kind] <> \"run out\",\n"
                    "    fact_deliveries[wicket_kind] <> \"retired hurt\",\n"
                    "    fact_deliveries[wicket_kind] <> \"retired out\",\n"
                    "    fact_deliveries[is_super_over] = FALSE()\n"
                    ")"
                ),
                "formatString": "#,##0",
                "lineageTag": str(uuid.uuid4())
            },
            {
                "name": "Bowler Death Overs Balls",
                "expression": (
                    "CALCULATE(\n"
                    "    COUNTROWS(fact_deliveries),\n"
                    "    fact_deliveries[phase] = \"Death\",\n"
                    "    fact_deliveries[is_legal_delivery] = TRUE(),\n"
                    "    fact_deliveries[is_super_over] = FALSE()\n"
                    ")"
                ),
                "formatString": "#,##0",
                "lineageTag": str(uuid.uuid4())
            }
        ]
        
        for m in deliveries_measures:
            if m['name'] not in existing_measures:
                t['measures'].append(m)
                print(f"Added measure '{m['name']}' to fact_deliveries.")

with open(bim_path, 'w', encoding='utf-8') as f:
    json.dump(bim, f, indent=2)

print("\nSuccessfully updated model.bim!")
