# Wrong-door penalties

Aaron's brief (2026-10-03): a wrong door should do something different and surprising every time, so a
player is nervous to walk through any door. Each map picks a pool of penalties; each wrong answer draws one
at random. Every penalty also flashes a big red **X** plus its name ("FROZEN!"). A right answer flashes a
big green **CORRECT!** and never stalls the player.

Runtime: `fnm_penalties.verse` (the enum and labels) plus `fnm_director.Punish`. A map's pool is
`"penalties"` in its `map.json` (PROTOCOL §6a), generated into `fnm_map_profile.verse` on `fnm sync`; omitted =
all of them. To watch every penalty without walking, set `DebugAutoWrongAnswers` to N.
Each joining player then auto-answers N questions wrong, one every 12 s, cycling through the pool.

## Status key
**Live**: in the runtime and seen working in a play session. **Broken**: in the runtime but doesn't
work yet. **Idea**: not built. The "how" column names the UEFN API or device it would use.

## Built
| Penalty | Effect | How | Status |
|---|---|---|---|
| Freeze | Encased in a block of ice for 5 s right where they stand, seen from a wide camera (walls see-through), frosted screen, then back to the station entry | `PutInStasis` + ice-cube rig + orbit camera rig (`AddTo`/`RemoveFrom`) + `PP_Frost` | **Live** |
| Spike | A ring of 6 spears bursts up where they stand and they are eliminated the moment the spears land (was a 1.2 s pin; Aaron: the death lagged the spikes); respawn, back to the entry with the pistol | spear rig + `PutInStasis` + `Damage(1000)`. The orbit camera as elimination camera jumped to a random wall, so the death view is Fortnite's own | **Live** |
| Mud | Back at the entry, slowed to half speed with a sepia screen for 8 s | `movement_modulator_device.Activate(agent)` (re-applied every 2.5 s: its 3 s Duration isn't settable from MCP) + `post_process_device` `PP_Sepia` | **Live** |
| Dizzy | Back at the entry with a wild colour-swirl screen for 6 s | `post_process_device` `PP_Crazy`, `BlendIn(agent)` / `BlendOut(agent)` | **Live** |
| Blackout | "LIGHTS OUT!": the screen goes fully black for 3 s, they wake up at the entry | full-screen black `color_block` on the HUD + `PutInStasis` (the `PP_Dark` effect only tinted the view) | **Live** |
| Yeet | Pulled out into the hallway, then thrown ~20 m back down it by an air vent tilted 50° back (no skydive), landing at the entry | tilted air-vent rig + 40 cm hop into the gust. Per-tick `TeleportTo` was choppy; a directional launcher has no Verse class | **Live** |

Freeze and Spike happen where the player stands (Aaron: no position change) under an orbit camera 9 m out whose
walls go see-through. Only Yeet first pulls the player 5 m in front of the door wall, so the throw clears it.

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
| More screen effects | 33 built-in effects (VHS, CCTV, Pixelizer, NightVision, OldCartoon, Heatwave…) at `/Game/Creative/PostProcess/PP_*` | another `post_process_device` row in `build_rigs.py` |
| Camera swap | Camera flips to first-person or side-scroller for a stretch | `gameplay_camera_first_person_device`, `gameplay_controls_side_scroller_device` |
| Fire floor | The floor catches fire; run! | `fire_volume_device.Ignite()` |
| Turret | A sentry or turret opens fire for 3 s | `automated_turret_device` / `sentry_device` |
| Creature | Wolves or chickens burst out and chase | `creature_spawner_device` / `wildlife_spawner_device` |
| Jail | Teleported into a cell, a 5 s time-out with a countdown | `TeleportTo` + HUD timer |
| Detour | The wrong door drops them onto a grind rail that loops back | `grind_rail_device` in the vestibule (layout-dependent) |

Not possible: forcing an emote on a player (`PlayEmote` exists only on mannequins).
