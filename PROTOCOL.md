# FNM Cartridge Protocol — v1 (`fnm-cart/1`)

The contract between a **cartridge** (one math topic) and a **console** (a Fortnite map, or the
browser emulator). Any cartridge that passes `validate` runs on any console that speaks the same
protocol major version. Neither side knows anything about the other beyond this document.

```
 cartridges/<id>/                fnm (Python toolchain)                consoles
 ┌──────────────────┐   bake    ┌──────────────┐   emit    ┌──────────────────────────────────┐
 │ cartridge.json   │ ────────► │ baked.json   │ ────────► │ console/verse/generated/          │
 │ generator.py     │ validate  │ (frozen,     │           │   fnm_active_cartridge.verse     │──► UEFN map
 │  (or items.src)  │           │  reviewable) │ ────────► │ emulator/carts.js                 │──► browser
 └──────────────────┘           └──────────────┘           └──────────────────────────────────┘
```

**Why build-time:** published Fortnite islands cannot read files or make network calls. A cartridge
therefore cannot be loaded at runtime; "inserting" one means regenerating exactly one Verse file
(`fnm_active_cartridge.verse`) and rebuilding Verse in UEFN. No other map file changes. That single
generated file is the cartridge slot.

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
- Choice order in `baked.json` is final. Consoles display choices in baked order (keeps the emulator
  and the map identical, and lets `validate` check answer-position balance).

`baked.json` = the manifest fields + `"baked_with": "<toolchain version>"` + `"items": [...]`.

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

What happens after a wrong answer (retry, respawn, lose a life) is map design, not protocol.

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

`fnm insert <cartridge>` emits to **every** registered map: `maps/<map-id>/generated/fnm_active_cartridge.verse`.
Which cartridge a map currently holds is recorded in `maps/<map-id>/generated/SLOT.txt` (id, version, profile).

## 7. Emit targets and render profiles

Baked text is canonical. Emitters apply a **render profile**:

| Profile | `^n` with digit exponent | `×` `÷` `−` etc. |
|---|---|---|
| `unicode` | superscript digits (`3^2` → `3²`) | kept |
| `ascii` | kept as `^` | `×`→`*`, `÷`→`/`, `−`→`-`, `≤`→`<=`, `≥`→`>=`, `≠`→`!=`, `√`→`sqrt`, `π`→`pi` |

Non-digit exponents (`2^(1 + 1)`) stay `^` in both. Which profile the UEFN map uses is decided once by
an in-game font test (O1, resolved: `unicode`); the emulator uses `unicode` too.

**Verse target** — `maps/<map-id>/generated/fnm_active_cartridge.verse` (one per registered map, §6a), defining exactly one function:

```verse
FnmActiveCartridge():fnm_cartridge = fnm_cartridge{ ... }
```

built only from the types in `console/verse/fnm_cartridge.verse` (§8), using struct literals and
`array{}` — nothing else, so the generated surface stays small enough to trust without a compiler.
Strings are escaped for Verse (`{ } " \` and any other character Verse requires). The file begins with
a `# GENERATED by fnm — do not edit` header naming the cartridge id, version and profile.

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
