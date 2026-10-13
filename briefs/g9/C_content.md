# Brief C: content lead, the grade-7 library (GOALS G3 "Grade 7 and 8 libraries", grade 7 now)

Read `briefs/g9/TEAM.md` first (ownership, machine rules, report format). You are **C**, a lead: you plan, you fire
builders, you audit them. You own `cartridges/LIBRARY.md`, the new `cartridges/<id>/` folders, the new
`tests/test_<id>.py` files and `.claude/skills/cartridge-library/BRIEF.md`. **You touch no UEFN, no Verse, and you do
not run `fnm insert` or `fnm emit`** (the parent inserts once at the end; until then the full suite shows
`test_emit.py::test_generated_slot_file_lints` and `test_carts_js` failing, which is expected).

## Procedure: `.claude/skills/cartridge-library/SKILL.md`, with these changes
- **Builders run on Sonnet** (`Agent(subagent_type: "general-purpose", model: "sonnet")`), not Opus: Aaron's standing
  instruction for this team is low-level work on lower models, management on Opus/Fable. That makes your audit the
  quality gate. Fire them all in ONE message so they run in parallel. Prompt per builder: "Read and follow
  `.claude/skills/cartridge-library/BRIEF.md` exactly. Your cartridge id: `<id>`. Also read `briefs/g9/TEAM.md`
  'The machine' and 'Working rules'. Checkpoint to disk as you go."
- If the Agent tool is not available to you, stop after step 1 and report the plan and the ids; the parent fires them.
- Existing grade 7: `integer-ops` only (do not rebuild it; it covers 7.NS.A.1-A.2 integer operations).

## Step 1: plan grade 7 in `cartridges/LIBRARY.md`
A `## Grade 7` section shaped exactly like `## Grade 6`: the cartridge table (id, title ≤ 32, subtitle ≤ 40,
standards), tier plans with seeds (`2026101N`-style, unique across the whole library: grep the existing seeds) and
starting misconception keys, and a "Grade-7 standards that do not fit the multiple-choice race" table.
- Cover the CCSS grade-7 domains the race can carry: 7.RP (proportional relationships, unit rates with fractions,
  percent problems), 7.NS (rational-number operations beyond `integer-ops`: fractions and decimals with signs), 7.EE
  (equivalent expressions, two-step equations and inequalities `px + q = r`), 7.G (scale drawings, angle relationships,
  circles, area / surface area / volume), 7.SP (probability; sampling only where a 3-second question exists).
  Six to eight new cartridges is the right size; fewer, sharper ones beat thin ones.
- **Content rule (Aaron, standing): simple numbers, concept over arithmetic.** Every example in your plan must satisfy
  PROTOCOL §4a / §4b; check each one yourself before firing (the grade-6 run found three of the parent's plan examples
  out of bounds). Read `PROTOCOL.md` §4a, §4b, §5 first. Mental math for a 7th grader, 3-second questions.
- Edit BRIEF.md's grade lines to grade 7 (its line 3 says how) before firing.

## Step 2: fire one Sonnet builder per cartridge (all in one message)

## Step 3: audit each report as it lands
Read its samples as a 7th grader would. Watch for grade drift (math from grade 8: e.g. exponent rules, scientific
notation, Pythagoras, slope), for §4a/§4b bound breaches, for wrong answers (run the cartridge's own tests, then print 2
random items per tier with `PYTHONIOENCODING=utf-8` and work them yourself), for prompts over 60 chars and choices over
14. Send fixes back to the SAME builder with SendMessage (one round, two at most). A cartridge you cannot get right
in two rounds: drop it from the plan and say why.

## Step 4: verify
- `.venv/Scripts/python -m pytest -q`: all green except the two expected slot tests above (name any other failure).
- Every new cartridge validates (`python -m fnm validate <id>`) and bakes (`python -m fnm bake <id>`), committed-style
  `baked.json` present.
- Do NOT run the emulator e2e or insert; the parent does both after inserting.

## Report (TEAM.md format) plus
- The final grade-7 table, item counts, the slot size estimate (KB of `baked.json` per cartridge), and 2 sample items per
  tier per cartridge, verbatim, so the parent can read them.
- For each builder: what you sent back and why.
