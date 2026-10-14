# Brief L: door lights must not blow out the doors up close (found by T1, 2026-10-13)

Read `briefs/g9/TEAM.md` first (lock, report format, "Wave 4-5": foreground allowed only while you hold the lock). You are
**L**, model Sonnet; the manager (Opus 5.5) audits you. **D2** (Opus) works on Verse and audio at the same time and shares
the UEFN lock: keep your holds short.

## The problem
`tools/build_door_marks.py` puts a letter-coloured point light (Customizable Light, `LIGHT_SIZE_PERCENT` 25,
`LIGHT_INTENSITY_PERCENT` 40) 100 cm in front of each lintel at 350 cm. With the new Titan Peak arches and stone, a player
standing at a door (to press E) sees the door panel and the arch stone blown out to near-white: T1's frames
`C:/Users/kicki/AppData/Local/Temp/claude/D--PyCharm-Projects-fortnitemath/26b46b63-033f-415b-aac7-f54eb20d33c6/scratchpad/team/T1/play/walk_sheet3.png`
(door A, station 1, Hour19). From the spawn (~20 m back) the doors read fine (manager's QA frames).

## You own
`tools/build_door_marks.py` (the light constants and light options only), its test file if one exists (grep tests/ for
`build_door_marks`). Nothing else. No commits.

## Do
1. Find the cause by experiment, cheapest first: lower intensity (e.g. 40 -> 15-20), smaller size, light further from the
   door (higher / further back), or the light's attenuation radius if the device exposes one (read its properties). Change
   one thing at a time.
2. Under the lock: rerun `python tools/build_door_marks.py` (idempotent; reads back), then ONE play session at ship hooks
   (no hook flips: D2 owns the director). The player spawns at station 1; walk to door A with
   `tools/playtest.py --no-relaunch --keys W:...` (you may take the foreground while you hold the lock; find the hold
   times from the spawn, Volt is on the right; door A is the leftmost) and capture at the door, plus one frame from the
   spawn. READ them. Accept when: at the door, the white door panel still shows its letter tile and the arch stone keeps
   its texture (not flat white); from the spawn, the four doors still read in their colours (white, blue, green, orange).
3. If no light setting fixes it, say what else does (e.g. the camera's auto-exposure) and leave the best setting in.

## Report (TEAM.md format)
Settings before/after, the frame paths (spawn + door, before + after), the lock times, anything unexpected.
