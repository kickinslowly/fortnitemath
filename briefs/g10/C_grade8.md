# C: the grade-8 library (Opus lead + Sonnet builders)

Read `briefs/g10/TEAM.md` first (ownership, report format; you need no UEFN and no lock), then the project skill
`.claude/skills/cartridge-library/SKILL.md` (the procedure; you are its "lead"), `PROTOCOL.md` §4, §4a, §4b, §5,
`cartridges/LIBRARY.md` (the grade-6 and grade-7 sections are your model, including their "does not fit" tables and
"Rules for every grade-7 cartridge"), `.claude/skills/cartridge-library/BRIEF.md` (the builder brief you will retarget),
and one grade-7 cartridge end to end (`cartridges/linear-expressions/` + `tests/test_linear_expressions.py`).

## Why

GOALS G3: grade 8 is the last empty grade ("Content runway: 11 grade-6 skills, 1 grade-7, 0 grade-8" in the review;
grade 7 has since landed 8). Island memory at 19 cartridges measured 35,635 / 100,000 on 2026-10-14, so there is room.
Aaron's content rule (PROTOCOL §4a, 2026-10-04): simple numbers, concept over arithmetic: a grade-8 kid must be able to
do every item in their head; what is tested is the idea.

## Deliverables

1. **Plan (checkpoint before firing anyone):** a `## Grade 8` section in `cartridges/LIBRARY.md` in the grade-7 shape:
   the cartridge table (id, title <= 32, subtitle <= 40, CCSS standards, a unique seed not used by any existing
   cartridge), tier plans with starting misconception keys, the rules list, and the "standards that do not fit the
   multiple-choice race" table. Aim for 8 cartridges spanning 8.NS, 8.EE, 8.F, 8.G and 8.SP, chosen for what fits a
   four-choice door with a one-line prompt (prompt <= 60 chars, the HUD charset: ASCII + × ÷ − ≤ ≥ ≠ √ π). Candidates
   (yours to change): irrational numbers and estimating roots; exponent rules; scientific notation; slope and
   proportional relationships; linear equations incl. one / none / infinitely many solutions; systems by inspection;
   functions (is it a function, rate of change, initial value from a table or rule); Pythagorean theorem with triples;
   transformations of a point on the coordinate plane; volume of cylinders, cones and spheres in terms of π; angle facts
   with parallel lines and triangles (check overlap with grade-7 `angle-relationships`); two-way tables and
   scatter-plot association. Grade-8 bounds that §4a/§4b do not cover yet (exponents, scientific notation, roots, π
   volumes) go into PROTOCOL §4b, which you own for this. Check every example in your plan against the bounds before
   firing (the grade-6 lead found three of its own out of bounds).
2. **Fire one Sonnet builder per cartridge, all in one message:** `Agent(model: "sonnet", subagent_type:
   "general-purpose")`, prompt "Read and follow `.claude/skills/cartridge-library/BRIEF.md` exactly. Your cartridge
   id: `<id>`." Retarget BRIEF.md to grade 8 first (its first lines say how). Each builder owns only
   `cartridges/<id>/` and `tests/test_<id>.py`.
3. **Audit each report as it lands:** read samples as an 8th grader would. Watch for grade drift (high-school math:
   quadratics, function notation beyond 8.F, irrational arithmetic), arithmetic heavier than the concept, ambiguous
   prompts, two defensible answers, distractors that are not real misconceptions. Send fixes back with `SendMessage` to
   the same builder id. Work 10+ items per cartridge yourself (80+ in all; the grade-7 lead worked 80, all right).
4. **Do NOT insert** (`fnm insert` / `fnm emit` are the parent's). Leave the slot alone.
5. **Write `<your scratch folder>/insert.md`:** the ids in insert order, each cartridge's test count, the slot-size
   estimate after insert (PROTOCOL O4), and 2 printed items per tier per cartridge (`PYTHONIOENCODING=utf-8`).

## Done means

Every builder reported and audited, the full `pytest -q` green except the two expected slot tests (TEAM.md), the plan in
LIBRARY.md matching what was built, and `insert.md` written. Report per TEAM.md, plus: which standards you left out and
why, and any PROTOCOL rule you changed.
