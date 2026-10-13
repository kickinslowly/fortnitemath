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
