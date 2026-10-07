# Brief A — Sound layer for the fortnitemath island (library SFX, UEFN wiring)

You are building GOALS.md **G6 item 1** (the sound half; the announcer VO is another builder's job and a later
import). Read these first, in order; they are the spec and the gotchas:

1. `D:\PyCharm Projects\fortnitemath\CLAUDE.md` (whole file: tools, Verse line-ending rule, sync + BuildAll rule)
2. `~/.claude/skills/uefn-mcp/SKILL.md` (whole file: MCP calling pattern, Verse tags vs device refs, property
   writes + save, device options cache, play sessions)
3. `GOALS.md` §G6 (the plan), `console/README.md` §3 (tagging), `maps/starter/LAYOUT.md` (the course)
4. `console/verse/fnm_rig.verse` and `tools/build_rigs.py` (the pattern: a Python builder places devices, tags
   them with Verse tags, the director finds them by tag at OnBegin and logs what it found)
5. `console/verse/fnm_director.verse`: `Countdown` (~line 1574), `HandleDoor` (~922), `Punish` (~1122),
   `FinishPlayer` (~1331), `Boost` (~1607), `WatchSkip` (~1002), `GuardLoop` (~606), `Pick` (~792),
   `AdvancePlayer` (~1013). `console/verse/fnm_tags.verse` (tag classes), `console/verse/fnm_penalties.verse`.

## Repo facts (checked 2026-10-07)
- Path `D:\PyCharm Projects\fortnitemath`, Windows 11, branch `master`, clean tree. Python: `.venv/Scripts/python`.
- Tests: `.venv/Scripts/python -m pytest -q` → **8685 passed** in 13 s. Keep it green.
- UEFN 42.30 is OPEN with the project loaded; MCP answers at `http://127.0.0.1:8000/mcp`. Client:
  `tools/uefn_mcp.py <toolset> <tool> '<json>'`; importable as `import uefn_mcp as u; u.call(toolset, tool, args)`.
  From Git Bash prefix MCP calls with `MSYS_NO_PATHCONV=1` when an argument starts with `/`.
- After any Verse edit: `.venv/Scripts/python -m fnm sync starter` then
  `.venv/Scripts/python tools/uefn_mcp.py ValkyrieToolset.VerseToolset BuildAll '{}'`. A clean build is the proof;
  read the error list if not.
- Verse files are LF. Edit them with the Edit tool or `tools/patch.py`; never `write_text` from Python.
- Headless run: `.venv/Scripts/python tools/playtest.py --until "finished run 1,stuck at stage" --timeout 240`
  relaunches the session and prints the director's `FNM:` log lines. Test hooks are `@editable` defaults on the
  director (`DebugAutoPick`, `DebugAutoRightAnswers`, `DebugAutoWrongAnswers`, `DebugStartStage`…): flip them in
  the Verse default with `tools/patch.py`, sync, BuildAll, run, and **flip them back to ship values** (0 / false / -1)
  before you finish. Screenshots never take the foreground. Only simulated keys do: for this session you MAY bring
  the client forward briefly if background audio is muted (see Verification), then leave it.

## Facts I probed for you (checked unless marked belief)
- Device: `PID_CP_Devices_CRD_AudioPlayer`, asset path
  `/CRD_AudioPlayer/SetupAssets/PID_CP_Devices_CRD_AudioPlayer.PID_CP_Devices_CRD_AudioPlayer` (from
  `DeviceToolset.ListDeviceAssets {"nameFilter":"audio"}`). `PlaceDevice` works on it. It is NOT a Verse
  ScriptDevice, so `DeviceToolset.ListDeviceProperties/GetDeviceProperties` reject it; use
  `ObjectTools.list_properties {"instance": ref(path)}` and `get_properties {"instance":…, "properties":[…]}` /
  `set_properties {"instance":…, "values": json.dumps({...})}` exactly as `build_rigs.props_set` does.
- `list_properties` on the actor shows the sound lives on a **component**: `creativeAudio`
  (`/Script/CRD_AudioPlayerRuntime.CreativeAudioComponent`), beside `creativeRegisteredPlayersManager`,
  `creativeAttenuationViz`, min/maxSphereViz. Get the component's refPath (`ActorTools.get_components`, or the
  actor's property value) and `list_properties` on it to find the sound asset property and the audibility /
  spatialisation / volume options. Belief: the Creative device's user options are the usual "Play for: everyone /
  registered / instigator", "Play location: player / device", looping, volume, attenuation radius. Find the real
  names; report them.
- Verse API (from the 42.30 digest): `audio_player_device` has `Enable/Disable`, `Play(Agent)`, `Play()`,
  `Stop(Agent)`, `Stop()`, `Register(Agent)`, `Unregister(Agent)`, `UnregisterAll()`, `Show/Hide`.
- Assets: `AssetTools.find_assets {"folder_path":"", "name":"<substring>", "asset_type":{"refPath":
  "/Script/Engine.SoundCue"}, "recursive":true}` (also `/Script/Engine.SoundWave`,
  `/Script/MetasoundEngine.MetaSoundSource`). The library is huge (16,652 cues). Names found 2026-10-07, use these
  as the first candidates (find their full paths; prefer the SoundCue, fall back to the SoundWave of the same name):
  `DM_Countdown_Three_01_Cue`, `DM_Countdown_Two_01_Cue`, `DM_Countdown_One_01_Cue`, `DM_Countdown_Go_01_Cue`
  (Rocket Racing's countdown VO), `DM_CheckpointReached_01` / `MSS_DM_CheckpointHit`, `DM_Turbo_Bonus_Success_Cue`,
  `DM_Turbo_Bonus_Fail_Cue`, `MSS_DM_UI_WrongWay_OneShot`, `DM_WrongWay_Countdown_OneShot`,
  `SC_VividRazorVault_Door_Open`, `Fort_XP_LevelUp_InWorld_Cue`, `DM_Turbo_ChargeGained_LevelOneCue` / `LevelTwo_Cue`
  / `LevelThree_Cue`, `DM_BoostPad_Cue`, `DM_Crowd_RaceFinish_Cue`, `MSS_DM_UI_FinishLine_Wipe`,
  `Sting_VictoryCrown_Match_Victory_Cue`, `EmoteFoley_Applause_Cue`, `Henchmen_Death_Stinger_Cue`,
  `Device_HenchmenSpawner_GuardSpawn_Cue`, `SC_GliderOpen_SnapFreeze`, `ShockwaveMace_LaunchWhoosh_Cue`,
  `DM_321_appear_Anim_whoosh_Cue`, `Alarm_Heist_GlassBroken_Alert_Cue`, `Mx_Sting_Heist_Fail_Cue`,
  `SkilledInteract_Success_Cue`, `SkilledInteract_Fail_Cue`, `SkilledInteract_Perfect_Cue`,
  `IP_SC_PoppySoap_Announcer_VO_Flawless` / `_Fight` / `_Laugh` (a real announcer voice, use for `perfect` /
  `go` fallback / a taunt on a wrong door if it fits). Search more by name for the penalties (try "Mud",
  "Squish", "Dizzy", "Stun", "Daze", "PowerDown", "Shutdown", "Lights", "Ice", "Frozen", "Spike", "Spear").
  Pick by name AND duration: read the asset's `Duration` with `get_properties` where available; a cue for a
  one-shot moment should be ≤ 2.5 s, a stinger ≤ 4 s, a loop only for the music beds.
- Custom wav import does NOT work headlessly (tested: a wav dropped in `Content/FNM_Audio/` is not picked up;
  the scripting toolset has no `unreal` module). Do not try. The announcer VO arrives later through the GUI.
- `tools/build_rigs.py` parks rigs at `PARK = (-4000, -8000, -1500)` in rows of `PITCH = 800`. Park the audio
  devices on their own row at `(-4000, -11000, -1500)` stepping +800 in X per device; first confirm with
  `SceneTools.find_actors` that nothing already stands there.

## Deliverables (numbered; names are fixed)
1. **`console/verse/fnm_audio.verse`** (new): `fnm_cue := enum { … }` with EXACTLY these members (other builders
   and the announcer pack use the same ids; keep them even where no library sound is wired yet):
   `Countdown3, Countdown2, Countdown1, Go, Correct, CorrectRetry, Wrong, DoorOpen, Boost, Streak2, Streak3,
   Streak4, Streak5, Streak6, Streak7, Perfect, Finish, NewBest, NewRecord, MedalGold, MedalSilver, MedalBronze,
   PenaltyFreeze, PenaltySpike, PenaltyMud, PenaltyDizzy, PenaltyBlackout, PenaltyYeet, NoSkip, GuardsUp,
   Welcome, Choose, MusicT1, MusicT2, MusicT3, MusicT4, MusicT5`.
   `FnmCueTag(Cue:fnm_cue):string` → the Verse tag name `fnm_cue_<snake_id>` (`fnm_cue_countdown3`,
   `fnm_cue_correct_retry`, `fnm_cue_penalty_freeze`, `fnm_cue_music_t1` …). A class `fnm_audio` built once at
   director OnBegin that finds one `audio_player_device` per cue by tag (the tag classes go in `fnm_tags.verse`,
   same style as the existing ones), with `Play(Player:player, Cue:fnm_cue):void` (no-op when the cue has no
   device; every call logs `FNM: cue <snake_id>` so a play log proves the wiring), `Stop(Player, Cue)`, and
   `PlayAll(Cue)` for the whole-island moments. Startup log line: `FNM: audio: N of M cues wired, missing: a, b, c`.
2. **Director hooks** (`fnm_director.verse`), each one line where the event already happens:
   - `Countdown`: `Countdown3/2/1` on each beat, `Go` with GO!.
   - `HandleDoor`: right door → `Correct` if first try else `CorrectRetry`; then on first-try streaks the milestone
     cue `Streak2..Streak7` for streak 2..7 and `Streak7` again for every streak above 7. Wrong door → `Wrong`,
     then the penalty's own cue (`PenaltyFreeze` … `PenaltyYeet`) from `Punish` at the moment the effect starts.
   - `AdvancePlayer` (barrier opened for the player): `DoorOpen`.
   - `Boost` start: `Boost` (only when a boost actually starts, not on every tick).
   - `WatchSkip` sent-back: `NoSkip`. `GuardLoop` guards up: `GuardsUp` for the players on that station (if the
     loop knows them; otherwise `PlayAll` is acceptable, say which).
   - `FinishPlayer`: `Finish` always; then `NewRecord` if island record, else `NewBest` if new best; then the medal
     cue; `Perfect` when first-try = total. Space them with short sleeps in a spawned block so they do not pile up.
   - `Pick`: `Choose` when the picker opens for a player (once per join), `Welcome` on join.
   - Music beds: when a player's station tier changes (`StationTier`), `Stop` the old tier's bed for them and
     `Play` the new one; stop it at the finish and while the picker is up. Wire real loops ONLY if you find five
     fitting looping tracks of rising intensity in the library (`Mx_`/`Music_` names with `Loop`, Rocket Racing
     `DM_Music_*`); otherwise leave the hooks and the tags in place, wire nothing, and say so. Do not spend more than
     ~20 minutes on music; the SFX are the deliverable.
3. **`tools/build_audio.py`** (new): idempotent via actor tag `fnm_audio` (delete-then-place, like `build_rigs.py`).
   A `CUES` table at the top: cue id → (asset path, options) — the single place the mapping lives. Places one
   audio player per wired cue on the park row, sets the sound on the `creativeAudio` component, sets the options so
   `Play(Agent)` is heard by THAT player only, non-spatial (2D, at the player, full volume, no attenuation fall-off)
   — except `Finish`, `GuardsUp` which may be spatial at the device if you also move those devices to the finish
   hallway / the station. Tags each device with the Verse tag from deliverable 1 (reuse `build_course.verse_tags`),
   labels it `FNM_Cue_<Id>`, saves. One property write per call like `props_set`, and READ BACK every value you set
   and print it (the device options cache gotcha in CLAUDE.md: a combined write silently kept the old value).
   `--list` prints the placed devices with their sound and the read-back options; `--probe NAME` prints the
   find_assets matches for a name with class and duration, for choosing sounds.
4. **`tools/hear.py`** (new): records the default speaker's WASAPI loopback with the `soundcard` package (already
   installed in `.venv`; `sc.default_speaker()` → `sc.get_microphone(id, include_loopback=True)`) for
   `--seconds N` to `%TEMP%/hear.wav`, then prints an onset table: times where the 50 ms RMS rises more than
   `--threshold` (default 12 dB) above the previous 500 ms, so a run's log lines can be matched to sounds.
   `--log <file>` or `--marks "t1,t2,…"` prints each mark with the nearest onset and the delta. It must run in the
   background (`run_in_background`) while a playtest runs in the foreground.
5. **Docs**: `console/README.md` §3 gains the `fnm_cue_*` tags and `tools/build_audio.py`; a short
   `console/AUDIO.md`: the cue table (id, moment, asset, duration, options), how to rewire one, the hear.py recipe.
   Add `tools/build_audio.py` to the tools list in `CLAUDE.md` §Gotchas in the same style as the other builders
   (one bullet, two lines max) — that is the ONLY edit to CLAUDE.md.

## Verification (do all; report what each showed)
- `BuildAll` clean after the Verse changes; pytest still 8685 (or more if you add a test for the cue-tag naming).
- `build_audio.py` twice in a row: second run leaves the same device count (idempotence); `--list` read-back shows
  the sound and options you intended on every device.
- Headless run with `DebugAutoPick 0` + `DebugAutoRightAnswers true`: the editor log must show
  `FNM: audio: N of M cues wired` with N ≥ 20 and no unexpected missing ids, `FNM: cue countdown3/2/1/go`, ten
  `cue correct`/`cue door_open`, `streak2..` rising, `cue finish`, a best/record cue. Then `DebugAutoWrongAnswers 6`
  (`--watch 6`): one `cue wrong` + one penalty cue per penalty.
- **Ear-proxy**: start `tools/hear.py --seconds 150` in the background, then the auto-right run; align the log's
  cue timestamps (editor log lines carry times; otherwise mark them from `playtest.py`'s own clock) with the onset
  table. Report: how many cue lines had an onset within 0.5 s. If the recording is flat: Fortnite may mute a
  background client (Settings → Audio → "Background Audio" belief). Bring the client forward for one run
  (`playtest.py` has the focus helper), record again, then report both. Do not loop on this more than twice.
- Look at one screenshot from the run to be sure the HUD is unchanged (no stray text).

## Non-goals / do NOT
- Do NOT commit. Do NOT run `build_course.py`, `build_rigs.py`, `build_decor.py` or any other builder (the course
  is live and tuned). Do NOT edit `GOALS.md`, `PROTOCOL.md`, `cartridges/**`, `emulator/**`, `fnm/**`,
  `tools/audio/**` (another builder is writing the announcer pack there right now; it never touches your files),
  `fnm_ui.verse` unless a hook genuinely needs it (say so).
- Do NOT change any game rule, penalty, timing, HUD text or layout. Sound only.
- Do NOT import files into UEFN or add assets to the project's Content folder.
- Leave every debug `@editable` at its ship value, re-synced and rebuilt, when you finish. Leave no probe devices
  in the level (check `find_actors` by your tag and by label `FNM_Cue_`/`probe` at the end).
- Checkpoint every deliverable to disk the moment it exists; what is on disk is what survives a session limit.

## Report (write it as your final message)
Files created/edited; the final CUES table with asset paths, durations and the option values read back; BuildAll
result; pytest count before/after; the log excerpt proving the wiring (`audio: N of M`, cue lines); the hear.py
alignment numbers (background client, and focused if needed); which cues have NO library sound yet; the names of
the component properties you set. Then two mandatory sections: **"Anything I decided differently from this brief
and why"** and **"Shakiest assumption, stated plainly"** (one that I should check myself). Also list anything in
the docs that turned out untrue.
