# RACE mode: spectacle, FX, lighting, world identity, assets, audio (art director / VFX lead review, 2026-10-13)

Read-only review. Sources: the frames in `frames/` (looked at: 01, 04, 09, 10, 11, 12, 14, 17, now_client, burst/wrong_13/22/50/71,
burst/door_02, editor_doors_s1), `fx_inventory.md`, `device_catalog.tsv`, `island_props.json`, `race_facts.md`, `market_research.md` §3.2,
`BOSS_MODE.md` §15-16, `tools/build_fx.py`, `console/AUDIO.md`, `maps/starter/LAYOUT.md`, and Meshy's animation library (free lookup).
Nothing edited, nothing launched, no credits spent.

Key: **P** = proven in this project. **Probe** = documented or in the catalog but never tried here (the probe is named). Wow 1-5.
Effort: S = under 2 h build + one playtest, M = half a day, L = 1-2 days, XL = several days.

---

## 0. Verdict from the frames

**What works (keep and reuse the look)**
- The cannon volley (12_cannons) is the one frame that looks like a real game: two cyan lightning lasers into a big monster, framed by
  chunky floating 3D letters. Even washed blue at night, it reads.
- **The floating 3D Alphabet letters are the best design element in the race.** They are big, coloured and chunky, and they read at
  25 m. They should be the door language everywhere (see the doors row).
- Frost penalty (wrong_13): the ice cube plus the white-out is a clean comic gag.
- Torches in daylight (wrong_22) add warmth. Station 6's icicles are the only hallway that feels like a place.

**What does not**
1. **No art direction holds because the lighting is random.** `timeOfDayOverride` = NoOverride. At night (most frames) everything
   reads blue-cyan, the five tier colours disappear, the orange titan reads blue, and the flat walls show a checker. At dawn
   (now_client, wrong_22) the white engine-cube floor turns into glare. Mud's sepia (wrong_71) blows the screen out to orange
   because the white floor is half the frame.
2. **The doors are identical** (editor_doors_s1, door_02): oil-rig doors, white frames, pale-blue leaves, no letter, no colour. The
   door dress from fb38d7d is no longer applied (`overrideMaterials: [null]`). This is P0 and costs nothing to fix.
3. **The world is a greybox with no identity.** Flat painted cubes, a white floor and pastel floating digits. Nothing says where you
   are or where you are going, and the titan is never foreshadowed.
4. **A right answer does nothing in the world.** The only feedback is the HUD and audio. Nothing in the world reacts, and a classmate
   sees nothing.
5. **The finish is text.** The medal is a word on a translucent board, and the podium and ALL-TIME screen are 55-60 m away and tiny in
   frame (17).

**Correction to the live notes.** "Race cannons log 0 muzzle vfx" is not a bug. Since BOSS_MODE §15g that counter counts the old VFX
Spawner muzzle devices, which are now zero by design. The Niagara `NS_fnm_muzzle` fires on every shot in both arenas, and §16 saw the
muzzle flash in the race finale.

**Art-direction rules I would lock now**
- **Colour story.** CYAN/white = the player, right answers and the cannons. MAGMA orange/red = the titan and danger. GOLD = rewards
  (medal, streak, finish). Each tier keeps its colour (green, blue, purple, orange, red) on walls and trim. The four letter colours
  (A white, B blue, C green, D orange) are reserved for doors and pads only.
- **Value rule.** Floors are mid-dark and walls mid. Only FX, letters and lights are bright. Flat Kd colours render lighter than
  their values (`bm_stone` needed 0.09), so aim dark.
- **No world FX on a door face before an answer.** Questions and letter shuffles are per player, so a global burst *behind* the wall,
  after a right answer, reveals nothing to a neighbour. But a door that lights up invites copying and the "she cheated" feeling. FX
  happen in the vestibule and go up into the sky, never on the door face.

---

## 1. Per-beat spectacle plan

### 1a. Beat table

| Beat | Today | Spectacle to add | Built with | Status | Wow | Effort |
|---|---|---|---|---|---|---|
| **Title / join** | Menu over a pastel hall, Fortnite's GAME MODE panel, clock at 0:00.0 | **Title vista.** The picking player stands on a balcony at station 1's start gate (already in stasis). In frame: the volcano and the giant titan on the skyline, and a logo card on the HUD | `texture_block` logo (nano-banana-pro), start-gate arch (Meshy), volcano (§3) | HUD texture P; vista depends on the volcano probe | 4 | M |
| | | Mascot "Volt" waves at the gate (idle + cheer loop) | Meshy rigged character on Animated Mesh (titan pattern) | P (pattern) | 3 | M |
| **Countdown / GO** | HUD 3-2-1, stock ticks, frozen player | Wire the imported, unused announcer `countdown1..3` voice lines. At GO: a cyan shock-ring burst at the player's feet and a 0.5 s per-player white flash | `NS_fnm_go` (new; OmnidirectionalBurst ring recipe), `PP_ActionLines` blend 0.3/0.5 | Voice P (already imported); Niagara recipe P; ActionLines probe (one screenshot) | 3 | S |
| **Hallway ambience** | Torches, floating digits, silence | Tier biome kit (§3): wall and floor textures, gallery dressing, one continuous VFX Spawner per tier (T1 Leaves + Firefly Spawner device, T2 Waterfall + LightFog over the wall tops, T3 Snow, T4 Ash + Embers, T5 Embers + Small_Fire), positional ambience loop | VFX Spawner V2 (P), Firefly Spawner (probe), audio player spatial (probe) | VFX P; spatial audio probe | 4 | M |
| | | Replace the 60 pastel sky digits with the **volcano on the horizon**. Every hallway faces +Y and the arena is at +Y, so a volcano at y ≈ +1.5-2.5 km is above the door wall in every station, grows as you climb, and has the titan on its rim | Meshy static hero ×1 (~44); titan SK reused at ~scale 40 on one Animated Mesh | Probe: draw/stream distance (`bIsSpatiallyLoaded` false), culling at 2 km, scale-40 Animated Mesh | **5** | M |
| **Door moment (doors themselves)** | Four identical oil-rig doors | (1) Re-run `build_course.py --doors-only` (P0). (2) A **3D Alphabet letter** (scale ~1.2, letter colour, `bNoCollision`) on each lintel, the same props as the arena letters. (3) A letter-colour Customizable Light (size 30-40 %) inside each arch, always on. (4) Later, a Meshy **portal arch** per tier around each door | Alphabet props + PointLight (P); door dress (editor P, play unseen); Meshy arch + retexture ×4 | Letters/lights P; frame check needed so lintel letters sit below the slate's bottom edge (~375 px) from the 4.5 m landing | 4 | S (1-3), M (4) |
| **Right answer** | HUD check, chime; barrier vanishes | **Gate burst**: when the barrier opens, a white-gold flash, a vertical shock ring at the barrier plane and 120 velocity-aligned sparks, so the kid runs through it | `NS_fnm_gate_burst` (new; SimpleSpriteBurst + OmnidirectionalBurst ring + VelocityAligned sparks) | Recipe P (impact/muzzle) | 4 | S |
| | | **Pillar of light**: a 40 m gold beam rises from the vestibule into the sky for 1.2 s. Every right answer on the island lights the sky ahead of everyone behind you, so a kid sees the class's progress | `NS_fnm_sky_pillar` (new; StaticBeam vertical, `NS_fnm_laser` glow/core layers retuned gold) | Recipe P; probe: Niagara cull distance at 50-100 m | **5** | S |
| | | Streak ≥ 3: a VFX Spawner Confetti burst in the vestibule (`Restart()`) | VFX Spawner (Burst) | P | 3 | S |
| **Wrong answer: FROZEN** | Ice cube, frost PP, orbit cam | On thaw, an `NS_fnm_ice_shatter` (white-blue shard sparks with gravity, snow puff) and an ice-crack stinger; bigger cube (×1.4) | Niagara (new, P recipe); prop scale P | P | 4 | S |
| **YEET** | Air vent throws them 18 m | Dust-ring poof at the vent, then a dust puff where they land (Verse polls landing, spawns at position) | `NS_fnm_dust_puff` (new) | P recipe; landing detection is Verse | 4 | S |
| **SPIKED** | Spears, kill, Fortnite's "bailed early" line | Dust kick plus a red-white "BONK" spark ring at the spears. (The elimination-feed line is a UX/HUD item for the other reviewers) | `NS_fnm_bonk` (new) | P recipe | 3 | S |
| **STUCK IN MUD** | Sepia that blows out to orange | Darker floor (§2) first. Then a brown `NS_fnm_mud_splat` at the entry, VFX Spawner **Insect_Flies** buzzing on the landing spot for 8 s (global, funny for the others), sepia at reduced strength | Niagara (new), VFX Spawner (P) | Flies P (enum); PP partial-strength = probe | **5** (flies) | S |
| **DIZZY** | Spin + radial blur | Cartoon "stars" ring at head height for the 1.5 s spin (the player is stationary in stasis, so a non-attached system works) | `NS_fnm_stars` (new; ring ShapeLocation + glow blobs; true orbiting = probe: no proven rotate module; sprites are round, no star shape) | Ring P; orbit probe | 4 | S |
| **LIGHTS OUT** | Black HUD block | Two blinking cartoon eyes on the black (HUD texture flipbook via `SetImage`) and a creak | nano-banana eyes ×2 (6) | HUD texture P; `SetImage` swap DOC | 3 | S |
| **Streak / boost** | Orange HUD line, invisible 2x modulator | **Speed lines**: `PP_ActionLines` blended in for the boost (per player, safe) | PostProcess device | Device P; this effect probe (one screenshot) | 4 | S |
| | | **Trail**: during a boost, Verse spawns a tiny burst at the player's position every 0.12 s, so others see a streaker's comet tail. Three baked colours: streak 1-2 cyan, 3-5 gold, 6+ magma "ON FIRE" | `NS_fnm_trail_cyan/_gold/_fire` (new; ~20 particles, 0.6 s life) | P primitives; budget: 16 players × 8 spawns/s ≈ 1.5k particles worst case | **5** | S-M |
| | | **ON FIRE aura** at streak 5+: a glow/outline that actually follows the player (the one "attach" route) | `PID_Device_Powerup_VFX` (`visual_effect_powerup_device`, Pickup(Agent)) | Probe: grant from Verse, duration, look | 5 | S (if it works) |
| **Connectors** | Bare 10 m corridors, chevron plates | Speed hoops: a looping ring of sparks standing over each speed plate. Arches every 10 m for speed perception. Tier dressing at the funnels | `NS_fnm_hoop` (new, looping; spawn/cancel per station like the guards), Meshy arch reused | Ring P; looping cancelables P (coil) | 4 | M |
| | | **Set piece: zipline down into the caldera** (station 7→8 descent) | `PID_Device_Zipline` / `PID_CP_Devices_GrindRail` are **in this project's catalog** (fx_inventory says "not in digest": placement exists, Verse API does not) | Probe: placement, glass lids, gameplay sign-off (UX) | 5 | M |
| **Titan reveal / intro** | Fires 44 m early: stinger, big flash, bar; titan 6.3 m behind the slate | At the arena threshold: a **magma eruption** (`NS_fnm_magma_burst`: orange-white flash, ember fountain, 8 m shock ring) + strike + the titan's **Jump-and-Slam** clip + the existing boss voice "You dare challenge ME?!" (am_onyx, `bm_boss_l1`, already imported) | Niagara (new), Meshy clip 382 (3 cr), VFX Spawner LightningBolt (P), cue reuse | Clip probe (root-motion clips misplayed before: Chest Pound, Knock Down) | **5** | M |
| | | Camera turn to the titan for 1.5 s | `PID_CP_Device_CameraFocus` (in catalog) or `PID_CP_Devices_FixedPoint` | Probe | 5 | S-M |
| | | Arena = the Titan's Forge: magma-red textured walls, Embers + Ash + LightFog VFX Spawners, 2 orange point lights under the platform, per-player `PP_Heatwave` light while in the arena | VFX Spawner, lights, PP (P devices) | Heatwave look probe | 4 | S |
| **Each cannon hit** | Muzzle, lasers, impact, strike, flail; HUD bar flash | Add: a magma spark burst at the titan's chest (orange `NS_fnm_magma_hit`, contrasting the cyan), a VFX Spawner Embers burst, a comic HUD "HIT!" burst texture under the bar | Niagara (new), VFX Spawner, nano-banana HUD art | P recipes | 3 | S |
| **Wrong pad** | Penalty + 2 pistol adds + stomp | Titan roar clip (Zombie Scream 386 / Shouting Angrily 51) + existing `bm_boss_wrong` voice | Meshy clips (3 each) | Clip probe | 3 | S |
| **The kill** | Fall clip, DEFEATED bar, 4 stacked stingers | **Titan death**: 5× strike (the boss-mode nuke recipe), `NS_fnm_titan_death` (15 m shock ring, magma fountain, 3 s ember rain), FireworksLarge ×2, per-player white flash, then a gold light beam opens the gate. HUD "TITAN DOWN!" banner art | Niagara (new), VFX Spawner (P), `color_block` flash (P), nano-banana banner | P recipes | **5** | M |
| | | Kill cam: 2.5 s orbit around the falling titan for everyone in the arena | Orbit device (P, but it orbits the player); a titan-centred view = FixedPoint/CameraFocus probe | Probe | 5 | M |
| **Finish + podium ceremony** | Board in the arena; podium 55-60 m away | Gate → **golden portal** → the kid lands on the podium in the Hall of Champions (gold-temple dressing). Confetti cannon + FireworksLarge + mascot dancing (YMCA 596 / Funny Dancing 22) beside the podium, crowd roar | `NS_fnm_confetti_cannon` (new; upward cone, gravity + drag, 4 colour emitters), VFX Spawner Confetti/FireworksLarge (P), Meshy podium + mascot | P except the teleport timing (UX) | **5** | M |
| | | **Medal as an object**: (a) now: big medal art on the finish board, shine flipbook. (b) Later: giant gold/silver/bronze Meshy medals hanging over the three podium steps, slowly turning | (a) nano-banana-pro ×3. (b) Meshy medal + 2 retextures; spin = medal as a 1-bone skeletal mesh with a Blender-keyed spin clip on an Animated Mesh device, or `MoveTo` rotation loops on the device | (a) P. (b) Probe: Blender-authored clip on Animated Mesh | 4 / 5 | S / M |
| | | **Champion statue**: the island-record holder's own avatar as a hologram on the top step | `PID_Device_PlayerReference` (+ `Dance_Mannequin` for an emote) | Probe | 5 | S-M |
| | | Crowd in the arena stands and the Hall of Champions | `PID_CP_Devices_CrowdVolume` | Probe (look and memory); Meshy "lava imp" fans are the fallback | 4 | S (probe) / M |
| **Victory area idle** | ALL-TIME screen, 2 lecterns, prop fireworks | Titan Cup trophy (Meshy) on a plinth, mascot dance loop, FireworksLarge every 20 s while anyone is there | Meshy static, VFX Spawner | P | 3 | S |

### 1b. New Niagara systems (one function each in `tools/build_fx.py`; engine templates only, baked params)

| System | Recipe base (proven) | Loop? | Notes |
|---|---|---|---|
| `NS_fnm_gate_burst` | impact flash + muzzle ring + VelocityAligned sparks | Once 1 s | white-gold, ring in the XZ plane |
| `NS_fnm_sky_pillar` | `NS_fnm_laser` (glow tube + core), +X rotated up, 4000 cm | Once 1.2 s | gold. A second, cyan variant for the arena gate |
| `NS_fnm_trail_cyan/_gold/_fire` | SimpleSpriteBurst + few sparks | Once 0.6 s | tiny. Spawned on a Verse timer |
| `NS_fnm_go` | muzzle shock ring, horizontal | Once 0.8 s | cyan |
| `NS_fnm_ice_shatter`, `_dust_puff`, `_mud_splat`, `_bonk` | OmnidirectionalBurst + GravityForce + Drag | Once ≤ 1.5 s | penalty punches |
| `NS_fnm_stars` | ring ShapeLocation, 6 glow blobs, pulsing | Once 1.6 s | probe a rotate/vortex module for real orbiting |
| `NS_fnm_hoop` | coil arcs → ring | Infinite | spawned/cancelled per station when occupied (cancelable P) |
| `NS_fnm_magma_burst`, `_magma_hit`, `_titan_death` | impact recipe, orange/red HDR (5,1.5,0.2), bigger ring, ember rain | Once 1.5-3 s | the colour opposite of the cyan lasers |
| `NS_fnm_confetti_cannon` | spark cone + gravity + drag, 4 colour emitters | Once 3 s | round sprites only: no custom material route (DefaultSpriteMaterial) |
| `NS_fnm_embers_loop` | coil sparks, slow upward | Infinite | arena ambience |

Limits to respect. Sprites are round soft blobs: no star, confetti-rectangle or flame shapes until a mesh renderer or custom
material is proven. Colours and sizes are baked: one asset per variant. Spawns are global. **Probe once:** a random per-particle colour
(Uniform Ranged LinearColor dynamic input). If it works, the confetti and trail colour variants collapse into one system each.

---

## 2. Lighting and atmosphere

### 2a. Lock the island (Island Settings, `IslandSettings0`; one `set_properties` per key, then save)

| Key (from `island_props.json`) | Options | Recommend | Status |
|---|---|---|---|
| `timeOfDayOverride` | NoOverride, ForceDay, ForceNight, Custom, Hour0-23, Random | **Hour17** (warm, long shadows, saturated walls, sky still blue); screenshot Hour10 / 14 / 17 / 19 from station 1, station 6 and the arena, pick by eye | Probe (4 frames) |
| `lightIntensityOverride` | Intensity0-10 | one notch under default if the floor still glares after 2b | Probe |
| `fogDensityOverride` / `fogColorOverride` | Fog0-10 / Black, White, Red, Green, Blue, Yellow, Magenta, Cyan | Fog1-2, Yellow or White: atmospheric depth so the volcano reads far away. Primaries only, so test before trusting | Probe |
| `characterRimlightIntensity` | number | raise ~1.5× so avatars pop off busy walls | Probe |
| `cameraFilter` | NoOverride, PostProcess0-15 | screenshot all 16 in one session. A free island-wide grade if one is subtle | Probe (16 frames, S) |
| `daySequenceOverride` + `PID_DaySequence_Device` / `PID_Device_Skydome` / `PID_Environment_Light_Rig` | bespoke sky: sun, clouds, sky colour | stage 2: a "volcanic golden hour" sky (orange horizon, violet zenith). Global, which is fine for a sky | Probe (properties unknown: dump with `get_properties` first) |
| `postGameCustomVictory*` (LightningBolt, FuriousFlame...) | end-of-game screens | **N/A**: the race never ends the round | - |

### 2b. Fix the white-floor glare (the second-biggest visual problem)
- The floors are the engine cube's default white (`build_course.py` paints walls and the ice floor only; "Floors stay white").
- **Now (S):** extend `paint` / `--paint-only` to floors. Per tier, use a flat `M_fnm_floor_tN` at Kd ≈ 0.08-0.12 (dark warm basalt; flat
  colours render light), with connectors matching the tier they lead into. This also fixes Mud's blow-out and makes every FX pop.
- **Then (M):** textured floors and walls. Make a 2K tile texture per tier (nano-banana-2, 6 cr) with ~8×8 flagstones painted in, then
  apply it with the OBJ `map_Kd` trick that made the door faces. The cube UVs stretch one texture per face, so the painted tile count
  sets the stone size (~3 m stones on a 22×30 m slab). Status: map_Kd world materials are proven in the editor (door faces) and were
  **never seen in play**. Probe with one slab first, and keep streaming on (Never Stream fails validation).

### 2c. Per-tier mood (the sky is global; kids are spread over stations, so mood must be local or per player)

| Tier (stations) | Spatial: lights + VFX (global but local) | Per player: PP blended on station entry | Status |
|---|---|---|---|
| T1 (1-2) jungle base camp | warm torches (existing), Leaves VFX, Firefly Spawner | none (clean) | P / probe |
| T2 (3-4) waterfall gorge | 2 cool cyan fills, Waterfall* + LightFog over the wall tops | none | P |
| T3 (5-6) frost ridge | lavender fills, Snow continuous on 6 (and 5 light) | `PP_Frost` at low strength on station 6 only | strength = probe |
| T4 (7-8) obsidian descent | orange fills low on the walls (lava glow from below), Ash + Embers | `PP_FilmWarm` light | probe |
| T5 (9-10) magma core | red-orange fills, Small_Fire in wall niches, Embers | `PP_Heatwave` light | probe |
| Arena | 2 orange under-platform lights, cyan cannon lights (existing) | `PP_Heatwave` | probe |
| Hall of Champions | gold fills, FallingSparkles | `PP_HappyPlace`? (probe; drop it if it washes out) | probe |

- **Probe:** does `BlendIn(Agent)` go to the device's configured strength or to 1.0? If only 1.0, use per-tier PP only where the effect is
  subtle by design, and grade with lights and materials elsewhere.
- **Light budget** (Xbox class demo, "Performance Warning" seen twice): ≤ 6-8 dynamic lights visible from any spot, sizes 30-50 %.
  Door-arch lights only on the station a player is on (Verse on/off, like the guards).

---

## 3. World identity

| Option | Fantasy | Tiers / biomes | Hero assets | Fit with what exists | Credits | Wow | Effort |
|---|---|---|---|---|---|---|---|
| **A. TITAN PEAK: the Volcano Ascent (recommended)** | Climb the ridge of a living volcano, then drop into its caldera to fight the Magma Titan that lives inside. You see him on the rim from the first second | T1 green: jungle base camp (stations 1-2, level 0). T2 blue: waterfall gorge (3-4, up to 400). T3 purple: frost ridge, the **highest point** (5-6, 800; the ice station sits here). T4 orange: obsidian descent into the crater (7-8, 800→400). T5 red: magma core (9-10, →0). Arena: the Titan's Forge. Finish: Hall of Champions (gold temple) | Volcano backdrop, giant idle titan on the rim (reused SK), door portal arch ×5 tier skins, start gate, podium, medals, trophy, mascot Volt (a chibi explorer robot, cyan, "the one who built the cannons") | **Near-perfect**: the existing tier colours and the course's elevation profile (up to 800 at the ice station, then down to 0 at the arena) already tell this story. The titan, the lava cracks and the cyan lightning cannons are already in its palette | ~880 Meshy | 5 | L (in phases) |
| B. Colosseum Trials | Gladiator tunnels under a stadium, ending in the arena | sandstone halls by tier, gladiator-gate doors with lettered shields, crowd stands visible over the walls | mostly the Coliseum kit already in the project (~470 actors in boss mode) + crowd | Matches boss mode's look; one world | ~250 | 3-4 | M |
| C. Neon Vault Heist | Break into a math vault; the titan is the core reactor | sci-fi corridors, neon trims, laser grids, cryo vault (ice) | vault-door arches, reactor titan reskin (retexture 10) | Cannons and lightning fit; the titan's magma does not; night lighting needs heavy light budgets (Xbox risk) | ~600 | 4 | XL |

**Why A.** It foreshadows the boss from station 1 (the Only Up principle: the goal is on screen and grows). It turns the existing
elevation into a story. It gives every tier a reason to look different. And its 15-second clips (pillars of light rising toward the
volcano, a zipline into the caldera, the titan exploding in magma and lightning) are the moments kids share. B is the fallback if
memory or performance forces a cheap path.

**A, phase order:** (1) lighting + floor + doors (no credits). (2) Volcano + giant titan on the horizon. (3) Tier textures + VFX
Spawners + lights. (4) Arch kit, start gate, Hall of Champions. (5) Mascot + crowd. Each phase ships on its own.

---

## 4. Asset shopping list

Balances: Meshy **1,468** (156 of it monthly, resets 2026-10-14T02:37Z, i.e. tonight 19:37 PT; whether monthly credits are spent first
is unverified). Mint **7,580** of 10,000, period ends 2026-10-21 (assumed not to roll over; at $0.0008/credit it is about $6 of value,
so spend it on audio and set dressing before it lapses). Meshy route costs: concept nano-banana-pro 9, image-to-3D meshy-7.1 textured
2K 30, +5 Ultra geometry, rig 5, clip 3, retexture 10, remesh 5, lite meshy-6-lite textured 15, image 3-9 (GPT Image 2: 9 text / 12
image-to-image).

### 4a. Meshy

| # | Asset | Pipeline | Cr each | Count | Cr | Why |
|---|---|---|---|---|---|---|
| 1 | Volcano backdrop "Titan Peak" (lava rivers, glowing crater, smoke-stained cone) | concept pro 9 + image-to-3D 7.1 textured + Ultra | 44 | 1 | 44 | Identity anchor, foreshadows the boss, always ahead (+Y) |
| 2 | Door portal arch (stone, keystone slot for the 3D letter, recess for the light) | concept 9 + i2-3D 30, then **retexture** ×4 for tier skins (river stone, ice crystal, obsidian, magma iron) | 39 + 4×10 | 1+4 | 79 | Fixes "identical oil-rig doors" for good; one mesh instanced 44× |
| 3 | Start gate "Base Camp" arch (banners, braziers) | hero static | 39 | 1 | 39 | Title vista, countdown frame |
| 4 | Champion podium (3 steps) | hero static | 39 | 1 | 39 | Ceremony |
| 5 | Medal (gold) + silver/bronze | hero static + 2 retextures | 39 + 20 | 1+2 | 59 | Medal as an object |
| 6 | "Titan Cup" trophy | hero static | 39 | 1 | 39 | Hall of Champions centrepiece, key art prop |
| 7 | Mascot "Volt" (chibi explorer robot, cyan, biped) | concept 9 + i2-3D 30 + rig 5 + clips: Idle 0, Victory Cheer 59, Cheer Both Hands Up 298, Finger Wag No 409, YMCA 596, Funny Dancing 22 (18) + remesh ~20k 5 | 67 | 1 | 67 | Host in the world + face of the HUD reaction cards + key art |
| 8 | Titan extra clips: Jump and Slam 382 (intro), Zombie Scream 386 (roar), Shouting Angrily 51 | clips on the existing rig | 3 | 3 | 9 | Intro and wrong-pad reactions (root-motion risk: probe) |
| 9 | Crowd fan "lava imp" ×2 variants (fallback only if Crowd Volume fails) | concept 9 + 6-lite textured 15 + rig 5 + Sit Cheer 300, Cheer 303, Victory Fist Pump 403 | 38 | 2 | 76 | Arena alcoves / Hall stands. Keep ≤ 12 placed |
| 10 | Tier set pieces where the gallery has gaps (obsidian spire, lava vent, crystal cluster, jungle ruin pillar, waterfall boulder, rune stone ×2, lava-imp statue) | 6-lite / t2 textured 2K | 15 | 8 | 120 | Biome dressing |
| 11 | Logo, transparent (name decision first: drop "Fortnite", market §3.9) | nano-banana-pro, ~4 iterations | 9 | 4 | 36 | Required from 2026-10-22 |
| 12 | Key art: 2 portrait (art+logo; art-only), 1 landscape art-only | GPT Image 2 / image-to-image from in-game captures, ~6 tries | 9-12 | 6 | 66 | Discover redesign (hero carousel, portrait tiles) |
| 13 | HUD art: gold/silver/bronze medals (pro 9 ×3), "HIT!" + "TITAN DOWN!" + "ON FIRE" bursts (6 ×3), mascot reaction cards ×6 (6), title card (9), blackout eyes ×2 (3) | nano-banana / -2 / -pro | 3-9 | 15 | 96 | Per-player reactions (the HUD is the only per-player canvas) |
| 14 | Tier floor + wall tile textures | nano-banana-2 | 6 | 10 | 60 | Kills the greybox and the glare |
| 15 | Banners / tier-name plaques ("BASE CAMP", "FROST RIDGE", "MAGMA CORE"...) | nano-banana-2 + OBJ map_Kd quad | 4-6 | 10 | 50 | Signage that names the place |
| | **Total** | | | | **~879** | Leaves ~590 for retries, re-rolls and a second wave |

Meshy rules learned here. FBX via Blender (no GLB import). LOD bias 0 on the base colour. 40k tris for heroes, ~15-20k (remesh) for
anything repeated or animated. Every Animated Mesh clip is a full mesh copy. **Probe:** import clips 2..N as animation-only against
clip 1's skeleton (one mesh, N anims). It failed only for the two broken clips so far. If it works, mascot and crowd memory drops ~5×.

### 4b. Mint (separate budget; write tools are gated, so Aaron authorizes in his session; read usage after each job)

| Asset | Type | Count | Est. | Why |
|---|---|---|---|---|
| Music: 5 tier beds (same key/tempo family, rising intensity), 1 boss theme, 1 victory fanfare | audio | 7 | **unknown** (learn first, §5) | Escalating score; stock StW ambient loops are generic |
| Crowd cheer loop + 3 crowd reactions (gasp, laugh, roar) | audio | 4 | unknown | Arena/Hall life; penalty laughs |
| Ambience loops: lava rumble, wind ridge, waterfall, jungle | audio | 4 | unknown | Positional biome sound |
| Titan roar ×2, ice crack, mud splat, "bonk", portal whoosh | audio SFX | 6 | unknown | Custom stingers |
| Fast single models for set dressing (only if Meshy lite + gallery leave gaps) | model, fast | ≤ 8 | ~248 each est. (packs billed 2.4× estimate: use singles, check usage after the first) | ~4.5-5k tris = memory-light repeats |
| Worlds / splats | - | 0 | - | Unusable in UEFN |

### 4c. Free (do these before spending)
- Gallery props: Coliseum kit, Arctic kit, Alphabet/Number props, torches, potted plants (all P). **Probe:** search the gallery for
  lava/volcano/jungle/temple kits (`ListDeviceAssets` / content search). Fortnite's own kits beat generated props on cost and memory.
- Kokoro voices (local): race-finale titan lines (am_onyx boss profile, already rendered for boss mode), mascot Volt's lines (a
  brighter voice), wiring of the unused `countdown1..3` lines.
- Synthesized chimes (numpy, the `make_announcer.py` pattern): a 7-note rising **streak chime ladder** (pentatonic, one note higher
  per streak step).
- `sfx-sourcing` skill: Mixkit / Freesound CC0 crowd, lava, wind. Check each licence.

---

## 5. Audio

| Layer | Today | Upgrade | Source | Status | Wow | Effort |
|---|---|---|---|---|---|---|
| Music | 5 stock StW loops by tier, 0.5 vol, Instigator 2D; Aaron's Music slider is 0 | 5 key-matched tier beds rising in instrumentation (T1 hand drums → T5 full drums + brass + choir), a boss theme in the arena, silence + a victory fanfare at the kill | Mint audio (price unknown) or licensed loops | Import P (GUI); **probe:** does an imported bed obey the player's Music slider? (Aaron's slider at 0 is the test rig) | 4 | M |
| Right-answer stinger | stock SkilledInteract_Success | Streak chime ladder (rising pitch per streak), whoosh on the gate burst | synthesized (free) | P path | 4 | S |
| Streak | announcer DOUBLE → UNSTOPPABLE | keep; add a 1 s riser under ON FIRE | free / Mint | P | 3 | S |
| Penalties | stock + voice | custom comic SFX per penalty (ice crack on thaw, mud splat, bonk, slide-whistle on yeet, crowd laugh if a crowd exists) | Mint / sfx-sourcing | P path | 4 | S |
| Ambience | none | positional loops per biome (jungle, waterfall, wind, lava rumble), heard by everyone, spatialized, attenuated | audio player with `can Be Heard By` everyone + spatialization + attenuation | Probe (only Instigator 2D proven) | 4 | S-M |
| Titan | stock Stinger_Threat, barrel boom | the boss-mode voice lines in the race (arrive, hit, wrong, dead), custom roar on intro and kill | already imported (am_onyx) + Mint roar | P (cue reuse) | 4 | S |
| Crowd | none | cheer on each cannon hit and the kill, gasp + laugh on a wrong pad, roar on the podium | Crowd Volume's own audio (probe) or Mint/sfx loops | probe | 4 | S-M |
| Mascot | none | Volt's lines at the start, on the podium, on a perfect run | Kokoro (free) | P path | 3 | S |

**How to learn Mint's audio price cheaply (no blind spend)**
1. Free reads first: `get_credits_balance` and `get_mint_context` (any per-operation hint).
2. If a Mint REST API key can be created: `POST /v1/pricing:estimate {operation: "audio_generation"}` prices without starting work
   (mint-gg skill).
3. Otherwise, one shortest job (a single 3-5 s SFX, e.g. the ice crack) with `get_credits_balance` read before and after. Report the
   delta, then price the 7 music loops off it. Audio has no preview gate, so the first job bills in full. Keep it tiny.

Mix rules (already learned): no voice on the same instant as a stinger (0.9 s offset), voice volume 2.5, at most 2 sounds in any 1 s
window at the kill (today up to 4 stack: `boss_dead`, `BOSS DOWN`, `finish`, `new_record`).

---

## 6. Ranking by wow per effort

| Rank | Item | Wow | Effort | Credits | Build first |
|---|---|---|---|---|---|
| 1 | Lock time of day (Hour17 after 4 frames) + dark tier floors + rim light | 4 | S | 0 | **★ 1** |
| 2 | Doors: re-run the door dress + 3D lintel letters + letter-colour arch lights | 4 | S | 0 | **★ 2** |
| 3 | Right answer: gate burst + **pillar of light** | 5 | S | 0 | **★ 3** |
| 4 | Boost: ActionLines speed lines + spark trail (cyan/gold/fire) | 5 | S-M | 0 | **★ 4** |
| 5 | Volcano on the horizon + giant idle titan on its rim | 5 | M | ~44 | **★ 5** |
| 6 | The kill: titan death burst + 5× strike + fireworks + gate beam (+ kill cam probe) | 5 | M | 0-6 | next |
| 7 | Finish ceremony: portal to podium, confetti cannon, HUD medal art | 5 | M | ~66 | next |
| 8 | Mud flies + dizzy stars + ice shatter + yeet puff | 4 | S | 0 | next |
| 9 | Probes: Powerup_VFX aura, PlayerReference champion, CrowdVolume, CameraFocus | 5 if they work | S each | 0 | one probe session |
| 10 | Titan intro (Jump and Slam, magma eruption, voice) | 5 | M | 9 | |
| 11 | Tier VFX Spawners + spatial lights + ambience | 4 | M | 0 | |
| 12 | Tier textures (floor/wall) + banners | 4 | M | ~110 | |
| 13 | Portal arch kit (5 skins) | 4 | M | ~79 | |
| 14 | Mascot Volt (world + HUD cards + voice) | 4 | M | ~100 | |
| 15 | Discover pack: logo + key art + trailer capture (**hard deadline 2026-10-22** to publish or update) | 5 for clicks | M | ~102 | deadline item, outside the ranking |
| 16 | Zipline into the caldera | 5 | M | 0 | needs UX sign-off |
| 17 | Custom music (Mint) | 4 | M | Mint ? | after the price probe |
| 18 | Speed hoops + connector arches | 4 | M | 0 | |
| 19 | Spinning 3D medals / trophy, Hall of Champions dressing | 4 | M | ~98 | |
| 20 | Bespoke sky (Day Sequence / Skydome) | 4 | M | 0 | probe |
| 21 | Crowd from Meshy (only if Crowd Volume fails) | 4 | L | ~76 | |
| 22 | Cinematic intro / trailer via Sequencer | 5 | XL | 0 | GUI-only, later |

**The five to build first (★), in one sitting.** Items 1-4 cost zero credits and use only proven devices and Niagara recipes. Item 5
costs ~44 Meshy credits and needs one distance probe. Together they change every frame of the race: true colours, readable doors, a
visible reward on every right answer, a visible streak, and the boss on the horizon from the first second.

---

## 7. Probe session (one UEFN session, ~2 h, before building rows that depend on it)

1. `timeOfDayOverride` Hour10/14/17/19 (4 frames from station 1, station 6, arena) + `cameraFilter` PostProcess0-15 (16 frames).
2. One floor slab with a `map_Kd` tile texture: does it render in play, and does validation pass?
3. A large placeholder static mesh (scale 100+) at y +2 km with `bIsSpatiallyLoaded` false: visible from station 1? Then the titan
   Animated Mesh at scale 40 on top.
4. `PID_Device_Powerup_VFX` granted from Verse: what glow, how long, does it follow?
5. `PID_CP_Devices_CrowdVolume` in the arena: look, sound, memory.
6. `PID_Device_PlayerReference` on the podium: hologram of a present player?
7. `PID_CP_Device_CameraFocus` / `PID_CP_Devices_FixedPoint`: point a player's camera at the titan for 1.5 s.
8. `PP_ActionLines` and `PP_Heatwave` screenshots. Does `BlendIn` honour a configured strength below 1?
9. Audio player spatialized, heard by everyone: positional lava loop.
10. Niagara: is a 40 m beam visible from 100 m (cull bounds)? Does random per-particle colour work?
11. Memory: GUI "Launch Memory Calculation" before and after the first asset wave (GUI-only; Aaron or scripted clicks).

---

## 8. Shakiest assumptions (unverified, flagged)
- **Distance rendering of the volcano** (World Partition streaming, culling, fog) is untested. The whole "boss on the horizon" idea
  depends on probe 3.
- **Island memory is unmeasured.** Every hero mesh, 2K texture and clip copy adds to it. The list above roughly doubles the project's
  custom art.
- `map_Kd` world materials were seen only in the editor. The door dress that used them never reached play.
- `PP_ActionLines` looks like speed lines by name only. Partial PP strength is unknown.
- New Meshy clips may misplay (two of six titan clips did, cause unknown). Jump and Slam has root motion.
- Mint audio price and both credit-expiry rules are assumptions. Mint write tools are gated by context.
- Niagara on Xbox: particle and light budgets are guesses. The class demo build has never been seen running.
- Key art must not show recreated Fortnite characters (thumbnail policy). Use the mascot, the titan and real in-game captures.
