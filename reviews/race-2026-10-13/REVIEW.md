# Race mode review: is it a blockbuster? (2026-10-13)

Aaron's ask: a full UX review of race mode. What works, what doesn't, would every kid tell a friend, what gamification is missing,
what FX we aren't using. Think big; the target is a blockbuster.

## 1. Bottom line

- **Not a blockbuster today, and kids would not all tell a friend yet.** The story they would tell already exists: *"pick the wrong door
  and you get YEETED, then everybody lasers a giant lava titan."* Today that story is buried under unreadable doors, random lighting,
  rewards that only happen on your own HUD, and a finish that is a wall of text.
- **Three P0 defects, found in live play today:**
  1. **The doors have lost their paint.** They carry no letters and no colours, in play or in the editor.
  2. **The HUD tiles mis-colour.** B and C render the same cyan, and D renders yellow instead of orange.
  3. **The island runs Fortnite's day/night cycle.** At night the whole race is blue, the tier colours vanish, and the orange titan reads
     blue. By day the white floor glares.
- **The gap is format and identity, not polish.** Market data from today:
  - Quiz and educational islands are dead on Fortnite: the top quiz island had 21 players and the top educational island 22.
  - Party rounds win: Pillars had 14,300, played as 12-player rounds with a random item every 6 s.
  - Time-trial islands are tiny: the top one had 129. Today's race is a solo time trial with a quiz gate.
- **Students cannot join a private version** (verified, `sources/class_access.md`).
  - Epic: "These versions are unmoderated, so only you can use the private version code".
  - Playtest groups require adult accounts.
  - **A class pilot needs an unlisted publish:** moderation, an IARC questionnaire (aim for E/E10+), and an 18+ publisher.
    From 2026-10-22, landscape and portrait thumbnails plus a logo are required for any release submitted for review.
  - Parents' rating limits can still gate individual kids.
  - So the rename, the thumbnails and a rating-safe build are now on the critical path for the classroom, not just for Discover.
- **The path:**
  1. Week 1 fixes the ground floor at **zero credits**.
  2. Next, test a synced multi-player "heat" with real kids.
  3. Then build the identity (name, world, game-show doors) and a math-fuelled economy (shield, strike, redemption) on top.

**Scores.** UX: clarity 3/10, juice 4, fairness 4, learning 5, replay 3, shareability 3. Blockbuster checklist: **22/75**, target 70.

## 2. How this was done

- **Live play.** 3 UEFN play sessions today: a full auto-run (GOLD, 1:29.8 on run 1, 1:26.6 on run 2), all six penalties, and a
  close-up at door B. About 130 frames, an editor capture, and reads of the door actors and Island Settings.
  - Key frames are in `frames/`.
  - Ship debug values were restored afterwards, compiled clean, and the git tree was clean.
- **Fact-gathering agents (Sonnet).** A code-level race inventory, an FX and asset inventory with credit balances, market and Epic-rules
  research, and classroom-access research. All are in `sources/`.
- **Design agents (Opus 5.5).** A UX teardown, a gamification system, a spectacle and FX plan, and a blockbuster vision. All are in `sources/`.
- **Lead audit.** I re-checked every load-bearing claim against the build:
  - door materials read back null;
  - HUD pixels sampled: B (0,255,255), C (0,255,246), D (255,255,0);
  - `timeOfDayOverride` reads NoOverride;
  - the `maxPlayers` range is 1-100.
- **Two reviewer claims were corrected:**
  - "16-player cap": the island is *set* to 16, but the setting goes to 100 (memory budget permitting).
  - "Race cannons have no muzzle FX": the 0 counts retired devices; the Niagara muzzle does fire.

## 3. What is working (keep)

- **The core loop's skeleton.**
  - Run a hall, pick a door, and success never stalls.
  - The next question appears while you run the connector.
  - The first question is up during the 3-2-1.
  - Join to GO takes two clicks.
- **Concept-first content (PROTOCOL §4a).** Three-second mental-math questions are what turn running and thinking into one skill.
  - Misconception feedback is already in the data for about 83% of wrong choices.
- **The STREAK line and the announcer ladder.** "STREAK x5 - SPEED BOOST 3s" plus DOUBLE...UNSTOPPABLE, echoed in the feed.
  - Big and readable (frame `02`).
- **The penalties as comedy.** The frost white-out with an ice cube (`05`), the yeet and the spike read instantly and get a laugh.
- **The cannon volley on the titan (`08`).** Lightning lasers and chunky floating 3D letters. This is the best frame in the race.
  - The floating Alphabet letters are the best design element on the island.
- **Smaller things to keep:**
  - Health refill every station.
  - The per-player question and letter shuffle: copying a classmate's door is useless.
  - Per-skill bests with the green pace delta on run 2.
  - The door backstop.
  - Connector variety. Aaron: "a lot more engaging".

## 4. What is not working

### P0: breaks the core loop

| # | Problem | Evidence | Fix | Cost |
|---|---|---|---|---|
| 1 | **Doors are identical.** No letters, no colours. The only mapping to the HUD is left-to-right order, and nothing states it. `FNM_S01_DoorB` reads back `overrideMaterials: [null]`; the `M_door_face_a..d` materials exist. The paint from fb38d7d was lost in a later rebuild (not diagnosed which) | `frames/03`, `04` (door B close-up); editor capture | Re-run the door dress and **see it in play**. Add a 3D Alphabet letter on each lintel (the arena-letter prop) and a letter-colour light in each arch | 0 cr, S |
| 2 | **HUD tile colours collapse.** B and C are the same cyan on screen; D is yellow, while the world D letter is orange. The tint values saturate | pixel samples of `wrong_22`; `fnm_ui.verse:36-42` | Pre-coloured tile textures or retuned tints, verified by sampling a capture. Grow the tile letter from 20 to 40 px (today the letter, the key to the game, is the smallest text on the slate) | 0, S |
| 3 | **Lighting is random.** `timeOfDayOverride` = NoOverride. Night washes the course blue (`02`, `07`, `08`); dawn and day turn the white engine-cube floor into glare (`03`, `09`), and Mud's sepia becomes orange glare (`06`) | Island Settings read; frames | Lock the time of day: compare Hour10/14/17/19 frames, Hour17 likely. Paint the floors a dark mid-tone per tier with the existing `--paint-only` path. Raise character rim light | 0, S |

### P1: most kids hit it

| Problem | Fix |
|---|---|
| **Nothing teaches the rule.** No copy says door = answer, press E, walking in commits, or A is on the left. A pistol guard shoots at you at station 1 while you read | Station 1 becomes the tutorial: first-run captions, no guard. Probe whether sprinting bashes the door open |
| **First screen is a form** (`01`). Fortnite's GAME MODE box sits over a "Fortnite Math" tag over a 0:00.0 clock. The heading says "CHOOSE YOUR SKILL" while the step says "Pick a grade", above three identical yellow buttons. BOSS BATTLE, a different game, sits above the grades | Title-screen picker: logo, one-line rules, RACE and BOSS BATTLE as two cards, a focused "CONTINUE: last skill". Hide the clock and tag until GO |
| **The explanation misleads.** "Correct! <previous answer's working>" sits under the NEXT question and shares its numbers. Frame `02b` shows "...5 + 2 = 7" over a question whose tile A is 7. The arena already fixed this with "Last one:" | A 3 s recap card (solved question, right tile lit, steps, "CORRECT! -1.8 s"), then the slate flips |
| **Wrong-door feedback is often empty.** "Check your arithmetic." covers 17% of wrong choices overall and 39% on Order of Operations, the default skill. Letters don't reshuffle on a retry, so guessing the next door costs only time | A baked first-step hint per item. Worked steps after a 2nd miss. Reshuffle the letters on every retry |
| **Penalties are public shaming.** "<Name> got frozen at station 1" goes to every HUD, and the projector, for 7 s. The strip shows who is last | Misses go to the victim's HUD only (the leader's misses can stay public as drama). Strip = top 3, the rival just ahead, and you |
| **A math slip costs a gauntlet re-run.** You go back to the 4.5 m landing and re-run 25.5 m of obstacles and live guards: five rocket-launcher guards at station 10. Penalty cost is a dice roll from about 5.8 s (Yeet) to 9.3 s (Freeze). Spike really eliminates you, takes your dropped guns, and shows Fortnite's "bailed early" line | Retry spot 3 m in front of the door wall. Holds of about 2.5 s. +3 s on the clock. Spike without the kill. Launchers come out of a chest as a reward, not from guards |
| **Rewards only exist on your HUD.** A right answer, a streak, a boost: nothing happens in the world. A classmate sees nothing, so there is nothing to clip | Gate burst plus a gold **pillar of light** into the sky. Boost speed lines plus a spark trail. All on proven Niagara recipes |
| **The arena reads small and confusing.** The intro fires 44 m early, and its hint is overwritten in the same tick. Pads sit in a 2x2 grid, so A and B are off-screen at entry and the mapping differs from the doors. There are two hit counters. The slate cuts the titan at the neck. The titan is 6.3 m (boss mode's is 12 m) | Pads in one A-B-C-D row. Intro fires on arena entry. One counter on the bar. A compact arena slate. Scale the titan up |
| **The finish is a text wall far from the podium.** Eight lines over the arena, with the feed overlapping it (`10`). The medal is a word, and its rule (10/10 first try; time ignored) is never shown. "NEW RECORD!" fires for the first finisher of every session. The podium is 55-60 m away, and there is no auto-restart (`11`) | Teleport to the podium when the titan falls. A 5-line, screenshot-ready finish card. Show the medal rule. "Today's record". RACE AGAIN within reach |

### P2 and P3 (details in `sources/ux_critique.md` §1, §3.10)
- The welcome and choose voice lines overlap.
- "Stage" and "station" are used for the same thing.
- The red-striped barrier reads as "blocked".
- Pickup pads auto-collect at the landing spot.
- The slate height jumps around.
- Dizzy's two full turns cause motion discomfort.
- The tier-5 label is "Boss Level" at stations 9-10, where there is no boss.
- A right pad with no boss up still says "DIRECT HIT! 5 TO GO".
- The strip shows "station 10" in the arena.
- Up to four sounds stack at the kill.

## 5. Would every kid tell a friend?

**No, not today.** The scores below are from the vision checklist (`sources/vision.md` §7).

| | Score /5 | Why |
|---|---|---|
| One-breath hook (name, pitch) | 1 | "Fortnite Math", with no logo, mascot or title card |
| First 10 seconds | 1 | Frozen in a menu with no default; two voice lines overlap |
| Core affordance readable | 1 | The doors are identical in play |
| Success is a world event | 1 | A 1.5 s HUD flash |
| Failure is funny and short | 3 | The gags land; holds and re-walks are long |
| Spectacle / clip moment | 3 | The cannon volley is strong; it comes at minute 3-5 |
| Identity (theme, set, lighting) | 1 | Greybox under random lighting |
| Social play | 1 | Nothing to do to or with friends; two humans have never played together |
| Round loop / requeue | 1 | No auto-restart; podium 60 m away |
| A number that goes up | 1 | Best time only; persistence across sessions unverified |
| Comeback / fairness | 1 | No catch-up; the leader runs away |
| Math is the power, concept first | 4 | Streak = boost; three-second questions |
| Content runway | 2 | 11 grade-6 skills, 1 grade-7, 0 grade-8 |
| Discover-ready | 0 | No name, thumbnails, logo or trailer; grade labels on screen one |
| Classroom-ready | 1 | Xbox build never seen; memory unmeasured |

What would make it tellable: a kid can say *"I froze Maya with a strike right before the boss"*, *"I beat Mr. A's time"*,
*"our class killed the titan in 3:58"*, or *"I finally caught LEFTY"*. Each of those sentences maps to a system in section 6.

## 6. Gamification we are missing (full system: `sources/gamification.md`)

**Design rule: the first-try right answer is the only thing that earns anything.** Nothing opens a door, skips a question or raises a
medal without one. Mistakes are private; the leader's mistakes are drama.

| Mechanic | What it is | Feasibility | Impact |
|---|---|---|---|
| **Shield (streak 3) and Strike (streak 5)** | A Shield blocks one penalty. A Strike auto-fires a light, in-place gag (2.5 s freeze, mud, blur) at the **nearest racer ahead**, with a warning, 20 s immunity and Shield blocks. The leader's Strike turns into boost, so strikes only flow forward: a comeback that needs 5 right answers in a row | Proven mechanics; needs a 2+ player test | 5 |
| **Redemption at the boss** | Each station you missed comes back as one of your arena pad questions. Getting it right deals a hit and restores half credit. The boss fight becomes personal review | Proven (arena draw) | 5 |
| **Named traps, then the Trap Dex** | Each misconception becomes a named trap ("LEFTY got you! Worked left to right"). There are **182 catalogued** across 11 skills. Capture one by beating its bait 3 times. Both the vision and gamification reviewers reached this independently: it makes mistakes collectible and gives the teacher data | Proven patterns + emit misconception ids | 5 |
| **Medal v2** | Accuracy gates each tier, then par time sorts the accurate kids. DEV medal = beat Aaron's time; TEACHER medal = beat the host's run in class ("Beat Mr. A"). A next-goal line: "GOLD needs 9/10 + 2:05" | Proven | 4 |
| **Brag-grid finish card** | Wordle-style: 10 check/cross tiles plus a boss tile, the medal, time, rank title, and the island code as text (no QR, per Rule 1.2). Screenshot-ready | Proven (check/cross textures exist) | 4 |
| **Ranks, titles, trails** | Stars from mastery (3 first-try rights on 2 different days, for spacing), 12 ranks, equippable titles ("Gold Fraction Slayer"), cosmetic trails. Earned, never sold | Proven persistence pattern; trail follow = probe | 4 |
| **Class mode** | Host = the first player to join; no PIN, so Rule 1.2 is safe. Controls: MASS START, SKILL LOCK, FREEZE ALL ("eyes on me"), a projector panel with a **misconception radar** (the class's top wrong rules with counts). Boss Raid with the whole class. Class records saved on the teacher's profile | Proven parts | 5 for teachers |
| **Daily Mix and Course of the Week** | Spaced review built from your weakest tiers (Leitner, day id from `GetSecondsSinceEpoch`). A weekly modifier, including a new comedy penalty each week. Weekly goals, never streak-guilt | Documented | 5 |
| **Accolades (Fortnite XP)** | 9 accolades, each triggered only by a math outcome, one award every 2-10 min. Never write "XP" in metadata | Documented | 5 (return reason) |
| **Party hooks** | Squad tag, SQUAD SURGE meter, buddy trail via the Social Synergy API (`GetLocalParty`) | Documented; probe | 4 |

**Do-not list.** These four G6 ideas Aaron previously liked are flipped:
- **Jackpot door that hits the whole class:** kids blame the kid who triggered it. Flipped to PARTY SURGE, where one kid's streak boosts everyone.
- **Wall coins plus a shop:** a currency earned by running. Replaced by streak charges.
- **50/50:** pure guessing. Replaced by X-RAY, which shows why two choices are wrong.
- **Gold door that skips a station:** skips a question. Replaced by I'M SURE, a confidence bet.

Also do not add: wheels or crates (Rule 1.11), streak-loss messaging, or anything that lets speed beat thinking.

## 7. FX we are not using (full plan: `sources/spectacle.md`)

**The five to build first.** Items 1-4 cost zero credits and use only proven devices and Niagara recipes:
1. **Lock lighting, darken the floors, raise rim light.** This fixes the P0 lighting problem and makes every FX pop.
2. **Doors:** re-paint, add 3D lintel letters and letter-colour arch lights.
3. **Right answer:** a gate burst plus a 40 m gold **pillar of light**. Every right answer lights the sky ahead of everyone behind you,
   so a kid sees the class's progress. It is safe because the burst happens behind the wall after the answer, and questions are per player.
4. **Boost:** per-player `PP_ActionLines` speed lines, plus a spark trail spawned behind the runner every 0.12 s: cyan, then gold, then
   magma "ON FIRE".
5. **The titan on the horizon:** a Meshy volcano (~44 credits) beyond the arena, with the existing titan mesh idling on its rim at huge
   scale. Every hall faces +Y, so the boss is above the door wall from station 1 and grows as you climb (the Only Up principle).
   *Depends on a draw-distance probe.*

**Then:**
- **The titan's intro:** a magma eruption, the Jump and Slam clip, and the boss voice already imported.
- **The kill:** a 15 m magma shock ring, five strikes, fireworks, and a gold beam that opens the gate.
- **The finish:** a portal to a podium ceremony with a confetti cannon, a medal as an object, a champion hologram of the record holder
  (`PlayerReference`, probe) and a crowd (`CrowdVolume`, probe).
- **Penalty punches:** ice shatter, yeet dust puff, **flies buzzing over a mudded kid**, dizzy stars.

**World: "Titan Peak" volcano ascent.** The existing tier colours and elevation already tell this story:
- jungle base camp;
- waterfall gorge;
- the frost ridge at the highest point (the ice station is already there);
- the obsidian descent;
- the magma core;
- then the Titan's Forge.

**Credits.** Shopping list ~879 of Meshy's 1,468 (volcano, a door arch with 4 tier skins, start gate, podium, medals, trophy, a mascot
with real clip ids, titan clips, set pieces, logo, Discover key art, HUD art, tier textures), leaving ~590.

**Mint.** 7,580 credits, best spent on audio: escalating tier music, a boss theme, crowd and SFX. Never on worlds, which UEFN cannot render.

## 8. Blockbuster direction (full: `sources/vision.md`)

- **North star:** a game-show gauntlet for up to 16 players. Sprint at four doors; your answer is the key. Right = smash through in light.
  Wrong = the show gets you, in front of everyone. In the final round the whole lobby lasers the titan.
- **Three pillars:**
  - *Brains are the power.* Math fuels boost, strikes and cannon shots.
  - *Every door is a show.* Funny, never shaming.
  - *One clock, one titan, one crown.*
- **Three tests for every build decision:**
  - *Spectator:* can someone 20 m away tell what happened to you?
  - *Projector:* does it read from the back row?
  - *Five-second:* a wrong door costs 5 s or less and gets a laugh.
- **Name** (drop "Fortnite" everywhere, including the welcome voice line; Rules 3.1.x and the thumbnail policy):
  - **DOORS OF DOOM** (recommended; check fortnite.gg for title collisions first);
  - BIG BRAIN GAUNTLET;
  - WRONG DOOR!
- **Lead's merge of two reviewers' ideas:** DOORS OF DOOM is the show and Titan Peak is its set. The robot host and the mascot "Volt"
  become one character.
- **Kid pitch:** *"Pick wrong and the door launches you across the room, then everybody lasers a giant lava titan."*
- **Positioning:** classroom first, built as a party game, so the class build is the Discover build. Genre: **Party & Mini Games**,
  never "educational".
- **Rule 1.15** (no content primarily targeting under-13s): the GRADE 6/7 buttons on screen one are a targeting signal.
  - Replace them with ROOKIE / PRO / LEGEND leagues; a teacher guide maps leagues to grades.
  - Use neutral metadata and a teen art direction.
- **Modes:**
  - **HEAT** (default): a synced ~3-minute round, 5 stations plus the titan, live places, FINAL CALL, podium awards (MVP, COMEBACK),
    auto-requeue.
  - **TIME TRIAL:** today's 10 stations.
  - **TITAN RAID:** today's boss mode.
  - **CLASS:** a host layer over the other modes.
  - Merge the two titans: the heat finale moves to the colosseum's 12 m titan.
- **Bold bets, each with a zero-credit test first:**
  1. **The party heat.** Test: synced start + auto-requeue on today's art, played with 4+ kids. Measure unprompted "again!".
  2. **Game-show doors.** Test: door paint + one burst + "TRAP:" copy. Film 15 s and show 10 students.
  3. **BRAIN POWER.** Test: a streak of 3 auto-zaps the leader; persist one number and print a meme rank.
- **What would sink it:**
  - Publishing it as a quiz.
  - Pain instead of comedy.
  - Building art before two humans have played it or island memory has been measured.
- **The 15-second clip:**
  1. Six avatars sprint at lit doors.
  2. Gold smash-through.
  3. A friend gets yeeted, with 0.5 s of slow motion.
  4. The colosseum titan staggers under lightning cannons.
  5. The titan topples; crown on the podium.
  6. The logo and island code.

## 9. Lead's calls where reviewers differed

| Topic | Positions | Recommendation |
|---|---|---|
| Guards | Vision: fewer, themed as "security bots" in heats. UX: remove station 1's guard, no splash weapons, retry spot near the doors. Aaron liked the guards and asked for the weapon ladder | **Keep the guards.** Remove station 1's. Launchers become a chest reward. The retry spot sits past the guards. Revisit after a real 4-kid heat |
| 16-player cap | All four reviewers treated it as fixed | **It is a setting** (`maxPlayers` 1-100). One 25-30 kid lobby may fit after a memory check, which avoids the two-server or pairs plans. Probe it |
| Name vs world | Vision: DOORS OF DOOM, a game show. Spectacle: Titan Peak, a volcano | **Both:** the show is the name, the volcano is the set, Volt is the host |
| Time trial vs party | Vision: party heat default. Gamification: class race with mass start | Same build: a synced start is both the heat and MASS START. Build it once |

## 10. Roadmap

### Now: week 1, zero credits, mostly S effort
1. Doors re-painted, lintel letters and lights added, **seen in play**.
2. HUD tile colours fixed and sampled; letters at 40 px.
3. Lighting locked from a 4-frame comparison; dark tier floors.
4. Copy pass: picker, "station" everywhere, one arena instruction, "Today's record", the medal rule shown, "RACE AGAIN".
5. Feed: misses private, strip shows the rival.
6. Recap card in place of "Correct! <old>".
7. Retry spot by the doors, shorter holds, non-lethal Spike, letter reshuffle on retry.
8. Teleport to the podium when the titan falls.
9. Station 1 as the tutorial.
10. **Gates before anything bigger:**
    - 2 real players in one session;
    - one human run timed;
    - island memory read once;
    - persistence survives a rejoin on a private version. Epic says published islands keep data and private links keep it until a new
      code is minted; the limit is 256 KB per player.
11. Rename: no "Fortnite" in the title, HUD tag or welcome line.
12. **Class pilot path = an unlisted publish.**
    - Steps: rename, logo, the three thumbnails (landscape 1920x1080, portrait 1440x1920, logo 1440x608), the IARC questionnaire, then
      moderation.
    - Set `maxPlayers` to about 30 (it takes 1-100; memory is a fixed 100,000-unit bar).
    - Then test that a handful of kid accounts land on one server from the code.

### Next: weeks 2-3
- The party heat (synced start, places, auto-requeue). Test with 4-8 kids.
- Right-answer pillar of light and boost trail.
- Shield and Strike.
- Redemption at the boss.
- Medal v2 and the brag card.
- Arena pads in one row, titan scaled up.
- Host controls with the misconception radar.
- Accolades.
- Volcano on the horizon (probe first).

### Later
- Trap Dex and Daily Mix.
- The Titan Peak biome pass and the door arch kit.
- Mascot Volt.
- Podium ceremony with hologram and crowd.
- Custom music.
- Team relay.
- Grade 7-8 cartridges: the real long-loop fuel, since grade 7 has 1 skill and grade 8 has none.

## 11. Credits and deadlines

| Item | When | Detail |
|---|---|---|
| Meshy **156 monthly credits** | reset **tonight 19:37 PT** (2026-10-14T02:37Z) | Use-it-or-lose-it is assumed, not confirmed. Pivot-proof spends: medal HUD art (36) and the host/mascot (67). The volcano (44) needs the theme decision |
| Mint **7,580 credits** | billing period ends **2026-10-21** | Rollover unknown; write tools are gated (Aaron authorises in his session). Learn the audio price with one tiny job, then music and SFX |
| **Release assets** | **from 2026-10-22** | Landscape and portrait thumbnails plus a logo are mandatory for any release submitted for review, **including the unlisted publish a class needs**. Private versions are not affected |

## 12. Unverified (shakiest first)

- **Timings.** No human run has ever been timed. Every run, heat and class-plan duration here is an estimate.
- **Multiplayer.** Two or more real players have never played: strip, feed, shared guards, items on teammates, strikes.
- **Persistence** is documented by Epic (published keeps it, 256 KB per player) but has never been seen surviving a session here.
- **Class access details.** The default rating limit on a new under-13 account; whether ~28 kids land on one server from one unlisted
  code; how long moderation takes; the class device setup (one Xbox or a device each).
- **Island memory** is unmeasured. Epic documents no player-count tiers for the 100,000-unit budget, but more players means more
  runtime load: measure it before raising `maxPlayers`.
- **Probe-dependent ideas.** Volcano at 2 km draw distance, `Powerup_VFX` aura, `PlayerReference` hologram, `CrowdVolume`,
  `CameraFocus`, partial post-process strength, door sprint-bash, `hud_controller_device` hiding Fortnite panels.
- **Why the door paint was lost** is not diagnosed. Re-applying it may need the "runtime material instance" workaround, as the door frame did.
- The UX reviewer's "red barrier reads as blocked" and "A/B pads off-screen" are readings of frames, not observed kid reactions.

## Files

- `frames/`: 12 key frames (1280x720).
  - `01` first screen;
  - `02` hallway at night with the misleading explanation;
  - `02b` the explanation sharing numbers with the new question's tiles;
  - `03` doors unlabelled by day;
  - `04` door B close-up;
  - `05` freeze;
  - `06` mud;
  - `07` arena entry;
  - `08` cannons at night;
  - `09` arena by day;
  - `10` finish board;
  - `11` still in the arena after the board hides.
- `sources/`: the nine agent reports (`class_access.md` included) plus the device catalog (384 placeable devices).
  - `live_observations.md` names frames by their capture names (e.g. `burst/wrong_22`); those originals stay in the session scratchpad.
