# Wrong-door penalties

Aaron's brief (2026-10-03): a wrong door should do something different and surprising every time, so a
player is nervous to walk through any door. Each map picks a pool of penalties; each wrong answer draws one
at random. Every penalty also flashes a big red **X** plus its name ("FROZEN!"). A right answer flashes a
big green **CORRECT!** and never stalls the player.

Runtime: `fnm_penalties.verse` (the enum and labels) plus `fnm_director.Punish`. A map's pool is the
director's `Penalties` @editable. To watch every penalty without walking, set `DebugAutoWrongAnswers` to N.
Each joining player then auto-answers N questions wrong, one every 12 s, cycling through the pool.

## Status key
**Live**: in the runtime and seen working in a play session. **Broken**: in the runtime but doesn't
work yet. **Idea**: not built. The "how" column names the UEFN API or device it would use.

## Built
| Penalty | Effect | How | Status |
|---|---|---|---|
| Freeze | Encased in a block of ice for 5 s, then back to the station entry | `PutInStasis` + an ice-cube rig moved onto them | **Live** |
| Spike | A ring of 6 spears bursts out of the floor around them; eliminated, respawn, back to the station entry | spear rig (`MoveTo` up in 0.12 s) + `Damage(1000)`, poll for respawn | **Live** |
| Yeet | An air vent appears under them and blasts them ~75 m up into a skydive; on landing (max 8 s) back to the station entry | air-vent rig moved under them, then the player is hopped 40 cm so they *enter* the gust | **Live** |

Rigs: `console/verse/fnm_rig.verse` (runtime) + `tools/build_rigs.py` (places 4 sets, parked underground, tagged
`fnm_ice` / `fnm_spike` / `fnm_yeet`). Rerun the builder after changing a rig. Real Fortnite traps can't be
rigs: a placed trap (BR or Creative/Figment floor spikes) fails island validation as an illegal reference.

## Catalog: what UEFN can do (from the 42.30 Verse digest and device list)
Gentle → harsh. Every row is controllable from Verse for one specific player.

| Idea | What the player experiences | How |
|---|---|---|
| Ice block | Frozen inside a block of ice for 5 s | Freeze + spawn an ice prop around them (`SpawnProp`, `CR_Legacy_IceStatue` prop exists) + frost post-process |
| Yeet (fixed) | Launched back down the hallway | Teleport a `bouncer_device` or directional launcher (`PID_CP_Device_DLauncherStandard`) under the player with `creative_device.TeleportTo`, then move it away |
| Rocket | Shot straight up into the sky, glides back down | `air_vent_device.Activate` moved under the player, or a `skydive_volume_device` |
| Trapdoor | The floor vanishes; they drop into a pit/slide that dumps them at the hallway start | `trick_tile_device.Trigger()` under each wrong-door vestibule |
| Boulder | A boulder releases and rolls down the hallway at them | `physics_boulder_device.ReleaseRollingBoulder()` |
| Pinball | Bumpers ping them around the vestibule | `pinball_bumper_device.Activate()` |
| Kaboom | An explosion knocks them back (non-lethal damage) | `explosive_device.Explode(agent)` |
| Zap | An electric wall/ceiling trap shocks them | Figment trap assets `Figment_Trap_Wall_Electric_Athena` / `_Ceiling_Electric_` |
| Mud | Slowed to a crawl for 5 s | `movement_modulator_device.Activate(agent)` (speed multiplier) |
| Moon gravity | Floaty, slow-motion jumping for a while | `player_movement_settings_device.AddTo(agent)` / `mutator_zone_device` |
| Flood | The vestibule fills with water; swim out | `water_device.BeginVerticalFilling()` |
| Disguise | Turned into a prop (chicken, toilet…) for 5 s | `disguise_device.ApplyDisguise(player)` |
| Blackout / dizzy | Screen goes dark, blurry or colour-washed for a few seconds | `post_process_device.BlendIn(agent)` |
| Camera swap | Camera flips to first-person or side-scroller for a stretch | `gameplay_camera_first_person_device`, `gameplay_controls_side_scroller_device` |
| Fire floor | The floor catches fire; run! | `fire_volume_device.Ignite()` |
| Turret | A sentry or turret opens fire for 3 s | `automated_turret_device` / `sentry_device` |
| Creature | Wolves or chickens burst out and chase | `creature_spawner_device` / `wildlife_spawner_device` |
| Jail | Teleported into a cell, a 5 s time-out with a countdown | `TeleportTo` + HUD timer |
| Detour | The wrong door drops them onto a grind rail that loops back | `grind_rail_device` in the vestibule (layout-dependent) |

Not possible: forcing an emote on a player (`PlayEmote` exists only on mannequins).
