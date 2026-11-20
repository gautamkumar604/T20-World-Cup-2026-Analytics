new_dax = """

// =============================================================================
// PHASE 4.3: TACTICAL ANALYSIS MEASURES & CALCULATED COLUMNS
// =============================================================================

// Calculated Column: dim_matches[Toss Decision Label]
// Description: Normalizes toss decision into clear presentation labels ("Bat First", "Bowl / Field First")
Toss Decision Label = 
IF(
    ISBLANK(dim_matches[toss_decision]), 
    BLANK(), 
    IF(dim_matches[toss_decision] = "bat", "Bat First", "Bowl / Field First")
)

// Calculated Column: dim_matches[Toss Match Result]
// Description: Evaluates whether the toss-winning team won or lost the match
Toss Match Result = 
IF(
    ISBLANK(dim_matches[toss_decision]) || dim_matches[outcome_type] = "no result", 
    BLANK(), 
    IF(dim_matches[toss_winner] = dim_matches[winner], "Toss Winner Won", "Toss Loser Won")
)

// Measure: Toss Completed Matches
// Description: Completed matches count with valid toss decision
Toss Completed Matches = 
CALCULATE(
    COUNTROWS(dim_matches),
    NOT(ISBLANK(dim_matches[toss_decision])),
    dim_matches[outcome_type] <> "no result"
)

// Measure: Powerplay Run Rate
// Description: Runs scored per 6 legal balls in Overs 1-6 (Powerplay)
Powerplay Run Rate = 
VAR TotalRuns = CALCULATE(SUM(fact_deliveries[total_runs]), fact_deliveries[phase] = "Powerplay", fact_deliveries[is_super_over] = FALSE())
VAR LegalBalls = CALCULATE(COUNTROWS(fact_deliveries), fact_deliveries[phase] = "Powerplay", fact_deliveries[is_legal_delivery] = TRUE(), fact_deliveries[is_super_over] = FALSE())
RETURN
    DIVIDE(TotalRuns * 6.0, LegalBalls, BLANK())

// Measure: Powerplay Wickets
// Description: Total dismissals in Overs 1-6 (Powerplay)
Powerplay Wickets = 
CALCULATE(
    COUNTROWS(fact_deliveries),
    fact_deliveries[phase] = "Powerplay",
    fact_deliveries[is_wicket] = TRUE(),
    fact_deliveries[is_super_over] = FALSE()
)

// Measure: Middle Overs Run Rate
// Description: Runs scored per 6 legal balls in Overs 7-15 (Middle Overs)
Middle Overs Run Rate = 
VAR TotalRuns = CALCULATE(SUM(fact_deliveries[total_runs]), fact_deliveries[phase] = "Middle", fact_deliveries[is_super_over] = FALSE())
VAR LegalBalls = CALCULATE(COUNTROWS(fact_deliveries), fact_deliveries[phase] = "Middle", fact_deliveries[is_legal_delivery] = TRUE(), fact_deliveries[is_super_over] = FALSE())
RETURN
    DIVIDE(TotalRuns * 6.0, LegalBalls, BLANK())

// Measure: Middle Overs Wickets
// Description: Total dismissals in Overs 7-15 (Middle Overs)
Middle Overs Wickets = 
CALCULATE(
    COUNTROWS(fact_deliveries),
    fact_deliveries[phase] = "Middle",
    fact_deliveries[is_wicket] = TRUE(),
    fact_deliveries[is_super_over] = FALSE()
)

// Measure: Death Overs Run Rate
// Description: Runs scored per 6 legal balls in Overs 16-20 (Death Overs)
Death Overs Run Rate = 
VAR TotalRuns = CALCULATE(SUM(fact_deliveries[total_runs]), fact_deliveries[phase] = "Death", fact_deliveries[is_super_over] = FALSE())
VAR LegalBalls = CALCULATE(COUNTROWS(fact_deliveries), fact_deliveries[phase] = "Death", fact_deliveries[is_legal_delivery] = TRUE(), fact_deliveries[is_super_over] = FALSE())
RETURN
    DIVIDE(TotalRuns * 6.0, LegalBalls, BLANK())

// Measure: Death Overs Wickets
// Description: Total dismissals in Overs 16-20 (Death Overs)
Death Overs Wickets = 
CALCULATE(
    COUNTROWS(fact_deliveries),
    fact_deliveries[phase] = "Death",
    fact_deliveries[is_wicket] = TRUE(),
    fact_deliveries[is_super_over] = FALSE()
)

// Measure: Phase Total Fours
// Description: Total boundary 4s struck in fact_deliveries
Phase Total Fours = 
CALCULATE(
    COUNTROWS(fact_deliveries),
    fact_deliveries[is_boundary_four] = TRUE(),
    fact_deliveries[is_super_over] = FALSE()
)

// Measure: Phase Total Sixes
// Description: Total boundary 6s struck in fact_deliveries
Phase Total Sixes = 
CALCULATE(
    COUNTROWS(fact_deliveries),
    fact_deliveries[is_boundary_six] = TRUE(),
    fact_deliveries[is_super_over] = FALSE()
)

// Measure: Phase Total Boundaries
// Description: Total boundaries (4s + 6s) struck in fact_deliveries
Phase Total Boundaries = 
CALCULATE(
    COUNTROWS(fact_deliveries),
    (fact_deliveries[is_boundary_four] = TRUE() || fact_deliveries[is_boundary_six] = TRUE()),
    fact_deliveries[is_super_over] = FALSE()
)

// Measure: Bowler Powerplay Wickets
// Description: Bowler-credited wickets taken in Overs 1-6 (excluding run outs, retired hurt/out)
Bowler Powerplay Wickets = 
CALCULATE(
    COUNTROWS(fact_deliveries),
    fact_deliveries[phase] = "Powerplay",
    fact_deliveries[is_wicket] = TRUE(),
    fact_deliveries[wicket_kind] <> "run out",
    fact_deliveries[wicket_kind] <> "retired hurt",
    fact_deliveries[wicket_kind] <> "retired out",
    fact_deliveries[is_super_over] = FALSE()
)

// Measure: Bowler Powerplay Overs
// Description: Overs bowled in Powerplay (e.g. 21.0 overs)
Bowler Powerplay Overs = 
VAR LegalBalls = CALCULATE(
    COUNTROWS(fact_deliveries),
    fact_deliveries[phase] = "Powerplay",
    fact_deliveries[is_legal_delivery] = TRUE(),
    fact_deliveries[is_super_over] = FALSE()
)
VAR FullOvers = INT(DIVIDE(LegalBalls, 6, 0))
VAR RemBalls = MOD(LegalBalls, 6)
RETURN FullOvers + DIVIDE(RemBalls, 10, 0)

// Measure: Bowler Powerplay Economy
// Description: Economy rate in Powerplay (runs per 6 legal balls)
Bowler Powerplay Economy = 
VAR RunsConc = CALCULATE(
    SUM(fact_deliveries[total_runs]),
    fact_deliveries[phase] = "Powerplay",
    fact_deliveries[is_super_over] = FALSE()
)
VAR LegalBalls = CALCULATE(
    COUNTROWS(fact_deliveries),
    fact_deliveries[phase] = "Powerplay",
    fact_deliveries[is_legal_delivery] = TRUE(),
    fact_deliveries[is_super_over] = FALSE()
)
RETURN
    DIVIDE(RunsConc * 6.0, LegalBalls, BLANK())

// Measure: Bowler Death Overs Economy (Min 10 Balls)
// Description: Death overs economy rate qualified with >= 10 legal balls bowled
Bowler Death Overs Economy (Min 10 Balls) = 
VAR RunsConc = CALCULATE(
    SUM(fact_deliveries[total_runs]),
    fact_deliveries[phase] = "Death",
    fact_deliveries[is_super_over] = FALSE()
)
VAR LegalBalls = CALCULATE(
    COUNTROWS(fact_deliveries),
    fact_deliveries[phase] = "Death",
    fact_deliveries[is_legal_delivery] = TRUE(),
    fact_deliveries[is_super_over] = FALSE()
)
RETURN
    IF(LegalBalls >= 10, DIVIDE(RunsConc * 6.0, LegalBalls, BLANK()), BLANK())

// Measure: Bowler Death Overs Wickets
// Description: Bowler-credited wickets taken in Overs 16-20 (Death Overs)
Bowler Death Overs Wickets = 
CALCULATE(
    COUNTROWS(fact_deliveries),
    fact_deliveries[phase] = "Death",
    fact_deliveries[is_wicket] = TRUE(),
    fact_deliveries[wicket_kind] <> "run out",
    fact_deliveries[wicket_kind] <> "retired hurt",
    fact_deliveries[wicket_kind] <> "retired out",
    fact_deliveries[is_super_over] = FALSE()
)

// Measure: Bowler Death Overs Balls
// Description: Total legal balls bowled in Death Overs
Bowler Death Overs Balls = 
CALCULATE(
    COUNTROWS(fact_deliveries),
    fact_deliveries[phase] = "Death",
    fact_deliveries[is_legal_delivery] = TRUE(),
    fact_deliveries[is_super_over] = FALSE()
)
"""

with open('power_bi/dax_measures.dax', 'a', encoding='utf-8') as f:
    f.write(new_dax)

print("Appended Phase 4.3 measures to power_bi/dax_measures.dax!")
