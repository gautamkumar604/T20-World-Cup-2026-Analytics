from fractions import Fraction

# India Super 8
# Runs For: 111 (SA) + 256 (ZIM) + 199 (WI) = 566
# Balls For: 120 (all-out vs SA) + 120 (vs ZIM) + 116 (vs WI) = 356 balls
# Overs For: 356 / 6 overs
rr_for = Fraction(566, 1) / Fraction(356, 6) # = 566 * 6 / 356 = 3396 / 356 = 849 / 89

# Runs Against: 187 (SA) + 184 (ZIM) + 195 (WI) = 566
# Balls Against: 120 (SA) + 120 (ZIM) + 120 (WI) = 360 balls
# Overs Against: 360 / 6 = 60 overs
rr_against = Fraction(566, 1) / Fraction(360, 6) # = 566 / 60 = 283 / 30

nrr = rr_for - rr_against
print("RR For:", rr_for, "=", float(rr_for))
print("RR Against:", rr_against, "=", float(rr_against))
print("NRR Exact Fraction:", nrr)
print("NRR Float:", float(nrr))
print("NRR Rounded (3 decimals):", round(float(nrr), 3))

# Compare with view_tournament_standings
# nrr_num = 2264, nrr_den = 128160 (note: 2264 / 128160 * 6 = 13584 / 128160)
view_nrr = Fraction(283, 16020) * 6
print("View NRR scaled by 6:", view_nrr, "=", float(view_nrr))
