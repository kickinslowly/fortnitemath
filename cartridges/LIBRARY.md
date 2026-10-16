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
1. Rectangles & Parallelograms — "Parallelogram: base 8, height 5. Area?" → `40 sq units`. PERIMETER, HALVED, ADD_SIDES (base and height only, Aaron 2026-10-09).
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

## Grade 7

| Cartridge | Title — Subtitle | Standards (CCSS 7.) |
|---|---|---|
| `integer-ops` (built 2026-10-03) | Integer Operations — Positive & Negative Numbers | NS.A.1, A.2, A.3 |
| `proportional-relationships` | Proportional Relationships — Unit Rates, Constant k, Scale Drawings | RP.A.1, A.2.A, A.2.B, A.2.C; G.A.1 |
| `percent-problems` | Percent Problems — Tax, Tips, Discounts & Percent Change | RP.A.3 |
| `rational-ops` | Rational Number Operations — Fractions & Decimals with Signs | NS.A.1.C, A.1.D, A.2.B, A.2.C, A.2.D, A.3 |
| `linear-expressions` | Equivalent Expressions — Combine, Expand & Factor with Signs | EE.A.1, A.2 |
| `two-step-equations` | Two-Step Equations — Equations & Inequalities: px + q = r | EE.B.3, B.4.A, B.4.B |
| `angle-relationships` | Angle Relationships — Complementary, Supplementary, Vertical | G.B.5 |
| `circles` | Circles — Radius, Circumference, Area & π | G.B.4 |
| `probability` | Probability — Chance, Outcomes & Compound Events | SP.C.5, C.6, C.7.A, C.8.A, C.8.B; SP.A.2 |

Built 2026-10-13 (G9 team: one Sonnet builder per cartridge, audited by the content lead): all eight baked and valid,
200 items each, one fix round (`two-step-equations` T4 group stories had two readings). Where a builder renamed a tier
or a misconception key, the manifest wins over the plan below. `angle-relationships` states its own angle bounds
(tens): PROTOCOL §4b has no angle row yet.

Rules for every grade-7 cartridge (on top of PROTOCOL §4a/§4b/§5):
- **Charset traps**: `°`, `≈`, `¢`, `½`, `²` are not in the §5 charset. Write "degrees", "about", "Use 3 for π", `1/2`,
  `r^2` (consoles render `^2` as a superscript, PROTOCOL §7).
- **Grade drift (grade 8, never)**: exponent rules, scientific notation, square roots (so no area → radius), Pythagoras,
  slope (say "unit rate" / "constant of proportionality"), variables on both sides, triangle angle sum, parallel lines
  and transversals, cylinder / cone / sphere volume, functions.
- Signed whole-number steps follow §4a's signs-as-concept bound (literals under + − of size ≤ 12).
- Prompts are unique per tier (§5 rule 4). Small numbers give few combinations: reach 40 with wording and contexts
  (wheel, pizza, pool), never with bigger numbers.
- Equivalent forms are equal in value: never put `3(2x + 1)` beside `6x + 3`, `2/6` beside `1/3`, or `0.5` beside `1/2`.

### Tier plans

Seeds: `2026102N` style, unique per cartridge (listed; grade 6 used 20261002-20261019). Misconception keys are the
build's starting set; a builder may add one when a real wrong rule appears, never a generic "wrong" key (that is `ARITH`).

**proportional-relationships** (seed 20261021). Bounds: §4b fractions for T1 (every cross product a times-table fact);
every unit rate, k and scale factor 2-10; every × ÷ a times-table fact; correct values whole and ≤ 100 (T1 may be a
simple fraction or mixed number).
1. Unit Rates with Fractions — "1/2 mile in 1/4 hour. Miles per hour?" → 2; "3/4 cup makes 1/2 batch. Cups for 1 batch?" → `1 1/2`. INVERTED (`1/2`, `2/3`), MULTIPLIED (`1/8`, `3/8`).
2. Proportional or Not? — "(2, 6) is on y = kx. Which point is too?" → `(5, 15)`; "Which shows y proportional to x, k = 4?" → `y = 4x`. ADDITIVE (`(5, 9)`: added 3 to both), SWAPPED (`(15, 5)`), ADDS_CONSTANT (`y = x + 4`), HAS_START (`y = 4x + 1`).
3. Constant of Proportionality — "y = 6x. Constant of proportionality?" → 6; "(4, 20) is on y = kx. k?" → 5; "4 tickets cost $28. Cost per ticket?" → `$7`. INVERTED (`1/5`), DIFFERENCE (16), PRODUCT (80).
4. Write the Equation — "5 pens cost $15. Cost c for p pens?" → `c = 3p`. INVERTED (`p = 3c`), TOTAL_AS_RATE (`c = 15p`), ADDITIVE (`c = p + 10`).
5. Scale Drawings — "Map scale 1 cm : 5 km. 4 cm is how many km?" → 20; "1 cm : 5 m. A 30 m wall is how many cm?" → 6; "1 cm = 2 m. Room drawn 3 cm by 4 cm. Area?" → `48 sq m`. WRONG_WAY (150: multiplied going back), LINEAR_AREA (`24 sq m`: scaled the area once), DRAWING_AREA (`12 sq m`).

**percent-problems** (seed 20261022). Bounds: §4b percents (25 % and 75 % of wholes ≤ 40; tens of percent of 10 × 2..10);
each amount added or subtracted (tip, tax, discount, markup, change, interest) ≤ 20 and every whole and total ≤ 100
(the data-statistics running-sum precedent); percent change and error land on a §4b percent through a times-table
division (5 of 20 is 1/4, so 25 %).
1. Tax & Tip — "$40 meal plus a 20% tip. Total?" → `$48`. PART_ONLY (`$8`), PERCENT_AS_DOLLARS (`$60`), TENTH_FOR_ALL (`$44`).
2. Discounts — "$40 shirt, 25% off. Sale price?" → `$30`. PART_ONLY (`$10`), PERCENT_AS_DOLLARS (`$15`), ADDED (`$50`).
3. Markups & Simple Interest — "Costs $30, marked up 50%. Price?" → `$45`; "$50 at 10% simple interest, 2 years. Interest?" → `$10`. PART_ONLY (`$15`), ONE_YEAR (`$5`), TOTAL_FOR_INTEREST (`$60`).
4. Percent Increase & Decrease — "$20 rises to $25. Percent increase?" → `25%`; "50 drops to 40. Percent decrease?" → `20%`. DIFFERENCE_AS_PERCENT (`5%`, `10%`), NEW_AS_BASE (`20%`, `25%`), RATIO_AS_CHANGE (`125%`, `80%`).
5. Percent Error & Two Steps — "Guessed 45. Actual was 50. Percent error?" → `10%`; "$40 coat, 50% off, then 10% tax. Cost?" → `$22`. DIFFERENCE_AS_PERCENT (`5%`), COMBINED_PERCENTS (`$24`: took 40 % off), FORGOT_SECOND (`$20`).

**rational-ops** (seed 20261023). Bounds: §4b fractions (denominators 2-12, like denominators or one a multiple of the
other for + −) and §4b decimals; signed steps ≤ 12 in size; every answer's size ≤ 12. T4 denominators 2, 4, 5, 10, 20, 25
(terminating) and 3, 9 (repeating, written `0.666...`); never `0.67` as a distractor for 2/3 (a sharp kid argues it).
1. Signed Decimals: Add & Subtract — "−0.5 + 0.8" → `0.3`; "−0.2 − (−0.7)" → `0.5`. WRONG_SIGN (`−0.3`), ADD_SIZES (`1.3`), SUB_NEG (`−0.9`).
2. Signed Fractions: Add & Subtract — "−1/2 + 3/4" → `1/4`; "1/3 − 2/3" → `−1/3`. WRONG_SIGN (`−1/4`), ADD_ACROSS (`1/3`: tops and bottoms added), ADD_SIZES (`1 1/4`).
3. Multiply & Divide with Signs — "−2/3 × 3/4" → `−1/2`; "−1/2 ÷ (−1/4)" → 2; "−0.6 ÷ 0.2" → −3. SIGN_RULE (`1/2`), NO_FLIP (`1/8`), FLIP_FIRST.
4. Fractions as Decimals — "−3/4 as a decimal?" → `−0.75`; "2/3 as a decimal?" → `0.666...`; "Which equals −3/5?" → `3/(−5)`. DIGITS_AS_DECIMAL (`−0.34`), DENOM_ONLY (`−0.4`), FLIPPED (`1.5`), DOUBLE_NEG (`−3/(−5)`).
5. Signed Stories & Two Steps — "Temp is −1.5 degrees, then drops 2 degrees. Now?" → `−3.5`; "−1/2 × (6 − 10)" → 2. WRONG_SIGN, ORDER, SUB_NEG.

**linear-expressions** (seed 20261024). Bounds: coefficients and constants of size ≤ 12 before and after each step; every
coefficient product a times-table fact; like-term sums of sizes ≤ 12; decimals and fractions per §4b. No `x^2` terms.
1. Combine Like Terms with Signs — "5x − 8x" → `−3x`; "4a + 3 − a" → `3a + 3`. WRONG_SIGN (`3x`), DROPPED_VARIABLE (`−3`), UNLIKE_COMBINED (`6a`), NO_COEF_ONE (`4a + 3`: read `−a` as nothing).
2. Distribute with Negatives — "−3(x − 4)" → `−3x + 12`; "−(2x + 5)" → `−2x − 5`. PARTIAL_DIST (`−3x − 4`), SIGN_INSIDE (`−3x − 12`), NEG_FIRST_ONLY (`−2x + 5`).
3. Add & Subtract Expressions — "(5x + 2) − (2x − 3)" → `3x + 5`; "(4a − 1) + (−2a + 6)" → `2a + 5`. FIRST_TERM_ONLY (`3x − 1`), WRONG_SIGN.
4. Factor — "6x − 9" → `3(2x − 3)`; "−4x + 8" → `−4(x − 2)`. PARTIAL_FACTOR (`3(2x − 9)`), SIGN_FACTOR (`−4(x + 2)`). No not-greatest-factor distractor: `2(6x + 4)` equals `4(3x + 2)` in value, so it is a second right door.
5. Rewrite to Show Meaning — "Price p, then 20% off. New price?" → `0.8p`; "a + 0.05a" → `1.05a`; "(1/2)x + (1/4)x" → `(3/4)x`. PART_ONLY (`0.2p`), PERCENT_AS_WHOLE (`p − 20`), ADDED (`1.2p`), ADD_ACROSS (`(1/3)x`).

**two-step-equations** (seed 20261025). Bounds: `px + q = r` and `p(x + q) = r` with p 2-10 in size, q and r per §4a
signs (literals ≤ 12 under + − on negative tiers, ≤ 20 on T1 and T4 where all values are positive), every division a
times-table fact, solutions whole numbers of size 1-10. Never a variable on both sides (grade 8).
1. Solve px + q = r — "2x + 6 = 14" → 4. SAME_OP (10: added 6), DIVIDE_FIRST (1: 14 ÷ 2 − 6), ONE_STEP (8: stopped at 2x).
2. Negatives — "−2x + 5 = 11" → −3; "4x − 3 = −11" → −2. SIGN_DROP (3), SAME_OP (−8), ONE_STEP (6).
3. Parentheses p(x + q) = r — "3(x + 2) = 21" → 5; "4(x − 1) = 20" → 6. WRONG_INVERSE (9: added the 2 back; 4), PARTIAL_DIST.
4. Write & Solve from Stories — "$4 to get in, $2 a ride. Spent $16. Rides?" → 6; the same story asking for the equation → `2r + 4 = 16`. IGNORED_FIXED (8), ADDED_FIXED (10), SWAPPED (`4r + 2 = 16`).
5. Two-Step Inequalities — "2x + 3 > 11" → `x > 4`; "−3x + 2 ≤ 11" → `x ≥ −3`. NO_FLIP (`x ≤ −3`), FLIP_WRONG (`x < 4`: flipped for a positive divisor), BOUNDARY_ONLY (`x = 4`). (The first plan's `≤ 14` broke the signed-literal bound of 12; the builder caught it.)

**angle-relationships** (seed 20261026). Bounds (proposed; PROTOCOL §4b has no angle row, so the parent confirms): every
angle (given, unknown, answer) a multiple of 10 from 10 to 180; every + − on angles is a tens fact whose digit work is a
§4a step (180 − 70 is 18 − 7 tens); x a multiple of 10; every × ÷ is a times-table fact in tens (3x = 180 is 18 ÷ 3).
Choices are plain numbers (`60`), the prompt says "degrees". No angles around a point (360 is 36 tens, past the
bound), no triangle angle sum, no parallel lines (grade 8).
1. Complements & Supplements — "Complement of a 30 degree angle?" → 60; "Supplement of a 70 degree angle?" → 110. COMP_SUPP_SWAP (150, 20), USED_360 (290).
2. Vertical & Adjacent — "Two lines cross. One angle is 40. Its vertical angle?" → 40; "... The angle next to it?" → 140. SUPP_FOR_VERT (140), VERT_FOR_ADJ (40), COMP_FOR_SUPP (50).
3. Name It & Split Angles — "Two angles that add to 180 are?" → `Supplementary`; "A straight angle is split into 50, 60 and x. x?" → 70; "A right angle is split into 30 and x. x?" → 60. VOCAB_SWAP (`Complementary`), FORGOT_ONE (130: took away only 50), WRONG_TOTAL (150: used 180 for a right angle).
4. Solve for the Angle — "x and 2x are supplementary. x?" → 60; "x + 20 and 50 are complementary. x?" → 20. ANGLE_NOT_X (120), WRONG_TOTAL (30, 110), NO_DIVIDE (180).
5. Multi-Step Angle Problems — "Vertical angles: 2x + 10 and 70. x?" → 30; "4x and 2x form a straight line. Larger angle?" → 120. SUPP_FOR_VERT (50), ANGLE_NOT_X (70), GAVE_X (30), SMALLER (60).

**circles** (seed 20261027). Bounds: §4b measurement; a given radius or diameter 2-10 (radius 1 gives a bare `π`); answers in terms of π (`8π`), every
π coefficient ≤ 100 and a times-table fact (r × r, 2 × r); halving goes through an even radius ((r/2) × r), the
area-volume precedent; "Use 3 for π" estimates give whole numbers ≤ 100. Never r = 2 on an item with both a
circumference and an area choice (4π = 4π: two right doors).
1. Radius, Diameter & π — "Radius 7. Diameter?" → 14; "Diameter 10. Radius?" → 5; "Circumference ÷ diameter = ?" → `π`. HALVED_FOR_DOUBLED (`3.5`), SAME_NUMBER (7).
2. Circumference — "Radius 4. Circumference?" → `8π`; "Diameter 6. Circumference?" → `6π`. R_FOR_D (`4π`), AREA_FOR_C (`16π`, `9π`), DOUBLED_D (`12π`).
3. Area — "Radius 3. Area?" → `9π`; "Diameter 10. Area?" → `25π`. C_FOR_AREA (`6π`, `10π`: doubled instead of squared), D_FOR_R (`36π`, `100π`).
4. Work Backward & Estimate — "Circumference 12π. Radius?" → 6; "Radius 5. Circumference? Use 3 for π." → 30. GAVE_DIAMETER (12), DOUBLED (24), AREA_ESTIMATE (75). No area → radius (square roots are grade 8).
5. Half & Quarter Circles — "Semicircle, radius 4. Area?" → `8π`; "Quarter circle, radius 6. Area?" → `9π`; "Semicircle, diameter 10. Curved edge length?" → `5π`. WHOLE_CIRCLE (`16π`, `36π`, `10π`), HALVED_RADIUS (`4π`), WRONG_PART (`18π`: halved a quarter).

**probability** (seed 20261028). Bounds: §4b fractions (denominators 2-12, simplest form; a die and a coin is 12 outcomes,
so no two-dice probabilities: 1/36 breaks the denominator bound); counts and sample spaces whole, ≤ 100, products
times-table facts; predictions through a times-table division (6 of 20, so 30 of 100).
1. How Likely? — "A probability of 0.9 means the event is?" → `Likely`; "Which can't be a probability?" → `1.5`. SCALE_FLIP (`Unlikely`), OVER_ONE (picks a value > 1 as fine), HALF_WORD (`Equally likely` for 0.9).
2. Simple Probability — "Bag: 3 red, 5 blue. P(red)?" → `3/8`; "Roll a die. P(number > 4)?" → `1/3`. PART_TO_PART (`3/5`), OTHER_EVENT (`5/8`, `2/3`), INCLUSIVE (`1/2`: counted 4 too).
3. Complement & Predict — "P(rain) is 3/10. P(no rain)?" → `7/10`; "P(win) = 1/4. Spin 40 times. Wins expected?" → 10; "6 of 20 sampled like jazz. Of 100 students?" → 30. SAME_AS_EVENT (`3/10`), SAMPLE_COUNT (6), ADDITIVE (86).
4. Sample Spaces — "Flip a coin and roll a die. Outcomes?" → 12; "3 shirts, 4 pants. Outfits?" → 12; "Flip two coins. Outcomes?" → 4. ADDED (8, 7), ORDER_BLIND (3: HT and TH counted once).
5. Compound Events — "Coin and die. P(heads and a 6)?" → `1/12`; "Two coins. P(one head, one tail)?" → `1/2`; "Three coins. P(all heads)?" → `1/8`. ADDED_PROBS (`2/3`), ADD_DENOMS (`1/8` for coin and die), ORDER_BLIND (`1/3`).

### Grade-7 standards that do not fit the multiple-choice race

| Standard | Why it does not fit | What would unlock it |
|---|---|---|
| 7.RP.A.2.A (graph part), 7.RP.A.2.D | Proportional on a graph, and what (x, y), (0, 0), (1, r) mean on one, need a picture or a sentence choice | Per-item image |
| 7.NS.A.1.A, 7.NS.A.1.B (number-line part) | "Opposite quantities make 0" is a sentence; the number-line model is a picture (the arithmetic is covered by `integer-ops` and `rational-ops`) | Per-item image |
| 7.NS.A.2.A, B (the "why") | Explaining why (−1)(−1) = 1 is an argument, not a value | — (classroom task) |
| 7.NS.A.2.D long division for non-benchmark denominators (5/7, 1/6) | Heavy arithmetic, which §4a forbids; benchmarks are covered (`rational-ops` T4) | — (conflicts with the content rule by design) |
| 7.EE.B.3 (estimation, long multi-step stories) | A 60-char prompt holds one-line stories; covered in part (`two-step-equations` T4, `percent-problems` T5, `rational-ops` T5) | A longer prompt limit (protocol bump) |
| 7.EE.B.4.A (compare the algebraic and arithmetic solutions), 7.EE.B.4.B (graph the solution set) | An explanation; a number-line graph | Per-item image for the graph |
| 7.G.A.1 (reproduce at a different scale) | Drawing; lengths and areas from a scale are covered (`proportional-relationships` T5) | — |
| 7.G.A.2 Draw shapes from conditions; one, many or no triangle | Drawing. The triangle-inequality check ("Can 3, 4, 8 make a triangle?") fits as words: a future grade-7 geometry cartridge | Fits in part; deferred to keep this run at 8 |
| 7.G.A.3 Cross sections of prisms and pyramids | Most slices need a picture; "Slice a cube parallel to a face?" → `Square` fits as words | Per-item image; the word part with 7.G.A.2 later |
| 7.G.B.6 Area, volume, surface area of composite figures and right prisms | Composite figures need a picture; prism volume (base area × height) fits | Per-item image; prisms with 7.G.A.2 later |
| 7.SP.A.1 Representative and random samples | The choices are sentences | Longer door labels |
| 7.SP.A.2 (several samples, gauge variation) | Simulation; the predict-from-a-sample part is covered (`probability` T3) | — |
| 7.SP.B.3, B.4 Compare two populations | Overlap needs dot plots; "means differ by how many MADs?" fits as a number, too thin for its own cartridge | Per-item image; a grade-7 statistics cartridge |
| 7.SP.C.7.B, 7.SP.C.8.C Models from observed frequencies; design a simulation | A data table or a design task | — |
| Two-dice probabilities (7.SP.C.8) | 1/36 breaks §4b's fraction denominators 2-12 | Aaron's say-so to allow denominator 36 for probability |

## Grade 8

| Cartridge | Title — Subtitle | Standards (CCSS 8.) |
|---|---|---|
| `exponent-rules` | Integer Exponents — Product, Quotient, Power, Zero, Negative | EE.A.1 |
| `scientific-notation` | Scientific Notation — Powers of 10, Huge & Tiny Numbers | EE.A.3, A.4 |
| `roots-irrationals` | Roots & Irrational Numbers — Square Roots, Cube Roots & Estimates | NS.A.1, A.2; EE.A.2 |
| `linear-equations` | Linear Equations — Both Sides, Solution Count & Systems | EE.C.7.A, C.7.B, C.8.A, C.8.B, C.8.C |
| `linear-functions` | Functions & Slope — Rate of Change, Start Value, y = mx + b | EE.B.5, B.6; F.A.1, A.2, A.3, B.4, B.5 |
| `pythagorean-theorem` | Pythagorean Theorem — Right Triangles, Distance & 3D | G.B.6, B.7, B.8 |
| `transformations` | Transformations — Slide, Flip, Turn & Dilate Points | G.A.1, A.2, A.3, A.4 |
| `triangles-parallel-lines` | Triangles & Parallel Lines — Angle Sum, Exterior Angles, Transversals | G.A.5 |
| `cylinders-cones-spheres` | Cylinders, Cones & Spheres — Volume in Terms of π | G.C.9 |
| `scatter-two-way` | Scatter Plots & Two-Way Tables — Association, Lines of Fit, Frequencies | SP.A.1, A.2, A.3, A.4 |

Built 2026-10-14 (G10, content lead + one Sonnet builder per cartridge): ten cartridges rather than the eight first aimed
for, so the angle facts (8.G.A.5) and the round solids (8.G.C.9) each get five tiers instead of being squeezed into
another cartridge; grade 6 already shows ten skills in two picker columns. All ten baked and valid, 200 items each, not
yet inserted. The lead audit sent fixes to seven: two right doors under a common misreading (`−2^−2`), guessing tells
(T3 angles always the given number; "Greatest:" always the decimal), too many coin flips (up to 32 two-choice items in a
tier), ARITH where a real miscount had a name, and wording (cats voting, an age that falls, a 1 ft door). Where a
builder renamed a tier or a misconception key, the manifest wins over the plan below.

Rules for every grade-8 cartridge (on top of PROTOCOL §4a/§4b/§5; the grade-8 bounds are §4b's grade-8 rows):
- **Charset traps**: `°`, `≈`, `±`, `²`, `³`, `∛`, `∠`, `∥`, `′`, `→`, `∞` are not in the §5 charset. Write "degrees",
  "about", `5 or −5`, `x^2`, "cube root of 27", "angle", "parallel", "image" or "moves to", `Infinite`. A choice is
  ≤ 14 chars, so "Infinitely many" (15) is the choice `Infinite`; the explanation can say "infinitely many".
- **Exponents** are written `^` with the exponent right after it (`2^7`, `10^−3`, the minus U+2212). The unicode profile
  turns `^7` into a superscript but leaves `^−3` as a caret (§7 superscripts digit runs only). Keep the canonical text
  `^−3` anyway, never `^-3` or `^(−3)`: if the profile learns the superscript minus, no cartridge changes.
- **Grade drift (high school, never)**: simplified radicals (`√20` stays `√20`, never `2√5`), adding or multiplying
  radicals, rational exponents, function notation `f(x)`, domain and range, quadratics, exponential functions as a topic
  (`y = x^2` or `y = 2^x` only as the "not linear" example), systems that need an equation multiplied before adding,
  trigonometry, pyramid volume, correlation coefficients, conditional-probability notation.
- **Grade-7 ground** (a step inside an item is fine, a whole tier is not): complements, supplements and vertical angles
  (`angle-relationships`), circle area and circumference (`circles`), unit rate and k (`proportional-relationships`),
  two-step equations (`two-step-equations`), reflection over an axis (grade-6 `rational-numbers` T4).
- **Equal-value traps** (§4b, never two right doors): `2^8` = `4^4` = `16^2`; `2^4 × 3^4` = `6^4`; `√16` = `4`;
  `0.333...` = `1/3`; `20 × 10^6` = `2 × 10^7`; `y = 2x + 4` = `y = 4 + 2x`; a congruent image is also similar, so never
  offer `Similar` when the answer is `Congruent`; never `Integer` beside `Rational`. Compare choices by exact value
  (ints, `Fraction`, a fingerprint), never by text.
- **Estimates have one answer**: every wrong choice is clearly farther from the true value than the right one (≥ 1 whole
  for whole-number estimates, ≥ 0.5 for one-decimal ones), and the right one is also what a rougher estimate gives
  (π ≈ 3 makes π^2 about 9: never put 9 beside 10). Compare a root with another number only when they are ≥ 0.3 apart.
- **"Which move?" / "which one?" items**: check every choice against the item, not only the intended one. (5, 2) →
  (−5, 2) is a reflection over the y-axis AND a slide 10 left; a flip over the x-axis and a slide right commute, so
  that pair cannot carry an order-swap distractor.
- Prompts are unique per tier (§5 rule 4). Small numbers give few combinations: reach 40 with wording and contexts
  (ladder, ramp, tank, ball), never with bigger numbers.
- Yes/No items (2 choices) only where the question is binary; prefer 3-4 choices, and at most 12 two-choice items per
  tier (the first builds had up to 32). When a "which one?" prompt cannot repeat, put the candidates in the prompt and
  make them the choices (`Which is irrational: √16, √20, 0.25, 2/3?`, grade 6's "Least: −2, 3, −7, 0"). Answer balance
  (§5 rule 8) holds per choice count.
- **No guessing tells**: across a tier the right answer must not always be the given number, the plain decimal, the
  smallest, or 180 minus the given angle (lead audit, 2026-10-14: four builds had one). A bare leading minus on a power
  (`−2^−2`) reads as (−2)^−2 to many kids: bracket it, `−(2^−2)`.
- Coordinates as `(−1, 3)`; fractions in simplest form, distractors too (an unsimplified distractor is a tell).

### Tier plans

Seeds `2026103N` and `20261040`, unique per cartridge (grades 6-7 used 20261002-20261028). Misconception keys are the
build's starting set; a builder may add one when a real wrong rule appears, never a generic "wrong" key (that is
`ARITH`). "Read" names the existing cartridges closest to each one (read, never edit).

**exponent-rules** (seed 20261031). Read `order-of-ops-exponents`, `integer-ops`. Bounds: §4b Exponents. Numeric bases
2-10 (8.EE.A.1 is numerical: no letters); every exponent in a prompt, a step and an answer is an integer of size ≤ 12,
every exponent step a §4a signed step or a times-table product ≤ 12. Answers stay in power form (`2^7`) except where a
tier evaluates, and then only to a power whose value is ≤ 100 (2^5 = 32 included), a power of 10, 1, or 1 over one
of those (`1/8`, `1/100`). A leading minus on a power in a choice is always bracketed, `−(2^−2)`: a bare `−2^−2` reads
as (−2)^−2 = 1/4 to many kids, a second right door.
1. Zero & Negative Powers — "7^0" → 1; "2^−3" → `1/8`; "Which equals 1/25?" → `5^−2`. ZERO_IS_ZERO (0), ZERO_KEEPS_BASE (7), NEG_VALUE (`−8`), NEG_TIMES (`−6`), TIMES_FOR_POWER (6 for 2^3).
2. Product Rule — "2^3 × 2^4" → `2^7`; "5^−2 × 5^6" → `5^4`. MULT_EXPONENTS (`2^12`), MULT_BASES (`4^7`), BOTH (`4^12`), SIGN_SLIP (`5^8`).
3. Quotient Rule — "7^8 ÷ 7^3" → `7^5`; "3^2 ÷ 3^6" → `3^−4`; "6^10 ÷ 6^2" → `6^8`. DIVIDE_EXPONENTS (`6^5`), ADD_EXPONENTS (`7^11`), DIVIDE_BASES (`1^5`), FLIPPED_SUB (`3^4`).
4. Power of a Power — "(2^3)^4" → `2^12`; "(5^−2)^3" → `5^−6`; "(2 × 3)^4" → `2^4 × 3^4`. ADD_FOR_POWER (`2^7`), FIRST_FACTOR_ONLY (`2^4 × 3`), SIGN_SLIP. Never `6^4` beside `2^4 × 3^4`.
5. Mixed Rules to a Value — "2^3 × 2^−5" → `1/4`; "(3^2)^3 ÷ 3^4" → 9; "10^5 ÷ 10^7" → `1/100`. NEG_VALUE (`−4`), MULT_EXPONENTS, SIGN_SLIP, and the tier-1 keys on the last step.

**scientific-notation** (seed 20261032). Read `decimal-ops`, `rational-ops`. Bounds: §4b Scientific notation.
Coefficients 1 to 9.5 with at most 2 non-zero digits; exponents of size ≤ 12; standard forms ≤ 14 chars with commas
(`3,000,000,000`, `0.000000003`); every coefficient × ÷ a times-table fact (5 × 4 = 20 is 2 × 10^1; 2 ÷ 4 = 0.5 is
5 × 10^−1); "how many times" answers a power of 10 or a times-table multiple of one.
1. Powers of 10 — "10^4 = ?" → `10,000`; "10^−3 = ?" → `0.001`; "1,000,000 is 10 to what power?" → 6. ZEROS_PLUS_ONE (`100,000`), NEG_IS_NEGATIVE (`−1,000`), DECIMAL_SLIP (`0.0001`), TIMES_FOR_POWER (40).
2. Write in Sci. Notation — "Write 4,000,000 in scientific notation." → `4 × 10^6`; "Write 0.0005 ..." → `5 × 10^−4`; "32,000" → `3.2 × 10^4`; "Which is in scientific notation?" → `3.5 × 10^4` (beside `35 × 10^4`, `0.5 × 10^3`, `3.5 + 10^4`: all different values). COUNTED_ALL_DIGITS (`4 × 10^7`), SIGN_FLIP (`5 × 10^4`), COUNTED_ZEROS (`5 × 10^−3`), COEF_NOT_1_TO_10. Never a same-value non-standard form (`40 × 10^5`) beside the answer.
3. Read in Standard Form — "6 × 10^5 in standard form?" → `600,000`; "3 × 10^−4 ..." → `0.0003`; "2.5 × 10^3" → `2,500`; "A calculator shows 4.2E6. Value?" → `4,200,000` (8.EE.A.4, technology). EXTRA_ZERO (`6,000,000`), SIGN_FLIP (`30,000`), APPENDED_ZEROS (`2.5000`, `25,000`), DECIMAL_SLIP (`0.003`).
4. Compare & How Many Times — "3 × 10^8 is how many times 3 × 10^6?" → 100; "Larger: 2 × 10^5 or 9 × 10^4?" → `2 × 10^5`; "8 × 10^7 is how many times 2 × 10^7?" → 4. EXPONENT_DIFF (2), COEF_FIRST (`9 × 10^4`), SUBTRACTED, DIVIDED_WRONG_WAY (`1/100`).
5. Multiply, Divide & Add — "(2 × 10^3) × (4 × 10^5)" → `8 × 10^8`; "(6 × 10^9) ÷ (2 × 10^3)" → `3 × 10^6`; "(5 × 10^4) × (4 × 10^2)" → `2 × 10^7`; "(3 × 10^4) + (2 × 10^4)" → `5 × 10^4`. MULT_EXPONENTS (`8 × 10^15`), ADD_COEFS (`6 × 10^8`), DIVIDE_EXPONENTS (`3 × 10^3`), NO_CARRY (`2 × 10^6`), ADD_EXPONENTS_ON_SUM (`5 × 10^8`). Never `20 × 10^6` beside `2 × 10^7`.

**roots-irrationals** (seed 20261033). Read `rational-ops` (T4 repeating decimals), `circles`, `order-of-ops-exponents`.
Bounds: §4b Roots. Square roots of perfect squares 1-100, cube roots of 1, 8, 27, 64 (in words: "cube root of 27");
estimates name the whole numbers around √n for n 2-99; repeating decimals with 1 or 2 repeating digits whose fraction
has a denominator 2-12.
1. Square & Cube Roots — "√49" → 7; "Cube root of 64?" → 4; "x^2 = 81 and x > 0. x?" → 9; "A square has area 36. Side?" → 6; "All solutions of x^2 = 25?" → `5 or −5`. HALVED (`24.5`), THIRD_FOR_CUBE (9 for 27), SQUARE_ROOT_FOR_CUBE (8 for 64), POSITIVE_ONLY (`5`).
2. Rational or Irrational? — "Which is irrational?" → `√7` (beside `√9`, `0.333...`, `2/3`); "Which is rational?" → `√36` (beside `√2`, `π`, `√5`); "0.121212... is?" → `Rational`. ROOT_IS_IRRATIONAL, REPEAT_IS_IRRATIONAL, PI_IS_RATIONAL (π as exactly 3.14). Word choices only `Rational` / `Irrational`.
3. Repeating Decimals — "0.333... as a fraction?" → `1/3`; "0.777..." → `7/9`; "0.1818..." → `2/11`; "Which equals 0.666...?" → `2/3`; "0.1666..." → `1/6`. OVER_TEN (`7/10`), OVER_HUNDRED (`9/50` for 0.1818...), NINE_FOR_TERMINATING.
4. Estimate Square Roots — "√20 is between which two whole numbers?" → `4 and 5`; "Nearest whole number to √50?" → 7; "√2 is about?" → `1.4`. HALVED (`10 and 11`), NEXT_SQUARE_DOWN (`3 and 4`), ROUNDED_WRONG.
5. Compare & Order Roots — "Greater: √50 or 7.5?" → `7.5`; "Which is between 4 and 5?" → `√20`; "Least to greatest: √5, 2, 3" → `2, √5, 3`; "π^2 is about?" → 10 (never 9 beside it). RADICAND_AS_VALUE (√50 > 7.5 because 50 > 7.5), HALVED, TIMES_FOR_POWER (6 for π^2).

**linear-equations** (seed 20261034). Read `two-step-equations`, `linear-expressions`. Bounds: coefficients 1-10 in size;
constants per §4a signs (≤ 12 in size with negatives, ≤ 20 when all positive); after collecting terms the coefficient is
1-10 and every division a times-table fact; solutions integers of size 1-10 (never 0: `x = 0` is a distractor), T4 may
reach a times-table product ≤ 40 when the last step multiplies by a denominator (x/3 = 4); T4 fractions 1/2, 1/3, 1/4,
1/5 and decimals 0.5, 0.25, 0.2, 0.1; T5 systems have integer solutions of size ≤ 10.
1. Both Sides — "5x + 2 = 3x + 10" → 4; "7x − 3 = 4x + 9" → 4; "2x + 9 = 5x" → 3. SAME_SIGN_MOVE (1: 8x = 8), CONST_SIGN (6: 2x = 12), ONE_STEP (8: stopped at 2x = 8).
2. Distribute, Solve — "3(x + 2) = x + 14" → 4; "2(x − 1) + x = 13" → 5; "4(x − 3) = 2x + 4" → 8. PARTIAL_DIST (6), SIGN_INSIDE, SAME_SIGN_MOVE.
3. One, None, Infinite — "2(x + 3) = 2x + 6. How many solutions?" → `Infinite`; "3x + 4 = 3x + 7. How many solutions?" → `None`; "4x + 1 = 2x + 7" → `One`; "5x + 9 = kx + 3. No solution when k is?" → 5 (built instead of "Which equation has no solution?": equation choices pass 14 chars and that prompt cannot repeat). Choices `One`, `None`, `Infinite`, `x = 0`. CANCEL_IS_ZERO (`x = 0`), ALWAYS_ONE (`One`), NONE_FOR_IDENTITY (`None` when 6 = 6), INFINITE_FOR_FALSE.
4. Fractions & Decimals — "(1/2)x + 3 = 7" → 8; "0.5x + 2 = x − 1" → 6; "x/3 − 1 = 3" → 12. DIVIDE_FOR_MULT (2: 4 ÷ 2), ONE_TERM_CLEARED, SAME_SIGN_MOVE.
5. Systems — "y = 2x + 1 and y = 2x + 5. How many solutions?" → `None`; "x + y = 10 and x − y = 4. x?" → 7; "y = x + 4 and y = 3x. Where do the lines meet?" → `(2, 6)`; the same line twice → `Infinite`. PARALLEL_ONE (`One`), SWAPPED_XY (`(6, 2)`), GAVE_Y (3), CANCEL_IS_ZERO.

**linear-functions** (seed 20261035). Read `proportional-relationships`, `expressions`. Bounds: coordinates and table
values integers of size ≤ 20; slopes integers of size 1-10 or a simplest fraction a/b with a, b ≤ 5; rise and run each
of size ≤ 10, the division a times-table fact; equations `y = mx + b` with m and b of size ≤ 10; no `f(x)` (8.F does
not require it).
1. Is It a Function? — "Which is NOT a function?" → `(2, 5), (2, 7)` (beside sets that only repeat an output); "Inputs 1, 2, 3 give outputs 4, 4, 4. Function?" → `Yes`; "y = x + 4. Input 3. Output?" → 7. REPEAT_OUTPUT (a repeated output read as breaking it), INPUT_OUTPUT_SWAP, PLUGGED_WRONG.
2. Slope & Rate of Change — "Slope through (1, 3) and (3, 7)?" → 2; "x: 0, 1, 2 and y: 5, 8, 11. Rate of change?" → 3; "Slope through (2, 9) and (4, 5)?" → −2; "(0, 0) and (3, 2)" → `2/3`. RUN_OVER_RISE (`1/2`), SIGN_SLIP (2), RISE_ONLY (4), START_AS_RATE (5).
3. Start Value & y = mx + b — "y = 3x + 5. Initial value?" → 5; "Slope of y = −2x + 7?" → −2; "$10 to start, then $5 a week. Equation?" → `y = 5x + 10`; "x: 0, 1, 2 and y: 3, 5, 7. Equation?" → `y = 2x + 3`. SWAPPED_MB (`y = 10x + 5`), SLOPE_AS_START, VALUE_AT_1 (`y = 2x + 5`).
4. Proportional & Compare — "A: y = 4x. B: 10 miles in 2 hours. Which is faster?" → `B`; "A line through (0, 0) and (4, 12). Unit rate?" → 3; "Which shows y proportional to x?" → `y = 5x` (beside `y = 5x + 1`). BIGGER_TOTAL (picks by 10 > 4), INVERTED_RATE (`1/3`), HAS_START.
5. Linear or Not? — "Which is NOT linear?" → `y = x^2` (beside `y = 3x`, `y = 2x + 1`, `y = 7 − x`); "y = −3x + 2. As x grows, y?" → `Decreases`; "x: 1, 2, 3 and y: 2, 4, 8. Linear?" → `No`. MINUS_SIGN_DECREASES (`y = 3x − 2` read as decreasing), CONSTANT_NOT_LINEAR, EQUAL_STEPS_MISSED.

**pythagorean-theorem** (seed 20261036). Read `area-volume`, `circles`, `rational-numbers` (T5 distance). Bounds: §4b
Pythagorean. Sides 1-10; every square ≤ 100 and every sum or difference of two (box: three) squares ≤ 100; whole answers
come from 3-4-5 and 6-8-10 (and box diagonals 1-2-2 → 3, 2-4-4 → 6, 2-3-6 → 7, 1-4-8 → 9, 4-4-7 → 9, 3-6-6 → 9: the complete list); every other
length is `√n`, n 2-99 not a perfect square, never simplified. Coordinates of size ≤ 10.
1. Find the Hypotenuse — "Legs 3 and 4. Hypotenuse?" → 5; "Legs 2 and 3. Hypotenuse?" → `√13`. ADDED_LEGS (7, 5), NO_ROOT (25, 13), ROOT_OF_LEG_SUM (`√5`), DOUBLED_FOR_SQUARE (`√10`: 2a + 2b).
2. Find a Leg — "Hypotenuse 10, one leg 6. Other leg?" → 8; "Hypotenuse 4, one leg 2. Other leg?" → `√12`. ADDED_SQUARES (`√136`, `√20`), SUBTRACTED_SIDES (4, 2), NO_ROOT (64, 12).
3. Is It a Right Triangle? — "Sides 6, 8, 10. Right triangle?" → `Yes`; "Which sides make a right triangle?" → `3, 4, 5` (beside `4, 5, 6`, `2, 3, 4`, `5, 5, 7`). CONSECUTIVE, CLOSE_ENOUGH (5, 5, 7: 50 vs 49), LEG_AS_LONGEST.
4. Distance on the Plane — "Distance from (1, 2) to (4, 6)?" → 5; "Distance from (1, 1) to (3, 4)?" → `√13`. TAXICAB (7, 5), ONE_LEG, NO_ROOT, ADDED_COORDS.
5. Stories & 3D — "A 10 ft ladder, base 6 ft from the wall. How high?" → 8; "Walk 3 km north, then 4 km east. How far?" → 5; "Box 2 by 3 by 6. Longest diagonal?" → 7. ADDED_ALL (11), FACE_ONLY (`√13`), NO_ROOT (49), ADDED_SQUARES for a leg.

**transformations** (seed 20261037). Read `rational-numbers` (T4 reflections), `proportional-relationships` (T5 scale).
Bounds: integer coordinates of size ≤ 10 before every move and after every rigid move; slides ≤ 10 per axis; rotations
90 and 180 degrees about the origin; reflections over the x-axis and the y-axis; dilations about the origin by 2-5 or
1/2, 1/3, 1/4 (coordinates divisible), images ≤ 20 in size, every product a times-table fact.
1. Slides — "(2, 5) slides 3 left and 4 down. Image?" → `(−1, 1)`; "(−3, 4) moves to (1, 4). The slide?" → `4 right`. WRONG_DIRECTION (`(5, 9)`), SWAPPED_AXES (`(−2, 2)`), ONE_AXIS (`(−1, 5)`).
2. Flips — "(3, −2) reflected over the x-axis?" → `(3, 2)`; "(5, 2) maps to (−5, 2). Which move?" → `Over y-axis` (and no slide choice that also works); "A segment of length 5 is reflected. New length?" → 5 (8.G.A.1). WRONG_AXIS (`(−3, −2)`), BOTH_SIGNS (`(−3, 2)`), SWAPPED_XY (`(−2, 3)`), SIZE_CHANGES.
3. Turns — "(3, 1) turns 90 degrees counterclockwise about (0, 0)?" → `(−1, 3)`; "(2, −5) turns 180 degrees about the origin?" → `(−2, 5)`. WRONG_TURN (`(1, −3)`), SWAP_ONLY (`(1, 3)`), NEG_ONLY (`(−3, 1)`), REFLECTED_INSTEAD.
4. Dilations — "(2, 3) dilated by scale factor 4 from (0, 0)?" → `(8, 12)`; "(6, 10), scale factor 1/2" → `(3, 5)`; "A side of 4 becomes 12. Scale factor?" → 3; "Scale factor 3. A 40 degree angle becomes?" → 40. ADDED_FACTOR (`(6, 7)`), ONE_COORD (`(8, 3)`), INVERTED (`1/3`), DIFFERENCE (8), ANGLES_SCALE (120).
5. Move Sequences — "(1, 2): flip over the x-axis, then slide 3 up?" → `(1, 1)` (order matters: slide first gives `(1, −5)`); "Which move can change a shape's size?" → `Dilation`; "Rotate it, then dilate by 2. The image is?" → `Similar` (beside `Congruent`; never `Similar` beside a `Congruent` answer). ORDER_SWAP, DILATION_CONGRUENT, RIGID_CHANGES_SIZE.

**triangles-parallel-lines** (seed 20261038). Read `angle-relationships` (its bounds string is the model). Bounds: §4b
Angles, grade-8 part: angles in tens 10-170; triangle sums 180, an exterior angle the sum of the two remote angles
(≤ 170), parallel-line pairs equal or adding to 180; x a multiple of 10 or a tens quotient (6x = 180 is 18 ÷ 6);
isosceles base angles through an even-tens top angle.
1. Triangle Angle Sum — "A triangle has angles 50 and 60 degrees. Third angle?" → 70; "Right triangle, one angle 30 degrees. Other?" → 60; "Isosceles triangle, top angle 40 degrees. Each base angle?" → 70. USED_360 (250), FORGOT_ONE (130), NO_HALF (140), USED_90 for a non-right triangle.
2. Exterior Angles — "Triangle: angles 40 and 70. Exterior angle at the third?" → 110; "Exterior angle 120, one remote angle 50. The other?" → 70. INTERIOR_FOR_EXTERIOR (70: the third interior angle), ONE_REMOTE (40), ADDED (170: 120 + 50).
3. Transversal Angles — "Parallel lines, transversal. Angle 70. Corresponding angle?" → 70; alternate interior and exterior equal, mixed with same-side interior and linear pairs (180 − a), so "copy the given number" is right on only 25-75 % of items (the first build had it right on all 34); vertical angles at most 4 items, explained as "always equal", never by parallel lines. SUPP_FOR_EQUAL (110), COMP_FOR_EQUAL (20), EQUAL_FOR_SUPP.
4. Equal or Add to 180? — "Parallel lines. Same-side interior angle to 70 degrees?" → 110; "Alternate interior angles are?" → `Equal` (beside `Add to 180`); "Same-side interior angles are?" → `Add to 180`. EQUAL_FOR_SUPP (70), VOCAB_SWAP, USED_90.
5. Solve for x & Similar — "Triangle angles x, 2x and 3x degrees. x?" → 30; "Alternate interior angles 2x and 80 degrees. x?" → 40; "Triangles: one has 40 and 60, one has 60 and 80. Similar?" → `Yes`. GAVE_ANGLE (90 for 3x), NO_DIVIDE, NEEDS_SAME_LISTED (`No`), SUPP_FOR_EQUAL.

**cylinders-cones-spheres** (seed 20261039). Read `circles` (π answers), `area-volume` (T4 prisms). Bounds: §4b
π volumes. Radii 1-5 (a sphere's 1 or 3, its diameter 2 or 6), heights 1-10; every π coefficient a whole number 1-100,
or `(4/3)π` / `(2/3)π` for a radius-1 sphere or hemisphere; every coefficient reached through times-table steps in some
order (2 × 5 × 5 is 10 × 5; 9 ÷ 3 × 4); "using 3 for π" answers whole ≤ 100.
1. Cylinders — "Cylinder: radius 3, height 4. Volume?" → `36π`; "Cylinder: diameter 4, height 5. Volume?" → `20π`. NO_SQUARE (`12π`), DIAMETER_AS_RADIUS (`80π`), LATERAL_AREA (`24π`: 2πrh).
2. Cones — "Cone: radius 3, height 4. Volume?" → `12π`; "Same base and height: cylinder 30π. The cone?" → `10π`. NO_THIRD (`36π`), HALF_FOR_THIRD (`18π`), TRIPLED (`90π`).
3. Spheres — "Sphere: radius 3. Volume?" → `36π`; "Ball, diameter 6. Volume?" → `36π`; "Hemisphere, radius 3. Volume?" → `18π`; "Sphere: radius 1. Volume?" → `(4/3)π`; "Sphere: radius 2. Volume, using 3 for π?" → 32. SQUARED_NOT_CUBED (`12π`), NO_FOUR_THIRDS (`27π`), DIAMETER_AS_RADIUS (`288π`), WHOLE_FOR_HALF.
4. Work Backward & Estimate — "Cylinder volume 45π, radius 3. Height?" → 5; "Sphere volume 36π. Radius?" → 3; "Cylinder: radius 2, height 5. Volume, using 3 for π?" → 60. FORGOT_SQUARE (15), FORGOT_THIRD, DIAMETER_FOR_RADIUS (6).
5. Compare & Scale — "Double a cylinder's radius. Volume times?" → 4; "Double its height?" → 2; "Double a sphere's radius. Volume times?" → 8; "Same r and h: a cone is what part of the cylinder?" → `1/3`. DOUBLE_IS_DOUBLE (2), SQUARE_FOR_CUBE (4), CUBE_FOR_SQUARE (8).

**scatter-two-way** (seed 20261040). Read `data-statistics`, `probability`. Bounds: §4b Two-way tables, and lines of fit
per Coordinates and lines. Point lists of 3-5 integer points with coordinates 0-20; lines of fit `y = mx + b` with m 1-10
(or −1 to −5) and b 0-20, x 1-10, predictions whole and ≤ 100; 2-by-2 tables with cells 0-20 and a grand total ≤ 60;
relative frequencies in simplest form with denominators 2-12, or a §4b percent; every division a times-table fact.
1. Association — "Study time goes up, test scores go up. Association?" → `Positive`; "A car's age goes up, its value goes down?" → `Negative`; "(1, 9), (2, 7), (3, 6), (4, 3): association?" → `Negative`; shoe size and favorite color → `None`. BOTH_DOWN_NEGATIVE (less sleep, lower scores read as negative), DOWN_IS_NONE, CAUSE_FOR_LINK.
2. Outliers & Lines of Fit — "Points (1, 2), (2, 3), (3, 4), (4, 15). Outlier?" → `(4, 15)`; "Which line fits (1, 3), (2, 5), (3, 7)?" → `y = 2x + 1`. LARGEST_X_OUTLIER (the high-x point that fits), SLOPE_FROM_ONE_POINT, START_AS_SLOPE.
3. Use a Line of Fit — "Line of fit y = 2x + 10. Predict y at x = 5." → 20; "Cost y = 3x + 4 (x hours). Cost per hour?" → `$3`; "Plant h = 2w + 5 (w weeks). Height at the start?" → 5. NO_START (10), SLOPE_AS_START, START_AS_SLOPE, ADDED_ALL (17).
4. Two-Way Table Counts — "Boys: 6 yes, 4 no. Girls: 7 yes, 3 no. Total yes?" → 13; "12 play sports; 5 of them play music. Sports only?" → 7. WRONG_ROW, GRAND_TOTAL, ADDED_FOR_ONLY (17).
5. Relative Frequency — "Boys: 6 yes, 4 no. Fraction of boys saying yes?" → `3/5`; "Boys: 6 of 12 say yes. Girls: 5 of 6. Who is more likely?" → `Girls`. PART_TO_PART (`3/2`), WRONG_TOTAL (`6/13`), GRAND_TOTAL (`3/10`), COUNT_NOT_RATE (`Boys`).

### Grade-8 standards that do not fit the multiple-choice race

| Standard | Why it does not fit | What would unlock it |
|---|---|---|
| 8.NS.A.1 (show a decimal repeats: 1/7 by long division) | Heavy arithmetic, which §4a forbids; benchmark repeats are covered (`roots-irrationals` T3) | — (conflicts with the content rule by design) |
| 8.NS.A.2 (locate on a number line diagram) | Needs a picture; the estimates are covered (`roots-irrationals` T4-T5) | Per-item image |
| 8.EE.A.2 (cube roots of 125 and up; `x^2 = p` for p past 100) | Cubes past 4^3 and squares past 10^2 break §4a's powers bound | Aaron's say-so to allow 5^3, 10^3, 11^2, 12^2 |
| 8.EE.B.5 (graph a proportional relationship; compare a graph with an equation) | Graphs need a picture; unit rate as slope from points or words is covered (`linear-functions` T4) | Per-item image |
| 8.EE.B.6 (explain with similar triangles why the slope is the same) | An argument, not a value; `y = mx + b` is covered (`linear-functions` T3) | — (classroom task) |
| 8.EE.C.8.B (estimate by graphing; solve by substitution or elimination) | Graphing needs a picture; general elimination is several steps past one line; systems by inspection and sum/difference are covered (`linear-equations` T5) | Per-item image; a longer prompt |
| 8.F.A.2, 8.F.B.4, 8.F.B.5 (functions given as graphs; sketch a graph from words) | Graphs and sketches need a picture; tables, rules and words are covered (`linear-functions`) | Per-item image |
| 8.G.A.1 (verify by experiment), 8.G.A.2, 8.G.A.4 (describe a sequence mapping one given figure to another) | Hands-on, and two figures need a picture with a sentence answer; single-point sequences are covered (`transformations` T5) | Per-item image; longer door labels |
| 8.G.A.5 (informal arguments) | An argument; the angle facts are covered (`triangles-parallel-lines`) | — (classroom task) |
| 8.G.B.6 (explain a proof of the theorem and its converse) | A proof; the converse check is covered (`pythagorean-theorem` T3) | — (classroom task) |
| 8.G.B.7 (triples 5-12-13, 8-15-17, 7-24-25) | 12^2 = 144 and up break §4a's squares bound | Aaron's say-so on squares to 15^2 |
| 8.G.C.9 (spheres of radius other than 1 and 3; real-world composites) | (4/3)r^3 is whole and ≤ 100 only at r = 3; composites need a picture | Cubes past §4a; per-item image |
| 8.SP.A.1, 8.SP.A.2 (construct a scatter plot; see clusters; fit a line by eye) | Plotting and judging a fit need a picture; association, outliers from a short list and lines of fit as rules are covered (`scatter-two-way`) | Per-item image |
| 8.SP.A.4 (construct a two-way table) | Building a table is a task; reading counts and relative frequencies is covered (`scatter-two-way` T4-T5) | — |
