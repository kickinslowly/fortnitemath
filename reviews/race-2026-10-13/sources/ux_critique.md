# RACE mode UX teardown (2026-10-13)

Lens: UX (clarity, flow, feedback, fairness, accessibility). Gamification, FX and vision are covered by other reviewers; touched here only where the UX needs them.
Evidence: frames in `frames/` and `frames/burst/` (cited by name), `race_facts.md` (RF), `live_observations.md` (LO), `fx_inventory.md` (FX), `market_research.md` (MR), code `D:` = `console/verse/fnm_director.verse`, `U:` = `fnm_ui.verse`. Read-only: no repo file edited, UEFN not driven, no credits spent.
Severity: **P0** breaks the core loop. **P1** most kids hit it; costs fun or learning. **P2** some kids or sessions. **P3** polish.
Caveats: no human run has ever been timed. Two or more real players have never played. Frames 02-20 come from an auto-run that teleports into the vestibules at night; the `burst/` frames are station 1 in daylight. Ignore the white `FNM:` debug lines.

---

## 0. Bottom line

**Would every kid tell a friend about it today? No.** The story a kid would tell is already there: "a math map where a wrong answer gets you yeeted, and at the end you laser a lava titan." Today that story is buried:
1. **The core rule is unreadable in the world.** The four doors look identical (LO "Doors", burst/wrong_22). On the HUD, tiles B and C render the same cyan (sampled below). A new kid has to work out that "door = answer" from the left-to-right order alone. Nothing teaches it.
2. **The first minute has no hook.** It opens on a form (three identical yellow buttons) over a glare-white greybox hall under random day or night lighting. The titan, the one thing worth bragging about, shows up at around minute 3-5.
3. **Every reward happens on the kid's own HUD.** Right answers, streaks, boost and finish are text and 2D sound. Nothing in the world reacts, so nothing is clip-worthy or visible to the kid sitting next to you. Only the penalties and the finale are.
4. **The finish leaves nothing to show.** It is an 8-line text wall over the arena, the podium is 55-60 m away, and there is no screenshot-ready card.
5. **The learning loop works against itself.** The previous answer's working sits under the next question and contains its distractors. A wrong door often says only "Check your arithmetic."

Fix the P0/P1 set (Top 15, items 1-7 are all S or S-M) and the kid's story becomes "I lasered a lava titan with math." That one is shareable.

| Axis | Today | Why |
|---|---|---|
| Clarity | **3/10** | Rule never taught; doors identical; HUD B = C colour; old explanation reads as current working; three versions of the arena instruction |
| Juice | **4/10** | Penalty gags and the cannon volley land (wrong_13, 12). Right answer, streak, boost and finish are HUD-only (LO 6, FX 1.4/1.6). Greybox halls under uncontrolled lighting |
| Fairness | **4/10** | Penalty cost is a 5.8-9.3 s dice roll (3.5 below); Spike also strips dropped guns; rocket guards re-met after a math mistake; one arena kill finishes everyone present |
| Learning | **5/10** | Concept-first bank, simple numbers (PROTOCOL 4a), misconception line on about 83% of distractors, medal rewards first-try accuracy. Undercut by the misplaced explanation, generic ARITH feedback (39% on Order of Ops), no worked solution after a miss, free elimination guessing |
| Replay | **3/10** | Per-skill best, pace delta, 200-item banks. Run 5 is run 1 with a different clock; restart needs a 60 m walk and a button; nothing to collect |
| Shareability | **3/10** | Yeet, freeze and the titan volley are clip-worthy; the finale comes late; no finish card; random lighting; "Fortnite" in the title is an Epic rules risk (MR 3.9) |

**What already works (keep):**
- The race skeleton: hall, door wall, varied connectors. Aaron: "a lot more engaging".
- No stall on success, with a per-player barrier.
- The next question appears while you run the connector, and question 1 is shown during the countdown (free reading time).
- A 46 px prompt with tiles in door order.
- The STREAK line: big, readable, echoed in the feed (07, 09).
- The escalating announcer.
- Comic penalties with one-word names. The ice block is visible to others.
- Health and shield refill every station.
- Pace delta in green (19).
- The finale volley with counted "Direct hit!" lines (12, 13).
- Per-skill bests.
- The simple-numbers rule.

---

## 1. Journey: a 12-year-old on Xbox, TV at about 3 m

### B1. First 10 seconds: join and picker (01_picker)
Keep: the player is put in place instantly with no lobby wait. The first button is focused for the controller (U:949). The BOSS BATTLE caption "Right answers NUKE the boss!" is the best line of copy on the island.

| Sev | Problem | Evidence | Fix |
|---|---|---|---|
| P1 | No title, logo, mascot or how-to-play. The first impression is a form: heading "CHOOSE YOUR SKILL", step line "Pick a grade", three identical yellow buttons | 01 | Title-screen picker (Top 15 #13) |
| P1 | BOSS BATTLE, a different game, sits **above** the grades with equal weight. A kid who came to race picks it, or doesn't know which one is "the game" | 01; U:886-894 | Make two mode cards (RACE / BOSS BATTLE, with art), or move BOSS below the grades in a different colour |
| P2 | Heading and step disagree ("CHOOSE YOUR SKILL" / "Pick a grade") | 01 | "PICK YOUR GRADE", then "PICK YOUR SKILL" |
| P2 | A race clock reading "0:00.0", the tag "Fortnite Math / Choose your skill" and Fortnite's own GAME MODE box are all up while picking: three panels with no use yet | 01 | Hide the clock and tag until GO; probe `hud_controller_device` |
| P2 | Two announcer lines fire in the same tick ("Welcome to Fortnite Math!" + "Choose your grade and your skill.") and overlap | RF 7b.1; D:1083, D:1137 | Play `choose` 2.0 s after `welcome` |
| P2 | Background: glare-white floor, pastel walls, floating pink digits. Nothing says "race" or "boss" | 01, wrong_22 | Fix the lighting and floor (#4); optionally put an idle titan copy in view beyond station 1 as the promise (memory cost unmeasured) |
| P3 | No timeout or default pick; the player is frozen indefinitely | RF B1 | Default focus on "CONTINUE: last skill" (#13). No timeout needed |

### B2. First minute: GO, station 1, the door wall (18_new_race, wrong_22, door_02)
Keep: the 2.4 s countdown with the question already up. The hall is short (25.5 m to the doors). Fortnite's own "E OPEN" prompt appears within about 2.5 m (door_02).

| Sev | Problem | Evidence | Fix |
|---|---|---|---|
| **P0** | Four identical white doors, no letters, no colours. The door paint (`M_door_face_a..d`) is not applied (`overrideMaterials: [null]`). The only mapping to the HUD tiles is left-to-right order, which is never stated | wrong_22, wrong_33, wrong_86, door_02, editor_doors_s1; LO "Doors" | #1 |
| P1 | Nothing teaches the rule. No text says walk through the door with the answer, open it with E, entering commits, or that A is on the left. Only the arena has instructions | RF 7b.2 (grep: no such copy in the director or UI) | #2: station 1 as the tutorial |
| P1 | A pistol guard stands at the door wall of the very first station. The first thing a new kid meets in a math game is being shot at while trying to read | 18 (guard at the doors); RF table, station 1 = 1 x pistol | Remove station 1's guard (it is the warm-up) |
| P2 | Doors need a stop and an E press. That is a speed-killer in a race, though it also gives a deliberate commit beat | door_02; RF B7 | Probe: does sprinting into the OilRig door prop open it (Fortnite's door bash)? If yes, keep E as a fallback and teach "run through" |
| P2 | Behind every door before you commit: a red diagonal-stripe barrier 7 m in. Red stripes read as "blocked / danger" on the right door too, so a kid may back out at the threshold (my reading of the frame) | wrong_48; FX 1.3 "Barrier renders red-striped" | Probe the Barrier's visibility option and make it invisible (the commit trigger and per-player ignore list are unaffected) |
| P2 | Everyone draws their own question and shuffle, but kids will follow a friend through "their" door and get punished without knowing why | RF §4 (per-player question); untested with 2+ players | One coach line on the first run: "Everyone gets different questions" |

### B3. First wrong door (burst/wrong_13 Freeze, wrong_33 Yeet, wrong_50 Spike, wrong_71 Mud, wrong_86 Dizzy)
Keep: the gags read instantly. FROZEN!, YEET! and the like are 96 px with a voice line. The frost cube is a world prop others can laugh at. The slate stays readable over the post-process (13).

| Sev | Problem | Evidence | Fix |
|---|---|---|---|
| P1 | The lesson is generic exactly when attention is highest. For `2 + 7 x 9` the feedback was "Check your arithmetic.". 17% of all distractors carry only that line; 39% on Order of Operations, the default skill | wrong_13, wrong_50, wrong_71; D:1312; RF §5 | #9: first-step hint; worked steps after the 2nd miss |
| P1 | The penalty broadcasts "<Name> got frozen at station 1" to every HUD on the island for 7 s. That is a public failure log in a classroom | wrong_13, 33, 50, 71, 86; D:1398 | #6: penalties only on the victim's own HUD |
| P1 | After the gag the kid is sent to the 4.5 m landing and re-runs 25.5 m of obstacles and live guards for a math mistake (Yeet about 7 m less) | RF B8b, 7b.18 | #8: retry spot 3 m in front of the door wall |
| P2 | Spike uses a real elimination: Fortnite's own feed line "Humanist_NA (91) bailed early", the death camera, and a respawn with **only the pistol**. It silently takes the guard-dropped guns, a hidden extra cost the other five penalties don't have | wrong_50; RF B6 "respawn returns only the pistol" | Spike without `Damage(1000)`: spears + stasis + teleport |
| P2 | Freeze holds 5 s with no turning and nothing to do (longest dead time) | RF B8b | Cut to 2.5 s and use the hold to show the hint big (#9) |
| P2 | Mud's sepia blows the whole screen out to orange glare (it reads as a broken screen, not as mud). Frost whites out the top HUD | wrong_71, wrong_13 | Blend the post-process to about 50% (probe a partial-strength setting); daylight lock (#4) also reduces bloom |
| P2 | Letters are not reshuffled on retry, so a guesser just walks the next door along. A blind guesser averages 1.5 wrong doors per question and loses only time | RF 7b.6 | #9: reshuffle on every retry |

### B4. Mid-run: stations 2-7, connectors, ice (02, 05, 07, 08, 09)
Keep: the STREAK xN, SPEED BOOST Ns line; the "Double / Triple / Mega" voice ladder; connector variety (stairs, winds, speed plates); the ice dressing and icicles (09); the pace delta (19).

| Sev | Problem | Evidence | Fix |
|---|---|---|---|
| **P1** | "Correct! <explanation of the PREVIOUS item>" sits under the NEW question and mixes with it. At 07 the question `2 x (2 + 10 / 2)` (answer 14, tile A = **7**) shows "Correct! 10 / 2 = 5, then 5 + 2 = **7**, then 4 x 7 = 28." At 11, a boss question answered **4** shows "...36 / 9 = **4**..." The arena already had this fixed ("Last one:", D:2321); the 10 stations did not | 05, 07, 10, 11; D:1389 | #5: recap card, then flip to the next question |
| P1 | Right answers produce nothing in the world: the barrier vanishes, plus a 1.5 s HUD flash and a chime. No burst, light or camera; nothing a classmate sees | LO 6; FX 1.4 "World: NOTHING" | #12 |
| P1 | Lighting: the whole auto-run happened at night. Every frame is a blue-cyan wash, the five tier wall colours (green/blue/purple/orange/red) are gone, and walls show a checker texture | 02-14 vs now_client | #4 |
| P2 | Boost is 2.0x but has no look: no FOV, lines, trail or post-process. Aaron could not feel 1.6x; his re-test of 2.0x is still open | FX 1.6; RF Aaron table | Per-player post-process during the boost (#12) |
| P2 | Halls read as a greybox: flat cube walls, white floor, torches. Nothing says "math" or gives a place identity except the ice station | LO 3; 02, 08 | FX/vision reviewers; UX minimum is tier lighting and colour (#4) |
| P2 | The slate's height jumps between about 225 and 335 px as the explanation and streak lines appear and vanish, so the bottom edge moves under the kid's eye | 22 (bottom y about 265) vs 05 (about 375) | Fixed-height slate; explanation moves to the recap (#5) |
| P2 | Pickup pads sit 30 cm past the landing (480 vs 450 cm), so kids auto-collect Boogie Bombs and Shockwaves they never chose. Whether those affect teammates on a Cooperative island is unverified, so they may do nothing | RF 7b.13 | Probe item-on-teammate; move pads 3 m in and give them a reason (a "use it on a rival" coach line) |
| P3 | Tier 5 of Order of Ops is named "Boss Level" and shows at stations 9-10, where there is no boss | 10 | Rename the tier label (manifest), or show "Boss Level" only in the arena |

### B5. Late run: stations 8-10
| Sev | Problem | Evidence | Fix |
|---|---|---|---|
| P1 | Gold heavy snipers (x4), grenade launchers (x5) and rocket launchers (x5) in a 22 m hall, re-met after every wrong door. A kid who is good at math but new to Fortnite is gated by aim and splash damage, not math. Aaron: "couldn't barely make it past stage 10 until the guards had killed themselves" | RF station table; RF Aaron 10-08 | #8 (retry spot at the door wall, so no re-run past the guards); no splash weapons on guards, and drop launchers from a chest as the reward instead |
| P2 | The next station's guards switch on the moment you answer, while you are still in the connector, so you arrive into fire with a fresh question to read | RF B6 (stage-based enable) | Enable the guards when the player enters the hall (trigger), not at the stage change |

### B6. The boss (11_arena_entry, 12_cannons, 13_boss_hit2)
Keep: the cannon volley (lightning, titan stagger, bar flash, "Direct hit! Three to go!") is the strongest moment in the race. The bottom-centre boss bar is clear. Teleport back after each hit keeps a rhythm.

| Sev | Problem | Evidence | Fix |
|---|---|---|---|
| P1 | Pads are a 2x2 grid (A/B near left and right, C/D far). From the landing only the C and D letters are on screen; A and B are off-camera at the kid's sides. It is also a new spatial mapping (front/back) at the climax, after ten doors that taught left-to-right | 12, 13 (only C, D visible); RF B13 pad coordinates | #11: one row, A-B-C-D left to right, about 10 m out |
| P1 | The arena is announced about 44 m early: the 4 s gold flash, the 7.36 s stinger and the hint line all fire at the stage-10 door while the kid is in the vestibule. The orange hint "Bullets can't hurt it..." is overwritten in the same tick by "Correct! <stage-10 explanation>" | 11 (flash over the connector; explanation where the hint should be); D:2294-2295 vs D:1389 | Fire the arena intro on entering the arena hall (trigger), keep the hint |
| P2 | Three copies of the instruction (flash, slate caption, bar) and two different counters: caption "BOSS - hits 0/5" (own) vs bar "team hits 2/5" | 11, 13; D:1294 | One counter, on the bar |
| P2 | The slate (bottom edge about y 330-375) cuts the titan at the neck during the volley, the best visual moment | 12, 13 | Compact arena slate (prompt + tiles); recap card replaces the feedback line |
| P2 | The titan is 6.3 m and small at the far end of a 30 m hall (11). Boss mode's is 12 m. Race cannons log "0 muzzle vfx" | 11; LO 8; FX §2 | Scale to 3+ (actor scale sticks, proven); add the muzzle system |
| P2 | A right pad while no boss is up still says "DIRECT HIT! 5 TO GO", sends you back and burns the question, for no damage | D:2366-2367 | Hold the answer: "The titan is rising..." until it spawns |
| P2 | The strip says "YOU station 10" in the arena | 11, 12, 13 | "YOU BOSS" |
| P3 | Multiplayer: one kill finishes everyone at stage 11, including a kid who arrived 2 s earlier. Cooperative is fine, but the clock credits the latecomer with the leader's kill | RF B14 | Acceptable for co-op; show "Team kill: you joined at 3/5" on the board |

### B7. Finish (14_boss_down, 15/16, 20_run2_finish)
Keep: FINISH! / GOLD MEDAL big and in medal colour. The NEW BEST! and NEW RECORD! tags. Top-5 session times. The board no longer captures input.

| Sev | Problem | Evidence | Fix |
|---|---|---|---|
| P1 | An 8-line translucent text wall over a busy, night-lit arena. The medal is a word, not an object. The public feed overlaps the board's right edge ("NEW RECORD!" collides at x about 1335-1460) | 14, 20 | #10: show it at the podium; cut to 5 lines (medal + time + delta/best + accuracy + rank); move the feed |
| P1 | The medal rule is invisible. GOLD = 10/10 first try, time ignored. A fast 9/10 kid gets SILVER with no reason given | RF B14; L:118-121 | "SILVER: 9/10 first try (GOLD = 10/10)" |
| P2 | "NEW RECORD!" plus the record voice plus a public feed line fire for the first finisher of **every** session on every skill (session board, in memory). It means nothing by day 2 | 14, 20; RF 7b.11 | Rename to "Today's record" and keep "RECORD" for the best of the players present (ALL-TIME screen data) |
| P2 | Up to 4 sounds in the first 3 s (boss_dead stinger, "BOSS DOWN!", finish, record/best, medal) | RF B14 | Sequence: BOSS DOWN, then fall, then medal; skip the duplicate stinger |
| P3 | A first-ever run shows "Your best 1:29.8" with no tag | 14 | "First finish! Best set: 1:29.8" |

### B8. After the finish: the walk and the podium (17_victory_area, now_client)
| Sev | Problem | Evidence | Fix |
|---|---|---|---|
| P1 | The clock stops in the arena; the podium is 55-60 m away and not on screen. After 10 s the only guide is one orange line, "Race again: NEW RACE at the podium". There is no auto-restart, so a kid who doesn't find the lectern idles forever | 17; RF B15, B16; D:2035 | #10: teleport to the victory area after the titan falls; podium within 3 m |
| P2 | The dead titan sprawls across the bottom of the ALL-TIME screen in the line of sight from the arena; the screen is tiny at that range | 17, now_client | Moot after the teleport; otherwise despawn the corpse after the fall |
| P2 | Four names for one action: prompt "Race again", label "NEW RACE", hint "Race again: NEW RACE at the podium", board "Walk on! NEW RACE / CHANGE SKILL" | D:1971, 1986, 2035 | "RACE AGAIN" / "NEW SKILL" everywhere |

### B9. Run 2 (18, 19, 20)
Keep: the target line "Record 1:29.8" and a live green "-3.1 s" delta (19), plus NEW BEST! on the board (20). That is the right loop.

| Sev | Problem | Evidence | Fix |
|---|---|---|---|
| P2 | The delta sits at 30 px in the left column; you won't look there while dodging guards | 19 | Put the station delta in the right-answer verdict ("CORRECT!  -1.8 s"), #12 |
| P2 | Restarting costs a 55-60 m walk plus an E press plus the countdown | RF B15/B16 | #10 |

### B10. Run 5
| Sev | Problem | Evidence | Fix |
|---|---|---|---|
| P1 | Run 5 is run 1. Same halls, the same six gags (all seen by now), the same titan; only the questions and the clock change. Nothing accumulates and there is nothing to unlock, collect or show (gamification reviewers own the remedy) | RF §5 | UX minimum: the picker shows each skill's best medal and time (a visible 11-skill shelf to complete); the pace delta per door; penalty variety escalates rather than repeats |
| P2 | The "beat your best tomorrow" promise depends on persistence surviving a session. That is unverified on a published version; every UEFN test session started empty | RF 3.7; GOALS 105-107 | Verify before the class demo |

---

## 2. Journey: the teacher running 25 kids

| Moment | Sev | Problem | Evidence | Fix |
|---|---|---|---|---|
| Joining | **P1** | Island max is 16 players. 25 kids means two servers, split session boards, split "records", and kids asking why a friend isn't there | `tools/build_island.py` (16); hard constraint | Plan two halves (two codes or two time slots); the class card (below) unifies the results |
| Choosing | P1 | Each kid picks their own grade and skill; the teacher wants "everyone does Ratios today". Nothing locks it | RF B3 | Build-time class preset: a `map.json` skill lock that skips the picker, for a class private version. Do not build an in-world keypad (Rule 1.2 bans custom keyboards) |
| Starting | P2 | No shared start. Kids GO whenever they click, so it is never really a race of the class; the strip mixes "picking", "station 4" and "FIN" | RF 3.5 | Later: an optional "ready up" countdown when 2+ players are picking (gamification/modes) |
| During | P1 | The feed broadcasts every kid's penalties to 16 screens, and the strip shows who is last. Weaker kids get labelled in front of peers; a teacher will notice in minute 1 | wrong_13 to wrong_86; RF §4 | #6 |
| During | P2 | The teacher can see only the screen in front of them. The strip tops out at 8 rows | RF 3.5 | Nothing native; the class card covers it |
| After | P1 | Nothing tells the teacher what each kid struggled with. The board shows first-try X/10 only | RF B14 | Class card on the finish board: skill, time, medal, first-try X/10, "Practice: Exponents, Parentheses" (tier names of the missed stations). The kid reads it out or the teacher photographs the TV |
| Idle | P2 | Kids freeze in the picker or wander the victory area with no prompt | RF B1, B16 | #10, #13 |
| Session length | P2 | Round time limit reads 5 min with override off. Sessions longer than 5 min have not ended in tests, but a published version hasn't been checked. A human run is estimated at 3.5-5.5 min | GOALS 171-172; 3.4 estimate | Verify once on the private version |
| Persistence | P2 | Bests across sessions are unverified on published versions | RF 3.7 | Verify before promising "beat your best" |

---

## 3. Cross-cutting

### 3.1 The core rule (door = answer)
- The rule rests on four mappings: tile letter to door letter, tile colour to door colour, tile order to door order, and walking in = committing. Today only the order mapping exists in the world, and it is never stated.
- Letters A-D are safe world signage: they are the same for everyone; only the values behind them are per player. The arena already floats 3 m letters (12) and the door paint pipeline exists. The fix is mostly re-application plus verification.
- Make the **letter** the primary key and colour secondary (colour-blind kids, and see 3.9 on the HUD colours).
- 2- and 3-choice items: the kid only learns "No choice D here" after walking into D (D:1369). Say it up front in the caption ("Only A, B, C this time"); the empty tile already collapses.

### 3.2 Slate readability and HUD hierarchy
HUD inventory at 1080p (frame 05):

| Element | Area (px) | Needed while racing? |
|---|---|---|
| Fortnite GAME MODE / Game in Progress box | 25-356 x 25-120 | No: probe `hud_controller_device` (DOC) |
| Skill tag (title + subtitle) | 20-298 x 137-205 | Once; hide after GO |
| Clock, target, delta, RACE strip | 20-266 x 228-450 | Clock and delta yes; strip trimmed (#6) |
| **Slate** (caption, prompt, 4 tiles, feedback, streak) | 364-1556 x 40-375 (about 19% of screen) | Yes: the core |
| Minimap | 1603-1900 x 20-317 | No: a linear course; mostly blank cyan in the frames |
| Feed (3 lines, 7 s) | right, under the minimap | Celebrations only |
| Health/shield, ammo, inventory | bottom | Fortnite: keep |
| Verdict / FlashBig (96 px) | centre, 0.68 down | Yes |
| Boss bar | bottom centre | Arena only |

- About a third of the screen is HUD when the slate is open, and that is the top third, where the door wall sits from mid-hall (05, 22).
- Hierarchy today, loudest first: STREAK line (40 px yellow), prompt (46 px white), tile values (34 px), explanation/feedback (28 px), **tile letters (20 px)**. The letter is the key to the whole game and it is the smallest text on the slate.
- Target hierarchy: (1) prompt + tiles with 40 px letters; (2) verdict flash; (3) clock + delta; (4) streak (smaller, or moved under the clock); (5) the rival; (6) feed.
- Slate prompt readability is good: 46 px, high contrast on chalk, centred (all frames). Keep.
- TV overscan: the slate top sits at 40 px; the 5% title-safe margin is 54 px. P3.

### 3.3 Learning loop
| Step | Today | Problem | Change |
|---|---|---|---|
| Right door | "Correct! <explanation>" under the next question for 4 s | Reads as working for the new question; shares numbers with its distractors (07, 11) | Recap card: solved question, right tile lit, steps, 3 s, then flip (#5) |
| Wrong door | Misconception line of the chosen distractor for the penalty + 4 s | Generic "Check your arithmetic." on 17% (OoO 39%); some stock lines name numbers that don't match the item (RF 7b.5) | First-step hint baked per item; audit the stock lines with fixed numbers |
| Retry | Same question, same letters | Elimination guessing is free except time | Reshuffle on every retry |
| 2nd miss | Nothing new | A stuck kid loops penalties with no new information | Show the worked steps and outline the right tile; the kid still has to walk through it |
| Medal | First-try accuracy only, rule hidden | Good principle, invisible | Show the rule on the board and at the countdown |
| Teacher | Nothing | No signal of what to reteach | Class card (section 2) |

### 3.4 Pacing and dead time (estimate: the repo has no human timing; assumes about 6 m/s sprint, per RF)
| Segment | Estimate | Dead (no control or no choice)? |
|---|---|---|
| Join to GO | 5-20 s picker (2 clicks, 10 skills to read) + 3.4 s countdown/GO | The countdown, yes (useful: question shown) |
| Running 813 m (boost and plates help) | about 2:05 | No |
| 10 door stops + E | about 15 s | Partly |
| Arena: 5 hits, teleport back each time, 4-18 m to a pad | 25-40 s + boss-spawn waits of 0-4 s | The waits, yes |
| Wrong doors at 70% first-try (about 4.5 misses) | 4.5 x (5.8-9.3 s) = 26-42 s | Holds about 12 s, re-walks about 18 s |
| Finish board, then walk to the podium | 10 s + about 10 s | Mostly |
| **Typical run** | **about 3:30-5:30** (best kids about 2:30) | **about 15-20% dead or repeat** |

A 45-minute class fits about 6-8 runs. Biggest dead-time cuts: retry spot (#8), teleport to the podium (#10), shorter holds (#8).

### 3.5 Frustration and fairness: penalty cost spread (RF B8b; re-walk at about 6 m/s)
| Penalty | Hold | Then | Est. cost | Hidden extra |
|---|---|---|---|---|
| Yeet | about 1.8 s + flight | lands about 18 m back, carry on | **about 5.8 s** (cheapest) | none |
| Dizzy | 1.5 s spin | entry; 7 s blur while moving | about 5.8 s | motion discomfort |
| Spike | about 3.5 s, death cam | entry | about 7.8 s | **loses dropped guns**; Fortnite "bailed early" line |
| Blackout | 3.5 s | entry | about 7.8 s | none |
| Mud | 0 s | entry at 0.5x for 8 s | about 8.5 s | orange glare |
| Freeze | 5.0 s, no turning | entry | **about 9.3 s** (dearest) | none |

- A 60% cost spread decided by a dice roll in a race, applied 4-5 times a run, decides close races. Equalize the cost (about 2.5 s hold + retry spot) and keep the variety cosmetic.
- Guards are the other unfairness: late stations test aim and splash survival, not math (B5).

### 3.6 Social exposure and multiplayer clarity
- Feed lines today: penalties (all six, named), finishes **with medal** (BRONZE published), records, streaks, skips, boss events. Keep: streaks 3/5/7/10, "reached the boss!", "landed the final hit!", finish times, records. Remove: penalties (send them to the victim only) and the medal word.
- An anonymous global counter is fun without blame: a billboard "YEETS TODAY: 37" at station 1 (global text, no names, no answers).
- Strip: show top 3, the **one rival just ahead**, and you, instead of a full rank where someone is visibly last. The closest rival is the motivating number in racing HUDs.
- Untested with 2+ players: strip order, shared guards, item use on teammates (Cooperative), a kid following another through a door. Run one 2-player session before any class demo.

### 3.7 Replay pull (UX side only)
- What pulls today: the clock target + delta (works, 19) and NEW BEST (20).
- What's missing on the UX side: progress made visible at the moment of choice. The picker shows nothing about past runs. Each skill button should carry its best medal and time; "CONTINUE: <last skill>" should be the focused default. Persisting the medal per skill is small (`fnm_save` already keys by cartridge id).
- Restart friction (60 m walk + E) kills the "one more run" impulse (#10).

### 3.8 Lighting
- `timeOfDayOverride` = NoOverride, so kids get a random mood each session (LO 2).
- Night (02-14): blue-cyan wash, tier colours lost, the orange titan reads blue.
- Dawn and day (now_client, wrong_22): the white floor glares, and the HUD's white and yellow sit on white.
- UX requirement: fixed, colour-true light, with the floor a mid-tone so HUD text and door colours read. Per-zone mood can then be added per player with post-process (proven device; FX 3e), since the sky is global.

### 3.9 Accessibility
| Issue | Sev | Evidence | Fix |
|---|---|---|---|
| HUD tile colours collapse: B ring/value (0,255,255) and C (0,255,246) are the same cyan; D renders pure yellow (255,255,0) while the world D letter is orange (255,185,0) and world C is green. The tint values in `FnmDoorColors` saturate on screen | pixel samples of 05 (rings at y 210) and now_client (letters); U:38-42 | Pre-coloured tile textures or retuned tints, verified by sampling a capture; letters at 40 px |
| Colour-only door coding (once painted): blue vs green is the classic colour-vision-deficiency pair (about 1 in 12 boys) | U:38-42 | Big letters on the doors; position as the third key |
| Reading load: explanations up to 115 chars at 28 px while running; word problems (Ratios) read under guard fire | RF B8a, §8 | Recap card read in the connector; steps as short chips; guards wait until the hall entry |
| Motion: Dizzy = 2 full turns in 1.5 s + 5 blur pulses over about 7 s; frost and sepia whiteouts | RF B8b; wrong_71 | 1 turn, 2 pulses; post-process at about 50% |
| Sound-off classrooms | - | Every key event has a HUD label. Keep it that way; never make a voice line the only carrier |
| Controller | U:949 | First button focused (good). Picker on a real Xbox: **not seen**; verify in the class-demo build |
| Phone/iPad | U:70-102 | HUD authored at 1080p; 20 px letters are tiny on a phone. Bigger letters cover most of it |

### 3.10 Copy pass (one sweep, S effort)
| Now | Where | Problem | Replace with |
|---|---|---|---|
| "CHOOSE YOUR SKILL" + "Pick a grade" | picker (01) | Disagree | "PICK YOUR GRADE" / "PICK YOUR SKILL" |
| "Fortnite Math" | tag, title | Epic rules 3.1.x risk (MR 3.9) | New island name (vision reviewers) |
| "Stage 3/10 - Parentheses" vs strip "station 3" vs "STATION N" billboards vs "You are on stage N." | slate, strip, D:1294, D:1328 | Two words for one thing | "STATION 3/10 - Parentheses" everywhere |
| "Stage 9/10 - Boss Level" | 10 | No boss there | Rename the OoO tier-5 label, or reserve "Boss" for the arena |
| "Correct!  <previous explanation>" | D:1389 (05, 07, 10, 11) | Misread as the current working | Recap card (#5) |
| "Check your arithmetic." | D:1312 (13, 50, 71) | No content | "Start with 7 x 9." (baked first step) |
| "No choice D here" | D:1369 | Told after the fact | Caption: "Only A, B, C this time" |
| Flash "STEP ON THE RIGHT ANSWER PAD!" + caption + hint (overwritten) | D:2294-2295, 11 | Three copies, fired 44 m early | One line on arena entry: "Stand on the pad with the right answer. Bullets can't hurt it." |
| "BOSS - hits 0/5" vs "team hits 2/5" | 11, 13 | Two counters | Bar only: "TITAN  2/5" |
| "YOU station 10" in the arena | 11-13 | Wrong | "YOU  BOSS" |
| "DIRECT HIT!  5 TO GO" with no boss up | D:2366 | False | "The titan is rising..." |
| "Island record ... NEW RECORD!" (first finisher every session) | 14, 20 | Inflated | "Today's record" |
| "GOLD MEDAL" | 14 | Rule hidden | "GOLD MEDAL  -  10/10 first try" |
| "Your best 1:29.8" on a first run | 14 | Flat | "First finish! Best set: 1:29.8" |
| "Walk on! NEW RACE / CHANGE SKILL at the podium ahead" + "Race again: NEW RACE at the podium" + prompt "Race again" | D:1971, 2035, 1986 | Four names | "RACE AGAIN" / "NEW SKILL" |
| Feed "<Name> got frozen at station 1" | D:1398 | Public shaming | Victim's own HUD only |
| Feed "<Name> finished in 1:23.4 (BRONZE)" | D:1955 | Publishes a low medal | Time only |
| "<Name> (91) bailed early" | Fortnite engine, Spike (50) | Engine elimination line | Gone with a non-lethal Spike |

---

## 4. Top 15 fixes (ranked by impact / effort, discounted for unproven tech)

| # | Player moment | Change | How to build | Impact | Effort | Evidence |
|---|---|---|---|---|---|---|
| 1 | Station 1, first look down the hall | Doors carry big letters A-D and the four colours, matching the HUD | Re-run `build_course.py --doors-only` (door_dress), then **screenshot it in play**. Add a 3 m Alphabet letter prop per door on the lintel (door colour, `bNoCollision`, the arena-letter pattern) + one Customizable Light per door at 50% in its colour. Letters are the same for everyone, so no answer leaks | 5 | S | wrong_22, door_02, editor_doors_s1; LO "Doors" |
| 2 | First run, first 20 s | Station 1 teaches the rule | First-run-only caption lines: "Walk through the door with the right answer. A is on the left." / "Press E to open" (Verse distance check at 5 m from the wall) / "Everyone gets different questions". Remove station 1's guard. Probe the door sprint-bash. Make the vestibule barrier invisible (probe its option) | 5 | S-M | RF 7b.2; 18 (guard at the doors); wrong_48 |
| 3 | Every question | HUD colours that render as the door colours; the letter as the key | Tiles render B = C = cyan and D = yellow (sampled). Pre-coloured tile textures in `make_hud_art.py`, or retune `FnmDoorColors` and verify by sampling a capture. Tile letter 20 to 40 px. Same values for the world letters and pads | 4 | S | 05/07 samples; now_client; U:38-42, 93-97 |
| 4 | Every session | Fixed, colour-true lighting; no floor glare | Island Settings `timeOfDayOverride` to a fixed daytime. Floor to a mid-tone flat material (OBJ trick, proven). Probe `skydome_device` (DOC) for a stylised sky | 4 | S | 02-14 (night) vs now_client, wrong_22 (glare) |
| 5 | Every right door | Recap, then the next question | Slate shows the solved item for about 3 s (right tile lit, steps, verdict "CORRECT!  -1.8 s"), then flips. Delete "Correct! <old>" (D:1389); the arena uses the same card instead of "Last one:". Verse: `fnm_hud.ShowRecap` + sequencing in `HandleDoor`/`HandlePad`; the connector gives 5-8 s of run to absorb it | 5 | M | 05, 07, 10, 11; D:1389, D:2321 |
| 6 | Every wrong door, seen by 15 classmates | The feed celebrates and never names a failure; the strip shows the rival, not the last place | Penalty `Broadcast` goes to the victim's HUD only; drop the medal word from finish lines; anonymous "YEETS TODAY" billboard; strip = top 3 + rival ahead + you | 4 | S | wrong_13/33/50/71/86; D:1398, D:1955; RF §4 |
| 7 | Whole run | One copy pass | Table 3.10: STATION everywhere, one arena instruction on entry, one counter, "Today's record", the medal rule shown, "RACE AGAIN", "Only A, B, C this time", strip "BOSS" | 3 | S | 3.10 |
| 8 | After a wrong door, worst at 8-10 | A math mistake costs time, not a re-run of the gauntlet | Retry spot 3 m in front of the door wall, facing the doors. That is past every obstacle (last at 20 m). It is inside the guards' patrol (spawn 21.5 m, radius 6 m), so exposure drops to the 1-2 s it takes to pick a door, instead of the whole 25.5 m. Holds to about 2.5 s. Spike without `Damage(1000)`. +3 s on the clock so time still carries accuracy. No grenade/rocket launchers on guards (put them in a chest as the reward) | 4 | M | RF B8b, 7b.14, 7b.18; wrong_50; 3.5 table |
| 9 | Wrong door, during the hold | The hold is the lesson | Bake a per-item `hint` (explanation's first step, result hidden) and show it instead of "Check your arithmetic.". 2nd miss on the same item: worked steps + right tile outlined. Reshuffle letters on each retry. Python bake + tests pinning PROTOCOL 4a + Verse | 4 | M | wrong_13/50/71; D:1312; RF §5 (17% / 39% ARITH) |
| 10 | Titan falls | Celebrate where you stand; podium in reach | 3 s after the fall, `TeleportTo` the victory area. VFX Spawner FireworksLarge + Confetti there (proven device). Finish board shown there, cut to 5 lines, feed moved off it. RACE AGAIN / NEW SKILL within 3 m | 4 | M | 14, 17, 20; RF B15/B16 |
| 11 | Arena | The boss reads as the boss; pads map like the doors | Pads in one row A-B-C-D left to right at about 10 m (hall is 22 m wide, 4 x 4.5 m fits). Rerun `trigger_fit` and the race-boss letters. Arena intro fires on hall entry. Compact slate in the arena. Titan scale 2.1 to 3+. Add the muzzle FX. No "DIRECT HIT" without a boss | 4 | M | 11, 12, 13; D:2294-2295, 2366; LO 8 |
| 12 | Every right door, every boost | The world reacts | Niagara door burst (build_fx sprite/spark templates, proven; global is fine because questions are per player) + 0.5 s light flash at the door passed. Per-player post-process during boost (ActionLines or VignetteMaskedColored). Pace delta in the verdict | 4 | M | LO 6; FX 1.4, 1.6, 3e |
| 13 | First screen, every return to the picker | A title screen, not a form | Banner texture (drawn, or Meshy nano-banana-pro, 9 credits). One-line rules. RACE / BOSS BATTLE as two cards. Focused "CONTINUE: <last skill> - 1:29.8 - GOLD". Each skill shows its best medal (persist the medal per skill). Skip the skill step for one-skill grades. Hide the clock and tag while picking. `choose` 2 s after `welcome` | 4 | M | 01; D:1083, 1137; U:886-970 |
| 14 | Whole run | A third of the screen back | Probe `hud_controller_device` (DOC) to hide the minimap and the GAME MODE box. Hide the tag after GO. Fixed-height slate | 3 | S (probe) | 01, 05, 22 |
| 15 | Teacher, 25 kids | A class can actually run it | Two-server plan (16 cap). Class card on the finish board (skill, time, medal, first-try X/10, "Practice: <missed tiers>"). Build-time skill lock in `map.json` for a class private version (no keypad: Rule 1.2). Verify persistence and the round time limit on the private version first | 3 | M | build_island.py; RF 3.7; GOALS 105-107, 171-172 |

Items 1-4 and 6-7 are all S effort and together fix the clarity score. Items 5, 8, 9 fix learning and fairness; 10-13 fix juice, replay and shareability.

---

## 5. Shakiest assumptions (unverified)
- **HUD colour collapse** was measured on PrintWindow captures (sRGB, 1080p). A TV in HDR mode may render differently, but two values 9 apart in blue will not separate.
- **Run-time estimates** assume about 6 m/s sprint and 70% first-try; no human run exists in the repo.
- **"A/B pads off-screen from the landing"** comes from the pad coordinates plus frames 12/13, which were taken at the arena entry after a teleport. The third-person camera FOV was not measured.
- **Red-stripe barrier reads as "blocked"** is my interpretation of wrong_48, not a kid's reaction.
- **Door sprint-bash**, **Barrier visibility option**, `hud_controller_device`, `skydome_device` and **item effects on Cooperative teammates** are all probes, not facts.
- Whether the 16-player cap overflows to a second server or refuses joins on a private code is unverified.
