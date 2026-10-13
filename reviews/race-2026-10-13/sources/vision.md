# Vision: what race mode has to BE to become a blockbuster

Creative-director review, 2026-10-13. Lens: format, identity, positioning. The parallel UX, gamification and FX reviews
cover the detail; this file sets the direction they serve. Evidence: `market_research.md`, `live_observations.md` + frames,
`race_facts.md`, `fx_inventory.md`, repo HEAD 0a4cc45 (GOALS G6-G8, BOSS_MODE.md, PROTOCOL §4a). Read-only: nothing edited,
nothing launched, no credits spent.

---

## 0. North star (one screen)

**What it becomes:** a 16-player game-show gauntlet. You sprint at a wall of four doors, and your answer is the key. Pick the right door and
you smash through. Pick the wrong one and the show gets you. In the final round the whole lobby lasers a 12 m lava titan.

**Three pillars.** Every feature serves at least one; cut what serves none.
1. **Brains are the power.** Math fuels boost, zaps and cannon shots. It is never a toll you pay to get to the game.
2. **Every door is a show.** Right and wrong are visible spectacle. Failure is funny, never shaming.
3. **One clock, one titan, one crown.** Everyone starts together, finishes together and gets ranked together.

**Three tests** for every build decision:
- *Spectator test:* can a player 20 m away tell what just happened to you (right, wrong, zapped, hit) without reading?
- *Projector test:* is it readable and funny from the back row of a classroom watching a TV?
- *Five-second test:* does a wrong door cost 5 s or less of lost control, and does it get a laugh?

**The fact that frees the FX budget:** each player gets their own question and their own letter shuffle, so a classmate's door
tells you nothing about yours. That makes global VFX at the doors (bursts, gags, launches) safe. The "global VFX" constraint
only rules out answer signage. It does not rule out spectacle.

---

## 1. Honest verdict

**No, it is not a blockbuster today, and it is not close. Right now it is a well-built solo time trial with a quiz gate, wearing a greybox.** The
market puts both halves of that in the graveyard. On the morning Pillars had 14,300 players, the top quiz island had 21 and the top
educational island had 22. The top runner/timed island had 129.

What it already has that hits are made of:
- **A comic fail state.** Frost, yeet and spikes are the same "fall and restart" pain that kids laugh at in Only Up.
- **One real spectacle.** The lightning-cannon volley on the titan is the best frame in the build.
- **A fast loop.** Two clicks to GO, three-second mental-math questions (thanks to §4a), and a streak announcer with Fortnite energy.
- **An engineering base most creators never reach.** Headless playtests, 8,700+ tests, and a proven Meshy and Niagara pipeline.

What it lacks is everything that makes a kid tell a friend:
- **An identity.** The title is "Fortnite Math", and the set is pastel cubes under a random day/night cycle. In play the four doors look identical, so the
  one thing the core loop depends on is broken.
- **A shared moment.** Each kid runs alone on their own clock, and no two humans have ever played it together.
- **Anything you can do to your friends.**
- **A reason to come back tomorrow.**
- **A clip or a thumbnail.**

In a classroom it would already beat a Kahoot for fifteen minutes. On Discover, as it stands, it gets about 20 players. **What's missing is format
and identity, not polish.**

**Keep, non-negotiable** (these work):
- §4a concept-over-arithmetic content
- The per-player shuffle
- The streak to speed-boost link and its announcer ladder
- The six penalties as gags
- The titan, cannons and Niagara rig
- Health refill on every station
- The door backstop
- Join-to-GO with no lobby wait
- HUD tiles in the door colours

---

## 2. Positioning

### Who it is for: classroom first, built as a party game, so the class build IS the Discover build
- **Why the classroom comes first.** Aaron has what no other creator has: 100+ real 11-14 year olds every day.
  - The build has never been played by two humans and never timed with one, and the Xbox build has never been seen running. The class is the playtest lab.
  - The class is also the seed of the only realistic organic channel. Kids who loved it at school play it at home in parties, and party play is a metric Discover ranks on.
- **Why not "an ed tool".** The class tools kids love (Blooket, Gimkit) win on the game *between* the questions. If the island is not fun with
  the math swapped for trivia, no amount of class time will save it on Discover.
- **The gate to Discover.** Publish publicly only when all four are true:
  1. 4+ kids ask for another heat without being prompted.
  2. The 15-second clip exists, cut from real play.
  3. The rename is done, with portrait and landscape thumbnails and a logo (required for any publish or update from 2026-10-22).
  4. Island memory has been measured on the full build.
- **Dependency to check first:** can students' own accounts join a private version code, or does the class need a Creator Portal playtest group
  (limits unknown) or a public publish? Try it with one student account before planning the rollout.

### Discover genre: **Party & Mini Games**
- **Why it fits:** the round loop ("a heat ends, someone wins, everyone requeues") is what players in this genre expect. Party players accept a brain gate,
  because trivia rounds are a party staple. Party play counts toward ranking.
- **Not Deathrun & Platformer:** those rows are full of clones, and their movement-focused players bounce at the first question.
- **Not Sport & Racing:** that genre means driving roleplay.
- **Never tag it "educational" or "quiz":** those rows are dead, and the words read as kid-targeted.

### Name (no "Fortnite"; no "Math" at the front)
| # | Name | Why | Check before committing |
|---|---|---|---|
| 1 | **DOORS OF DOOM** (recommended) | Names the signature loop. Easy for a kid to say. "Doom" is comic and E10+-safe. The logo can be four lettered doors | Search fortnite.gg for "Doors" islands (clones of Roblox's DOORS horror game). Discover shows "highly similar" titles less |
| 2 | BIG BRAIN GAUNTLET | "Big brain" is kid slang for a smart play. It says brains without saying school | Less visual; "Gauntlet" is generic in search |
| 3 | WRONG DOOR! | The scream on every clip; comedy first | Frames failure; doesn't carry the titan |

Remove "Fortnite" everywhere: the title, the thumbnails, the HUD tag, and the announcer's "Welcome to Fortnite Math!" line (Rules 3.1.1 and 3.1.3, plus the
thumbnail policy). Kokoro re-records it for free. Keep "Math" off the front: it files the island in the dead quiz row in a kid's head before they have seen a
door. The description must still say "mental-math questions" (Rule 1.13 requires accurate representation).

### The pitch a kid gives a friend
> "There's this game show where you sprint at four doors. Pick wrong and the door launches you across the room. At the end everybody
> lasers a giant lava titan."

### How the math becomes the power source
- **Words.** The question is the door's lock, and the answer is the key. Game copy uses CRACK THE DOOR, BRAIN POWER and TRAP. It never uses quiz, test,
  grade, homework, lesson, learn or student.
- **Every right door pays out power you can feel.**
  - Speed boost (already built).
  - A charge you can spend: zap the leader, or buy a shield (Bet 3).
  - In the finale, your right answer *is* the cannon shot (already built in the arena).
- **Every wrong door is a named trap built from a classic mistake.**
  - The cartridges already carry the misconception keys ("Worked left to right", "Order matters").
  - "TRAP: LEFT-TO-RIGHT" becomes a gag kids repeat.
  - It is also the most useful teacher data the island can give without a dashboard. The finish board shows "Your trap: LEFT-TO-RIGHT x3", and the
    17% of wrong choices that only say "Check your arithmetic." need real trap names.
- **Keep §4a.** Three-second questions are what turn running and thinking into one skill. Heavier arithmetic would kill the game feel.

### Rule 1.15, head-on
- **The rule.** Epic "doesn't accept content that targets children under 13 as its primary audience", and promo must suit ESRB E10+.
- **The problem.** Grades 6-8 are ages 11-14, and the first screen says so today ("GRADE 6", "GRADE 7"). That is a targeting signal Epic can read.
- **The honest position.** Mental-math game shows are all-ages entertainment; adults watch "Are You Smarter Than a 5th Grader". The island is for
  "anyone who thinks they're quick". Classroom use is how some players use it, not who it is marketed to.
- **Do:**
  - Replace the grade buttons with leagues ROOKIE / PRO / LEGEND. A teacher guide outside the island maps them to grades 6/7/8.
  - Keep the skills named by topic.
  - Use neutral metadata: none of the words kids, students, grade, class, homework, learn or educational.
  - Use a teen-Fortnite art direction (neon game show, lava titan), not pastel or preschool-cartoon.
  - Cut a General Audience trailer.
- **Don't:** plan around Rule 1.17. Educational exceptions are discretionary, with no published process. It is the fallback if Epic flags the island,
  not the strategy.
- **Classroom friction to test early:** under-13 "cabined" accounts may need a parent's setup before a pilot. (That comes from a 2022 source; re-check.)

---

## 3. Core fantasy and signature mechanic

**Fantasy:** you are a contestant on the most dangerous game show in Fortnite.

**Signature mechanic, in one breath:** sprint at four lettered doors and let your answer pick one. Right, and you smash through in a burst of light. Wrong,
and the door's trap gets you in front of everyone. The lobby's right answers fire the cannons that bring down the titan.

**Heritage:** the Takeshi's Castle / Wipeout doors you run at, where some are solid and you bounce off into the mud. Kids already find that format funny, and
no Fortnite island owns it.

**The identity is the comedy plus the spectacle (the clip-able parts), not the questions:**
- **The doors.** Big game-show doors, lit in their letter colour (A white, B blue, C green, D orange, matching the HUD tiles).
  - The stock door frame ignores material overrides, so the colour has to come from lights or a frame prop.
  - First fix: in play today the four doors look identical. The paint was lost in a later rebuild (`live_observations.md`, "Doors").
- **The wrong door.** The six penalties become the show's traps: world-visible slapstick that passes the spectator test.
  - Examples: the door bounces you back, the floor drops you into slime, the ice cube, the yeet.
  - The target gag is "the door punches you". It needs a glove (Meshy prop on an Animated Mesh device or a movable prop); feasibility is **unverified**.
- **The right door.** A global smash-through burst. Today a right answer leaves no trace in the world.
- **The host.** A robot game-show host, built as a Meshy animated character on the titan pipeline and voiced by the existing announcer.
  - He gives the show a face for the thumbnail and catchphrases kids quote ("WRONG DOOR!").
  - He lives in the green room, over the door walls and on the podium.
- **The titan.** The show's undefeated champion: one titan, 12 m tall, in the colosseum.
- **The course story.** The tier colours already run cool to hot (green, blue, purple, orange, red). Make that a descent into the titan's lair:
  studio, then ice, then crystal, then lava, then the arena. It needs no text.

**Solo time trial or party race? Both, with the party race as the front door.**
- **HEAT (the default).** Up to 16 players on one clock:
  - Green room, then a 3-2-1 for everyone.
  - Live places on the way.
  - Titan finale, podium, requeue.
  - This is the Pillars / Fall Guys shape the market rewards, and the shape a class needs.
- **TIME TRIAL.** Today's solo 10-station run, kept for record hunters and practice. It is already built.
- **Why per-player questions make the party better.** Everyone runs the same doors with different answers, so half the lobby goes through B while
  the other half goes through C. Every door wall becomes a crowd scene, and none of it gives an answer away.

---

## 4. The 15-second clip and the key art

### Clip, shot by shot (cut for 9:16 and 16:9; no guns on screen, because the hero carousel needs a General Audience trailer)
| t (s) | Shot | Sound |
|---|---|---|
| 0.0-2.0 | Low tracking shot behind 6 avatars sprinting down a neon hallway at a lit wall of doors A-D. The slate shows "6 + 2² = ?" in big type | Host: "Pick a door!" |
| 2.0-4.0 | The hero hits door B. It bursts open in gold light and number confetti, with speed lines as he exits | "TRIPLE!" |
| 4.0-7.0 | Beside him, his friend takes C. The door launches him back down the hall in a high arc, with 0.5 s of slow motion at the top. Feed: "got YEETED" | Scream, then "WRONG DOOR!" |
| 7.0-11.0 | Hard cut to the colosseum. The 12 m Magma Titan roars over 6 kids on four lit pads. A right pad: both mega cannons fire lightning, and the titan staggers | Cannon crackle, "DIRECT HIT! One more!" |
| 11.0-14.0 | The final hit. The titan topples, fireworks go up, and the hero stands on the podium wearing the crown | "BOSS DOWN!", crowd |
| 14.0-15.0 | Logo DOORS OF DOOM with four door icons, plus the island code | Sting |

### Thumbnails and key art (portrait, landscape, art-only versions and a transparent logo are all required to publish or update from 2026-10-22)
- **Landscape.**
  - Left third: an avatar mid-leap through a bursting gold door.
  - Right two thirds: the titan, with the lightning cannons firing across the frame.
  - Bottom left: a second avatar flying out of a red door with motion lines.
  - Top centre: the logo, with the O's drawn as lettered doors.
- **Portrait (Top 10 row).** The titan fills the top half, the door smash fills the bottom half, and the logo sits between them.
- **Rules.**
  - Epic-owned outfits only.
  - No Fortnite logo or name, no "XP", no V-Bucks.
  - Everything shown must exist in the game (Rule 1.13).
  - Minors' display names must never be visible. Film with names hidden in the feed (class mode) or with alt accounts.
- **How to make it.** Composite in-game captures taken under locked lighting. Use Meshy image generation (about 9 credits a frame) only for the logo and the
  paintover.

### What must exist in the game before either can be filmed
1. Doors painted and lit, and seen that way in play (the frames show four identical white doors today).
2. Locked time of day plus a night "studio" lighting look. Today `timeOfDayOverride` is NoOverride: the night run is flat blue and the dawn floor is white glare.
3. The right-door burst (Niagara, on the proven `build_fx.py` pipeline, 0 credits).
4. One wrong-door gag big enough to read from 20 m away.
5. The colosseum finale with 6+ players on the pads.
   - The 12 m titan, cannons and Niagara are already built there.
   - The race finale's 6.3 m titan in a 30 m hall reads small (frame 17), so it won't carry the shot.
6. A crown and podium moment. Today the finish is a HUD wall of 8 text lines, shown 55-60 m away from the podium.
7. A way to shoot it: 4-8 real players (the class, names hidden) plus a camera client.
   - Creative replay support is **unverified**.
   - The cinematic sequence device is documented but untried.

---

## 5. Structure

### Modes
| Mode | Players | Length | What it is | Status |
|---|---|---|---|---|
| **HEAT** (default) | 1-16 | ~3 min (estimate: no human run has ever been timed) | Green room, then 5 stations (one per tier), then the titan (hits scale with the players present), then podium and requeue. Three heats make one show, with a crown for the points leader | New: synced start, places, requeue |
| TIME TRIAL | any | 3-4 min (estimate) | Today's 10 stations plus finale, medals, personal bests per skill | Built |
| TITAN RAID | 1-16 co-op | ~5 min | Today's BOSS BATTLE: 5 levels, 16 hits, waves, chests | Built |
| CLASS (host layer) | any | per heat | The host picks the skill or league for the lobby, a fixed heat count, names hidden in the feed, and a projector camera (fixed-camera device: documented, untried) | New |

### Heat flow
- **0:00, green room in the colosseum stands.**
  - Late joiners wait here too and watch the live titan fight, so the finale gets a crowd.
  - A 20-second countdown runs, with the league pick on the HUD.
  - A default is pre-selected, so doing nothing still starts the heat.
- **0:20, start.** Everyone gets the 3-2-1 together at station 1.
- **About 2:00, final call.** When the first player reaches the colosseum, everyone else gets a 45-second FINAL CALL (Fall Guys-style qualification). The
  titan's hit count scales with the players present.
- **Titan down or time up, podium.**
  - Places, plus two awards that reward behaviour and not just speed: MVP (most cannon hits) and COMEBACK (most places gained).
  - Requeue after 10 seconds, with no walk to a podium button.

### Cut and merge
- **Merge the two titans into one titan in one colosseum.**
  - The heat finale runs in the colosseum: the 12 m titan, the stands and the cannons are the money shot.
  - Retire the 30 m race-arena hall.
  - TITAN RAID becomes the colosseum's long mode, entered from the green room, instead of the first button on the first screen.
  - Engineering question: routing race stage 11 to the colosseum pads. The two modes cannot share the colosseum at the same moment; a lobby-wide mode
    solves that.
- **10 stations become 5 per heat** (one per tier). All 10 stay in TIME TRIAL.
- **The first screen changes.**
  - No grade step, and no BOSS BATTLE button sitting above the race.
  - The default heat starts on its own; the league is picked inside the green room.
  - Today's first screen is a frozen player in a menu with no default.
- **Guards.** My recommendation is fewer of them, themed as "security bots". In heats, the threats are the show's traps, and weapons become something you grab
  for the finale. This is Aaron's call; he liked the guards and asked for the weapon ladder.
  - The case against them: they are generic Fortnite filler that fights the identity, and they keep the trailer from a General Audience rating.
  - A wrong door at station 10 today means re-walking past five rocket-launcher guards. That fails the five-second test.
  - Keep the guard ladder in TIME TRIAL and TITAN RAID.
- **Text.**
  - The 8-line finish board becomes a podium moment.
  - The right-answer explanation becomes "HOW YOU CRACKED IT", shown after a beat. The arena's delayed "Last one:" line already gets this right; the 10
    stations still show the previous answer's working under the new question.

### A 30-minute class
This assumes kids on their own devices, at most 16 per lobby. A 30-kid class means two lobbies, run as two "houses".

| Minutes | What happens |
|---|---|
| 0-4 | Code on the board, green room, the teacher sets the skill as host. A warm-up heat on ROOKIE with no guards teaches E-to-open by doing it |
| 4-16 | Three heats (about 4 min each including requeue). House points go on the whiteboard |
| 16-24 | TITAN RAID with the whole lobby, co-op: a finale every kid reaches |
| 24-28 | Crown and podium. Each kid reads their first-try accuracy and "your trap" off the finish board |
| 28-30 | The teacher writes the trap of the day (the misconception most kids called out) on the whiteboard |

**Variant for one Xbox on a projector (likelier in a rural room): the hot seat.**
- One or two kids run each heat; whether split-screen works on Creative islands is **unverified**.
- The class shouts door letters, and rows score as teams.
- About 8 runners get a turn in 30 minutes.
- The projector test matters most in this setup.

### Update cadence (the hit pattern: "Updated" badges matter, and v1 islands that are never updated fade)
- **A new titan every 4 weeks.** It uses the proven `import_boss.py` pipeline at about 62 Meshy credits each, so 1,468 credits pays for a year of them with
  plenty left over.
- **A new trap each season, and a season reset of the boards.**
- **One island forever.** Rule 1.9.1 penalises duplicate islands.

---

## 6. Three bold bets, and three ways to sink it

### Bet 1: turn the time trial into a 16-player party race (HEAT)
- **Thesis.** Time-trial islands are tiny (the top one had 129 players). Round-based party games are the kid hit: Pillars is a 12-player round with
  "a random item every 6 s" and saved wins. Discover ranks social play, and a class needs one clock.
- **Build.** Green room, synced 3-2-1, live places, the FINAL CALL timer, a podium with two awards, auto-requeue, and a heat of 5 stations plus the titan.
- **Cheapest test first** (no credits, about 2 days).
  - On today's art, add a synced start and auto-requeue for everyone in the session.
  - Play three heats with 4+ real kids.
  - Measure: whether they ask for "again" unprompted, the real heat time, and laughs per heat.
  - This is also the first test of the never-tested multiplayer: strip order, shared guards, items used on teammates.
- **Kill signal.** If kids drift off after one heat even with friends present, the problem is the loop, not the format. Fix doors and feedback first.

### Bet 2: DOORS OF DOOM, with the door as the star of a game show
- **Thesis.** The comedy (the wrong door) and the spectacle (the titan) are the only parts worth clipping. A game-show wrapper with a host turns both
  into an identity no Fortnite island owns, and makes the math the show's mechanic instead of the homework.
- **Build.**
  - Lit, lettered show doors.
  - A smash-through burst on the right door.
  - Each wrong door a named misconception trap with a world-visible gag.
  - The robot host.
  - Lighting locked to a night studio look so the VFX pop.
- **Cheapest test first** (0 credits, about 2 days).
  - Fix the door paint, add one Niagara burst at the right door, and relabel the wrong-door feedback "TRAP: ...".
  - Film 15 seconds and show it to 10 students: "Would you send this to a friend?"
  - Only then spend credits: about 62 Meshy for the host, about 39 for one gag prop.
- **Kill signal.** Fewer than half say yes. Rework the gag before buying any art.

### Bet 3: BRAIN POWER, one currency that makes math the power source
- **Thesis.** Blooket and Gimkit win on the economy between questions. Every long-lived Fortnite hit shows a persistent number going up. One currency
  does both, and it gives kids something to trash-talk about.
- **Build.**
  - Every first-try right door earns +1 BRAIN.
  - Spend it during the run on ZAP THE LEADER (a 2 s Freeze or Dizzy from the existing penalty code; the Mario Kart blue shell) or SHIELD (absorbs one
    trap).
  - In the finale, BRAIN is cannon ammo.
  - Lifetime BRAIN persists and sets a meme rank (SMOL BRAIN, BIG BRAIN, GALAXY BRAIN), shown in the feed and on the podium.
  - Ranks unlock door-burst colours. Global VFX helps here: everyone sees your burst.
  - All of it is earned and free. Nothing random is ever paid for (Rule 1.11).
- **Cheapest test first** (0 credits, about 1 day).
  - A streak of 3 auto-zaps the current leader with a 2 s Freeze, plus a feed line "<name> ZAPPED the leader!".
  - Persist one number (lifetime right answers) and print the rank on the finish board.
  - With 4+ kids, watch whether they go after the leader, and whether the leader still usually wins (they should, mostly).
- **Caveat.** Whether persistence survives between sessions on a private or published version is **unverified**; every UEFN test session starts empty.
  Prove it on the private version first.

### Three ways to sink it
1. **Publishing it as a quiz.**
   - "Fortnite Math", grade buttons and a greybox land it in the 20-player quiz row and expose it to brand and Rule 1.15 trouble.
   - Discover's two-week test window would be spent on a build nobody wants to film.
   - Islands that are never updated fade: Hard Parkour v1, the 2024 Fortnite Trivia island.
2. **Pain instead of comedy.**
   - Freeze holds you 5 s without turning.
   - A math slip means a 25 m re-walk past five rocket-launcher guards.
   - The feed names you publicly, the screen fills with walls of text, and the feedback says "Check your arithmetic."
   - If a wrong answer feels like being graded at gunpoint, kids bounce and parents complain.
   - Rule: 5 s or less, always a laugh, and the leader gets gagged too.
3. **Building blind.**
   - The risk: adding modes, art and credits before two humans have played together, before one human run is timed, and before the Xbox build is seen.
   - Island memory has never been measured, with the course, about 670 colosseum actors and one titan copy per animation clip already on the island.
   - The next Meshy hero could be the asset that blocks publishing. Measure first, then build.

---

## 7. Blockbuster checklist (0-5; today vs target)

| # | Criterion | Today | Evidence | Target |
|---|---|---|---|---|
| 1 | One-breath hook: a name and pitch a kid repeats | 1 | "Fortnite Math"; no logo, mascot or title card | 5 |
| 2 | First 10 seconds: fun before any menu | 1 | Frozen in a picker with no default; BOSS BATTLE sits above the grades; two announcer lines overlap at join | 4 |
| 3 | Core affordance readable (door = answer) | 1 | The four doors look identical in play; left-to-right order is the only mapping | 5 |
| 4 | Success is a world event | 1 | A 1.5 s HUD flash and the barrier vanishing; the streak line and announcer are good | 5 |
| 5 | Failure is funny and short | 3 | Frost, yeet and spike read well; Freeze is 5 s with no turning; 25 m re-walk past live guards; "Check your arithmetic." on 17% of wrong choices | 5 |
| 6 | Spectacle and clip moment | 3 | Cannon volley is strong; the race titan is 6.3 m and reads small; no right-door FX | 5 |
| 7 | Identity: theme, set, lighting | 1 | Greybox cubes, flat colours, uncontrolled day/night | 4 |
| 8 | Social play: things you do to and with friends | 1 | Feed and strip only; two humans have never played together; items on teammates unverified | 5 |
| 9 | Round loop with instant requeue | 1 | No auto-restart; podium 55-60 m away; a kid who never presses E idles forever | 5 |
| 10 | A number that goes up across sessions | 1 | Best time per skill; persistence between sessions unverified | 4 |
| 11 | Comeback and fairness across ability | 1 | No catch-up; medals are accuracy only; the leader runs away | 4 |
| 12 | Math is the power, concept first | 4 | §4a three-second questions; streak = boost; misconception keys already in the data | 5 |
| 13 | Content runway for grades 6-8 | 2 | 11 grade-6 skills, 1 grade-7, 0 grade-8 (`cartridge-library` skill exists) | 4 |
| 14 | Discover-ready: name, genre, thumbnails, logo, GA trailer, 1.15-safe copy | 0 | None of these exist; grade labels on screen one | 5 |
| 15 | Classroom-ready: Xbox build seen, 30-minute flow, host controls, memory measured | 1 | The private version predates the boss work; Xbox never seen; memory unmeasured | 5 |
| | **Total** | **22 / 75** | | **70 / 75** |

---

## 8. Order of work (one teacher + Claude, about 4 weeks)

1. **Week 1, fix the ground floor (no credits).**
   - Door paint seen in play.
   - Lighting locked.
   - The rename everywhere, including the announcer line.
   - 2+ real players in one session.
   - One human run timed.
   - The Xbox private version seen running.
   - Island memory read once.
   - Check whether a student account can join the private code.
2. **Week 2, Bet 1.** Prototype heats on today's art, then test with 4-8 kids.
3. **Week 3, Bet 2.**
   - Door burst and one world-visible gag.
   - The host (credits).
   - The titan finale in the colosseum.
   - Film the clip.
4. **Week 4, Bet 3 plus the Discover kit.**
   - Zap the leader and the BRAIN rank.
   - Thumbnails, logo and trailer.
   - Publish once the four-part gate in section 2 is met.
5. **Content, in parallel.** Grade 7 and 8 libraries (`cartridge-library`) before the class rollout reaches the 7th- and 8th-grade periods.

**Credit timing.**
- Mint's 7,580 credits may lapse when its billing period ends on 2026-10-21; rollover is **unverified**.
- If they will lapse, the safest use is assets that survive any pivot: the host, the crown or trophy, and game-show music and crowd audio. Mint's audio
  price is unpublished, so probe one cheap job first.
- Meshy's 156 monthly credits reset 2026-10-14.

---

## 9. Unverified (the shakiest assumptions first)
- **Run time.** No human run has ever been timed. Every heat length here is an estimate: about 813 m of path at an assumed 6 m/s.
- **Class access.** Whether students' accounts can join a private version code, the classroom device setup (one Xbox vs one device each), whether
  split-screen works on Creative islands, and whether a 30-kid class can split cleanly into two 16-player lobbies.
- **Persistence.** Whether Verse persistence carries over between sessions on private or published versions (Bet 3 depends on it).
- **Items on teammates.** Whether Boogie Bombs and Shockwaves affect Cooperative-team players (relevant to any item-based sabotage).
- **Title collision.** "Doors of Doom" has not been checked against live island titles.
- **Rule 1.15.** How Epic applies it to all-ages math framing is undocumented.
- **The glove gag.** The "door punches you" prop is a feasibility guess. A launch gag on the air vent is proven.
- **Memory.** The island memory budget has never been measured.
- **Filming.** Creative replay or camera support for the trailer is unchecked.
- **Projector camera.** The fixed-camera device is documented but untried here.
