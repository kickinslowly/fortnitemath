# Wrong-door penalties

Aaron's brief (2026-10-03): a wrong door should do something different and surprising every time, so a
player is nervous to walk through any door. Each map picks a pool of penalties; each wrong answer draws one
at random. Every penalty also flashes a big red **X** plus its name and the time it costs ("FROZEN!  +3 s"). A
right answer flashes a big green **CORRECT!** and never stalls the player.

**The five-second wrong door (G9, 2026-10-13; `reviews/race-2026-10-13` ux_critique #8).** Every penalty now costs the
same: a gag of about 2.5 s where the player stands, then the station's **retry spot**, 6 m in front of its door wall
(`RetryStandOff` 600; it was 3 m, where only doors B and C were on screen), centred on the doors and facing them, under the
wide camera until the player moves 1.5 m or 4 s pass, so all four doors and their lintel letters are on screen (`fnm_director.RetrySpotFor`, read at OnBegin from the station's own door triggers;
logged per station with `clear yes`, and never inside a door's zone, or the backstop would answer that door by position
again and again). **+3 s** go on the race clock (`WrongDoorSeconds`), and the **letters are shuffled again** for the
retry (same question, new order). Until then a wrong door cost 5.8 s (Yeet) to 9.3 s (Freeze) plus a 25.5 m re-run past
the obstacles and the guards, back from the start of the hallway: a dice roll in a race. The arenas (race finale, boss
mode) keep their entry as the retry point: their pads stand in the open. In BOSS BATTLE the player is moved to the
arena entry FIRST and held there (round 2: monsters spawn by the pads on a wrong answer, and stasis does not block damage;
Mud has no stuck beat there, only the slow, as before G9: a player held at the entry was shot by the wave's guards in a test).

Runtime: `fnm_penalties.verse` (the enum and labels) plus `fnm_director.Punish`. A map's pool is
`"penalties"` in its `map.json` (PROTOCOL §6a), generated into `fnm_map_profile.verse` on `fnm sync`; omitted =
all of them. To watch every penalty without walking, set `DebugAutoWrongAnswers` to N.
Each joining player then auto-answers N questions wrong, one every 12 s, cycling through the pool.

## Status key
**Live**: in the runtime and seen working in a play session. **Broken**: in the runtime but doesn't
work yet. **Idea**: not built. The "how" column names the UEFN API or device it would use.

## Built
| Penalty | Effect (since G9: hold, then the retry spot) | How | Status |
|---|---|---|---|
| Freeze | Encased in a block of ice for 2.5 s (`FreezeSeconds`, was 5) right where they stand, seen from a wide camera (walls see-through), frosted screen, then the retry spot | `PutInStasis` + ice-cube rig + orbit camera rig (`AddTo`/`RemoveFrom`) + `PP_Frost` | **Live**; G9 seen in play 2026-10-13: ready on the retry spot 2.50 s after the verdict |
| Spike | A ring of 6 spears bursts up where they stand and pins them for 2.3 s (`SpikeHoldSeconds`) under the wide camera, then the retry spot. **No elimination since G9**: the kill showed Fortnite's "bailed early" line and the respawn took every gun the guards had dropped | spear rig + `PutInStasis` (no `Damage`) | **Live**; G9 seen in play 2026-10-13: ring up round the player, health 100/100, pistol kept, ready on the retry spot 2.44 s after the verdict |
| Mud | "STUCK IN MUD!": stuck where they stand (turning allowed) with a sepia screen for 2 s (`MudStuckSeconds`), then on the retry spot at half speed for 3 s (`MudSeconds`, was 8; a right answer ends it) | `PutInStasis` + `movement_modulator_device.Activate(agent)` (re-applied every 2.5 s: its 3 s Duration isn't settable from MCP) + `post_process_device` `PP_Sepia` | **Live**; G9 seen in play 2026-10-13: ready on the retry spot 2.00 s after the verdict, then slowed |
| Dizzy | Spun round once on the spot in 1.5 s (was twice: a motion-comfort risk), then on the retry spot the view blurs in and out twice (0.7 s each way, 2.8 s, was 6). Aaron (2026-10-04): the earlier colour swirl (`PP_Crazy`) was confusing, not dizzying | character `TeleportTo` in place with the yaw advanced every 0.05 s under stasis (a character teleport turns the view too) + `post_process_device` `PP_RadialBlur` pulsed with `BlendIn(agent)` / `BlendOut(agent)` | **Live**; G9 seen in play 2026-10-13: one turn ending at yaw 450 (facing the doors), ready on the retry spot 2.00 s after the verdict, 2 blur pulses (whether the spin is smooth at full fps is unverified: if it strobes, set `DizzySpinStepSeconds` to 0.033) |
| Blackout | "LIGHTS OUT!": the screen goes fully black for 2 s (was 3), they wake up on the retry spot; the black lifts 0.5 s later | full-screen black `color_block` on the HUD + `PutInStasis` (the `PP_Dark` effect only tinted the view) | **Live**; G9 seen in play 2026-10-13: ready on the retry spot 2.50 s after the verdict |
| Yeet | Pulled onto the retry spot, thrown back down the hallway by an air vent tilted 50° back, and at most 1.6 s after the vent (`YeetAirSeconds`, was a 6 s wait to land wherever) put back on the retry spot | tilted air-vent rig + 40 cm hop into the gust. Per-tick `TeleportTo` was choppy; a directional launcher has no Verse class | **Live**; G9 seen in play 2026-10-13: thrown 18.3 m back, landed in 1.15 s, ready on the retry spot 1.70 s after the verdict |

In the race, Freeze, Spike, Mud's stuck beat, the Dizzy spin and Blackout happen where the player stands (Aaron: no position change),
out of the guards' line of fire behind the door; Freeze and Spike under an orbit camera 9 m out whose walls go
see-through. Only Yeet first moves the player (onto the retry spot), so the throw clears the door wall. Every penalty
logs `FNM: wrong door <NAME>: ready on the retry spot <x,y,z> <t> s after the verdict`.

Rigs: `console/verse/fnm_rig.verse` (runtime) + `tools/build_rigs.py` (places 4 sets, parked underground, tagged
`fnm_ice` / `fnm_spike` / `fnm_yeet`, plus `fnm_penalty_cam` and the `fnm_loadout` trigger; ice and spears have collision off). Rerun the builder after changing a rig. Real Fortnite traps can't be
rigs: a placed trap fails island validation as an illegal reference. Tried: the BR and Figment floor-spike item
definitions (`TID_...`) and the trap actor class itself (`Trap_Athena_Spikes_Figment_C`, 2026-10-03). Even if one
passed, a trap sits still and fires on anyone, including a right-answer player, and Verse can't move it.

## Catalog: what UEFN can do (from the 42.30 Verse digest and device list)
Gentle → harsh. Every row is controllable from Verse for one specific player.

| Idea | What the player experiences | How |
|---|---|---|
| Ice block | Frozen inside a block of ice for 5 s | Freeze + spawn an ice prop around them (`SpawnProp`, `CR_Legacy_IceStatue` prop exists) + frost post-process |
| Rocket | Shot straight up into the sky, glides back down | `air_vent_device.Activate` moved under the player, or a `skydive_volume_device` |
| Trapdoor | The floor vanishes; they drop into a pit/slide that dumps them at the hallway start | `trick_tile_device.Trigger()` under each wrong-door vestibule |
| Boulder | A boulder releases and rolls down the hallway at them | `physics_boulder_device.ReleaseRollingBoulder()` |
| Pinball | Bumpers ping them around the vestibule | `pinball_bumper_device.Activate()` |
| Kaboom | An explosion knocks them back (non-lethal damage) | `explosive_device.Explode(agent)` |
| Zap | An electric wall/ceiling trap shocks them | Figment trap assets `Figment_Trap_Wall_Electric_Athena` / `_Ceiling_Electric_` |
| Moon gravity | Floaty, slow-motion jumping for a while | `player_movement_settings_device.AddTo(agent)` / `mutator_zone_device` |
| Flood | The vestibule fills with water; swim out | `water_device.BeginVerticalFilling()` |
| Disguise | Turned into another character for 5 s (the 42.30 device only offers default human skins, no props: not funny enough yet) | `disguise_device.ApplyDisguise(player)` |
| More screen effects | 34 built-in effects at `/Game/Creative/PostProcess/PP_*` (listed 2026-10-04): 70sPrint, 80sCartoon, ActionLines, Blackout, CCTV, Comic, ComicNoir, Crazy, Dark, Desolate, FilmNoir, FilmWarm, Frost, Halftone, HappyPlace, Heatwave, HeavyLinework, HorrorMovie, LowExposure, NeoComic, NeonParty, NightVision, Oak, OldCartoon, Pixelizer, RadialBlur, Rain, Red, Retro, SimpleBlurSharpen, Sepia, Spooky, VHS_Filter, VignetteMaskedColored. RadialBlur is the only true blur; the folder's `PostProcessEffectActor` is not an effect | another `post_process_device` row in `build_rigs.py` |
| Camera swap | Camera flips to first-person or side-scroller for a stretch | `gameplay_camera_first_person_device`, `gameplay_controls_side_scroller_device` |
| Fire floor | The floor catches fire; run! | `fire_volume_device.Ignite()` |
| Turret | A sentry or turret opens fire for 3 s | `automated_turret_device` / `sentry_device` |
| Creature | Wolves or chickens burst out and chase | `creature_spawner_device` / `wildlife_spawner_device` |
| Jail | Teleported into a cell, a 5 s time-out with a countdown | `TeleportTo` + HUD timer |
| Detour | The wrong door drops them onto a grind rail that loops back | `grind_rail_device` in the vestibule (layout-dependent) |

Not possible: forcing an emote on a player (`PlayEmote` exists only on mannequins).
