# RACE mode review: gamification, progression, social, virality (2026-10-13)

Reviewer lens: retention, meta-game, social and virality. Other reviewers cover UX, FX and the overall vision. This review is read-only:
nothing was edited, launched or spent.
Inputs: `live_observations.md`, `race_facts.md` (RF), `market_research.md` (MR, sources `[Sn]`, takeaways `#n`), `fx_inventory.md` (FX),
`device_catalog.tsv`, frames 01/07/12/14/17/burst-wrong_13, repo GOALS G6/G7/G8, `fnm_save.verse`, `PROTOCOL.md`, `PENALTIES.md`,
`cartridges/*/baked.json`, and the 42.30 Verse digests (FD = Fortnite, UD = UnrealEngine, VD = Verse, by line).

**Feasibility key.** **P** = proven in this project (built and seen). **D** = documented in the 42.30 digest or Epic docs, never tried here.
**?** = needs a probe (named). **Impact** 1-5 (5 = kids tell friends, or teachers adopt it). **Effort** S (under half a session), M (about one),
L (2-3), XL (4+).

---

## 0. Verdict

- **Is it awesome, and will every kid tell a friend? Not yet.** Today it is a good solo time trial with comic penalties and one great finale.
  The only playground sentences it produces are "I got yeeted" and "there's a lava titan at the end". Nothing lets a kid **beat a
  friend**, **own something**, or **show something**, and those three are what spread a game.
- The math is in the right place: first-try right answers drive the streak, and the streak drives the boost. Every new system below
  keeps that rule. **The first-try right answer is the only thing that earns anything.**
- **Biggest risk:** two or more real players have never played the race (RF §4, §7a.2), and persistence across sessions is unverified
  (RF §3.7). Every social and long-loop idea here depends on both, so test them before building anything.
- **Target playground sentences.** Each one maps to a system below:

| Kid says | System |
|---|---|
| "I froze Maya with a strike right before the boss." | Strike and Shield (§4) |
| "I beat Mr. A's time on Ratios." | Teacher and Dev medals (§6) |
| "Our class killed the Titan in 3:58. New class record." | Boss Raid, with the class record saved on the teacher's profile (§8) |
| "I'm a Math Ninja now. I've got the gold trail." | Ranks, titles and trails (§9) |
| "I finally caught LEFTY." (the left-to-right misconception) | Trap Dex (§9c) |
| *(sends a screenshot)* "look at my run" | Brag grid finish card (§10) |

---

## 1. What works and what doesn't (my lens)

| Element | Verdict | Why (evidence) |
|---|---|---|
| Streak gives a 2x boost, with voice lines from DOUBLE to UNSTOPPABLE | **Works** | Speed is the reward for first-try thinking. Readable on the slate (frame 07; RF B9) |
| Comic penalties | **Works** (best story today) | The frost white-out with an ice cube (burst/wrong_13) is a strong gag. Aaron, 10-04: "all work" |
| Shared co-op Titan finale | **Works** | Strongest moment in the race. One kill finishes everyone in the arena, which builds class bonding (frame 12; RF B13) |
| Per-player question and letter shuffle | **Works** (keep) | Following a classmate through a door gets you nothing, so copying is useless (G7 decision) |
| Personal best per skill, persisted, plus pace delta | Good foundation | `fnm_save.verse` holds only `BestTimes` and `BestSplits`. Cross-session behaviour is unverified |
| RACE strip and public feed | Good surface, used badly | The feed names every kid who misses ("got frozen at station 1"), to every HUD and the projector (RF 7b.12) |
| Medal = first-try accuracy only | Half works | Math-first is right. But the clock is the headline number and never counts, so "what is winning?" is unclear. GOLD is a word on a wall of 8 text lines (frame 14) |
| NEW RECORD | Broken incentive | The first finisher of every session on a skill always gets it, with a voice line and a feed line (RF 7b.11) |
| Boogie Bomb / Shockwave pads | Unearned sabotage | Picked up automatically at the landing spot (RF 7b.13). Unrelated to the math, and the effect on teammates is unverified |
| Retry | Leaky | Same question, same letters, so kids walk the doors by elimination: 1.5 wrong doors per question for a blind guesser (RF 7b.6) |
| In-run agency | Missing | The only choice is the door. G6 item 4 is unbuilt |
| Persistent progression | Missing | No rank, collection or visible status. Nothing to return for tomorrow (MR #1, #16) |
| Social and party play | Missing | Nothing rewards playing with friends. No team mode. "Social play" is a Discover ranking metric [S9] |
| Class and teacher | Missing | No host controls, and class data is invisible. **The 16-player cap is less than a 25-kid class** |
| Return reasons (D1/D7) | Missing | No daily goal, no XP accolades. Grade 7 has 1 skill and grade 8 has none (RF §0) |
| Brag artifact | Missing | The finish card is a text wall, the medal is text, and there is nothing shareable (frame 14) |
| Loop closure | Weak | The board hides after 10 s, the podium is 55-60 m away, there is no auto-restart and no "next goal" (RF B15-16, frame 17) |

---

## 2. Design pillars (every mechanic must pass all five)

1. **The first-try right answer is the only currency source.** Time played, walking, coins and attendance earn nothing.
2. **Speed comes from thinking, never replaces it.** Nothing opens a door, skips a question, or raises a medal without a right answer.
3. **Mistakes are content, not shame.** Misses are private by default. The leader's misses are public, as drama.
4. **Always show the next reward** (goal gradient): "1 more for a SHIELD", "GOLD needs 9/10 + 2:05".
5. **One home per number:** in-run (streak, charges), per-run (medal), persistent (Stars, Rank, Traps), class (stored in the host's save).

## 3. The system on one page

```
                       FIRST-TRY RIGHT ANSWER  (the only mint)
                                   |
  +----------------+---------------+------------------+------------------------+------------------------+
  | CORE (1 door)  | RUN (3-6 min*)| SESSION (class)  | LONG (per kid, weeks)  | CLASS (host's save)    |
  | streak -> boost| medal = acc.  | host mass start  | Stars -> Rank, titles  | class raid best time   |
  | 3 -> SHIELD    |  gate + par   | class points     | tier boxes (spacing)   | class trap tallies     |
  | 5 -> STRIKE    | brag grid     | boss raid        | Trap Dex captures      | sessions, total rights |
  | lecterns: HINT | redemption at | misconception    | Daily Mix review       | (aggregates only,      |
  | X-RAY, SURE    |  the boss     |  radar           | trails (cosmetic)      |  no kid names)         |
  +----------------+---------------+------------------+------------------------+------------------------+
  * no human run time exists anywhere (RF §5): 3-6 min is an assumption
```

Loops: core is about 20-30 s per station. A run is one race. A session is one 35-min period. The long loop runs across weeks at home with friends.

---

## 4. Core loop: in-run economy (one station)

Beat: read the question in the connector, *optionally* use a lectern (HINT / X-RAY / I'M SURE), then walk through a door.
Right: verdict, streak, boost, a charge. Wrong: penalty and misconception line, then retry with the letters reshuffled.

| # | Idea | Spec | Feas. | Imp. | Eff. | Evidence |
|---|---|---|---|---|---|---|
| C1 | **Next-reward line** | The slate streak line reads "STREAK x2 - 1 more for a SHIELD" / "x4 - 1 more for a STRIKE" | P (slate streak line, `D:2195`) | 4 | S | Goal gradient; MR #1; Aaron 10-04 "couldn't notice the streak" |
| C2 | **SHIELD** at streak 3 | Hold at most 1. Blocks the next penalty: your own wrong door *or* an incoming strike. On a wrong door the penalty is skipped, but the streak resets, first-try credit is lost and the door stays shut. HUD: "SHIELD SAVED YOU - still wrong: <misconception>". Shield icon by your name in the strip | P (Punish/Cleanse paths `D:1341-1405`) | 4 | S-M | Wayground Streak Saver / Immunity [S51]; MR #8 |
| C3 | **STRIKE** at streak 5 (then 10, 15) | Auto-fires 1 s after earning at the **nearest racer ahead** in strip order (not immune, not in a vestibule, the arena, or finished). If you lead, it converts to +2 s boost ("LEADER BONUS"), so strikes only flow forward. Effect from a *light, in-place* pool: Freeze 2.5 s (the ice cube everyone sees), Mud 4 s at 0.6, Dizzy blur 3 s (no spin), Lights Out 1.5 s. No send-back. 1 s "INCOMING STRIKE from Sam" warning; Shield blocks it; 20 s immunity after a hit. Never touches the target's question, streak or credit. Feed: "Sam froze Maya!" / "Maya's shield blocked Sam!" Host toggle | P mechanics; **? 2+ players never tested** | **5** | M | Wayground Strike/Shield [S52], Blooket Gold Quest [S46], Pillars item cadence [S3]; MR #4-5 |
| C4 | **HINT lectern** (hold E, by the door wall, off the running line) | Shows step 1 of the worked explanation. Cost: this station is "assisted" (half credit), and the streak neither grows nor breaks. 1 per run. **Data gap:** many explanations are one clause, so step 1 *is* the answer (rough count: fraction-division 200/200, area-volume 144, decimal-ops 143, rational 138, ratios 96 of 200). Needs an authored `hint` per item, or the tier's strategy line | P (button_device + HUD); data M | 3 | M | G6 item 4; Wayground power-ups [S51] |
| C5 | **X-RAY lectern** (replaces G6's 50/50) | Greys out two wrong tiles *and prints why each is wrong* (their misconception text; prefer non-ARITH). Same cost as HINT. 1 per run | P (Feedback strings on the slate) | 3 | S | 50/50 is pure guessing; error analysis teaches |
| C6 | **I'M SURE lectern** (replaces G6's gold 5th door) | Locks in confidence. Right: 2x Stars, +3 s boost, and a launch-pad shortcut through the next *connector* (never past a question). Wrong: a full penalty and the shield is lost. Persist confident-and-right % for a "Sharpshooter" title | P (button, air vent, teleport) | 3 | S-M | Kahoot Confidence mode [S50]. A 5th door can't carry its own per-player question |
| C7 | **Retry reshuffle** | A wrong door redraws the letter order (same item). Host option "Strict": the retry is a sibling item from the same tier | P (Order redraw `D:1280-1288`) | 3 | S | RF 7b.6 door-walking |
| C8 | **Earned pickups** | Pad row triggers grant only if your last answer was first-try right ("your streak earned it"). Otherwise the pad is decor | P (row-trigger granters `D:2721`) | 2 | S | Pillar 1; RF 7b.13 |
| C9 | **ON FIRE aura** at streak 5+ | A sticky effect on the player that classmates see. A status signal and a clip moment | ? `vfx_creator_device` "Stick to Player", `Begin(Agent)` (FD:3210): does it follow, can it use `FNM_FX` Niagara, how many devices | 4 | M | FX §4b; visible status drives talk |

---

## 5. Comeback mechanics

| # | Idea | Spec | Feas. | Imp. | Eff. | Evidence |
|---|---|---|---|---|---|---|
| R1 | Strikes flow forward | Only racers behind someone can strike, and the leader's charge becomes a boost. A built-in rubber band that still requires 5 right answers in a row | P (with C3) | 4 | - | Mario Kart-style catch-up, earned by math |
| R2 | Underdog boost | Racers 2+ stations behind the leader get +2 s on every right-answer boost | P (`D:2204-2231`) | 3 | S | Comeback = repeat play (MR §4) |
| R3 | Second Wind | After 2 misses at one station, the HINT is free (no lifeline spent) and penalties drop to the light pool. Stops rage-quits at a hard station | P | 4 | S | Discover bounce metric [S9] |
| R4 | **Redemption at the boss** | Each missed station queues its tier. The player's arena pad questions come from those tiers first ("REDEMPTION: Parentheses"), then tier 5. A right pad deals a boss hit, shows "REDEEMED!" and restores half credit (a miss can climb back to Gold). The boss fight becomes personal review | P (arena draw `D:2373-2385`) | **5** | M | Wayground Redemption [S53]; Blooket Mastery [S45]; spaced retrieval |
| R5 | Mid-hall return | After the first miss at a station, return to a mid-hall point instead of the 450 cm landing. Today a miss at station 10 means facing five rocket-launcher guards again (RF 7b.18). UX reviewer's call; flagged here as a comeback cost | P | 3 | S | RF 7b.18 |

---

## 6. Medals redesign (accuracy gates; par time sorts the accurate)

| Medal | First-try accuracy (redeemed misses count half) | Time | Notes |
|---|---|---|---|
| BRONZE | finish | - | |
| SILVER | 7/10 or better | Silver par or faster | |
| GOLD | 9/10 or better | Gold par or faster | |
| **DEV** | 10/10 | Aaron's own best on that skill (a baked constant per cartridge) | "Beat the Dev": Trackmania author medal [S61][S62]. 11 runs of Aaron's time |
| **TEACHER** (class) | 10/10 | The host's best on that skill this session | "Beat Mr. A." Class hook, in-memory, no persistence needed |
| FLAWLESS (badge) | 10/10 | any | Celebrated as much as Gold, so a slow but exact kid (ELL, IEP) still has a top prize |

- Rules: a missed time gate drops the medal **one** tier. Accuracy can never be bought with speed. Host option "Medals: accuracy only" (today's rule).
- **Par calibration:** provisional Gold = DEV x1.25 and Silver = DEV x1.6. Then recalibrate from real runs: put an `analytics_device` (FD:2583, D) at
  each station and the finish, which gives a per-station funnel in the Creator Portal (the same pattern as the Speedway template [S43]). That doubles as the
  drop-off map. **No human run time exists today (RF §5), so par is a guess until this runs.**
- Finish card adds a **next-goal line**: "GOLD needs 9/10 + 2:05 - you: 8/10, 2:11". MR #10.
- Fix the record inflation: "ISLAND RECORD" only when 2+ players have finished that skill this session *or* the time beats every present
  player's saved best (data the ALL-TIME screen already reads). P, S.

## 7. Ghosts and pacers

| # | Idea | Feas. | Imp. | Eff. | Note |
|---|---|---|---|---|---|
| G1 | **Pace ribbon** (HUD): a 10-segment bar with markers YOU / BEST / RECORD / TEACHER, from the saved splits | P (Verse UI, `BestSplits`) | 3 | S-M | Mario Kart staff ghost / TM medal ghosts [S62][S63]; MR #11 |
| G2 | Rival line under the clock: "2.4 s behind Maya", turns green when you pass | P (strip data) | 3 | S | Local rivalry beats a global rank |
| G3 | Heartbeat tick (per player audio) while you're behind your best pace | P (instigator audio) | 2 | S | |
| G4 | Hologram of the session record holder at the finish gate | ? `player_reference_device` hologram (FD:3561); needs the holder present | 3 | M | Global, which is fine because it celebrates the best |
| G5 | World ghost avatar | **Rejected** | - | - | Props are visible to everyone (FX §5). 16 ghosts in shared halls is clutter, and a ghost shows someone's door |

---

## 8. Session loop: class mode (one 35-min period on the teacher's code)

**8a. Reality check.** The island caps at 16 players and a class has 25 kids. Recommend **pairs** ("pilot and navigator", swap every race): 13 devices,
and the math gets talked out loud. The class device setup (lab, Xboxes, one projector console) is **unknown and unverified**. A single-screen class
can use **hot-seat**: one runner, the class solves aloud.

**8b. Host model** (no typed input, no keypad PIN, so it stays clear of Rule 1.2):
- Host = the **first player to join** (the teacher launches the private version first). The director already sees join order (OnPlayerAdded).
  Pass host with a hold-E lectern. At home the "host" only controls their own lobby, so a kid holding it is harmless.
- Host panel = Verse UI opened from a host-only `button_device` at the start hall (P: podium buttons `D:1984-2045`, picker UI).

| Control | Does | Feas. | Eff. |
|---|---|---|---|
| MASS START | Teleports everyone to station 1, shared 3-2-1 | P (`StartNewRun D:2142`) | S |
| SKILL LOCK | Everyone on skill X, or a grade lock, or free choice (differentiation) | P (pick path) | S |
| **FREEZE ALL** ("Eyes on me") | Stasis for everyone plus a banner. For reteaching a misconception live | P (`PutInStasis`, FlashBig) | S |
| Strikes ON/OFF; penalty strength light/normal; names in feed ON/OFF | Teacher tunes the heat | P | S |
| Mode: Class Race / Boss Raid / Co-op Gate | See 8c | mixed | - |
| END + CEREMONY | Results and podium | P/D | M |
| Projector panel toggle | See 8d | P | M |

**8c. Modes**

| Mode | Spec | Feas. | Imp. | Eff. | Evidence |
|---|---|---|---|---|---|
| **Class Race** | Mass start. Class Points = first-try rights x10 + boss hits x10 + redemptions x5 + medal bonus. Time only breaks ties, so kids on different skills compete fairly | P | 4 | M | Kahoot Accuracy mode [S50] |
| **Boss Raid** | Reuse BOSS BATTLE (G8: shared team boss). Hits needed = 3 x players present. Wrong pad punishes only that kid (no team cost, no blame). Class best time saved in the **host's** persistence: "Class record 4:12 - beat it" | P (boss mode) + persistence ? | **5** | M | One Way Out co-op [S48], Wayground Team [S52] |
| **Co-op Gate** (G6 5) | The class needs N right answers (N = 8 x players) to open the finish. A world `progress_based_mesh_device` tower or cage grows with every right answer, seen by all (global is fine for a shared goal) | D (FD:1979) | 4 | M | G6 item 5 |
| Team Relay (G6 5) | 4 teams; each runner runs 2-3 stations, then the next teammate drops in at the vestibule | D (`team_settings_and_inventory_device` FD:5702) | 4 | L | Blastball / Team mode [S48][S52] |
| Hot-seat (1 screen) | No build needed. Teacher rotates the controller; the class solves the projected slate | P | 3 | - | |
| Shared-question Showdown (G7 3) | Question on a wall billboard, same for all. **Gives up anti-copying.** Only for a teacher-paced whole-class moment | P (billboard) | 2 | M | G7 item 3 |

**8d. Projector panel** (the host's HUD, anonymous by default):
- Station histogram ("S1 ●● S2 ●●●● ..."), class first-try %, live raid HP.
- **Misconception radar:** the top 3 wrong-choice misconceptions this session, with counts ("Worked left to right: 9"). The runtime already holds
  each wrong choice's feedback text, so count by it. This is the teacher-adoption feature: live formative assessment. P, S-M, **Impact 5 for teachers.**
- Names appear only on positive lines (streak leaders, records). The host can turn names on.

**8e. Run of show (35 min)**

| Min | Beat | Systems |
|---|---|---|
| 0-3 | Teacher joins first (host). Pairs join. Warm-up: station 1 open, no clock | host, picker |
| 3-6 | Teacher demo race on the projector sets the **TEACHER medal** | §6 |
| 6-22 | 3 mass-start Class Races (~4-5 min each, assumed). Pit stop 60 s each: radar, FREEZE ALL, 1-min reteach. Pairs swap | 8b-8d |
| 22-30 | **BOSS RAID**: whole class vs the Titan, with each kid's misses as their redemption pads | §5 R4, 8c |
| 30-35 | Ceremony: podium categories **Sharpest** (accuracy), **Fastest** (per skill), **Comeback** (redemptions), **Trap Hunter**. Class record saved to the teacher's profile | §10 |

---

## 9. Long loop (weeks, at home, with friends)

**9a. Persistence v2.** Additive fields with defaults in `fnm_saved` (`fnm_save.verse`: never remove or retype a field). Flat keys keep it simple:
```
Medal        : [string]int      # skill -> 0..4 best medal
TierRight    : [string]int      # "skill:tier" -> first-try rights (lifetime)
TierBox      : [string]int      # "skill:tier" -> Leitner box 0..4
TierDay      : [string]int      # "skill:tier" -> day id last practised
Traps        : [string]int      # misconception id -> -1 unseen-but-met / 0..3 capture progress / 4 captured
DayPlayed, WeekId, DaysThisWeek, DailyDone : int
Runs, FirstTry, BossHits, Flawless : int
Title, Trail : int              # equipped cosmetic ids
# host-only "class memory" (the teacher's own save; aggregates, never kid names):
ClassRaidBest : float ; ClassRight : int ; ClassSessions : int ; ClassTraps : [string]int
```
Day id = floor(`GetSecondsSinceEpoch()` / 86400) (VD:2153, D). Size is about 300 ints for 11 skills. A per-player cap is documented by Epic
(the 42.30 digest doesn't state it; **unverified**). Needs: misconception **ids** emitted into the slot. Today only the text is emitted
(PROTOCOL §8: "Ids stay in baked.json for later analytics"), so add an `FeedbackId : []string` field. Toolchain S.

**9b. Stars and ranks** (mastery thresholds, not per-answer points, so they can't be farmed):
- Per skill, max 9 Stars = 5 tier Stars (a tier is mastered with 3 first-try rights on **2 different days**, which builds in spacing
  and blocks cramming) + medal Stars (Bronze 1, Silver 2, Gold 3, Dev 4). 11 skills = 99 Stars, and the ladder grows with every new cartridge.
- Capping per skill pushes kids to the *next* skill, so collection completion becomes curriculum coverage (Trackmania campaign tiers [S61]).
- 12 ranks: Rookie, Number Scout, Calculator, Number Cruncher, Pattern Hunter, Equation Ace, Brainstormer, Math Ninja, Mastermind, Professor,
  Grandmaster, Legend. Thresholds 0/3/6/10/15/21/28/36/45/55/70/90.
- **Titles** you equip per skill = best medal + skill title (Aaron's G6 example: "Gold Fraction Slayer"). Shown next to the name in the race strip
  and on the finish card, so the status is visible to classmates. P (Verse UI). Rank-up moment: banner, announcer, accolade.

**9c. Trap Dex (misconception monsters): the long-loop hook**
- Every misconception in the catalog becomes a named monster: **182 across 11 skills** plus ARITH as the "Glitch Gremlin" (counted from
  `baked.json`: expressions 33, rational 24, area 20, data 19, factors 19, ratios 18, decimals 12, equations 11, fraction-div 10,
  integer-ops 9, order-of-ops 7).
- **Meet:** a wrong door that hits misconception X shows its card ("LEFTY got you! Worked left to right..."). The penalty becomes the
  monster's attack, and naming the error helps kids remember it.
- **Capture:** 3 first-try rights on items that *bait* X (a distractor tagged X). Falling for X again costs 1 progress. No incentive to
  answer wrong: capture never needs a meeting.
- Dex panel (HUD, at the podium): silhouettes, met, captured. Completion % per skill. Title "Trap Hunter".
- Feeds the Daily Mix (9d) and the teacher radar (8d), using the same keys.
- Art: one monster per skill first (11 x nano-banana-pro 9 = **99 Meshy credits**), per-misconception cards later (182 x 3-9 = 546-1,638).
  **Credits need Aaron's go-ahead.**
- Feas. P (persistence pattern, HUD) + toolchain ids. Imp. **5**. Eff. L. Evidence: collectibles with visible rarity (Blooket Blooks, Prodigy
  pets [S46][S55]; MR #16), Epic's Picks "hidden secrets, being the best" [S12].

**9d. Daily and weekly** (no loss-aversion messaging, anywhere)

| # | Idea | Spec | Feas. | Imp. | Eff. |
|---|---|---|---|---|---|
| L1 | **Daily Mix** (spaced practice) | A 10-station run built from *due* tiers across the skills you've played (Leitner: due when days since last >= 0/1/3/7/14 for box 0-4). First-try right moves the box up 1; a miss drops it 2. The arena baits your un-captured traps. Uses the all-cartridge slot (`FnmCartridges()` registry) | D (`GetSecondsSinceEpoch`) + P | **5** | M-L |
| L2 | Weekly goal, not a daily streak | "Days played this week ●●●○○○○, goal 3". Rewards Stars x2 that day. Never "your streak will die" | D | 3 | S |
| L3 | **Course of the Week** | The same modifier for everyone, from the week id: Double Guards, Night Run (skydome, FX §4b), Ice Everywhere, or **one new comedy penalty per week** from the PENALTIES catalog (trapdoor, boulder, flood). Kids compare at school; gives a reason for the Discover "Updated" badge | P/D mix | 4 | M per week |
| L4 | Wordle-style shared daily puzzle | **Not recommended**: it breaks the "own question per player" constraint. Only if Aaron relaxes it, and only off the race | - | - | - |

**9e. Cosmetics** (island-only, earned, never sold; Rule 1.21 stays clean)
- Trails by rank and medal (rank 4 blue sparks, rank 8 gold, any DEV medal "Dev lightning" reusing the `NS_fnm_coil` look). ? same
  `vfx_creator_device` probe as C9. Imp. 4, Eff. M.
- Finish celebration variant (fireworks colour at your finish spot, global). P (VFX Spawner, FX §4a). S.
- Later: a free **Season Track** (10 cosmetic steps, filled by first-try rights, soft daily cap of 100 against marathon grinding). Never
  call it a pass, and no "XP" (Rules 4.4.4/4.4.5 and 1.13 [S28][S7]).

**9f. Content cadence is the real long-loop fuel.** Ranks and the Dex scale with cartridges. Grade 7 has 1 skill and grade 8 has 0 (RF §0), so grade
7-8 kids hit the ceiling in a week. Islands that are never updated fade (Hard Parkour v1, Fortnite Trivia [S3]; MR #24).

---

## 10. Brag artifacts and clip moments

| # | Idea | Spec | Feas. | Imp. | Eff. | Evidence |
|---|---|---|---|---|---|---|
| B1 | **Brag grid finish card** | Centre, 3 s hold, screenshot-ready: big medal art, time, skill, rank title, a row of 10 check/cross tiles plus a boss tile (Wordle grid), streak, NEW BEST stamp, the **island code as text** (no URL or QR, Rule 1.2). Then it slides aside | P (check/cross textures exist, FX §3c) | **4** | S-M | Wordle [S65]; MR #14 |
| B2 | Medal art | 4 HUD medal textures (nano-banana-pro 4 x 9 = 36 credits) now; 3D medals or trophies for the podium later (~30-39 each) | P pipeline | 3 | S | Credits need the go-ahead |
| B3 | **Podium ceremony** | Session top 3 (Class Points or per-skill time) teleported onto podium blocks. A giant hologram of #1's own skin dancing their emotes behind them | D `dance_mannequin_device.ActivateSkinAndEmoteCapture(Agent)` (FD:4001); ? probe | **4** | M | G6 item 8 |
| B4 | Clip moments (each needs a 2-3 s readable caption) | (1) Strike lands: target frozen in ice, "SAM FROZE MAYA" on both HUDs; (2) Titan falls; (3) record broken: fireworks at the player; (4) ON FIRE aura | P/D | 4 | S each | Only Up spread through creator clips [S4]; MR #15 |
| B5 | Rare **PARTY SURGE** (flips G6 9's class-wide jackpot penalty) | About 1 in 20 streak milestones gives *every* racer a 3 s boost and fireworks: "MAYA STARTED A PARTY SURGE!" Good news from one kid's right answer is shared by all | P | 3 | S | Positive social, no blame |

## 11. Accolades (Battle Pass XP) plan

XP comes only from `accolades_device` awards (FD:2568, D). Epic calibrates each island from play sessions and **republishing** resets the calibration.
Aim for 1 award per 2-10 min, with frequent awards worth less [S14][S15]. Every trigger is a math outcome. Never write "XP" in the
name, description, thumbnail or lobby (1.13.3), and don't imitate Epic's XP bar (1.13.1).

| Accolade | Trigger | Cap | Expected cadence | Weight |
|---|---|---|---|---|
| Finish Line | finish a race | 1 per 4 min | about 1 per run | Small |
| Hot Streak | first-try streak 5 in a run | 1 per run | most runs, for strong kids | Small |
| Redeemed | 2+ redemptions in a run | 1 per run | struggling kids' accolade | Small |
| Medal Up | beat your best medal on a skill | 44 total | rare | Medium |
| Tier Mastered | a tier reaches mastery (9b) | 55 total | early: 1 per 15-30 min | Medium |
| Trap Captured | capture a Dex monster | 183 | about 1 per 10 min | Small |
| Flawless | 10/10 first try | 1 per run | rare | Large |
| Rank Up | each rank | 12 | rare | Medium |
| Daily Mix | finish today's mix | 1 per day | daily | Medium |

- Test in unpublished builds through `TestAwardEvent` (FD:2569). Expect "Analyzing" status after publishing. Republish once, when content is stable (MR #23).
- **Why it matters:** XP is a Fortnite-native reason to return that costs no design debt. Impact 5, effort S (9 devices + calls).

## 12. Party and social-play hooks (Social Synergy, 42.10)

`(InPlayer:player).GetLocalParty()` returns an `agent_group_interface` with `GetMemberMap`, `AddMemberEvent` and `RemoveMemberEvent` (UD:1776, VD:1893). D. **? Probe: does it
return the real party in a private version** (it may return only self in an edit session).

| # | Idea | Spec | Imp. | Eff. |
|---|---|---|---|---|
| S1 | Squad tag | Party members grouped and coloured in the race strip; feed "Squad Maya + Sam finished" | 3 | S |
| S2 | **SQUAD SURGE** | A shared meter filled by *all* members' first-try rights. At 10 the whole squad gets a 4 s boost and fireworks. Co-op inside a race, and every member must do the math | 4 | M |
| S3 | Buddy trail | Cosmetic unlocked by finishing 3 races in a party of 2+. Rewards playing together, never invite counts | 3 | S |
| S4 | Party relay | Auto-forms a relay team from a party (after 8c relay exists) | 4 | L |
| S5 | Strikes between friends allowed | The prank is the story. The host can turn strikes off | 4 | - |

Evidence: Discover ranks on social play (invites, time in party) [S9]; Epic: "build gameplay that rewards playing together" [S21][S70]; MR #9.

## 13. Feed and exposure rework (Now; P, S)

- Wrong-door lines go **only to the player who missed**, except for the top 3 runners ("Leader Maya got YEETED!"). The leader's misses are drama;
  a struggling kid's misses stay private.
- Public lines become positive: streak 5/10, rank-up, trap captured, medal, record, strike and shield exchanges, boss hits, Party Surge.
- Host toggle for names. Today's feed reaches the projector, so this matters in class first.

---

## 14. Do NOT do

**Rule violations**
- Wheels, crates, raffles or "spin" reveals, even free (1.11 [S7]; the Steal the Brainrot backlash [S5]). A visible "pick 1 of 3" is the most allowed.
- Any purchase (in-island transactions are restricted for minors [S29]) or any reward for likes, favourites or follows (1.9).
- Typed answers, chat, or a keypad PIN for the teacher (1.2 "custom keyboards"). Host = first joiner instead.
- URLs, QR codes or external dashboards (1.2, 1.12, 1.2.1). Kid names stored in the host's save (only aggregates).
- "XP" in the name, description, thumbnail or lobby, or an XP-bar look-alike (1.13.3, 1.13.1). "Battle Pass" wording (4.4.4/4.4.5).
- Advantages tied to Epic skins (1.21). Per-grade island copies (1.9.1 spam). Marketing aimed at under-13s (1.15): say "middle school / 10+".

**Dark patterns on kids**
- Consecutive-day streak loss messaging, sold streak freezes, FOMO-limited cosmetics, login rewards for just showing up, energy or wait timers.
- Public bottom ranks or "you're last" copy, and wrong-answer name feeds on the projector.
- **G6 item 9 "jackpot door that hits the whole class":** one kid's miss punishes everyone, so kids blame the struggling kid. Flip it (B5).
- Storm or elimination modes in class (G6 5): they remove the struggling kids first, the ones who need the practice. Party lobbies only, if ever.

**Ways speed could beat thinking**
- Question timers, skip tokens, or anything that opens a door without a right answer (Strike and Shield never do).
- 50/50 (pure guessing). Replaced by X-RAY.
- G6 item 4's "gold door: skip the next station" (skips a question) and its "coins on the walls + shop" (currency earned by running). Replaced by I'M SURE and streak charges.
- Wrong-then-right worth the same as first try; medals from time alone; Stars per answer (farmable); keeping the same letters on retry.
- Any global VFX, beacon or light that marks a right door *before* a choice. A shared question on a wall during a live race (copying).
- Penalty collections or achievements that pay for being wrong.

---

## 15. Roadmap

**Now (1-2 sessions).** Prerequisites first, then cheap, high-leverage changes:

| # | Item | Feas. | Eff. | Done when |
|---|---|---|---|---|
| N0 | **Gate test:** 2 real players (Aaron's PC + Xbox account) on a private version: strip order, feed, shared boss, a thrown Boogie Bomb, then a second session to confirm `BestTimes` survived | probe | S | Frames show both players in the strip; a best survives a relaunch |
| N1 | `analytics_device` per station and finish (funnel and par calibration) | D | S | Creator Portal shows per-station counts after a published or private run |
| N2 | Feed rework + record-inflation fix (§13, §6) | P | S | A miss by the last-place kid shows on their HUD only |
| N3 | Next-reward line (C1) + **SHIELD** (C2) + retry reshuffle (C7) | P | S-M | Streak 3 grants a shield, and a wrong door logs "shield blocked" with the door still shut |
| N4 | Medal v2: accuracy gate + provisional par + DEV times (Aaron plays each skill once) + next-goal line | P | S-M | The finish card shows the medal *and* the next target |
| N5 | Brag grid on the finish card (B1) + 4 medal textures (36 credits, go-ahead first) | P | S | Screenshot read back: 10 tiles, medal, code |
| N6 | 9 accolade devices wired (§11) | D | S | `TestAwardEvent` fires per trigger in a playtest |
| N7 | Persistence v2 fields written (9a) + `FeedbackId` emitted. UI later | P | S-M | Fields read back after a relaunch |

**Next (about 4-6 sessions):** STRIKE (C3) with host toggle; Redemption at the boss (R4); Second Wind + Underdog (R2-R3); host v1 (mass start,
skill lock, FREEZE ALL, projector panel + **misconception radar**, TEACHER medal); ranks and titles in the strip; lecterns X-RAY and I'M SURE
(HINT after the hint data pass); pace ribbon and rival line (G1-G2); party squad tag and SQUAD SURGE (after the probe); podium ceremony with
the dance hologram (after the probe); ON FIRE aura and trails (after the `vfx_creator` probe).

**Later:** Trap Dex + monster art (99 credits for per-skill monsters first) + Daily Mix spaced review; Boss Raid class mode with class records in the
host's save; Co-op Gate tower; Course of the Week with a weekly comedy penalty; Season Track; Team Relay; a Signal Remote held strike and teacher
remote (`signal_remote_manager_device` FD:3795, ? whether the item can be granted and validates); secrets and collectibles ("Explorer" title,
`collectible_object_device` FD:4792); grade 7-8 cartridges (the long loop's fuel, §9f).

**Discover metric map:** first-60-s bounce: C1, C2, R3. Social play: S1-S5, C3. D1/D7: §11, L1-L3, 9b-9c. Session length: N4 next goal, B1, Class
Race. Epic's Picks replayability ("secrets, being the best, multiple ways to interact" [S12]): Trap Dex, medals and ranks, lecterns and strikes.

## 16. Probes (about 10 min each, before building) and the shakiest assumptions

| Probe | Question | Blocks |
|---|---|---|
| 2+ players (N0) | Do the strip, feed, shared guards and boss, and items on others work? | C3, §8, §12, §13 |
| Persistence on a private version | Does `fnm_saved` survive a new session? (RF §3.7: UEFN test sessions start empty) | §9 entirely |
| `vfx_creator_device` | Does Stick to Player follow, does it take `FNM_FX` Niagara, and does `Begin(Agent)` work for many players? | C9, 9e |
| `GetLocalParty` | Does it return the real party in a private version? | §12 |
| `dance_mannequin_device` / `player_reference_device` | Do the skin capture and hologram render in play? | B3, G4 |
| `accolades_device` | Does `TestAwardEvent` fire, and what can MCP set (XP weight)? | §11 |
| Hint data | How many items need an authored `hint` (my one-clause count is a rough heuristic)? | C4 |

Unverified and flagged:
- **No human run time exists** (RF §5). The 3-6 min run, 35-min pacing and every par value are assumptions until N1 and a class pilot.
- The classroom setup (devices per kid, platform) is unknown. Pairs are a workaround for the 16-player cap, not a tested plan.
- Host = first joiner assumes the teacher launches first, and that join order is stable for the session.
- The persistence size cap isn't in the 42.30 digest. Epic docs set a per-player cap, value not checked.
- Accolade XP only flows on a published, calibrated island. A private-version class demo earns none.
- Strike balance numbers (light-pool durations, 20 s immunity, streak 5) are design guesses. Tune them after a 4+ player session.
