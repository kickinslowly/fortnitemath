# Cartridge library

One cartridge per skill, grouped by grade in the player's picker (PROTOCOL §6b). Every cartridge is 5 tiers ×
40 items, procedural (`generator.py`), and meets PROTOCOL §4a (whole-number topics) or §4b (fractions,
decimals, percents, measurement, data). Display limits that shape every spec below: prompt ≤ 60 chars, each
choice ≤ 14, misconception `student` text ≤ 80, explanation ≤ 160 (PROTOCOL §5 rule 6).

## Grade 6

| Cartridge | Title — Subtitle | Standards (CCSS 6.) |
|---|---|---|
| `order-of-ops-exponents` | Order of Operations — Exponents & Parentheses | EE.A.1 |
| `ratios-rates` | Ratios & Rates — Equivalent Ratios, Unit Rates, Percent | RP.A.1, A.2, A.3 |
| `fraction-division` | Dividing Fractions — How Many Groups? | NS.A.1 |
| `decimal-ops` | Decimal Operations — Add, Subtract, Multiply, Divide | NS.B.3 |
| `factors-multiples` | GCF & LCM — Factors, Multiples, Distributing | NS.B.4 |
| `rational-numbers` | Rational Numbers — Number Line & Coordinate Plane | NS.C.5, C.6, C.7, C.8 |
| `expressions` | Expressions — Write, Read, Evaluate | EE.A.2, A.3, A.4 |
| `equations-inequalities` | Equations & Inequalities — Solve One Step | EE.B.5, B.6, B.7, B.8 |
| `area-volume` | Area & Volume — Shapes, Prisms, Surface Area | G.A.1, A.2, A.4 |
| `data-statistics` | Data & Statistics — Mean, Median, Range, MAD | SP.A.2, A.3, B.5c |

### Tier plans

Seeds: `2026100N` style, unique per cartridge (listed). Misconception keys are the build's starting set;
a builder may add one when a real wrong rule appears, never a generic "wrong" key (that is `ARITH`).

**ratios-rates** (seed 20261011)
1. Ratio Language — "3 red, 5 blue. Blue to red?" → `5:3`. REVERSED (`3:5`), PART_TO_WHOLE (`5:8`).
2. Equivalent Ratios — "2:3 = ?:12" → 8. ADDITIVE (added instead of scaled: 2 + 9 = 11), WRONG_TERM (scaled the wrong term).
3. Unit Rates & Units — "$24 for 6 pens. Per pen?" → `$4`; "3 ft = 1 yd. 12 ft = ? yd" → 4. MULTIPLIED_RATE, INVERTED.
4. Percent of a Number — "25% of 40" → 10. PERCENT_AS_PART (answers 25), SUBTRACTED (40 − 25), TENTH_FOR_ALL (÷ 10 for any %).
5. Parts & Wholes — "Boys:girls 2:3, 20 kids. Girls?" → 12; "10 is 25% of what?" → 40. PART_AS_TOTAL (3/20 read wrong: answers 8 or 3 × 20…), PERCENT_OF_PART (25% of 10).

**fraction-division** (seed 20261012)
1. Whole ÷ Unit Fraction — "4 ÷ 1/3" → 12. DIVIDED_WHOLE (`4/3`), FLIPPED_ANSWER (`1/12`).
2. Unit Fraction ÷ Whole — "1/2 ÷ 4" → `1/8`. FLIPPED_ANSWER (8), MULT_WHOLE (2).
3. Same Denominators — "3/4 ÷ 1/4" → 3; "6/8 ÷ 3/8" → 2. FLIP_FIRST, NO_FLIP (multiplied straight across).
4. Any Two Fractions — "2/3 ÷ 3/4" → `8/9`. FLIP_FIRST (`9/8`), NO_FLIP (`1/2`), FLIPPED_ANSWER.
5. Story Problems — "6 cups, 3/4 cup per serving. Servings?" → 8; "3/4 lb shared by 3. Each?" → `1/4 lb`. WRONG_ORDER (divisor and dividend swapped), NO_FLIP.

**decimal-ops** (seed 20261013)
1. Add & Subtract — "0.4 + 0.35" → 0.75. ALIGN_RIGHT (0.39), DROP_PLACE.
2. Decimal × Whole — "0.3 × 4" → 1.2. PLACE_LOST (12), EXTRA_PLACE (0.12).
3. Decimal × Decimal — "0.6 × 0.2" → 0.12. COUNT_PLACES (1.2), TOO_MANY_PLACES (0.012).
4. Decimal ÷ Whole — "2.4 ÷ 3" → 0.8. PLACE_LOST (8), EXTRA_PLACE (0.08).
5. Divide by a Decimal — "1.2 ÷ 0.3" → 4; money stories ("$1.50 per pen. Pens for $6?"). SHIFT_ONE_SIDE (0.4, 40).

**factors-multiples** (seed 20261014)
1. Factors & Primes — "Which is a factor of 36?", "Which is prime?". MULTIPLE_FOR_FACTOR, ODD_IS_PRIME.
2. Greatest Common Factor — "GCF of 12 and 18" → 6. LCM_FOR_GCF (36), NOT_GREATEST (2, 3), SMALLER_NUMBER.
3. Least Common Multiple — "LCM of 4 and 6" → 12. PRODUCT (24), GCF_FOR_LCM (2).
4. Factor Out the GCF — "24 + 36 = ?" → `12(2 + 3)`. NOT_GREATEST (`6(4 + 6)`, true but not the GCF), SUBTRACTED_GCF.
5. GCF or LCM? — "Buns in 8s, dogs in 6s. Fewest of each?" → 24; "18 red, 24 blue. Most equal bags?" → 6. WRONG_TOOL.

**rational-numbers** (seed 20261015)
1. Opposites — "Opposite of −7?" → 7; "5 below zero as an integer?" → −5. SAME_NUMBER, WRONG_SIGN_CONTEXT.
2. Absolute Value — "|−9|" → 9; "|−3| + |4|". KEEPS_SIGN (−9), OPPOSITE_FOR_ABS.
3. Compare & Order — "Least: −2, 3, −7, 0" → −7. NEG_SIZE (thinks −2 < −7), ABS_ORDER.
4. Quadrants & Reflections — "(−3, 4) is in quadrant?" → `II`; "(2, −5) over the x-axis?" → `(2, 5)`. WRONG_AXIS, SWAPPED_XY.
5. Distance on the Plane — "Distance (−3, 2) to (4, 2)?" → 7. SUBTRACTED_SIZES (1), WRONG_COORD.

**expressions** (seed 20261016)
1. Words to Expressions — "5 less than n" → `n − 5`. ORDER_SUB (`5 − n`), WRONG_OP.
2. Parts of an Expression — "Coefficient in 7x + 3?" → 7; "How many terms: 3a + 2b + 5?" → 3. CONSTANT_FOR_COEF, COUNTS_VARIABLES.
3. Evaluate — "3x + 4 when x = 5" → 19; "2a^2, a = 3" → 18. CONCAT (3x read as 35), SQUARE_PRODUCT (36), ORDER.
4. Distributive Property — "3(x + 4)" → `3x + 12`; "6x + 9" → `3(2x + 3)`. PARTIAL_DIST (`3x + 4`), ADD_ALL (`7x`).
5. Equivalent Expressions — "2(x + 3) + x" → `3x + 6`; "x + x + x" → `3x`. UNLIKE_COMBINED (`9x`), POWER_FOR_SUM (`x^3`).

**equations-inequalities** (seed 20261017)
1. Is It a Solution? — "Which makes x + 6 = 14 true?" → 8. SAME_OP (20), VALUE_SHOWN.
2. Add & Subtract — "x + 7 = 15" → 8; "x − 4 = 9" → 13. SAME_OP (22 / 5).
3. Multiply & Divide — "4x = 28" → 7; "x ÷ 5 = 6" → 30. SAME_OP (4x = 28 → 112), SUBTRACTED (24).
4. Write the Equation — "Had x cards, got 6, now 15." → `x + 6 = 15`. WRONG_OP, SWAPPED.
5. Inequalities — "At least 12 players" → `p ≥ 12`; "A solution of x < 4?" → 3. BOUNDARY (4), FLIPPED_SIGN, STRICT_VS_INCLUSIVE.

**area-volume** (seed 20261018)
1. Rectangles & Parallelograms — "Parallelogram: base 8, height 5. Area?" → `40 sq units`. PERIMETER, SLANT_SIDE.
2. Triangles — "Triangle: base 10, height 6. Area?" → 30. NO_HALF (60), PERIMETER.
3. Trapezoids & Missing Sides — "Trapezoid: bases 4 and 6, height 5" → 25; "Area 48, width 6. Length?" → 8. ONE_BASE, NO_HALF.
4. Volume of Prisms — "Box 2 by 3 by 4. Volume?" → 24; "4 by 3 by 1/2" → 6. ADDED_EDGES, SQUARE_UNITS (right number, wrong unit).
5. Surface Area — "Cube, edge 3. Surface area?" → 54. VOLUME_FOR_SA (27), ONE_FACE (9), FOUR_FACES (36).

**data-statistics** (seed 20261019)
1. Range & Mode — "Range: 4, 9, 2, 7, 5" → 7. LARGEST (9), FIRST_LAST, MOST_FOR_MODE.
2. Median — "Median: 6, 2, 9, 4, 7" → 6. UNSORTED (middle as listed), MEAN_FOR_MEDIAN.
3. Mean — "Mean: 3, 5, 8, 4" → 5. SUM_ONLY (20), MEDIAN_FOR_MEAN, WRONG_COUNT.
4. Missing Value & Outliers — "Mean of 4 scores is 6: 5, 7, 4, ?" → 8; "Add 40 to 2, 3, 4. Which moves most?" → `Mean`. MEAN_AS_MISSING, MEDIAN_MOVES.
5. Mean Absolute Deviation — "MAD: 2, 4, 6, 8" → 2. RANGE_FOR_MAD (6), MEAN_FOR_MAD (5), SUM_DEVIATIONS (8).

### Grade-6 standards that do not fit the multiple-choice race

| Standard | Why it does not fit | What would unlock it |
|---|---|---|
| 6.SP.A.1 Recognize a statistical question | The choices are whole sentences; a door holds ≤ 14 chars | Longer door labels, or 2 choices quoted in a longer prompt |
| 6.SP.B.4 Dot plots, histograms, box plots | Needs a picture per question; items are text only | An optional per-item image (protocol bump: textures imported per item) |
| 6.SP.B.5a, b, d Describe data collection and context | Written explanation, no single right value | — (classroom task) |
| 6.G.A.3 Draw polygons in the plane | Drawing; only the distance part is covered (`rational-numbers` T5) | Per-item image |
| 6.G.A.4 Nets | Needs the net drawn; the surface-area number is covered (`area-volume` T5) | Per-item image |
| 6.NS.B.2 Divide multi-digit numbers (standard algorithm) | The skill *is* heavy arithmetic, which §4a forbids | — (conflicts with the content rule by design) |
| 6.NS.B.3 multi-digit decimal algorithms | Same; only place-value-sized decimals are covered (`decimal-ops`) | — |
| 6.NS.C.6c, 6.EE.B.8 (graph part), 6.RP.A.3a (plot part), 6.EE.C.9 (graphs) | Plotting and reading graphs/number lines need a picture | Per-item image |
| Long word problems (6.RP.A.3, 6.EE.B.7) | Covered, but a 60-char prompt keeps stories to one line | A longer prompt limit (HUD wrap allows it; protocol bump) |
