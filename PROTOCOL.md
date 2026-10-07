# FNM Cartridge Protocol — v1 (`fnm-cart/1`)

The contract between a **cartridge** (one math topic) and a **console** (a Fortnite map, or the
browser emulator). Any cartridge that passes `validate` runs on any console that speaks the same
protocol major version. Neither side knows anything about the other beyond this document.

```
 cartridges/<id>/                fnm (Python toolchain)                consoles
 ┌──────────────────┐   bake    ┌──────────────┐   emit    ┌──────────────────────────────────┐
 │ cartridge.json   │ ────────► │ baked.json   │ ────────► │ maps/<map>/generated/             │
 │ generator.py     │ validate  │ (frozen,     │           │   fnm_active_cartridge.verse     │──► UEFN map
 │  (or items.src)  │           │  reviewable) │ ────────► │ emulator/carts.js                 │──► browser
 └──────────────────┘           └──────────────┘           └──────────────────────────────────┘
```

**Why build-time:** published Fortnite islands cannot read files or make network calls. A cartridge
therefore cannot be loaded at runtime; "inserting" one means regenerating exactly one Verse file
(`fnm_active_cartridge.verse`) and rebuilding Verse in UEFN. No other map file changes. That single
generated file is the cartridge slot, and since 2026-10-04 it holds **every** inserted cartridge: the
player picks one at run start (§6b). Twelve 200-item cartridges (862 KB of Verse) compiled clean in
UEFN 42.30 in under 3 s (O4).

## 1. Vocabulary

| Term | Meaning |
|---|---|
| Cartridge | One topic. Source dir `cartridges/<id>/`. |
| Item | One question: prompt, 2–4 choices, exactly one correct. |
| Tier | Difficulty band, 1..T (T = 1–5). Every item has one tier. |
| Misconception | A named wrong mental rule. Wrong choices point at one, so a console can say *why* a choice is wrong. |
| Console | Anything that plays a cartridge: the UEFN map runtime, the browser emulator. |
| Bake | Run the generator (deterministic seed), validate, write `baked.json`. Committed to git so content is reviewable as a diff. |
| Emit | Turn `baked.json` into a console's native form (Verse file, emulator JS). |
| Insert | `bake` + `validate` + `emit` for every console. The one command that "plugs in" a cartridge. |

## 2. The interaction model (the one gameplay assumption)

A console presents a **prompt** and **2–4 labeled options**, and the player selects one by a physical
action (run through a door, stand on a pad, shoot a target). There is no free-text entry — Fortnite
has no practical number input. Every topic must therefore be expressible as multiple choice. This is
the only constraint the protocol places on map design; *how* a map presents the choice is the map's business.

## 3. Cartridge source

`cartridges/<id>/cartridge.json` (the manifest):

```json
{
  "protocol": "fnm-cart/1",
  "id": "order-of-ops-exponents",
  "version": "1.0.0",
  "title": "Order of Operations",
  "subtitle": "Exponents & Parentheses",
  "grade": "6",
  "standards": ["CCSS.MATH.CONTENT.6.EE.A.1", "CCSS.MATH.CONTENT.5.OA.A.1"],
  "seed": 20261002,
  "items_per_tier": 40,
  "tiers": [
    { "tier": 1, "name": "Warm-up", "description": "Two operations; multiply before add." }
  ],
  "misconceptions": {
    "LTR": { "student": "Worked left to right. Do × and ÷ before + and −.", "teacher": "Evaluates strictly left to right, ignoring precedence." }
  }
}
```

Content comes from exactly one of:
- `generator.py` exposing `generate(manifest: dict, rng: random.Random) -> list[dict]` returning
  items in the §4 shape **without** `id` (the toolchain assigns ids). Procedural topics.
- `items.src.json` — a hand-authored list in the same shape. Topics written by hand.

`id`: lowercase kebab-case, ≤ 40 chars, equals the directory name.
`grade`: a short string (`"6"`, `"7"`); the skill picker groups cartridges by it (§6b).
Tiers: use 5 unless there is a reason not to — the starter map paints its hallway walls per tier for 5.

## 4. Item shape (in `baked.json`)

```json
{
  "id": "order-of-ops-exponents/t1/007",
  "tier": 1,
  "prompt": "3 + 4 × 2",
  "choices": ["14", "11", "10", "9"],
  "answer": 1,
  "misconceptions": ["LTR", null, "ARITH", "ARITH"],
  "explanation": "4 × 2 = 8, then 3 + 8 = 11."
}
```

- `misconceptions[i]` is `null` for the correct choice, otherwise a key of the manifest catalog.
  `ARITH` ("Check your arithmetic.") is reserved and always available without declaring it — the
  generic distractor when no real misconception yields a distinct value.
- Choice order in `baked.json` is final for the data (it lets `validate` check answer-position balance), and
  the emulator shows it as baked. The UEFN map shuffles the display order every time it shows an item, so a
  repeated question does not keep its right door (Aaron, 2026-10-05: "after enough runs it would just become
  memorization"). Choice text therefore must never depend on position ("all of the above", "both A and B").

`baked.json` = the manifest fields + `"baked_with": "<toolchain version>"` + `"items": [...]`.

## 4a. Content rule: concept over arithmetic (Aaron, 2026-10-04)

A map tests whether the player can apply the **concept**. The arithmetic around it must be mental math
for the grade, so nobody reaches for paper or a calculator and nobody guesses because the numbers got
heavy. Difficulty comes from step count, grouping and signs — never from number size. Applies to every
cartridge for every map until Aaron says otherwise.

Defaults every cartridge meets (a cartridge may tighten them; loosening needs Aaron's say-so, recorded in
its manifest):

| What | Bound |
|---|---|
| Literals under `+` / `−` | size ≤ 20 (integer topics with signs as the concept: ≤ 12) |
| Factors and divisors | size 2–10 |
| A bare dividend | ≤ 100 and always divisor × quotient with both ≤ 10 (a times-table fact) |
| Every `×` step | both operand *values* ≤ 10 in size (a group's value counts: `(3 + 4) × 8` is fine, `12 × 6` is not) |
| Every `÷` step | exact; divisor and quotient 2–10 in size |
| Powers | result ≤ 100: squares of 2–10, cubes of 2–4 (a group as the base must land in that range) |
| Every intermediate value and the answer | integers, size ≤ 100 (non-negative where the topic has no negatives) |
| Wrong choices | whatever a misreading produces, size ≤ 999 — a too-big distractor is a wrong answer, not a flaw |

Each procedural cartridge's tests assert its bounds against `baked.json` by walking every correct step
(the generator's `trace`), so a generator that drifts fails before it reaches a map.

### 4b. Topics whose concept is not whole numbers (Aaron, 2026-10-05: "doable in head, even topic related")

Fractions, decimals, percents, measurement and data topics cannot keep every value an integer; the
non-integer *is* the concept. They keep §4a's spirit by these rules, stated in the manifest's optional
`"bounds"` string so the tests and a reviewer can find them:

| Topic | Bound |
|---|---|
| Every topic | Every hidden whole-number step is a §4a step (× and ÷ inside the times tables, + − ≤ 20 per literal, results ≤ 100) |
| Fractions | Denominators 2–12; numerators ≤ 12; a mixed number's whole part ≤ 10; every numerator/denominator product a times-table fact; answers in simplest form, written `a/b` or `w a/b` (mixed when > 1) |
| Decimals | Operands with at most 2 decimal places and at most 2 non-zero digits; the digit work is a §4a fact (`0.6 × 0.2` → `6 × 2`); quotients exact |
| Percents | 10, 20, 25, 50, 75 % and multiples of 10; the whole ≤ 100 and chosen so the hidden ÷ is a times-table fact (25 % and 75 % of wholes ≤ 40, tens of percent of 10 × 2..10); the answer an integer |
| Measurement | Lengths 1–10 (a ½ edge allowed where the standard asks for fractional edges; a length of 1 may be a × factor, the one exception to §4a's 2–10); areas, volumes and surface areas ≤ 100 |
| Data | 3–7 values, each 0–20, sum ≤ 100; means, medians and MADs integers |
| Choices | No two choices equal in **value** (`1/2` and `2/4`, `0.5` and `1/2` never sit together): the player must never face two right doors |

Like §4a, each such cartridge's tests assert its bounds against `baked.json`.

## 5. Validation rules (`fnm validate`, hard failures)

1. `protocol` major matches the toolchain's (`fnm-cart/1`).
2. Tiers numbered 1..T contiguously, T ∈ 1..5; every item's tier exists.
3. Each tier has ≥ `items_per_tier` items, and `items_per_tier` ≥ 24 (enough that a replay differs).
4. Item ids unique; prompts unique within a tier.
5. 2–4 choices; choices unique after trimming; `answer` in range; `misconceptions` same length as
   `choices`, `null` exactly at `answer`, every non-null key is declared or `ARITH`.
6. Length limits (display-driven): prompt ≤ 60 chars, each choice ≤ 14, explanation ≤ 160,
   misconception `student` text ≤ 80, tier name ≤ 24, title ≤ 32, subtitle ≤ 40.
7. Charset: every display string uses only printable ASCII plus `× ÷ − ≤ ≥ ≠ √ π`.
   Exponents are written `^` (`3^2`, `(1 + 2)^3`); consoles render them (§7).
8. Answer balance: per tier, for items with n choices, each position holds the answer in
   ≥ 0.5/n and ≤ 1.5/n of items. (Stops "it's always B".)
9. Bake determinism: baking twice with the manifest seed yields byte-identical `baked.json`.

Cartridge-specific correctness (e.g. "is 11 actually the answer") is the generator's job, and each
procedural cartridge ships a test that re-checks every baked answer by an independent method.

## 6. Console contract

Maps differ (station count, doors per station, linear or free-roam). The rule: **the protocol fixes the
minimums both sides meet; each map declares its shape in a map profile (§6a); the toolchain adapts the
cartridge to the map at emit time.** Content is never truncated mid-string, and every map spans the
cartridge's full difficulty range — easiest tier first, hardest tier last — whatever its size.

A console MUST:
- Give every question station a **difficulty position** p ∈ [0, 1]. Station tier =
  `1 + round_half_up(p * (T - 1))`. A linear map with S stations uses p = (s - 1) / (S - 1) for
  stage s (1-based); S = 1 gives p = 0. Integer form (Verse, no floats):
  `tier = 1 + (2*(s-1)*(T-1) + (S-1)) div (2*(S-1))` for S > 1, else 1.
  Examples, T = 5: S = 3 → 1, 3, 5. S = 5 → 1, 2, 3, 4, 5. S = 10 → 1,1,2,2,3,3,4,4,5,5.
  A free-roam map sets p per station by hand (e.g. the tower top is p = 1).
- Display the §5 rule-6 maximum lengths without truncation. A map that cannot fit them is not a
  conforming console.
- Draw items within a tier at random **without replacement** per player per run; reshuffle when exhausted.
- On a wrong choice, show that choice's misconception `student` text (or "Check your arithmetic." for `ARITH`).
- On a correct choice, show the item's `explanation`.
- Show the cartridge `title` / `subtitle` somewhere at run start.
- Never depend on a specific cartridge id, tier count, or item content.
- Hold every inserted cartridge and let each player choose one at run start (§6b).

What happens after a wrong answer (retry, respawn, lose a life) is map design, not protocol.

## 6b. Skill picker (Aaron, 2026-10-04)

The slot holds every inserted cartridge (§7) and each **player** chooses one at run start — their own
choice, so two players in the same hallway may be racing different skills through the same doors. Fortnite
islands have no custom pre-game lobby, so the picker is in-game UI. A console MUST:
- Before the first countdown, show a two-step picker: the grades present (`grade`, ascending, numeric when
  every grade parses as a number), then that grade's cartridges, each showing its `title` and `subtitle`, in
  registry order (§7). Skip the grade step when only one grade exists; skip the picker when only one cartridge exists.
- Hold the player still while they pick; the race clock is not running.
- Apply every per-player rule of §6 to the chosen cartridge: tier count, pools, decks, title.
- Offer "change skill" on the finish board. A new run with the same skill needs no re-pick.
- Keep race times **per skill and per map**: personal bests, the session board and the island record are each
  keyed by the cartridge (the map is the island), and the board names the skill. Timings of different skills are
  never compared (Aaron, 2026-10-04: "best Order of Operations on the default map").
- Keep split times (the race clock at each right answer, used as the next runs' pace target) **per skill and per
  map** like times: a run is only ever paced against splits of the same skill on the same map.
- Provide a test hook that pre-selects a cartridge so automated runs skip the picker.

## 6a. Map profiles

Every map is registered as `maps/<map-id>/map.json`:

```json
{
  "protocol": "fnm-cart/1",
  "id": "starter",
  "title": "Starter Course",
  "max_choices": 4,
  "render_profile": "unicode",
  "penalties": ["Freeze", "Yeet", "Spike", "Mud", "Dizzy", "Blackout"],
  "uefn_project": null
}
```

- `penalties` (optional; default all): the wrong-door penalty pool, distinct names from the console's
  `fnm_penalty` enum. `fnm insert` / `fnm sync` write it to `maps/<map-id>/generated/fnm_map_profile.verse`
  (`FnmMapPenalties()`), which sync copies with the cartridge slot. Map design, not cartridge content.

- `max_choices` (2–4): doors/pads per station. When an item has more choices than this, emit keeps the
  correct choice and drops distractors in this order until it fits: `ARITH` choices first (last in baked
  order first), then misconception choices (last in baked order first). Remaining choices keep their
  baked relative order; `Answer`/`Feedback` are re-indexed.
- `render_profile`: §7 profile for this map's fonts.
- `uefn_project`: absolute path to the UEFN project root, or null until it exists. When set,
  `fnm sync <map-id>` copies `console/verse/*.verse` + the map's generated slot into the project's Verse folder.
- Station count and difficulty positions are NOT in the profile — they live in the map (Verse @editable
  config), because the map's runtime already knows its stations. The protocol's tier formula makes any
  count work.

`fnm insert <cartridge>` bakes and validates that cartridge, then emits **every baked cartridge** to **every**
registered map: `maps/<map-id>/generated/fnm_active_cartridge.verse` (§7). Every baked cartridge must be valid
or the emit stops. What a map holds is recorded in `maps/<map-id>/generated/SLOT.txt`: one `cartridge=<id> <version>`
line per cartridge in picker order, plus `profile=`.

## 7. Emit targets and render profiles

Baked text is canonical. Emitters apply a **render profile**:

| Profile | `^n` with digit exponent | `×` `÷` `−` etc. |
|---|---|---|
| `unicode` | superscript digits (`3^2` → `3²`) | kept |
| `ascii` | kept as `^` | `×`→`*`, `÷`→`/`, `−`→`-`, `≤`→`<=`, `≥`→`>=`, `≠`→`!=`, `√`→`sqrt`, `π`→`pi` |

Non-digit exponents (`2^(1 + 1)`) stay `^` in both. Which profile the UEFN map uses is decided once by
an in-game font test (O1, resolved: `unicode`); the emulator uses `unicode` too.

**Verse target** — `maps/<map-id>/generated/fnm_active_cartridge.verse` (one per registered map, §6a), defining
one function per baked cartridge plus the registry the console reads:

```verse
FnmCartridge_order_of_ops_exponents():fnm_cartridge = fnm_cartridge{ ..., Grade := "6", ... }
FnmCartridge_integer_ops():fnm_cartridge = fnm_cartridge{ ..., Grade := "7", ... }
# Every inserted cartridge in picker order: grade ascending (numeric when every grade is a number), then title.
FnmCartridges():[]fnm_cartridge = array{FnmCartridge_order_of_ops_exponents(), FnmCartridge_integer_ops()}
```

The per-cartridge function is `FnmCartridge_` + the id with `-` replaced by `_`. Everything is built only from
the types in `console/verse/fnm_cartridge.verse` (§8), using struct literals and `array{}` — nothing else, so
the generated surface stays small enough to trust without a compiler. Strings are escaped for Verse (`{ } " \`
and any other character Verse requires). The file begins with a `# GENERATED by fnm — do not edit` header naming
every cartridge id and version, the profile and the map. (Before 2026-10-04 the slot held one cartridge as
`FnmActiveCartridge()`.)

**Emulator target** — `emulator/carts.js`:

```js
window.FNM_CARTRIDGES = window.FNM_CARTRIDGES || {};
window.FNM_CARTRIDGES["<id>"] = { /* baked.json, profile applied */ };
```

One file holds every inserted cartridge (rewritten from all `cartridges/*/baked.json` on each insert),
so the emulator works from `file://` with no server.

## 8. Verse types (console side, fixed; a change here is a protocol bump)

```verse
# console/verse/fnm_cartridge.verse
fnm_tier := struct:
    Tier : int
    Name : string
    Description : string

fnm_item := struct:
    Id : string
    Tier : int
    Prompt : string
    Choices : []string
    Answer : int
    # Per choice: student-facing text for a wrong choice, "" at Answer.
    Feedback : []string
    Explanation : string

fnm_cartridge := struct:
    Protocol : string
    Id : string
    Version : string
    Title : string
    Subtitle : string
    # The manifest's grade, the picker's grouping key (§6b). Added 2026-10-04 with the picker.
    Grade : string
    Tiers : []fnm_tier
    Items : []fnm_item
```

Misconception ids are resolved to `student` text at emit time (`Feedback`), so the Verse runtime never
needs the catalog. Ids stay in `baked.json` for later analytics.

## 9. Versioning

- Protocol `fnm-cart/MAJOR`. Additive optional fields do not bump; anything a v1 console could
  misread does. Toolchain refuses to emit across a major mismatch.
- Cartridge `version` is semver; bump minor on content changes, major on tier restructuring.

## 10. Open items

- ~~O1~~ Resolved 2026-10-04: the Fortnite UI font renders `×`, `÷`, `−` and superscript digits in play, so maps use
  `unicode`. (✓ ✗ do not render; the console draws those as textures.)
- ~~O2~~ Resolved 2026-10-03: the 200-item generated file compiles clean in UEFN 42.30 and cooks server-side.
- ~~O3~~ Resolved: all Verse files sit flat in `<project>/Content/` (one module); no `<public>` needed.
- O4 (2026-10-04): the all-cartridges slot is proven to **compile** at 12 cartridges × 200 items (862 KB, 2.4 s,
  disproof: a planted unknown identifier on line 2606 was reported). Cook and runtime memory are proven only at
  the number of cartridges actually inserted; re-check in play after each insert past ~6.
