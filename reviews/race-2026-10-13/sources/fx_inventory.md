# fortnitemath RACE mode: visual / audio / FX inventory (2026-10-13)

Read-only audit. Repo `D:\PyCharm Projects\fortnitemath` (cited `file:line`; `director` = `console/verse/fnm_director.verse`, `ui` = `console/verse/fnm_ui.verse`; BM = `BOSS_MODE.md`; UEFN skill = `~/.claude/skills/uefn-mcp/SKILL.md` (`SK:`line)). UEFN was closed; nothing was run or edited. Verse digests read from `C:\Users\kicki\AppData\Local\UnrealEditorFortnite\Saved\VerseProject\FortniteMath\Digests\BuiltIn\` (`Fortnite.digest.verse` = FD, `UnrealEngine...` = UD, `Verse...` = VD).

Status key: PROVEN = built and seen working in this project. DOC = in the 42.30 digest / Epic docs, never tried here. ? = uncertain or untested, reason given.

Headline finding: in race mode the world itself is almost silent and static. Every celebration (right answer, streak, boost, finish) lives on the HUD and in the audio; the only world-space VFX in the whole race is the finale arena (Niagara + strike) and the finish fireworks props. Hallways have torches as their only lights, the sky/fog/lighting is the Blank template default (grep for skydome/fog/atmosphere/day-sequence/post-process-volume across `tools/`, `console/`, docs: nothing).

---

## 1. Race mode today, per beat

### 1.0 Island, join, picker
| Layer | What | Cite |
|---|---|---|
| Devices | 2 template spawn pads + 6 more (`PID_Device_PlayerSpawnPad`), island settings (Cooperative, DBNO off, SpawnImmediately, env damage off, building none, 16 players) | `tools/build_island.py:23-48` |
| Director | One `fnm_director` Verse device at (-3000, START_Y); everything else found by Verse tag | `tools/build_course.py:699-707`, `director:230` |
| Join | HUD attached, teleported to station 1 entry, held in stasis (`PutInStasis` turn-only), picker menu | `director:1069-1099` |
| HUD | Verse UI: `button_loud`/`button_regular` picker (grade then skill, captions as 22 px text), gold BOSS BATTLE button | `ui:886-970`, BM §1 |
| Audio | `welcome` (Match_Start_01 + announcer), `choose` (SkilledInteract_Open) | `console/AUDIO.md:57-58` |
| Textures | `FNM_Art.T_fnm_slate`, `T_fnm_tile` (answer tiles, tinted per letter), check, cross | `ui:84`, `tools/import_art.py:1-30`, `tools/art/*.png` |

### 1.1 Start (countdown + GO)
| Layer | What | Cite |
|---|---|---|
| HUD | `FlashBig` "3","2","1" white, "GO!" lime 1 s; race clock top-left 52 px; pace delta; streak line | `director:2164-2191`, `ui:678` |
| Audio | `countdown3/2/1` (Timer_UI_Tick_Minigame_Cue), `go` (Timer_UI_Minigame_Go + am_michael voice), music bed `music_tN` for the station's tier | `AUDIO.md:37-38,74`, `director:2183,2894` |
| World | none. Player held in stasis during the count. No lights, VFX, camera move | `director:2173-2180` |

### 1.2 Hallway (10 stations; 30 m long, 22.1 m wide inside, 6 m walls)
| Layer | What | Cite |
|---|---|---|
| Structure | engine cube slabs/walls/lintel/dividers (`/Engine/BasicShapes/Cube`), 7 m vestibules behind doors | `tools/build_course.py:330-349` |
| Colour | flat unlit-ish materials `M_fnm_wall_tier1..5` (green, blue, purple, orange, red; finish gold) painted by tier; hurdles gold; stair steps tier-coloured | `build_course.py:584-608`, `import_art.py:36-40` |
| Lighting | torches only: `PPID_CR_Legacy_BP_TRV_ALight_Torch_02_CP` (real flame + point light + crackle sound), 3 per wall x 2 = 6 per station (+6 in finish); ice station uses wall snowflakes instead | `tools/build_decor.py:47,66,154-162,305-306` |
| Dressing | 3D station-number digits over the lintel (`PPID_CP_Number_*`), chalkboard prop + billboard chalk line, potted plant x2, 6 giant floating sky digits per station (7-12 m, no collision), "STATION N" billboard | `build_decor.py:49-65,143-175,274-291`, `build_course.py:354-355` |
| Ice station (6) | pale-blue floor material, snow piles, ice blocks, ice statues, snowman, snowy tree, icicles hanging off wall tops, snow ridge on wall tops, giant snowflakes on connector walls + icicles on the approach; mutator zone + `player_movement_settings_device` (friction 0.05, accel 500) | `build_decor.py:68-89,208-271`, `build_course.py:128-143,358-366` |
| Obstacles | gold 70 cm hurdles, baffle walls, shipping containers swept by Verse (`creative_prop.MoveTo`) | `build_course.py:79-90,391-407`, `director:2241-2248` |
| Guards | `PID_Device_GuardSpawner_V2` per hallway, 1,1,2,2,3,3,4,4,5,5 guards, weapon ladder pistol to rocket launcher (48 WIDs accepted), health bars, drop guns; enabled only while a player is on the station; cue `guards_up` | `tools/build_guards.py:23-75`, `director:969`, `AUDIO.md:56` |
| Pickups | even stations 2..10: holo Item Spawner pads (`PID_CP_Devices_ItemSpawnerProp`) with Boogie Bomb + Shockwave Grenade (sides swap); odd 3+: Slap Splash pads; row triggers feed item granters | `tools/build_pickups.py:46-92`, `director:2721` |
| Lids | invisible 40 cm collision slabs over every floor piece (glass material, hidden) | `tools/build_lids.py:36-45` |
| HUD | slate (texture + 46 px prompt + 4 answer tiles), race strip (rivals ranked), public feed (top right, 3 lines, 7 s), pace delta | `ui:84,132,142-147`, `director:2750-2866` |
| Audio | music bed per tier (5 stock loops, volume 0.5, Instigator-only 2D), NO ambience, NO positional sound | `AUDIO.md:74`, `build_audio.py:75-88` |

### 1.3 Doors
| Layer | What | Cite |
|---|---|---|
| Props | 4x `PPID_CR_Legacy_OilRig_Platform_Wall_01_Door_01` stretched to 553 cm; panel material `M_door_face_a..d` (letter colour + dark tile + letter, painted into the texture); E to open (stock prop door) | `build_course.py:52,309-314,373`, `LAYOUT.md:269-278` |
| Devices | Trigger V2 per vestibule (fitted StepBox), Barrier (per-player `AddToIgnoreList`, `invisibleToIgnoredPlayers`) at far end of each vestibule | `build_course.py:374-387` |
| Audio / FX | stock door creak only; no cue on touching a door. Barrier renders red-striped in play | SK:100 |

### 1.4 Right answer
| Layer | What | Cite |
|---|---|---|
| Logic | Cleanse penalties, streak++, split recorded, `AdvancePlayer`: vitals refilled, barrier lowered for that player only, next question drawn | `director:1370-1391,1471-1489` |
| HUD | verdict check texture + "CORRECT!" or "N IN A ROW!" (1.5 s), then green "Correct! <explanation>" feedback line; feed line at streak 3/5/7/10 | `ui:662`, `director:1381-1389` |
| Audio | `correct` (SkilledInteract_Success) or `correct_retry` (Good), `door_open` (SlidingDoor_Open); `streak2..7` voice lines 0.9 s later; boost whoosh only if streak < 2 | `AUDIO.md:39-44`, `director:1379-1383,2210-2211` |
| World | NOTHING visible besides the barrier going invisible for that player. No confetti, no light, no beacon, no camera, no post-process | grep: no VFX call in `HandleDoor` |

### 1.5 Wrong answer / penalties (6, random from `map.json` pool)
Common: streak reset, boost stopped, cue `wrong` (Target_Error 0.77 s) + red X texture + penalty label (96 px) + red feedback + public feed line; penalty voice 0.9 s after the buzzer (`director:1392-1405`, `AUDIO.md:41,48-54`).

| Penalty | Devices / props / FX | Audio | Cite |
|---|---|---|---|
| FROZEN (5 s) | `PutInStasis`; ice cube prop `PPID_CR_Legacy_Apollo_IceCube_NoLoot` (0.9x0.9x1.05, no collision); wide orbit cam `PID_CP_Devices_Orbit` (9 m, walls see-through); `PP_Frost` post-process (blend 0.3 in / 0.8 out) | Trap_IceBlock_Placed + voice | `build_rigs.py:40-41,53-57,80`, `director:1672-1687` |
| SPIKED | 6 Coliseum spears (`..._Coliseum_Spear_01` x1.5) risen by `MoveTo`; orbit cam; `Damage(1000)` kills; respawn at entry | DestructionObject_Impact + voice | `build_rigs.py:43-44`, `director:1746-1769` |
| STUCK IN MUD (8 s) | teleport to entry; movement modulator speed 0.5 (re-applied every 2.5 s); `PP_Sepia` | ExplodingBarrel_Explode_Stink + voice | `build_rigs.py:61-64,81`, `director:1720-1726,1793-1813` |
| DIZZY (6 s) | teleport to entry; yaw spin by `TeleportTo` steps under stasis; `PP_RadialBlur` pulsed in/out | GhostMode_Enter + voice | `build_rigs.py:82`, `director:1727-1733,1817-1853` |
| LIGHTS OUT (3 s) | stasis; full-screen HUD `color_block` black | ActionTrigger_PowerOff + voice | `director:1734-1745`, `ui:166` |
| YEET | pull-out + tilted `PID_Device_AirVent_V2` (strength 0.5, no dive) throws ~18 m back | Cube_LaunchPlayer + voice | `build_rigs.py:48-50`, `director:1688-1719` |

Every effect is per-player (post-process, camera, HUD, modulator) except props (ice cube, spears, vent are world objects everyone nearby sees) and the audio is 2D and instigator-only. Placed Fortnite traps fail validation (SK:84-85).

### 1.6 Streak / boost
| Layer | What | Cite |
|---|---|---|
| Device | invisible `movement_modulator_device` speed 2.0 (`visibleDuringGame No`), re-activated each ~2.5 s, 3 s + 0.5 s per streak step, max 7 s | `build_rigs.py:67-70`, `director:2204-2231,411-415` |
| HUD | orange 40 px "STREAK x3 - SPEED BOOST 4s" | `ui:105`, `director:2195` |
| Audio | streak2..7 = Target_Impact_Success_2D, Target_Impact_Bullseye, Creative_PowerUp_Collect, CaptureDevice_Capture_Finish, Stinger_Success_02/03 + announcer DOUBLE/TRIPLE/MEGA/ULTRA/MONSTER/UNSTOPPABLE | `AUDIO.md:44,100` |
| World | none (no speed lines, no trail, no FOV, no post-process on boost) | |

### 1.7 Connectors (10, between stations and into the arena)
| Layer | What | Cite |
|---|---|---|
| Geometry | funnel from 22 m down to a 10 m corridor, segments, flare back out; stairs (25 cm steps of cubes, +/-4 m), 45-degree winds; walls tier-coloured, lids hidden | `build_course.py:105-124,416-479`, `LAYOUT.md:35-47` |
| Speed plates | visible `PID_Device_MovementModulator` (chevrons), speed 1.8 + forward impulse 2000 + up 300, 513 cm | `build_course.py:122-127,445-450` |
| Dressing | none, except ice-hall approach (snowflakes, icicles, snow ridge) | `build_decor.py:250-271` |
| Audio | music bed only | |

### 1.8 Boss arena (stage 11; 30 m hall)
| Layer | What | Cite |
|---|---|---|
| Hall | tier-5 red walls; 4 pad tiles in letter colours (`M_fnm_wall_pad_a..d`) with hidden Trigger V2 (450x450x150); gold platform 6x4x1 m; sign "BOSS ARENA"; gate Barrier at exit (opens per player at the kill) | `build_course.py:510-546` |
| Boss | hidden Megabrute (`PID_Device_CreatureSpawner_V2`, 100000 HP, only pads damage it) under the Magma Titan: 4 `Device_AnimatedMesh` clips (idle_0, flail_172, stomp_255, dead_8), scale 2.1 = 6.3 m | `tools/build_race_boss.py:1-45,56`, BM §15b,§16 |
| Cannons | 2 Meshy "mega cannon" static meshes (`FNM_CannonArt/SM_fnm_megacannon`, scale 3), 2 cyan `PID_Device_PointLight` each (size 50 %), beam-marker props (Alphabet "I", hidden) | `build_race_boss.py:65-69`, BM §15d |
| Per right pad | 3 shots/cannon: `NS_fnm_muzzle` (0.15 s charge) then `NS_fnm_laser_race` (4.98 m) on the beam axis; first shot also `NS_fnm_impact`; strike VFX (VFX Spawner LightningBolt_03 x4) + explosive device (no damage) at the boss's feet; `KnockBoss` impulse; titan Hurt/flail; coil crackle `NS_fnm_coil` looping from setup | `director:2348-2385,2601-2653,2690-2709`, `fnm_fx.verse:32-66` |
| Per wrong pad | penalty (above) + adds spawner (2 pistol guards) + titan Taunt | `director:2325-2341,2429-2442` |
| HUD | boss bar "THE MAGMA TITAN - FINAL BOSS" (680x44 red `color_block` bar), DIRECT HIT! N TO GO verdict, "Last one: <explanation>" 2.5 s delayed, STEP ON THE RIGHT ANSWER PAD flash | `ui:113,740`, `director:2294,2369,2403` |
| Letters | 4 floating Alphabet props (scale 1.5, 2.3 m up, turn to nearest player, bob) | `build_race_boss.py:73-76`, `director:2569` |
| Audio | boss_fight (Stinger_Threat_01), boss_hit (ExplodingBarrel_Explode_01), hits_left4..1 + direct_hit voice, boss_dead (BlackMonday_Win), boss_down voice | `AUDIO.md:59-61,102` |

### 1.9 Finish + victory area
| Layer | What | Cite |
|---|---|---|
| Finish board | HUD board: FINISH!, medal (gold/silver/bronze colour), time/best/record, accuracy, top-5 session times; hides itself after 10 s; "Walk on!" hint | `director:1905-1972`, `ui:842` |
| Audio | finish (Match_Win_01), new_record (Music_Fantasy_Lrg_Victory_Stinger_02) / new_best, medal stinger, perfect, spaced 1.6 s + announcer lines | `director:2900-2913`, `AUDIO.md:45-48` |
| Finish hallway | gold walls, 6 torches, potted flowers (`CP_PottedFlower01`) + plants | `build_course.py:549-560`, `build_decor.py:294-306` |
| Victory area | giant billboard screen (scale 5, framed) with ALL-TIME BEST heading + 6 text rows cycling per skill every 8 s (persistence via `fnm_save`); 2 Podium lecterns (`PPID_CR_Legacy_Podium` x1.5) with `button_device` NEW RACE / CHANGE SKILL + label billboards; 2 fireworks props `CP_P_Atmospheric_Fireworks` 15 m behind the end wall | `tools/build_finish.py:20-99`, `director:1984-2012,2050` |
| Stale doc | LAYOUT.md:238 says a "100" floats over the finish; `build_decor.finish()` places none (the screen replaced the sign) | `build_decor.py:294-306` |

---

## 2. Boss mode vs race mode

| Capability | BOSS BATTLE (BM) | RACE |
|---|---|---|
| Titan size | 12 m (scale 4), 4 clips, `TITAN_SCALE` 4.0 | 6.3 m (scale 2.1) in the finale only |
| Level-start summon | banner texture `T_fnm_banner` (900x200 burst) + 84 px "LEVEL N" + sub line, announcer level line, 8 boss voice lines (am_onyx, pitched down, echo) | none |
| Anger ring | 5 VFX Spawners (LightningBolt_01) lit L of 5 | none |
| Gate FX | VFX Spawner LightningBolt_02 + Electric_Blast per gate; 4 arch alcoves | none |
| Monsters | Fiend / Brute / Ranged / Red Fiend / Exploding Brute via `creature_spawner` pulses + gate guards, escalating cap and rate | 2 pistol adds on wrong pad; per-hallway guards |
| Nuke | `T_fnm_nuke` mushroom icon, white screen flash `color_block`, nuke VFX (Small_Fire x6), 2nd blast, bigger strike (x5), MEGA NUKE! text | DIRECT HIT! text, strike x4, one blast |
| Weapon chests | 4 gold perches with stepping stones, hold-E chest (TreasureChest mesh + hidden `button_device` + Item Granter), Beacon arrow+badge (Both) + gold Customizable Light | none |
| Colosseum dressing | ~470 Coliseum-kit actors (stands, colonnade, tribune, statues, braziers) by `build_colosseum.py` | plain hall |
| Music | bed per LEVEL (1..5) | bed per tier |
| Cannon scale | 2x mega cannon scale 4, 18.3 m laser | scale 3, 5 m laser (`NS_fnm_laser_race`) |
| Shared | Niagara muzzle/laser/impact/coil, strike, blast, KnockBoss, boss bar, letters, "Last one:", penalty on wrong pad, streak/boost, medal, feed | same code (`FireCannons`) |
| RACE only | hallways, doors/vestibules, connectors, ice, obstacles, per-hallway guards, pickups, glass lids, countdown, clock, pace deltas, rivals strip, victory area/all-time screen/podium, announcer streak lines | |

Sources: BM §3-§9, §15-§16; `LAYOUT.md:132-226`; `director:2601`; `fnm_bossmode.verse:831-1030`.

---

## 3. Proven pipelines and their limits

### 3a. Niagara authored through MCP (`tools/build_fx.py`, 464 lines)
**Toolsets used:** `NiagaraToolsets.NiagaraToolset_System` (CreateNiagaraSystem, GetSystemSummary, AddEmitter, RemoveEmitter, SetEmitterData, SetStackInputData, AddModule, SetRendererData, SetSystemData, GetSystemCompileState, GetStackIssues, GetSystemDependencies), `NiagaraToolset_Info` (UEnum_Info, GetModuleInputValues), `AssetTools` (exists/delete/save_assets/get_dependencies). Per SK:376-382 also `_Component` and `_Assets` toolsets exist (not used). The tool schemas for these were never dumped into `tools/uefn_mcp_ref/` (only 13 other toolsets are).

**Emitter templates used (all `/Niagara/DefaultAssets/Templates/Emitters`):** `StaticBeam` (ribbon beams), `SimpleSpriteBurst` (single big soft sprite), `OmnidirectionalBurst` (sparks / shock ring). `build_fx.py:142-257`.
**Renderers:** sprite (default or `VelocityAligned` streaks) and ribbon (beam, `TessellationMode Disabled` for jagged lightning). Material is always `/Niagara/DefaultAssets/DefaultSpriteMaterial` (round radial falloff, takes colour; HDR values like (3,7,10) read as white-hot). `build_fx.py:161,200`.
**Modules touched:** JitterPosition (lightning), ScaleBeamWidth (curve), ScaleSpriteSize (curve), ShapeLocation (sphere, ring/disc, with axis-angle rotation), AddVelocity (negative = pull-in), GravityForce, Drag, ScaleColor alpha curve, EmitterState loop/duration, SpawnBurst_Instantaneous (count, delayed spawn time), SystemState.

| System | Content | Baked size | Cite |
|---|---|---|---|
| `NS_fnm_laser` | 3 m glow tube, 0.9 m white core, 2 jagged arcs, muzzle + hit flares, 2 spark bursts; 0.5 s hold, gone 0.8 s | length 1830 cm | `build_fx.py:259-289` |
| `NS_fnm_laser_race` | same | 498 cm | `:262,399` |
| `NS_fnm_impact` | flash, glow, ~5 m shock ring (160 blobs), sparks, 4 arcs; 1.6 s | ~5 m | `:303-319` |
| `NS_fnm_muzzle` | 0.15 s charge (cyan specks pulled in), flash 4.8 m, glow, ring round barrel axis, spark cone, 4 arcs; 1 s | tuned to scale-4 cannon | `:348-372` |
| `NS_fnm_coil` | 6 arcs on staggered loops, sparks, pulsing glow; loops forever (~60 particles) | tuned to scale-4 coils | `:375-396` |

**Verse side:** `SpawnParticleSystem(FNM_FX.NS_x_asset, Position, ?Rotation)` returns a `cancelable`; `FnmAimAlong` turns +X onto a direction (`fnm_fx.verse:25-67`).

**Limits (proven):**
- Engine `/Niagara` content only. Session validation rejects `/Game` refs (Fortnite's own `/Game/Effects`), and `/CRD_VFX_Spawner/Assets/Niagara` (53 Epic systems incl. `NS_Explosion_Large/Medium/Small`) cannot be duplicated ("not writable"). SK:392-395.
- Custom HLSL expressions refused (`bSupportsExpressions` false): use curve data interfaces. SK:380.
- Verse cannot set user parameters, so length, colour, size are baked; one system per variant (hence `_race`). `fnm_fx.verse:1-6`.
- Spawn is position + rotation only: no attach to a moving actor, no follow. Global: every player sees it (no agent argument).
- Looping systems need the returned cancelable kept and a once-guard. SK:388.
- Editor does not tick particles while UEFN is in the background; previews use `--preview` warm-up copies.
- Beam / ribbon / sprite / shape-ring / curves are proven. NOT tried: mesh renderer, light renderer, GPU sims, collision, event handlers, SubUV flipbooks, other templates, custom sprite textures/materials (no material authoring tool in MCP; the OBJ-import trick only makes flat Kd or map_Kd materials, probably not particle-ready). Epic docs: "Not all Effect nodes and Emitter settings are available in UEFN" (Beam Effect: no Engine/Plugin Content settings; GPU Sprite: no Emitter/Sphere Location) [dev.epicgames.com effects-and-particle-systems page].

### 3b. Meshy to UEFN
**Static mesh (cannon, `tools/import_cannon.py`):** Meshy GLB -> headless Blender re-export to FBX with embedded textures (`tools/glb_to_fbx.py`, `blender -b --factory-startup --python`) -> `StaticMeshTools.import_file` (FBX/OBJ only, not GLB) -> `lODBias 0` on the base-colour texture (one key per `set_properties`) -> `save_assets`. Meshy's own FBX welded UV seams (blotches). Never Stream / NoMipmaps fails validation ("Texture needs to support streaming"). A deleted mesh name stays registered: import under a new name. Validation warns on LOD0 vertex count at 40k tris (warning only). Blotchy captures are an editor mip-streaming artefact; play is fine. SK:396-403, BM §15d.
**Skeletal mesh + animation (titan, `tools/import_boss.py`):** per clip FBX with its own skin -> `SkeletalMeshTools.import_file {import_animations:true}` -> mesh + `_Skeleton` + `_Anim` (find_assets, then `AssetTools.move`) into `FNM_BossArt/Clip_<clip>` (folder must not look like a Verse identifier) -> placed on `/CRD_AnimatedMesh/Device_AnimatedMesh.Device_AnimatedMesh_C` (props `skeletalMesh`, `animation`, `loop`, `initialState Playing`). Actor scale sticks (12 m titan from a 3 m mesh). SK:346-373.
- Works: Meshy Idle 0, Electrocution Reaction 172 (flail), Angry Ground Stomp 255, Dead 8 (plays once, holds; `PlayReverse` rewinds it).
- Fails / misplays: Chest Pound Taunt 88 and Knock Down 187 (hips turn/tip: flat or spinning on the spot); cause not found (own skeleton, rig-file skeleton, Blender round trip all failed). Untested idea: Meshy has `_inplace` variants for some clips (ids 6xx, e.g. 608, 630, 649, 666-691 in Fighting); not tried.
- Device API is only Play / Pause / PlayReverse (+ TeleportTo / MoveTo). `Play()` never starts a Stopped device; `PlayReverse` on a loop throws it flat; a device parked 30 m under the floor returns in a broken pose. Working pattern: one device per clip, all Playing + looping, swap by `TeleportTo` with resting clips scaled 0.001. So N clips = N copies of the mesh (memory unmeasured; GOALS says the memory panel is GUI-only).
- Fortnite's own skeletal meshes pass the editor but fail StartSession (`ValidationFixup ... IllegalPropertyValue`). SK:348-350.
- Characters themselves cannot be scaled (entity scale reads back, reverts in 3 s); spawner scale not inherited. SK:343-345.
- Meshy rig/animation library is biped (preview URLs under `/animation/preview/biped/`); non-humanoid creature rigs unproven.

### 3c. HUD textures and flat materials
PNG drawn by `tools/make_*_art.py` (no PIL, deterministic) -> one-quad OBJ with `.mtl` `map_Kd` -> `StaticMeshTools.import_file` makes Texture2D `<name>_ncl1_1` -> helper mesh deleted -> `AssetTools.move` -> UI texture settings (TC_EditorIcon, TEXTUREGROUP_UI, NoMipmaps) -> Verse `FNM_Art.T_x` in `texture_block` (tint via `SetTint`, stretch 9-slice-less). A `Kd` colour alone makes a flat Material (`M_fnm_wall_*`), `map_Kd` + material kept makes door faces. Recipe `tools/import_art.py:1-60`; SK:147-152,333-340. Art on hand: check, cross, slate, tile, banner, nuke, door_face_a-d (`tools/art/`). Limits: no PBR (flat colours render lighter than values: bm_stone needed 0.09), UV mapping is the cube's, a PNG dropped into Content is not auto-imported, MCP has no importer for audio.

### 3d. Imported SoundWaves + announcer
Voice lines from local Kokoro TTS (`tools/make_announcer.py`; voices am_michael, am_onyx, bm_george; 53 lines; 48 kHz mono, -13 LUFS; boss profile = -18 % pitch + soft clip + echo). Import is GUI-only (Content Drawer > Import dialog, scripted clicks), then `build_audio.py --announcer am_michael --boss-voice am_onyx` puts each wave on its cue device. Project SoundWaves pass validation. Library sounds pass only from `/Game/Sounds/Creative` and `/CRD_SkilledInteractionDevice`. One `audio_player` device per cue (65 cues, parked underground), `can Be Heard By Instigator Only`, 2D, no attenuation; `volume` accepts > 1 (voice 2.5). Lessons: voice lines buried under same-instant stingers; Fortnite mutes itself when not foreground; the Windows mixer re-mutes the client on relaunch; Aaron's in-game Music slider is 0 on this PC. `AUDIO.md:13-30,82-197`.

### 3e. Post-process devices
`/CRD_PostProcess/SetupAssets/PID_CP_Devices_PostProcess` with `postProcessEffect` = `/Game/Creative/PostProcess/PP_<Name>.PP_<Name>_C`; 34 effects: 70sPrint, 80sCartoon, ActionLines, Blackout, CCTV, Comic, ComicNoir, Crazy, Dark, Desolate, FilmNoir, FilmWarm, Frost, Halftone, HappyPlace, Heatwave, HeavyLinework, HorrorMovie, LowExposure, NeoComic, NeonParty, NightVision, Oak, OldCartoon, Pixelizer, RadialBlur, Rain, Red, Retro, SimpleBlurSharpen, Sepia, Spooky, VHS_Filter, VignetteMaskedColored. `startingStrength 0`, then per-player `BlendIn(agent)/BlendOut(agent)`; blend durations settable. Used: Frost, Sepia, RadialBlur. RadialBlur is the only true blur; PP_Dark only tints (blackout is a HUD `color_block`); PP_Crazy confused Aaron. `PENALTIES.md:51`, SK:171-175.

### 3f. Beacons, lights, other proven devices
- Beacon (`PID_Device_Beacon`): style Arrow / Light Beam / Flare; `beacon Color` Direct + `custom Beacon Color`; badge needs `beacon to Show` Both; `hide HUD Icon at` is a MAX range (set 100 m); badge text and distance did not draw; icon by path fails validation; `particlePropAbsoluteScale` false to scale. SK:404-413, BM §15e.
- Customizable Light (`PID_Device_PointLight`): `lightSize` enum refuses writes, `lightSizePercentage` works (100 floods white, 50 reads as glow); on/off from Verse. SK:414-416.
- VFX Spawner V2 (`PID_Device_VFX_Spawner_V2`): `visual_Effect` enum = DiscoBalls, LaserBeams, AreaOfFog, SpookyGhosts, Balloons, Snow, FloatingSpaceRocks, Bubbles, FallingSparkles, Confetti, FlyingSpaceRocks, DustClouds, Rain, SmallTornado, LightFog, SkyLanterns, RainLight, Waterfall*, MusicalNotes_*, Small_Fire, Insect_Flies, Ambient_Dust, Eyes, LightningBolt_01..03, Bats, Embers, Fireworks, Fog, Leaves, Sparkles, FireworksLarge, RainConcert, SparkRain, Ash; `effectType` Continuous/Burst; `sound_Effect` incl. Explosion, Lightning_Strike, Electric_Blast. No explosion/smoke (Small_Fire is the closest). Global. `LAYOUT.md:200-205`, digest `vfx_spawner_device` has Enable/Disable/Restart only (FD:1951).
- Alphabet 3D letters (`/CRG_Props/.../PPID_CRG_Props_CP_Alphabet_<L>_<hash>`, ~206x201x50, colour option, `bNoCollision`), Number props, Coliseum kit, Arctic/winter props: all placeable gallery props. SK:231-233, `build_decor.py:20-24,70-89`.
- Other: Billboard text (size 8-24, colour/border settable), Button (hold-E), Item Spawner pad, Item Granter, Barrier, Teleporter, Mutator zone, Player Movement Settings, Movement Modulator, Air Vent, Orbit camera, Explosive, Guard spawner, Creature spawner (V2), Animated Mesh. `uefn-mcp` skill sections 49-340.

---

## 4. Available but unused in race

### 4a. PROVEN in this project, not used in the race beats

| Feature | What it would give the race | Status | Source |
|---|---|---|---|
| VFX Spawner V2 (Confetti, Fireworks/FireworksLarge, Sparkles, FallingSparkles, Snow, Embers, SparkRain, Balloons, SkyLanterns, MusicalNotes, DiscoBalls, Ash, Fog/LightFog/AreaOfFog, Rain) | right-door sparkle at the door the player went through, finish fireworks on the VFX not props, falling snow on ice station, embers at tier 5, fog in the arena. Global (all players see it) so fine for celebration/penalty spectacle, wrong for anything that reveals the answer | PROVEN (boss mode gates/anger/perches/strike) | `build_bossmode.py:278-296`, `LAYOUT.md:200-205` |
| Own Niagara systems | per-beat bespoke FX: door-open burst, streak trail, finish confetti cannon, penalty impacts, ice-sparkle ambient, portal swirl. Authoring cost is one function per system in `build_fx.py` | PROVEN (5 systems) | `build_fx.py` |
| Customizable Light / Point Light | colour-graded hallway fill by tier, door-glow, flash on penalty, finish celebration, arena threat light. Global | PROVEN (chest lights, cannon lights) | SK:414-416, `build_bossmode.py:243-244,273` |
| Beacon | arrow/pin over the finish or the arena platform, "next station" guidance for lost players (do NOT mark the right door: global). Per-player visibility unknown | PROVEN | SK:404-413 |
| Post-process per player (34 effects) | persistent tier grading (FilmWarm to Retro to NeonParty to Spooky) blended on station entry; boost look (ActionLines / VignetteMaskedColored / RadialBlur light); finish PP_HappyPlace; arena PP_HorrorMovie; ice PP_Frost light. Per-player so safe | PROVEN (3 of 34) | `build_rigs.py:76-83`, SK:171-175 |
| Meshy static props | custom door arches, trophies, signage, tier set pieces, podium upgrade, mascot statues | PROVEN (cannon) | `import_cannon.py` |
| Meshy animated characters on Animated Mesh | idle mascots/crowd in hallways, podium dancers with Meshy Dancing clips, referee, boss variants per tier | PROVEN (titan) with clip caveats | `import_boss.py`, SK:346-373 |
| Verse UI texture_block / color_block | HUD flashes: boost speed-lines overlay, streak badge art, confetti frames by `SetImage` swaps (flipbook), vignettes, medal art on finish board | PROVEN (static); flipbook swap is DOC (`texture_block.SetImage`, UD:1031+) | `ui:84-170` |
| Imported SoundWaves | new music beds, custom stingers, crowd cheers, door SFX, ambience; GUI import | PROVEN | `AUDIO.md:138-157` |
| Per-player audio devices | personal reactions only; positional/ambient audio would need a non-instigator audio_player (2D flag currently) | PROVEN 2D; 3D = DOC | `build_audio.py:75-86` |
| Gold chest (static mesh + hidden button + Item Granter) | reward/agency chests (G6 item 4: coins, shop, lifelines) | PROVEN (boss perches) | BM §7, `build_bossmode.py:219-225` |
| Item Spawner pads with other consumables | Chiller (IceGrenade), Impulse (KnockGrenade), Smoke, Sticky, Stink bomb pads | listed in skill, not placed: DOC | SK:243-245 |
| Creature spawner (Fiend, Brute, Ranged, Red Fiend, Exploding Brute, Megabrute, Ice variants, Poison Fiend, Rush/All Random) via Enable/Disable pulse | per-hallway creature hazards, ice station Ice Fiends, finale adds | PROVEN (boss mode) | `LAYOUT.md:194-199`, BM §14 |
| Air Vent tilted, Movement Modulator (speed < or > 1) | launch pads, boost lanes, slowing mud zones as terrain | PROVEN | SK:88-89,106-109 |
| Mutator zone + Player Movement Settings | low-friction, acceleration cap; also gravity/jump? (Common settings group not fully listed: ?) | PROVEN for friction | `build_course.py:141-143` |
| Orbit camera device | victory orbit, finish cam, bigger penalty view | PROVEN (penalty cam) | `build_rigs.py:53-57` |
| Prop MoveTo / TeleportTo (`creative_prop`) | moving scenery, bobbing letters, rising platforms | PROVEN | `director:2241,2585` |
| Barrier ignore lists, Teleporter, Trigger V2 `trigger_fit` | per-player gates/doors, secret rooms (G6 item 10) | PROVEN | SK:93-96 |
| Billboard text | big signage, per-station chalk, leaderboards | PROVEN | `build_finish.py` |
| Explosive device (no-damage, knockback None..Super High) | scripted booms at traps, shockwaves | PROVEN | `build_bossmode.py:291-294` |

### 4b. DOCUMENTED (digest or Epic docs), never tried here

| Feature | What it would give the race | Status | Source |
|---|---|---|---|
| `vfx_creator_device` (Begin/End/Toggle with `Agent`, `BeginForAll`, `SpawnAt(Agent)`) | per-player VFX, and Epic's page says custom Niagara can be referenced by devices and "selected to replace native effects" i.e. our own `FNM_FX` systems might drive it. Fixes the "global VFX" limit | DOC; whether it accepts project Niagara systems and whether MCP can set the property = ? | FD digest `vfx_creator_device`; dev.epicgames.com effects page |
| `cinematic_sequence_device` + Sequencer Level Sequence (Play/Stop/Pause/SetPlayRate, `Play(Agent)`, StoppedEvent; tracks: animation, transform, audio, camera) | intro fly-through, finish cutscene, boss-entry cinematic, per-player cameras | DOC; needs a Level Sequence asset: no Sequencer tool in the 13 dumped toolsets, GUI authoring likely; Python `execute_tool_script` is import-restricted. Memory heavy per Epic | FD digest; dev.epicgames.com cinematic device page |
| `skydome_device` (Enable/Disable; sun, moon, stars, clouds, fog, light colour in details) | sunset hallways, night arena, tier-coloured skies; the race has no sky control at all | DOC; global; settings must be set through `set_properties` (properties unknown, UEFN closed) | FD `skydome_device` |
| Island settings (`IslandSettings0`, 521 properties) | may carry time-of-day/lighting/fog keys; only teams/DBNO/join/damage/building/maxPlayers were read | ? (list never inspected for sky/lighting) | SK:215-221 |
| `hud_message_device` (`Show(Agent, Message, DisplayTime)`) | built-in per-player toasts, alt to Verse HUD flashes | DOC | FD |
| `hud_controller_device` (hide/show HUD parts per player/team) | strip default HUD clutter; clear minimap corner | DOC | FD |
| `map_indicator_device`, `player_marker_device` (label/health/distance on minimap), `map_controller_device` | rival markers on minimap, objective pulses toward next station | DOC | FD |
| `player_reference_device` (project a hologram of an agent, display text, relay stats) | hologram of the leader / session winner at the victory area; "ghost" of top time holder | DOC; hologram needs the player present | FD |
| `dance_mannequin_device`, `character_device` (mannequin visualising a character, performs emotes) | champion mannequin dancing at the podium (G6 item 8), cheering crowd | DOC | FD, `GOALS.md:294-296` |
| `crowd_volume_device` ("spawns a crowd to cheer you on") | spectators in finale arena / victory area | DOC | FD |
| `progress_based_mesh_device` (mesh transitions with progress) | a tower/rocket/trophy that grows with the class's total correct answers or a player's progress | DOC (added in 36.00 notes) | FD, uefncentral 36.00 notes |
| `accolades_device` | Battle Pass XP for kids who complete the island | DOC | FD |
| `tracker_device`, `timer_device`, `stat_creator_device`, `score_manager_device`, `round_settings_device`, `end_game_device` | native HUD objectives, stopwatch/countdown, scoreboard stats, win conditions (we use Verse + persistence) | DOC | FD |
| `elimination_feed_device` | custom feed lines (we have our own feed) | DOC | FD |
| `popup_dialog_device`, `conversation_device` | instructions, NPC dialogue with choices | DOC | FD |
| Patchwork music (`music_manager_device`, `note_sequencer`, `drum_sequencer`, `omega_synthesizer`, `instrument_player`, `song_sync` etc.), `radio_device` (curated music per agent), `audio_mixer_device` (bus mixes) | procedural/adaptive music that reacts to streak/boss HP, ducking music under the announcer | DOC; per-player routing = ? | FD:3860+ |
| `bouncer_device` (BouncedEvent), `crash_pad_device` | jump pads in connectors, bounce reward | DOC | FD |
| `skydive_volume_device` | pneumatic tubes ("unique traversal"), launch lanes | DOC | FD |
| `grind_rail_device`, `vine_rail_device` | rail connector, "Detour" penalty (PENALTIES), traversal variety (G6 item 6) | DOC | FD, `PENALTIES.md:57` |
| Vehicle spawners (40+: sports car, sedan, driftboard, surfboard, quadcrasher, shopping cart, baller, hammerhead, helicopter, UFO, X-wing, tanks, boats...) | go-kart / driftboard / surfboard straights as connectors (G6 item 6) | DOC; glass lids + 10 m corridor widths untested with vehicles | FD |
| `water_device` (BeginVerticalFilling) | flood penalty, water slide connector | DOC | FD, `PENALTIES.md:49` |
| `physics_boulder_device`, `pinball_bumper_device`, `trick_tile_device`, `fire_volume_device`, `damage_volume_device`, `automated_turret_device`, `sentry_device`, `wildlife_spawner_device` | the unbuilt PENALTIES.md catalog: boulder, pinball, trapdoor, fire floor, turret, chickens | DOC (listed in PENALTIES.md "Catalog" from the 42.30 digest) | `PENALTIES.md:39-57` |
| `prop_mover_device` (Begin/End/Advance/Reverse, speed, events incl. `AgentHitEvent`) | moving obstacles without Verse `MoveTo` loops | DOC | FD |
| `prop_manipulator_device`, `hiding_prop_device`, `color_changing_tiles_device`, `collectible_object_device`, `firefly_spawner_device`, `item_shop_device`, `vending_machine_device`, `earth_sprite_device`, `powerup_device` family (`visual_effect_powerup_device` = glow/outline on pickup, `health_powerup`, `damage_amplifier_powerup`, `grind_powerup`) | coins/collectibles, shop (G6 4), colour-reveal floors, glow-outline streak reward | DOC | FD |
| Gameplay camera devices: `gameplay_camera_fixed_point/fixed_angle/first_person`, `gameplay_controls_side_scroller` | side-scroll hallways, fixed finish camera, first-person penalty | DOC (orbit proven) | `PENALTIES.md:52`, FD |
| `storm_controller_device` family, `capture_area_device`, `objective_device`, `timed_objective_device`, `race_manager/race_checkpoint` | storm elimination mode (G6 5), co-op gate, native race checkpoints (Rocket Racing vehicle-oriented) | DOC | FD |
| `npc_spawner_device` (NPCs from Character Definition assets) | custom NPC with behaviour/mesh | DOC; Character Definition creation is a content-browser GUI asset, not reachable by MCP: ? | FD |
| `fort_character.GetPlayAnimationController()` -> `Play(animation_sequence, layer, rate, blend...)` | play an imported/library animation on a player or NPC (victory dance, penalty pose) | DOC. Imported clips ARE exposed to Verse as `animation_sequence` (e.g. `FNM_BossArt.Clip_dead.A_fnm_titan_dead`, project Assets digest). Whether a Meshy-skeleton clip plays on the Fortnite mannequin skeleton = ? (almost certainly retarget-incompatible); Fortnite emotes: `PlayEmote` only on mannequins, not players | FD:9588-9660; Assets digest; `PENALTIES.md:59` |
| `creative_prop.SetMaterial / SetMesh` | swap a prop's look at runtime (door flash, neon sign) | DOC; GLOBAL (not per-player); materials only flat colours/textures from the OBJ trick | FD:8990-8993, SK:153-155 |
| Scene Graph components in Verse (`particle_system_component`, `sound_component`, light components point/spot/rect/capsule/directional, `camera_component`s, `keyframed_movement_component`, `mesh_component`) | entity-based lights/sounds/particles attached to moving things | DOC; Beta, "not by default Fortnite/FAB assets", no text component in 42.30 | VD:10+, dev.epicgames.com scene-graph-known-issues, SK:153-155 |
| Verse UI `material_block` (shows a `material`) | animated HUD effects if an animated material existed | DOC; MCP cannot author materials | UD:1072 |
| Wind, zipline, leaderboard devices | no such class in the 42.30 digest (grep zipline/wind/leaderboard: no device); leaderboard is built from persistence + billboards (ours) | NOT AVAILABLE | FD |
| Gravity / "moon gravity" | `mutator_zone_device` doc says custom effects "e.g. gravity, no build, no weapons"; PENALTIES.md lists `player_movement_settings_device` for moon gravity | DOC; never set. Mutator zone's `bAllowWeaponFire` was the one option learned | FD:3483, `PENALTIES.md:48` |

### 4c. Highest-leverage, lowest-risk candidates (my read, for the review)
1. Right-answer world feedback is zero today: a Niagara burst at the door the player ran through (global is fine; it does not reveal the answer because the player is already through) + streak trail + boost post-process. Same pipeline as the lasers.
2. Sky/lighting: skydome + a Customizable Light or two per tier is unexplored; the hallways inherit Blank-template lighting.
3. Finish: replace/add to prop fireworks with VFX Spawner FireworksLarge + a Niagara confetti cannon + crowd_volume + a Meshy dancer mannequin on the podium.
4. Meshy Dancing/Daily clips on Animated Mesh for mascots (reuse the clip-swap pattern, avoid root-motion clips).
5. Per-player VFX via `vfx_creator_device` is the one unknown that would remove the "global VFX" limit: worth a 10-minute probe once UEFN is open (`ListDeviceAssets` filter "VFX" / "Creator").

---

## 5. Hard constraints (proven NOT possible)

| Constraint | Evidence |
|---|---|
| No per-player world text: `billboard.SetText`, `creative_prop.SetMaterial/SetMesh`, `debug_draw.DrawText` are global; Scene Graph has no text component in 42.30. Per-player text = Verse UI only | SK:153-155, `GOALS.md:339-343` |
| Characters cannot be scaled (entity scale reverts in 3 s; spawner/actor scale not inherited) | SK:343-345, BM §15a |
| Fortnite's own skeletal meshes (e.g. `TidalCrane_Boss_Creature`) fail StartSession validation on Animated Mesh | SK:348-350, BM §15a |
| Imported skeletal meshes pass; FBX/OBJ only (no GLB import); Meshy FBX welds UV seams | SK:351-353,401-403, `import_cannon.py:2-3` |
| Sound paths: only `/Game/Sounds/Creative` and `/CRD_SkilledInteractionDevice` pass; Rocket Racing, `/FNGameplayCues`, `/PoppySoap`, `/ShockwaveMace`, `/MudGameplay`, `/SpireSharedAssets`, `/CRD_HenchmanSpawner`, `Fort_Traps`, `Fort_GamePlay_Sounds`, `Fort_Music`, `Fort_Human_Barks`, `Athena` all refused | `AUDIO.md:82-88`, `build_audio.py:62-66` |
| Audio import has no headless route (wav in Content is never picked up; no AssetTools import); GUI automation only; texture import only via the OBJ trick | `AUDIO.md:138-139`, SK:147-148 |
| Placed Fortnite traps (BR and Figment floor spikes, actor class) fail island validation | SK:84-85, `PENALTIES.md:31-35` |
| Epic library Niagara (`/CRD_VFX_Spawner/Assets/Niagara/*`, 53 systems) cannot be duplicated; `/Game/Effects` fails validation; custom HLSL refused; Verse cannot set Niagara user parameters | SK:380-395 |
| Never Stream / NoMipmaps textures fail validation; import default LOD bias 1 drops the top mip | SK:396-400 |
| Adding a StaticMeshComponent to a placed Creative prop: editor-only, respawned without it in play | SK:156-158 |
| Raw `/Game/...` static mesh reference (e.g. `CP_Spooky_Letter_A`) fails validation ("Disallowed reference") and opens a modal that hangs every MCP call | SK:158-161 |
| A placed mesh actor's `NoCollision` set in the editor does not hold in play (blocked players); `bNoCollision` property on gallery props does | SK:161-163,230-233 |
| Door wall frame is a runtime material instance that ignores `overrideMaterials` | SK:165-166 |
| Borderless billboard text did not render in play; default text pale grey; size 8-24 | SK:167-168,264-266 |
| Engine basic shapes (`add_to_scene_from_asset` cubes) are scenery: no `creative_prop`, Verse cannot find or move them | SK:296-297 |
| Hero Chest: renders as white pod, rank loot options refused | SK:223-227 |
| Animated Mesh: Play() never starts a Stopped device; PlayReverse breaks loops; underground parking breaks poses; Chest Pound / Knock Down clips misplay | SK:358-372 |
| Player physics: `SetLinearVelocity` does nothing to players; `ApplyLinearImpulse` moves NPCs only; per-tick `TeleportTo` arcs are choppy | SK:103-109,298-299 |
| `movement_modulator` duration not settable (re-activate every 2.5 s) | SK:176-177,202 |
| Guard spawner silently refuses some weapons (set returns True, list reads empty); creature spawner `SpawnAt` refused (use Enable/Disable pulse) | SK:123-125, BM §14 |
| Elimination camera overrides the orbit camera device | SK:111-113 |
| `disguise_device` only default human skins; no forced emotes on players | SK:178, `PENALTIES.md:59` |
| Beacon: HUD icon text/distance do not draw; icon by path fails validation | SK:409-412 |
| `lightSize` enum on Customizable Light refuses writes (percentage works) | SK:414-416 |
| VFX Spawner enum has no explosion or smoke; explosive knockback has no "Large" | `LAYOUT.md:203-207` |
| No camera shake, NPC colour/scale/emote API known | BM §13,§6, `GOALS.md:47-49` |
| Default HUD font lacks check/cross glyphs; minimap owns top-right corner of HUD and draws over Verse UI | SK:127-128,185-186 |
| Verse persistence starts empty in each UEFN test session (unverified for published versions) | SK:272-273, `GOALS.md:105-107` |
| Editor does not tick Niagara in the background; editor captures show low mips | SK:396-399, `build_fx.py:27-29` |
| No MCP publish tool; private version = GUI "Launch Memory Calculation"; scripted clicks denied by the classifier | SK:281-284 |
| Mint Gaussian-splat worlds cannot be rendered in UEFN (no splat renderer; the collider GLB alone is not the world) | derived: mint-gg skill describes Spark/WebGL runtime only. UEFN has no splat support in the 42.30 digest (inference, unverified) |
| Island memory budget: unmeasured (panel is GUI-only); first thing to watch when adding characters, 2K textures, or per-clip device copies | `GOALS.md:376-380` |

---

## 6. Credits (checked 2026-10-13, free calls only; nothing spent)

### Balances
| Account | Balance | Detail |
|---|---|---|
| Meshy | **1,468** | permanent 1,312 + monthly 156; monthly resets 2026-10-14T02:37Z (rollover unverified: assume the 156 are use-it-or-lose-it) |
| Mint | **7,580** of 10,000/month | Explorer tier, active; 2,420 used (the 2026-09-23 explorer tree pack); additional 0, usage credits 0; period ends 2026-10-21T16:55Z (8 days; unused monthly credits likely do not roll); `requiresApprovalByDefault: true`, `writeToolEligibility: not_authorized_by_context` (write tools are gated) |
| Mint existing assets | 10 | 2 worlds (Moonlit Island Vista, Cartoon Island Adventure, final), 1 preview-stage world, 1 asset pack (4 trees) + 4 models, 1 Leaf Mantle Druid (humanoid, T-pose, riggable) | 

### Meshy price list (credits; MCP tool header, matches docs.meshy.ai pricing as of 2026-10-12)
| Operation | Cost |
|---|---|
| text-to-3D preview (mesh only) | 20 (meshy-7.1 / latest / meshy-6); 5 (meshy-6-lite, t2, t2.5) |
| text-to-3D refine / retexture | 10 (15 at 8K) |
| image-to-3D / multi-image, meshy-7.1 / latest / 6 (mesh only; +2K/4K tex; +8K tex) | 20; 30; 35 |
| same, meshy-6-lite | 5; 15; (2K only) |
| same, meshy-t2 / t2.5 (single image) | 5; 15; 20 |
| Ultra geometry (`geometry_resolution` 2k/4k) | +5 on meshy-7.1 |
| remesh, rig (incl. walking + running), uv-unwrap | 5 each |
| animate (library clip) | 3 per clip (154 "Fighting" entries incl. in-place variants; also WalkAndRun, BodyMovements, DailyActions, Dancing) |
| text-to-motion | 10 prime / 3 swift |
| convert, resize | 1 |
| repair printability, multicolor, auto-split | 10 |
| creative lab | 36 (keycap 62, fidget-collapsible 6) |
| text-to-image / image-to-image | nano-banana 3, nano-banana-2 6, nano-banana-2-lite 3, nano-banana-2-1 4, nano-banana-pro 9; GPT Image 2 family 9 text / 12 image |
| balance, status, list, download, analyze printability, animation library, usage | free |

Project actuals: Magma Titan = 62 (concept nano-banana-pro 9 + image-to-3D textured 40k 30 + rig 5 + 6 clips x 3 = 18); mega cannon = 39 (9 + 30). Balance went 1507 -> 1468 for the cannon (`BOSS_MODE.md:605`). Other Meshy facts: GLB results come normalised (longest side 1.9 units), 2K textures; this project asked for 40k triangles on both hero assets.

### Mint price list (credits; 1 credit = $0.0008)
| Operation | Cost | Source |
|---|---|---|
| World, fast: preview + final | 100 + 150 = 250 | skill mint-gg (`pricing:estimate` 2026-09-16) |
| World, standard (MCP default) | 150 + 1,500 = 1,650 (balance tool confirms preview 150, world final 1,500) | skill + `get_credits_balance` |
| World, production | 200 + 3,000 = 3,200 | skill |
| Single model, fast / standard / production | 123+125 / 173+625 / 223+375 | skill (estimate 2026-09-22) |
| 4-item asset pack, fast estimate | 492 + 500 = 992; ACTUAL billed 2,420 (292 + 2,128) | skill: estimates unreliable, price approval separately |
| Audio, PBR material, material pack, image, video, animation/rig, optimize, retopology | NOT PUBLISHED; MCP has no estimate tool; REST `pricing:estimate` needs an API key we do not have; docs pages list no rates | docs.mint.gg llms.txt |

### What N credits buys
| Budget | Buys |
|---|---|
| Meshy 62 | one hero animated character (concept + textured 40k mesh + rig + 6 clips) |
| Meshy 39 | one hero static prop (concept + textured mesh) |
| Meshy 30 | text-to-3D prop (preview 20 + refine 10) with no concept image |
| Meshy 15 | a lite textured prop (meshy-6-lite image-to-3D 2K) |
| Meshy 9 | a nano-banana-pro 2D image (HUD art, banner, concept); 3 for a plain nano-banana |
| Meshy 3 | one extra animation clip on an existing rig; 10 for a custom text-to-motion clip |
| Meshy 1,468 | ~23 titan-class characters, or ~37 hero props, or ~97 lite props, or a mix: e.g. 8 characters (496) + 12 props (468) + 40 extra clips (120) + 80 images (240) = 1,324 |
| Mint 7,580 | ~30 fast single models (248 each), or ~9 standard (798), or a handful of packs (budget ~2,400 each given the 2026-09-23 overrun), or ~30 fast worlds. Worlds are not usable in UEFN (see section 5). Audio/material/image prices unknown: ask Mint for one cheap audio/material job and read `get_credits_balance` before/after to learn the rate |

Where credits matter for UEFN specifically: Meshy = characters, props, clips, 2D art. Mint = audio (SFX / music loops, imported as SoundWave via the proven GUI path), a different 3D model vendor, a second animation library, images. Mint worlds / splats / video / PBR sets have no supported landing in UEFN as far as the project has shown (video_player_device shows "curated videos"; no Material authoring tool in MCP).

---

## 7. Unverified / shakiest assumptions
- Every status above is from docs, code and past play logs; I ran nothing. UEFN is closed, so no device-catalog probe (`ListDeviceAssets`) was possible: vfx_creator, skydome, cinematic, hud_message, etc. are confirmed in the Verse digest only, not as placeable assets in this project.
- `tools/uefn_mcp_ref/` has no dump of the Niagara or SkeletalMesh toolsets, so tool names for those come from `build_fx.py` and the skill; a fresh `list_toolsets` may reveal more (material, texture, animation, sequencer).
- "Global VFX" means: `vfx_spawner_device` and `SpawnParticleSystem` have no agent parameter in the digest. Not play-tested with two players.
- Meshy `_inplace` clip ids and the "root motion explains the misplayed clips" idea are my inference from the id list, not tested.
- Mint credits "do not roll over" and Meshy monthly "do not roll over" are assumptions from the field names; neither was confirmed in docs.
- The mint-gg/meshy-3d skills contain an inline Meshy API key; not repeated here.
- LAYOUT.md:238 "100 over the finish" is stale vs `build_decor.finish()`.
