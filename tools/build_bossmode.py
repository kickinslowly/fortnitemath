"""Build the BOSS BATTLE mode's arena (BOSS_MODE.md section 3, maps/starter/LAYOUT.md "Boss battle arena") in the open
UEFN project through UEFN MCP.

Aaron (2026-10-09): "an arena fight, just like the boss battle, but it's only a boss battle ... monsters and npcs spawn
at increasing intervals from gates in the walls ... weapons spawn around map each level but in set places the player
must reach, like elevated platforms that must be jumped to". A round arena 64 m across, 140 m east of the course (it reads
no course geometry, so a course rebuild never moves it). Colosseum pass (Aaron, 2026-10-09: "an arena, large, circular
colloseum like, with pillars"): sand floor, a podium ring of Coliseum-kit bays (stone below, marble above, a marble arch at
each gate, the kit's main gate behind the entry); the stands, colonnade, tribune and statues are tools/build_colosseum.py
(its own actor tag, rerun on its own). Four answer pads (fnm_bm + fnm_door_a..d), a marble boss platform
with one guard spawner per level (fnm_bm_boss + fnm_bm_slot_L), four gates in the side walls, each a real opening with a
dark alcove holding a monster spawner (fnm_bm_gate + slot) and a lightning VFX at its mouth (fnm_bm_gate_fx + slot),
four gold perches reached by stepping stones with a hidden trigger and a beacon VFX on each top (fnm_bm_perch /
fnm_bm_perch_fx + slot), one Item Granter per level parked under the floor and bound to its own hidden trigger
(fnm_bm_grant + slot; the weapon comes with extra ammo), two Meshy mega laser cannons (cannons(); their muzzle discharge and
coil crackle are Niagara systems Verse spawns, BOSS_MODE 15g) plus a parked strike, two blasts and a nuke VFX, an anger ring of five VFX round the platform
(fnm_bm_anger_fx + slot), and one creature spawner per creature kind in the gate alcoves (fnm_bm_creature + slot = kind;
B5, BOSS_MODE.md 5). The director (console/verse/fnm_bossmode.verse) finds every piece by those Verse tags.

Dressing (dress(), tag DRESS_TAG, rerun alone with --dress): a gold chest on every perch with a hidden button in it
(fnm_bm_chest + slot), off until its level's weapon drop, held E for the weapon and its ammo (Aaron, 2026-10-09: "I dont know that weapons
were spawning ... maybe a chest with the weapon and ammo inside?"), and a giant 3D letter floating over each answer pad
(fnm_bm_letter + slot 1..4) that the director turns to face the nearest player ("the boards with letters above the
platform were okay, but hard to see from certain angles").

Coordinates are relative to ORIGIN, the podium's inner face due south (behind the entry) on the arena's centre line; the
arena's centre is CENTRE = (0, ARENA_R). The player enters facing +Y, so +X is their LEFT (pad A, like door A). Angles
(gates, perches, podium slots) are degrees from +X round CENTRE: 270 is the entry, 90 the boss end. Every actor is
labelled FNM_BM_* and tagged TAG; kit props are made indestructible (bCanBeDamaged off: the L5 rocket launcher).

Idempotent: every actor this script creates is tagged TAG; a run first deletes everything with TAG.
Materials first (once): python tools/import_art.py bm_sand bm_stone bm_marble bm_perch  (plus steel, glow, pad_a..d).

    python tools/build_bossmode.py            # (re)build the arena
    python tools/build_bossmode.py --dress    # (re)place only the chests and the floating letters (+ granter ammo)
    python tools/build_bossmode.py --check    # list what is placed, with the devices' read-back options
    python tools/build_bossmode.py --probe    # answer BOSS_MODE.md 3's UNVERIFIED items from the editor (no build)
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402
import build_course as c  # noqa: E402
import build_guards as g  # noqa: E402
import build_pickups as p  # noqa: E402
from build_course import (ACTOR, ASSETS, BILLBOARD, BOSS_SETTINGS, CUBE, DEV, LETTERS, OBJ, PAD_H,  # noqa: E402
                          PAD_SIZE, PAD_TILE_T, SCENE, SIGN_COLOUR, SLAB_T, STEP_BOX, STEP_Z, TELEPORTER, TRIGGER,
                          props, ref, trigger_fit, verse_tags, xform)
from build_rigs import GRANTER, TRIGGER_CLASS  # noqa: E402

TAG = "fnm_bossmode"
ORIGIN = (14000.0, -14000.0, 0.0)   # the podium's inner face due south, centre line; the floor's top is at z 2
FLOOR_Z = 2
# The round arena: sand floor ARENA_R in radius round CENTRE (relative to ORIGIN), ringed by a podium of SLOTS straight
# bays, slot k centred at slot_angle(k) (slot 0 due south, behind the entry). A bay is a Coliseum-kit wall piece BAY wide at
# the inner face, PODIUM_T deep, two rows of ROW_H: WALL_LOW (dark stone, base moulding) under WALL_HIGH (marble). A gate bay
# is GATE_ARCH (a marble arch) stretched ARCH_SZ tall under GATE_FILL; slot 0 is the kit's MAIN_GATE. Kit bounds at scale 1,
# measured in the editor 2026-10-09 (x along the bay, y depth, z up from the pivot): Wall_01 587 x 74 x 384, Wall_02 592 x
# 80, Arch_02 592 x 130 x 384 (opening ~0.65 x 0.75 of it), Wall_04 552 x 40, ExtWall_MainGate_01 1051 x 411 x 1270 (x
# -479..572, its face at y -15).
ARENA_R = 3200
CENTRE = (0, ARENA_R)
SLOTS = 36
BAY = 2 * ARENA_R * math.tan(math.pi / SLOTS)   # 560 cm at the inner face
PODIUM_T = 80
BAY_W = 2 * (ARENA_R + PODIUM_T) * math.tan(math.pi / SLOTS) * 1.02   # a kit bay's width: its back corners overlap
BACKING_T = 30          # a plain stone skin behind the bays (not the arches): the kit pieces' bevelled ends leave slits
ROW_H = 384
WALL_H = 2 * ROW_H
SAND_BAND = 120         # a stone band this wide round the sand, at the podium's foot
KIT = "/CR_Legacy/Playsets/PlaysetProps/PPID_CR_Legacy_{0}.PPID_CR_Legacy_{0}"
WALL_LOW, WALL_HIGH = "Coliseum_Wall_01", "Coliseum_Wall_02_277f0639"
GATE_ARCH, GATE_FILL = "Coliseum_Arch_02_27fb14b8", "Coliseum_Wall_04_4f283961"
MAIN_GATE = "CP_Coliseum_ExtWall_MainGate_01_NoDestroy"
KIT_W = {WALL_LOW: 587, WALL_HIGH: 592, GATE_ARCH: 592, GATE_FILL: 552}
ARCH_SZ = 1.4           # the arch's opening ~400 tall: a Brute's way out
MAIN_GATE_DX = (572 - 479) / 2                  # its pivot is this far left of its middle
ENTRY_BACK = 450        # a stone wall this far behind the main gate's face: its open leaf looked out to sea
ENTRY = (0, 250)        # the entry teleporter (yaw 90): arrival and respawn point
SIGN = (0, 2 * ARENA_R - 5, 430)                # on the podium due north, under the tribune, facing the entry
SIGN_SCALE = 2.5
# Answer pads A..D (x, y): +X is the player's left, so they read A B / C D like the HUD. Tile, trigger and (dress) letter as
# the race arena's (build_course.arena). Clear of the floor medallion round CENTRE (build_colosseum.MEDALLION).
PAD_SPOTS = [(900, 1900), (-900, 1900), (900, 2900), (-900, 2900)]
# A giant 3D letter over each pad (the CRG_Props Alphabet set, ~206 wide x 201 tall x 50 deep at scale 1, its pivot at
# the bottom centre, the readable face toward +Y at yaw 0, so it is placed at yaw 180 to read from the entry; the
# director turns it to face the nearest player). Its own
# colour option, the nearest stock colour to the pad's LETTER_COLOURS.
LETTER_ASSET = "/CRG_Props/SetupAssets/Maps/PPIDs/"
# Low enough to sit under the HUD's question slate at a level camera (at 450 the slate hid them, seen in play); no
# collision (bNoCollision reads back true; bNoPawnCollision and bNoCameraCollision are refused), so a jump on the pad
# never bumps a head on one.
LETTER_Z = 250
LETTER_SCALE = 1.8
LETTER_PROP_COLOURS = ("White", "Sky Blue", "Apple Green", "Orange")
PAD_TRIGGER = {"timesCanTrigger_Override": False, "triggerDelay": 0.0, "reset Delay": 0.0, "visible in Game": False,
               "triggeredByVehicles": False, "triggeredByWater": False, "triggeredByPhysicsProps": False}
# The boss platform (marble), its centre, size and height; the boss's creature spawner and the titan stand on it
# (boss_rig). 1 m: it was raised to 3.5 m for the 3 m Megabrute, but the 12 m titan on it put its head and chest behind
# the question panel at the player's eye line (play frames 2026-10-10).
PLATFORM_X, PLATFORM_Y = 0, 4500
PLATFORM_W, PLATFORM_D, PLATFORM_H = 800, 500, 100
_W = "/Game/Athena/Items/Weapons/{0}.{0}"
# Gates G1..G4 as angles round CENTRE: G1 right-front, G2 left-front, G3 right-back, G4 left-back (right = -X, front = the
# entry half), each on a podium slot (an arch bay). Behind the arch an ALCOVE_D deep alcove GATE_W wide and GATE_H tall
# (back, sides, roof and its own floor) in stone, the monster spawner at the alcove centre facing into the arena, a
# lightning VFX at the mouth.
GATES = [200, 340, 160, 20]
GATE_W, GATE_H = 400, 420
ALCOVE_D = 300
GATE_WEAPONS = [_W.format(n) for n in (
    "WID_Pistol_SemiAuto_Athena_R_Ore_T03",
    "WID_Pistol_AutoHeavyPDW_Athena_R_Ore_T03",
    "WID_Shotgun_Standard_Athena_VR_Ore_T03",
    "WID_Assault_Heavy_Athena_R_Ore_T03")]
# The director calls Spawn() (spawnOnTimer False) and caps the alive count itself; Disable() despawns at a level clear.
# Team: every gate guard and every boss is on build_guards' "Team Wildlife & Creatures", the team the creature spawners'
# creatures belong to (the creature spawner has no team option of its own; probed 2026-10-09), so guards, bosses and
# creatures are allies and all hunt the player (Aaron, 2026-10-09: "monsters and guards should all go after the player,
# never fight each other"). Gate guards drop nothing (B6, 2026-10-09): dropped guns littered the arena floor and Verse has
# no call that removes a dropped pickup (Fortnite digest 42.30 checked); the player's weapons come from the perches. The race
# course's guards (build_guards.SETTINGS) still drop theirs.
GATE_SETTINGS = {**g.SETTINGS, "spawnCount": 2, "allowInfiniteSpawn": True, "spawnOnTimer": False,
                 "spawnRadius_InMeter": 2.0, "spawnThroughWalls": False, "enablePatrol": True,
                 "maxPatrolDistance_InMeter": 30.0, "visibilityRange_InMeter": 45.0, "accuracy": "LOW",
                 "despawnGuardsWhenDisabled": True, "dropInventoryOnElimination": False}
TEAM = g.SETTINGS["guardTeamOption"]
# Creature spawners (Creature Spawner V2), one per creature KIND, slot K = CREATURES[K - 1] (the Verse names them the same,
# FnmBmCreatureName), invisible and off, standing on the floor just inside a gate alcove's mouth (CREATURE_GATES; two
# share gate 4). At the alcove's back, 60 cm from its wall, the Brute never came (6 s, twice) while the Ranged did. The director pulses one per creature: Enable, SpawnAt(a gate's alcove), its SpawnedEvent, Disable: so the
# device's own waves (every few seconds while on, wave Timer not settable from MCP) never start. Probed headless
# 2026-10-09: SpawnAt is refused at once unless the device stands on the ground (5 m under the slab or 40 m down: refused)
# AND a player is inside its activation range (1 refused, 100 worked from 45 m); when it works the creature appears at once
# but the call does not return within 30 s, so the director counts the SpawnedEvent. Do Not Despawn (the creatures roam
# far from the device). Megabrute left out: too tough for grades 6-8.
CREATURE = "/CRD_Creatures/SetupAssets/PID_Device_CreatureSpawner_V2.PID_Device_CreatureSpawner_V2"
CREATURES = ["Fiend", "Brute", "Ranged", "Red Fiend", "Exploding Brute"]
CREATURE_GATES = [1, 2, 3, 4, 4]          # the gate whose alcove holds kind K's device
CREATURE_DY = [0, 0, 0, -100, 100]        # beside each other where two share an alcove
CREATURE_IN = 50                          # just inside the alcove mouth (a Brute did not come from the back)
CREATURE_SETTINGS = {"enabled at Game Start": False, "number of Creatures": 1, "spawner Visibility": False,
                     "invincible Spawner": True, "damage Spawner After Spawn": False,
                     "damage Structures at Spawn Location": False, "despawn Type": "Do Not Despawn",
                     "limit Spawned Creatures": True, "enum Total Spawn Limit": "100", "total Spawn Limit": 100,
                     "activation Range": 100.0, "spawn Effects Visibility": True}
# The boss is a Megabrute (Aaron 2026-10-10: "make boss bigger and more epic model ... hard to even tell he is the boss"):
# a guard cannot be scaled (Guard Spawner V2 has no size option, Verse no character scale; 42.30 checked) and the
# Megabrute is the game's own giant. One creature spawner on the platform centre (Verse tag fnm_bm_megaboss) replaces the
# five per-level guard boss spawners; the director pulses it once per level, pins the creature on the platform (stasis,
# turning allowed) and gives it 100000 health that only the pads take away (fnm_bossmode.verse OnBossSpawned). Its
# melee never reaches a pad from the platform. Left out of the monster gates (too tough to fight for grades 6-8).
MEGABOSS = "Megabrute"
MEGABOSS_SETTINGS = {**CREATURE_SETTINGS, "creature Type": MEGABOSS}
# A laser beam from each cannon's muzzle to the boss (Aaron 2026-10-10: "attacks on him more obviously coming from the side
# laser cannons"): the Alphabet "I" (57 x 50 x BEAM_H at scale 1, pivot at the bottom centre) laid along the shot, its
# +Z from the muzzle (muzzle_point) to BEAM_AIM above the platform top (the titan's waist: higher, the hit lands behind the answer panel, which grows for the first seconds after a right pad; 2026-10-10 frames),
# BEAM_W scale thick (~1 m: at 0.8 it read as a thin line on the horizon from the entry, 2026-10-10 frames), in
# BEAM_COLOUR, no collision. Placed at full length with Verse tag fnm_bm_beam; the director hides it
# at start and shoots it out of the muzzle on every hit (fnm_director FireBeam). A gallery prop because Verse moves only
# creative props, in its own colour option: the Glow Rings beam materials render as a checker on a gallery prop and the
# Tech primitives refuse a colour (probed 2026-10-10).
BEAM_LETTER = "I"
BEAM_H = 201.3
BEAM_W = 2.0
BEAM_AIM = 450
BEAM_COLOUR = "Aqua"         # the mega cannons' coils (15d); was Neon Green
BOSS_RIG_TAG = "fnm_bm_bossrig"
# The titan (2026-10-10, BOSS_MODE.md section 15b): what players see of the boss. A character cannot be scaled (the
# Megabrute stays hidden inside it and keeps the health), so the boss is a Meshy monster (art/boss, tools/import_boss.py)
# on Animated Mesh devices: one device per clip (the device plays one animation), Verse swaps them in by TeleportTo.
# Slot N = TITAN_CLIPS[N - 1]; the idle stands home, the rest wait TITAN_PARK under the floor until Verse shrinks them
# to nothing at home. Every clip starts Playing and loops (fnm_titan.verse says why), except the fall (TITAN_ONCE):
# it plays once and holds lying down, and Verse restarts it with Play() at each level clear.
ANIMATED_MESH = "/CRD_AnimatedMesh/Device_AnimatedMesh.Device_AnimatedMesh_C"
TITAN_ART = "FNM_BossArt"
TITAN_MESH = "SK_fnm_titan"
# The chest pound (taunt) and knockdown (defeat) clips are imported but unused: on the device one tipped the titan flat
# partway through its loop and the other turned on the spot instead of falling (BOSS_MODE.md section 15b).
# G9 D2 (2026-10-13): slot 5 the jump-slam (the entrance: boss mode's level start, the race arena's walk-in), slot 6 the
# scream (boss mode's wrong pad; the race places only the first five, build_race_boss RACE_TITAN_CLIPS). Both play once from
# their first frame like the fall (TITAN_ONCE; fnm_titan.verse Once) and on idle's mesh (TITAN_SHARED: tools/import_boss.py
# brings them in as animations on idle's skeleton). The shout (Shouting Angrily, 7.2 s) is imported but placed nowhere.
TITAN_CLIPS = ["idle", "flail", "stomp", "dead", "jumpslam", "scream"]
TITAN_ONCE = {"dead", "jumpslam", "scream"}
TITAN_SHARED = {"jumpslam": "idle", "scream": "idle", "shout": "idle"}
TITAN_SCALE = 4.0        # the mesh is 3 m tall: 12 m, head just under the question panel at the player's eye line
TITAN_PARK = 3000
# Perches P1..P4 as (x, y, top above the floor): P1 front-right, P2 front-left, P3 back-right, P4 back-left. A PERCH_TOP
# square gold block; stepping stones STONE long (along the climb) and STONE_D wide (as wide as the perch), each STONE_RISE
# lower than the next, STONE_GAP apart edge to edge, laid from the perch toward the arena's centre line (the lowest
# farthest out). B6 keys test 2026-10-09: with 120 x 120 stones, 60 cm rises and 150 cm gaps the player reached the top
# stone but fell into the 150 cm gap before the perch and stood against its 180 cm face (a restart); the stones were
# also as narrow as a player's sideways drift. Now 50 / 100 (the spec's fallback) and stones as wide as the perch.
PERCH_R = 2850         # perch centres this far from CENTRE: a perch's outer corner stays ~1.4 m off the podium
PERCH_ANGLES = (235, 305, 125, 55)
PERCH_TOPS = (180, 180, 240, 240)
PERCH_TOP = 300
STONE = 120
STONE_D = PERCH_TOP
STONE_RISE = 50
STONE_GAP = 100
PERCH_TRIGGER_H = 200
# Item granter per level, parked under the floor; its item is the level's weapon (BOSS_MODE.md 4, weapon perch column).
GRANT_WEAPONS = [_W.format(n) for n in (
    "WID_Pistol_AutoHeavyPDW_Athena_R_Ore_T03",        # L1 SMG at P1
    "WID_Shotgun_Standard_Athena_VR_Ore_T03",          # L2 pump shotgun at P2
    "WID_Assault_AutoHigh_Athena_VR_Ore_T03",          # L3 assault rifle at P3
    "WID_Sniper_Heavy_Athena_SR_Ore_T03",              # L4 heavy sniper at P4
    "WID_Launcher_Rocket_Athena_SR_Ore_T03")]          # L5 rocket launcher at P3 / P4
# giveExtraAmmo: the granter's own ammo table rides along (stock 42.30: light 50, medium 30, shells 30, heavy 10,
# rockets 10, read back from a placed granter), so the chest's weapon comes with its ammo.
GRANT_SETTINGS = {**p.GRANT_SETTINGS, "equipItemOnGrant": 1, "giveExtraAmmo": 1}
# A weapon chest on each perch: the classic gold chest mesh (84 x 69 x 69 at scale 1, pivot at the bottom centre, its
# lock toward -X at yaw 0) on the half away from the stones, lock toward them, and a hidden button in it that the
# director enables at the level's weapon drop: held E grants the level's weapon to whoever presses it. Tried first and
# dropped (2026-10-09): the Chest & Ammo gallery's Hero Chest device (hero_chest_device, OpenEvent) renders in play as
# a white and orange pod nobody would read as a chest, and set_properties refuses its rankLootTierNames, so it also
# spills random rank loot.
CHEST_MESH = "/Game/Environments/Props/Boxes/Meshes/TreasureChestLootTier1.TreasureChestLootTier1"
CHEST_SCALE = 2.5
BUTTON = "/CreativeCoreDevices/SetupAssets/PID_Device_Button.PID_Device_Button"
CHEST_BACK = 50
CHEST_BUTTON = {"visibleDuringGame": False, "interactTime": 1.0, "interaction Text": "Open Weapon Chest",
                "interactionRadius": 1.5, "enabledAtGameStart": False}
DRESS_TAG = "fnm_bm_dress"
# A chest open for the level is marked (Aaron 2026-10-10: "i can't tell when a chest is active. can we make it glow or have
# an arrow over it"; BOSS_MODE 15e): a Beacon device in its Arrow style, gold, CHEST_BEACON_Z over the perch top, whose HUD
# marker reads WEAPON with the distance and shows through walls; and a gold point light CHEST_LIGHT_Z over the chest.
# The HUD marker needs "beacon to Show" Both: its default, Particle, shows the arrow only, and every Icon Text / distance
# option is Badge-only. "hide HUD Icon at" is a MAXIMUM range in metres (the marker shows only to players closer than
# it), so it covers the whole arena. CHEST_BEACON_SCALE is the actor scale; the arrow ignores it unless
# particlePropAbsoluteScale is off. The badge renders as a gold marker pin with no text in play (42.30): Icon Text and
# the distance never drew, and an icon from the picker's textures, set by path, fails session validation.
# Verse switches both with the chest's button (fnm_bm_chest_beacon / fnm_bm_chest_light + slot).
BEACON = "/CreativeCoreDevices/SetupAssets/PID_Device_Beacon.PID_Device_Beacon"
GOLD = {"r": 1.0, "g": 0.75, "b": 0.1, "a": 1.0}
CHEST_BEACON = {"beacon to Show": "Both", "showOffscreenArrow": True, "badge uses Beacon Color": True, "particlePropAbsoluteScale": False,
                "beacon Particle Style": "Arrow", "beacon Color": "Direct Color", "custom Beacon Color": GOLD,
                "neutral Icon Text": "WEAPON", "friendly Icon Text": "WEAPON", "hostile Icon Text": "WEAPON",
                "requires Line of Sight": False, "displayDistanceText": True, "hide HUD Icon at": 100}
CHEST_BEACON_SCALE = 2.0
CHEST_BEACON_Z = 120
CHEST_LIGHT = {"lightColor": GOLD, "lightSizePercentage": 50, "lightIntensityPercentage": 100, "enabledDuringPhase": "Always"}
CHEST_LIGHT_Z = 220
GRANT_X0, GRANT_DX, GRANT_Y, GRANT_TRIGGER_Y = -1200, 300, 600, 300
# The cannon rig: one cannon on the podium due left and due right (slots 9 and 27, where the ring's face runs along Y),
# CANNON_Y in from ORIGIN, aimed at the platform top + BOSS_EYE.
CANNON_Y = ARENA_R
BOSS_EYE = 90           # the aim point this high above the platform top (a standing guard's chest; only its x, y aim now)
# The mega laser cannons (Aaron 2026-10-10: "make them mega cannon lasers ... glowing areas, lightning fx"; BOSS_MODE 15d):
# the Meshy mesh SM_fnm_megacannon (tools/import_cannon.py) standing on the sand CANNON_R from CENTRE at CANNON_DEG (left,
# +X) and 180 - CANNON_DEG (right), barrel turned onto the titan's waist. Due left and right they sat 46 degrees off the
# view's centre for a player at the entry, out of frame in play (2026-10-10 frames, as the old wall cannons were); at 36
# degrees, beside the titan, they are 27 degrees off, in frame, and the beams cross the view. 36 keeps clear of gate 4's
# mouth (20) and the back perch (55). At scale 1 the mesh is 93 x 190 x 96 cm, pivot at its centre, barrel along
# +Y; CANNON_SCALE 4 makes it 7.6 m long and 3.8 m tall. Points on it are (across, along the barrel, up) from the pivot at
# scale 1: CANNON_MUZZLE the muzzle's mouth, CANNON_COIL the middle of the glowing coils (editor frames 2026-10-10).
CANNON_ART = "FNM_CannonArt/SM_fnm_megacannon.SM_fnm_megacannon"
CANNON_SCALE = 4.0
CANNON_R = ARENA_R - 480     # its tail clears the sand band and the wall
CANNON_DEG = 36
CANNON_HALF_H = 48           # pivot height above the floor at scale 1
CANNON_MUZZLE = (0, 95, 10)
CANNON_COIL = (0, 42, 10)
# The beam (and Verse's muzzle discharge, fnm_fx FnmSpawnMuzzle) starts MUZZLE_AHEAD cm in front of the mouth. The cannon's
# effects are our own Niagara systems since 2026-10-11 (BOSS_MODE 15g, tools/build_fx.py NS_fnm_muzzle / NS_fnm_coil),
# spawned by Verse from the beam's placed transform; the coils sit fnm_fx FnmCannonCoilBack behind that point (a test ties
# it to CANNON_MUZZLE, CANNON_COIL, CANNON_SCALE and MUZZLE_AHEAD). The VFX Spawner muzzle burst, zap and coil crackle are
# gone (the crackle never showed from the player's spot ~38 m away).
MUZZLE_AHEAD = 40
# Always on, no Verse: cyan point lights in the coils and the muzzle (the light's `lightSize` enum refuses writes;
# `lightSizePercentage` takes them: 100 flooded the whole bay white, editor frames 2026-10-10).
POINT_LIGHT = "/CRD_PointLight/SetupAssets/PID_Device_PointLight.PID_Device_PointLight"
CANNON_LIGHT = {"lightColor": {"r": 0.2, "g": 0.9, "b": 1.0, "a": 1.0}, "lightSizePercentage": 50,
                "lightIntensityPercentage": 60, "enabledDuringPhase": "Always"}
PARK_DROP = 600         # strike, blasts, nuke and granters park this far under the floor
STRIKE_SCALE, NUKE_SCALE = 5.0, 6.0
GATE_FX_SCALE, PERCH_FX_SCALE, ANGER_FX_SCALE = 2.0, 2.0, 1.5
ANGER_RADIUS = 650
ANGER_ANGLES = (198, 234, 270, 306, 342)    # degrees from +X round the platform centre: the half facing the entry
GATE_FX = {"enabled On Phase": "None", "visual_Effect": "LightningBolt_02", "effectType": "Burst",
           "sound_Effect": "Electric_Blast", "clearParticlesOnDisable": True}
PERCH_FX = {"enabled On Phase": "None", "visual_Effect": "LightningBolt_01", "effectType": "Burst",
            "sound_Effect": "None", "clearParticlesOnDisable": True}
ANGER_FX = {"enabled On Phase": "None", "visual_Effect": "LightningBolt_01", "effectType": "Burst",
            "sound_Effect": "Electric_Blast", "clearParticlesOnDisable": True}
# The strike moved onto the boss and the explosive blasts at its feet on every hit (fnm_director FireCannons), here and
# in the race arena (tools/build_race_boss.py, which also takes these): no damage, the math is the only weapon.
STRIKE_FX = {"enabled On Phase": "None", "visual_Effect": "LightningBolt_03", "effectType": "Burst",
             "sound_Effect": "Electric_Blast", "clearParticlesOnDisable": True}
BLAST = {"visible During Game": False, "can be Damaged": False, "player Damage": 0, "structure Damage": 0,
         "knockback": "Medium", "play Audio / VFX": True, "explode on Proximity": False,
         "has Timed Detonation From Game Start": False, "time Until Reset Allowed": 0.5}
BLASTS = 2
NUKE_FX = {"enabled On Phase": "None", "visual_Effect": "LightningBolt_01", "effectType": "Burst",
           "sound_Effect": "Explosion", "clearParticlesOnDisable": True}
# Fallbacks decided from the device's own enums at build time (nuke_effect, knockback).
NUKE_WORDS = ("Explosion", "Smoke", "Fire", "Blast")
NUKE_FALLBACK = "LightningBolt_01"
KNOCKBACK_WANT, KNOCKBACK_FALLBACK = "High", "Medium"
GLASS = "/Game/Creative/Environments/Meshes/Glass/Materials/Glass_version_02/MI_CP_GlassGallery.MI_CP_GlassGallery"
LID_T, LID_SINK = 40, 20
VFX = "/CRD_VFX_Spawner/SetupAssets/PID_Device_VFX_Spawner_V2.PID_Device_VFX_Spawner_V2"
EXPLOSIVE = "/CreativeCoreDevices/SetupAssets/PID_Device_ExplosiveBarrel.PID_Device_ExplosiveBarrel"
CYLINDER = "/Engine/BasicShapes/Cylinder.Cylinder"     # 100 cm tall along its Z, 100 cm across


# ---------------------------------------------------------------- pure layout (tests read these)

def polar(r, deg):
    """(x, y) relative to ORIGIN of the point r from CENTRE at deg (degrees from +X)."""
    return radial(deg, r)


def radial(deg, u, v=0.0):
    """(x, y) relative to ORIGIN of a point u out from CENTRE along deg and v across it (counter-clockwise positive)."""
    a = math.radians(deg)
    return CENTRE[0] + u * math.cos(a) - v * math.sin(a), CENTRE[1] + u * math.sin(a) + v * math.cos(a)


def slot_angle(k):
    return (270 + k * 360 / SLOTS) % 360


def slot_of(deg):
    """The podium slot centred on deg; every gate and cannon stands on one."""
    k = ((deg - 270) % 360) * SLOTS / 360
    if abs(k - round(k)) > 1e-9:
        raise ValueError(f"{deg} is not a slot centre")
    return int(round(k)) % SLOTS


PERCHES = [(round(polar(PERCH_R, a)[0]), round(polar(PERCH_R, a)[1]), top) for a, top in zip(PERCH_ANGLES, PERCH_TOPS)]


def stones_for(perch):
    """The stepping stones below a perch (x, y, top): [(cx, cy, top)], highest first, toward the centre line."""
    px, py, top = perch
    toward = -1 if px > 0 else 1
    out, h, i = [], top - STONE_RISE, 0
    while h > 0:
        cx = px + toward * (PERCH_TOP / 2 + STONE_GAP + STONE / 2 + i * (STONE + STONE_GAP))
        out.append((cx, py, h))
        h -= STONE_RISE
        i += 1
    return out


def creature_spots():
    """Each creature kind's spawner (x, y, gate) relative to ORIGIN: on the alcove floor of its gate, at the mouth."""
    out = []
    for gate, dv in zip(CREATURE_GATES, CREATURE_DY):
        x, y = radial(GATES[gate - 1], ARENA_R + PODIUM_T + CREATURE_IN, dv)
        out.append((x, y, gate))
    return out


def anger_spots():
    return [(PLATFORM_X + ANGER_RADIUS * math.cos(math.radians(a)), PLATFORM_Y + ANGER_RADIUS * math.sin(math.radians(a)))
            for a in ANGER_ANGLES]


def boss_aim():
    """The cannons' aim point, relative to ORIGIN."""
    return PLATFORM_X, PLATFORM_Y, FLOOR_Z + PLATFORM_H + BOSS_EYE


def nuke_effect(choices):
    """The nuke's visual_Effect: the first current (not _Deprecated) entry naming an explosion, smoke, fire or blast."""
    for name in choices:
        if not name.endswith("_Deprecated") and any(w.lower() in name.lower() for w in NUKE_WORDS):
            return name
    return NUKE_FALLBACK


def knockback(choices):
    return KNOCKBACK_WANT if KNOCKBACK_WANT in choices else KNOCKBACK_FALLBACK


# ---------------------------------------------------------------- editor helpers (every actor tagged TAG)

def at(dx, dy, z=0.0):
    return ORIGIN[0] + dx, ORIGIN[1] + dy, ORIGIN[2] + z


def tagged(actor, label, tag=TAG):
    u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": tag})
    u.call(ACTOR, "set_label", {"actor": ref(actor), "label": label})
    return actor


def paint(actor, material, **extra):
    comp = json.loads(u.call(OBJ, "get_properties", {"instance": ref(actor), "properties": ["staticMeshComponent"]})["returnValue"])
    u.call(OBJ, "set_properties", {"instance": comp["staticMeshComponent"],
                                   "values": json.dumps({"overrideMaterials": [ref(material)], **extra})})


def box(label, x0, x1, y0, y1, z0, z1, material=None, tag=TAG, **extra):
    """A solid from a scaled engine cube; x / y relative to ORIGIN, z absolute (the floor's top is FLOOR_Z)."""
    x0, x1, y0, y1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    cx, cy, _ = at((x0 + x1) / 2, (y0 + y1) / 2)
    r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": CUBE, "name": label, "xform": xform(
        cx, cy, (z0 + z1) / 2, (x1 - x0) / 100, (y1 - y0) / 100, (z1 - z0) / 100)})
    actor = tagged(r["returnValue"]["refPath"], label, tag)
    if material:
        paint(actor, material, **extra)
    return actor


def rbox(label, deg, u0, u1, v0, v1, z0, z1, material=None, tag=TAG, **extra):
    """A solid in the radial frame of deg: u out from CENTRE, v across (counter-clockwise), z absolute."""
    cx, cy, _ = at(*radial(deg, (u0 + u1) / 2, (v0 + v1) / 2))
    r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": CUBE, "name": label, "xform": xform(
        cx, cy, (z0 + z1) / 2, abs(u1 - u0) / 100, abs(v1 - v0) / 100, (z1 - z0) / 100, deg)})
    actor = tagged(r["returnValue"]["refPath"], label, tag)
    if material:
        paint(actor, material, **extra)
    return actor


def disc(label, radius, z0, z1, material, tag=TAG):
    """A flat engine cylinder round CENTRE."""
    cx, cy, _ = at(*CENTRE)
    r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": CYLINDER, "name": label, "xform": xform(
        cx, cy, (z0 + z1) / 2, 2 * radius / 100, 2 * radius / 100, (z1 - z0) / 100)})
    actor = tagged(r["returnValue"]["refPath"], label, tag)
    paint(actor, material)
    return actor


def kit(name, label, dx, dy, z, yaw=0.0, sx=1.0, sy=1.0, sz=1.0, tag=TAG):
    """A Coliseum-kit (or any CR_Legacy playset) prop, made indestructible."""
    x, y, _ = at(dx, dy)
    r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": KIT.format(name), "name": label,
                                                  "xform": xform(x, y, z, sx, sy, sz, yaw)})
    actor = tagged(r["returnValue"]["refPath"], label, tag)
    props(actor, {"bCanBeDamaged": False})
    return actor


def bay(name, label, deg, z, sz=1.0, u=None, tag=TAG):
    """A kit wall piece standing on the ring at deg (slot width at the inner face), long side across the radius."""
    x, y = polar(ARENA_R + PODIUM_T / 2 if u is None else u, deg)
    return kit(name, label, x, y, z, deg + 90, BAY_W / KIT_W[name], 1.0, sz, tag)


def device(asset, label, dx, dy, z, yaw=0.0, sx=1.0, sy=None, sz=None):
    x, y, _ = at(dx, dy)
    r = u.call(DEV, "PlaceDevice", {"assetPath": ref(asset), "transform": xform(x, y, z, sx, sy or sx, sz or sx, yaw)})
    return tagged(r["returnValue"]["refPath"], label)


def get(actor, keys):
    return json.loads(u.call(OBJ, "get_properties", {"instance": ref(actor), "properties": list(keys)})["returnValue"])


def options(actor, values, label):
    """One key per call (a combined write can keep an old value), then read back; returns what differs."""
    for key, value in values.items():
        try:
            props(actor, {key: value})
        except RuntimeError as e:
            print(f"  {label}: could not set {key}: {str(e)[:120]}")
    back = get(actor, values)
    wrong = {k: back.get(k) for k, v in values.items() if back.get(k) != v}
    if wrong:
        print(f"  {label}: read back differently: {wrong}")
    return wrong


def enum_values(actor, key):
    """The enum a device property takes (list_properties is ~100 KB on a VFX spawner; asked once per build)."""
    schema = json.loads(u.call(OBJ, "list_properties", {"instance": ref(actor)}, timeout=180)["returnValue"])
    return schema.get(key, {}).get("enum", [])


def item_list(actor, key, weapon, label):
    """Set a spawner's / granter's one-item list (sub-object `key`) to weapon; read it back; stop the build on a refusal."""
    lst = get(actor, [key])[key]["refPath"]
    props(lst, {"itemListData": [{"itemDefinition": ref(weapon), "itemQuantity": 1}]})
    back = get(lst, ["itemListData"])["itemListData"]
    if not back or (back[0].get("itemDefinition") or {}).get("refPath") != weapon:
        sys.exit(f"{label}: refused {weapon.rsplit('.', 1)[1]} (read back {back}); the parent decides the swap")


def guard(label, dx, dy, z, yaw, project, tags, settings, weapon, health=None):
    """A guard spawner: tagged first (the tag component rebuilds its sub-objects), settings one key per call, weapon read
    back. health: ask max/starting health and return what the device kept."""
    actor = device(g.SPAWNER, label, dx, dy, z, yaw=yaw)
    verse_tags(actor, project, tags)
    options(actor, {**g.SETTINGS, **settings}, label)
    kept = None
    if health is not None:
        props(actor, {"max Health": health})
        props(actor, {"startingHealth": health})
        kept = get(actor, ["max Health", "startingHealth"])
    item_list(actor, "itemList", weapon, label)
    return actor, kept


def vfx(label, dx, dy, z, scale, project, tags, settings):
    fx = device(VFX, label, dx, dy, z, sx=scale)
    verse_tags(fx, project, tags)
    options(fx, settings, label)
    return fx


def hidden_trigger(label, dx, dy, z, w, d, h, project, tags, settings=PAD_TRIGGER):
    """A trigger whose detection box is w x d x h with its bottom at z (trigger_fit)."""
    dz, sx, sy, sz = trigger_fit(z, w, d, h)
    trig = device(TRIGGER, label, dx, dy, dz, sx=sx, sy=sy, sz=sz)
    verse_tags(trig, project, tags)
    options(trig, settings, label)
    return trig


def clear(tag=TAG):
    found = u.call(SCENE, "find_actors", {"tag": tag, "collision_channels": []})
    actors = [a for a in (found if isinstance(found, list) else found.get("returnValue", [])) if isinstance(a, dict)]
    for a in actors:
        u.call(SCENE, "remove_from_scene", {"actor": ref(a["actorPath"])})
    return len(actors)


def placed(tag=TAG):
    found = u.call(SCENE, "find_actors", {"tag": tag, "collision_channels": []})
    return [a for a in (found if isinstance(found, list) else found.get("returnValue", [])) if isinstance(a, dict)]


def materials(keys):
    """{key: material path} for M_fnm_wall_<key>; stops the build naming the import_art command when one is missing."""
    art = f"/{c.project_mount().strip('/')}/FNM_Art"
    missing = [k for k in keys if not u.call(ASSETS, "exists", {"path": f"{art}/M_fnm_wall_{k}"})["returnValue"]]
    if missing:
        sys.exit(f"materials missing: {missing}: python tools/import_art.py {' '.join(missing)}")
    return {k: f"{art}/M_fnm_wall_{k}.M_fnm_wall_{k}" for k in keys}


# ---------------------------------------------------------------- build

FLOOR_SPAN = 6200       # the stone slab's half width round CENTRE: under the alcoves and the whole colosseum


def shell(mat):
    """Stone slab and sand disc, the podium ring of kit bays with an arch at each gate and the main gate behind the
    entry, the gate alcoves, the hidden lid and the hidden wall behind the main gate's grille."""
    z0, R, t = FLOOR_Z, ARENA_R, PODIUM_T
    cx, cy = CENTRE
    box("FNM_BM_Floor", cx - FLOOR_SPAN, cx + FLOOR_SPAN, cy - FLOOR_SPAN, cy + FLOOR_SPAN, z0 - SLAB_T, z0, mat["bm_stone"])
    disc("FNM_BM_Sand", R - SAND_BAND, z0, z0 + 1, mat["bm_sand"])
    gates = {slot_of(g) for g in GATES}
    for k in range(SLOTS):
        deg = slot_angle(k)
        if k == 0:
            continue
        if k in gates:
            bay(GATE_ARCH, f"FNM_BM_Bay{k:02d}_Arch", deg, z0, ARCH_SZ)
            bay(GATE_FILL, f"FNM_BM_Bay{k:02d}_Fill", deg, z0 + ROW_H * ARCH_SZ, (WALL_H - ROW_H * ARCH_SZ) / ROW_H)
        else:
            bay(WALL_LOW, f"FNM_BM_Bay{k:02d}_Low", deg, z0)
            bay(WALL_HIGH, f"FNM_BM_Bay{k:02d}_High", deg, z0 + ROW_H)
            u0 = R + t + 5
            half = (u0 + BACKING_T) * math.tan(math.pi / SLOTS) * 1.02
            rbox(f"FNM_BM_Bay{k:02d}_Backing", deg, u0, u0 + BACKING_T, -half, half, z0, z0 + WALL_H, mat["bm_stone"])
    # slot 0 (due south): the kit's main gate, its face flush with the ring, the frame running out under the stands
    kit(MAIN_GATE, "FNM_BM_MainGate", MAIN_GATE_DX, -15, z0, 180)
    box("FNM_BM_EntryBack", -700, 700, -ENTRY_BACK - 40, -ENTRY_BACK, z0, z0 + 1300, mat["bm_stone"])
    for k, deg in enumerate(GATES, 1):
        a, b, back = R + t, R + t + ALCOVE_D, R + 2 * t + ALCOVE_D
        w = GATE_W / 2
        rbox(f"FNM_BM_Gate{k}_Back", deg, b, back, -w - t, w + t, z0, z0 + GATE_H + t, mat["bm_stone"])
        rbox(f"FNM_BM_Gate{k}_SideA", deg, a, b, -w - t, -w, z0, z0 + GATE_H + t, mat["bm_stone"])
        rbox(f"FNM_BM_Gate{k}_SideB", deg, a, b, w, w + t, z0, z0 + GATE_H + t, mat["bm_stone"])
        rbox(f"FNM_BM_Gate{k}_Roof", deg, a, back, -w - t, w + t, z0 + GATE_H, z0 + GATE_H + t, mat["bm_stone"])
    lid = z0 + WALL_H - LID_SINK
    box("FNM_BM_Lid", cx - R - t, cx + R + t, cy - R - t, cy + R + t, lid, lid + LID_T, GLASS, bVisible=False,
        bHiddenInGame=True)
    print(f"shell: sand r {R - SAND_BAND}, {SLOTS - 1} podium bays ({len(GATES)} arches), main gate, {len(GATES)} "
          f"alcoves, hidden lid at z {lid}")


def build():
    project = c.project_mount().strip("/")
    keys = ("bm_sand", "bm_stone", "bm_marble", "bm_perch", "steel", "glow", "pad_a", "pad_b", "pad_c", "pad_d")
    mat = materials(keys)
    print("removed", clear(), "old boss battle actors;", clear("fnm_test"), "test actors")
    z0 = FLOOR_Z
    shell(mat)

    tp = device(TELEPORTER, "FNM_BM_Entry", *ENTRY, 0, yaw=90)
    props(tp, {"knob_TeleporterGroup": "Group_None", "knob_TargetTeleporterGroup": "Group_None"})
    verse_tags(tp, project, ["fnm_bm", "fnm_entry"])
    sign = device(BILLBOARD, "FNM_BM_Sign", SIGN[0], SIGN[1], SIGN[2], yaw=180, sx=SIGN_SCALE)
    c.board(sign, "BOSS BATTLE", SIGN_COLOUR)
    print("entry teleporter and sign placed")

    for i, (dx, dy) in enumerate(PAD_SPOTS):
        letter = LETTERS[i]
        h = PAD_SIZE / 2
        box(f"FNM_BM_Pad{letter}", dx - h, dx + h, dy - h, dy + h, z0, z0 + PAD_TILE_T, mat[f"pad_{letter.lower()}"])
        hidden_trigger(f"FNM_BM_Trigger{letter}", dx, dy, z0, PAD_SIZE, PAD_SIZE, PAD_H, project,
                       ["fnm_bm", f"fnm_door_{letter.lower()}"])
    print("4 answer pads placed (A B near, C D far; A on the player's left)")

    # The platform, the boss and the beams: boss_rig, after the cannons.

    for k, (deg, weapon) in enumerate(zip(GATES, GATE_WEAPONS), 1):
        guard(f"FNM_BM_Gate{k}_Spawner", *polar(ARENA_R + PODIUM_T + ALCOVE_D / 2, deg), z0, deg + 180, project,
              ["fnm_bm_gate", f"fnm_bm_slot_{k}"], GATE_SETTINGS, weapon)
        vfx(f"FNM_BM_Gate{k}_Fx", *polar(ARENA_R + PODIUM_T / 2, deg), z0, GATE_FX_SCALE, project,
            ["fnm_bm_gate_fx", f"fnm_bm_slot_{k}"], GATE_FX)
    print("4 gate spawners + 4 gate VFX placed")

    for k, (sx, sy, gate) in enumerate(creature_spots(), 1):
        kind = CREATURES[k - 1]
        cs = device(CREATURE, f"FNM_BM_Creature{k}", sx, sy, z0, yaw=GATES[gate - 1] + 180)
        verse_tags(cs, project, ["fnm_bm_creature", f"fnm_bm_slot_{k}"])
        wrong = options(cs, {**CREATURE_SETTINGS, "creature Type": kind}, f"Creature{k}")
        if "creature Type" in wrong:
            sys.exit(f"creature spawner {k}: type {kind} not taken: {wrong}")
    print(f"{len(CREATURES)} creature spawners in the gate alcoves: {', '.join(CREATURES)}")

    for k, perch in enumerate(PERCHES, 1):
        px, py, top = perch
        h = PERCH_TOP / 2
        box(f"FNM_BM_Perch{k}", px - h, px + h, py - h, py + h, z0, z0 + top, mat["bm_perch"])
        for n, (sx, sy, st) in enumerate(stones_for(perch), 1):
            box(f"FNM_BM_Perch{k}_Stone{n}", sx - STONE / 2, sx + STONE / 2, sy - STONE_D / 2, sy + STONE_D / 2, z0, z0 + st,
                mat["bm_perch"])
        hidden_trigger(f"FNM_BM_Perch{k}_Trigger", px, py, z0 + top, PERCH_TOP, PERCH_TOP, PERCH_TRIGGER_H, project,
                       ["fnm_bm_perch", f"fnm_bm_slot_{k}"])
        vfx(f"FNM_BM_Perch{k}_Fx", px, py, z0 + top, PERCH_FX_SCALE, project, ["fnm_bm_perch_fx", f"fnm_bm_slot_{k}"],
            PERCH_FX)
    print("4 perches with stepping stones, triggers and beacons placed")

    park = z0 - PARK_DROP
    for lv, weapon in enumerate(GRANT_WEAPONS, 1):
        gx = GRANT_X0 + GRANT_DX * lv
        trig = device(TRIGGER, f"FNM_BM_Grant{lv}_Trigger", gx, GRANT_TRIGGER_Y, park)
        verse_tags(trig, project, ["fnm_bm_grant", f"fnm_bm_slot_{lv}"])
        options(trig, {"visible in Game": False, "reset Delay": 0.0}, f"Grant{lv}_Trigger")
        grant = device(GRANTER, f"FNM_BM_Grant{lv}_Granter", gx, GRANT_Y, park)
        wrong = options(grant, GRANT_SETTINGS, f"Grant{lv}_Granter")
        if wrong:
            sys.exit(f"granter {lv}: settings not taken: {wrong}")
        props(grant, {"grantItem": {"eventSubscriptions": [{"object": ref(trig), "eventDescriptor": {
            "memberParent": ref(TRIGGER_CLASS), "memberName": "OnTriggered"}}]}})
        item_list(grant, "pickupItemList", weapon, f"granter {lv}")
    print("5 granters bound to 5 parked grant triggers")

    cannons(project)
    vfx("FNM_BM_Strike", PLATFORM_X, PLATFORM_Y, park, STRIKE_SCALE, project, ["fnm_bm_strike"], STRIKE_FX)
    nuke = device(VFX, "FNM_BM_Nuke", PLATFORM_X - 300, PLATFORM_Y, park, sx=NUKE_SCALE)
    verse_tags(nuke, project, ["fnm_bm_nuke_fx"])
    effect = nuke_effect(enum_values(nuke, "visual_Effect"))
    options(nuke, {**NUKE_FX, "visual_Effect": effect}, "Nuke")
    knock = None
    for n in range(BLASTS):
        blast = device(EXPLOSIVE, f"FNM_BM_Blast{n + 1}", PLATFORM_X + 300 * (n + 1), PLATFORM_Y, park)
        verse_tags(blast, project, ["fnm_bm_blast"])
        if knock is None:
            choices = enum_values(blast, "knockback")
            knock = knockback(choices)
        options(blast, {**BLAST, "knockback": knock}, f"Blast{n + 1}")
    print(f"2 cannons, strike, nuke ({effect}), {BLASTS} blasts (knockback {knock}) placed")

    for lv, (fx, fy) in enumerate(anger_spots(), 1):
        vfx(f"FNM_BM_Anger{lv}", fx, fy, z0, ANGER_FX_SCALE, project, ["fnm_bm_anger_fx", f"fnm_bm_slot_{lv}"], ANGER_FX)
    print("5 anger VFX placed")

    boss_rig(project)
    dress(project)
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    n = len(placed())
    cx, cy, _ = at(*CENTRE)
    print(f"boss battle arena built round ({cx:.0f}, {cy:.0f}), radius {ARENA_R}: {n} actors tagged {TAG}; "
          f"nuke effect {effect}; blast knockback {knock}")


def cannon_frame(deg):
    """The cannon at deg round CENTRE: its body (x, y), heading (radians, the barrel turned onto boss_aim), pivot height,
    and point(local, ahead) -> (x, y, z) relative to ORIGIN for a point on the mesh (scale-1 local coordinates, as
    CANNON_MUZZLE) pushed `ahead` cm further along the barrel."""
    ax, ay, _ = boss_aim()
    bx, by = polar(CANNON_R, deg)
    heading = math.atan2(ay - by, ax - bx)
    k = CANNON_SCALE
    pz = FLOOR_Z + CANNON_HALF_H * k

    def point(local, ahead=0.0):
        a, f, up = local
        f = f * k + ahead
        return (bx + f * math.cos(heading) + a * k * math.sin(heading),
                by + f * math.sin(heading) - a * k * math.cos(heading), pz + up * k)
    return (bx, by), heading, pz, point


def muzzle_point(deg):
    """Where the cannon at deg's beam starts, relative to ORIGIN."""
    return cannon_frame(deg)[3](CANNON_MUZZLE, MUZZLE_AHEAD)


CANNON_SIDES = (("L", CANNON_DEG), ("R", 180 - CANNON_DEG))


def cannons(project=None):
    """The two mega laser cannons (CANNON_*): the mesh and two glow lights (always on). Their muzzle discharge and coil
    crackle are Niagara systems Verse spawns (BOSS_MODE 15g). Removes the cannon actors an older build left (the
    engine-shape cannon and the old VFX spawners too). Rerun boss_rig after: the beams start at muzzle_point."""
    project = project or c.project_mount().strip("/")
    old = [a for a in placed() if a.get("label", "").startswith("FNM_BM_Cannon")]
    for a in old:
        u.call(SCENE, "remove_from_scene", {"actor": ref(a["actorPath"])})
    print("removed", len(old), "old cannon actors")
    ax, ay, az = boss_aim()
    tz = FLOOR_Z + PLATFORM_H + BEAM_AIM
    k = CANNON_SCALE
    for side, deg in CANNON_SIDES:
        (bx, by), heading, pz, point = cannon_frame(deg)
        yaw = math.degrees(heading) - 90           # the mesh's barrel runs along its +Y
        x, y, _ = at(bx, by)
        r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": f"/{project}/{CANNON_ART}", "name": f"FNM_BM_Cannon{side}_Body",
                                                      "xform": xform(x, y, pz, k, k, k, yaw)})
        body = tagged(r["returnValue"]["refPath"], f"FNM_BM_Cannon{side}_Body")
        props(body, {"bCanBeDamaged": False})
        mx, my, mz = muzzle_point(deg)
        for name, (lx, ly, lz) in (("Glow", point(CANNON_COIL)), ("MuzzleGlow", point(CANNON_MUZZLE, 60))):
            options(device(POINT_LIGHT, f"FNM_BM_Cannon{side}_{name}", lx, ly, lz), CANNON_LIGHT, f"Cannon{side}_{name}")
        rng = math.hypot(ax - mx, ay - my, tz - mz) / 100
        print(f"cannon {side}: body at ({bx:.0f}, {by:.0f}) yaw {yaw:.1f}, muzzle ({mx:.0f}, {my:.0f}, {mz:.0f}), {rng:.1f} m to the titan's waist")


def boss_rig(project=None):
    """The boss platform, the Megabrute boss spawner on it and a laser beam per cannon (idempotent via BOSS_RIG_TAG;
    removes the platform and the per-level guard boss spawners FNM_BM_Boss1..5 an older build left). Each beam starts at
    its cannon's muzzle_point (the cannons themselves need not be placed first)."""
    project = project or c.project_mount().strip("/")
    old = [a for a in placed() if re.fullmatch(r"FNM_BM_Boss\d|FNM_BM_Platform", a.get("label", ""))]
    for a in old:
        u.call(SCENE, "remove_from_scene", {"actor": ref(a["actorPath"])})
    print("removed", clear(BOSS_RIG_TAG), "old boss rig actors and", len(old), "guard boss spawners")
    top = FLOOR_Z + PLATFORM_H
    marble = materials(["bm_marble"])["bm_marble"]
    platform = box("FNM_BM_Platform", PLATFORM_X - PLATFORM_W / 2, PLATFORM_X + PLATFORM_W / 2, PLATFORM_Y - PLATFORM_D / 2,
                   PLATFORM_Y + PLATFORM_D / 2, FLOOR_Z, top, marble)
    tagged(platform, "FNM_BM_Platform", BOSS_RIG_TAG)
    boss = device(CREATURE, "FNM_BM_Megaboss", PLATFORM_X, PLATFORM_Y, top, yaw=-90)
    tagged(boss, "FNM_BM_Megaboss", BOSS_RIG_TAG)
    verse_tags(boss, project, ["fnm_bm_megaboss"])      # tag first: the tag component rebuilds a device's sub-objects
    options(boss, MEGABOSS_SETTINGS, "Megaboss")

    tx, ty, _ = at(PLATFORM_X, PLATFORM_Y)
    tz = top + BEAM_AIM
    for k, (side, deg) in enumerate(CANNON_SIDES, 1):
        mx, my, mz = muzzle_point(deg)
        lx, ly, lz = at(mx, my, mz)
        loc = {"x": lx, "y": ly, "z": lz}
        dx, dy, dz = tx - loc["x"], ty - loc["y"], tz - loc["z"]
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        # Local +Z along the shot: yaw = its heading, pitch = its elevation - 90 (a rotator's up axis).
        rot = {"pitch": math.degrees(math.atan2(dz, math.hypot(dx, dy))) - 90, "yaw": math.degrees(math.atan2(dy, dx)), "roll": 0}
        r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": letter_asset(BEAM_LETTER), "name": f"FNM_BM_Beam{side}",
                                                      "xform": {"location": loc, "rotation": rot,
                                                                "scale": {"x": BEAM_W, "y": BEAM_W, "z": length / BEAM_H}}})
        beam = tagged(r["returnValue"]["refPath"], f"FNM_BM_Beam{side}", BOSS_RIG_TAG)
        u.call(ACTOR, "add_tag", {"actor": ref(beam), "tag": TAG})
        props(beam, {"bCanBeDamaged": False})
        options(beam, {"color": BEAM_COLOUR, "bNoCollision": True}, f"Beam{side}")
        verse_tags(beam, project, ["fnm_bm_beam", f"fnm_bm_slot_{k}"])
        print(f"beam {side}: {length / 100:.1f} m from ({loc['x']:.0f}, {loc['y']:.0f}, {loc['z']:.0f}), "
              f"pitch {rot['pitch']:.1f} yaw {rot['yaw']:.1f}")
    titan(project, top)
    print(f"boss rig: a {MEGABOSS} spawner on the platform, 2 beams, {len(TITAN_CLIPS)} titan clips")


def titan(project, top):
    """The titan's Animated Mesh devices FNM_BM_Titan1..N (tag fnm_bm_titan + slot, TITAN_CLIPS order), facing the entry.
    Needs tools/import_boss.py once per UEFN project."""
    x, y, _ = at(PLATFORM_X, PLATFORM_Y)
    ex, ey, _ = at(*ENTRY)
    yaw = math.degrees(math.atan2(ey - y, ex - x))       # the mesh faces +X
    for k, clip in enumerate(TITAN_CLIPS, 1):
        z = top if k == 1 else top - TITAN_PARK
        r = u.call(DEV, "PlaceDevice", {"assetPath": ref(ANIMATED_MESH),
                                        "transform": xform(x, y, z, TITAN_SCALE, TITAN_SCALE, TITAN_SCALE, yaw)})
        dev = tagged(r["returnValue"]["refPath"], f"FNM_BM_Titan{k}", BOSS_RIG_TAG)
        u.call(ACTOR, "add_tag", {"actor": ref(dev), "tag": TAG})
        verse_tags(dev, project, ["fnm_bm_titan", f"fnm_bm_slot_{k}"])
        props(dev, titan_clip_props(project, clip))
        got = get(dev, ["skeletalMesh", "animation"])
        if not got.get("animation", {}).get("refPath", "").endswith(f"A_fnm_titan_{clip}"):
            sys.exit(f"FNM_BM_Titan{k}: animation did not take ({got}); run tools/import_boss.py")
    print(f"titan: {len(TITAN_CLIPS)} clips at scale {TITAN_SCALE}, yaw {yaw:.1f}")


def titan_clip_props(project, clip):
    """An Animated Mesh device's settings for one titan clip: its mesh (its own, or for a TITAN_SHARED clip the base clip's)
    and animation, Playing from the start, looping unless it is a one-shot (TITAN_ONCE: it plays once and holds; Verse
    rewinds and replays it, fnm_titan.verse). The race finale's titan and the volcano's use them too
    (tools/build_race_boss.py, tools/build_landmarks.py)."""
    art = f"/{project}/{TITAN_ART}"
    mesh = TITAN_SHARED.get(clip, clip)
    return {"skeletalMesh": {"refPath": f"{art}/Clip_{mesh}/{TITAN_MESH}_{mesh}.{TITAN_MESH}_{mesh}"},
            "animation": {"refPath": f"{art}/Clip_{clip}/A_fnm_titan_{clip}.A_fnm_titan_{clip}"},
            "loop": clip not in TITAN_ONCE, "initialState": "Playing"}


def retitan(project=None):
    """Re-place only the titan's clip devices (FNM_BM_Titan*), the rest of the boss rig left as it is: what a new titan clip
    needs (G9 D2). Their transform comes from the platform, as boss_rig places them."""
    project = project or c.project_mount().strip("/")
    old = [a for a in placed() if re.fullmatch(r"FNM_BM_Titan\d+", a.get("label", ""))]
    for a in old:
        u.call(SCENE, "remove_from_scene", {"actor": ref(a["actorPath"])})
    print("removed", len(old), "old titan clip devices")
    titan(project, FLOOR_Z + PLATFORM_H)


def letter_asset(letter):
    """The Alphabet set's PPID for letter (the plain one, not the x2 or TA variants)."""
    found = u.call(ASSETS, "find_assets", {"folder_path": LETTER_ASSET.rstrip("/"), "name": f"CP_Alphabet_{letter}_",
                                           "recursive": False})["returnValue"]
    plain = sorted(p for p in found if re.search(rf"PPID_CRG_Props_CP_Alphabet_{letter}_[0-9a-f]+\.", p))
    if not plain:
        sys.exit(f"Alphabet letter {letter} not found under {LETTER_ASSET}")
    return plain[0]


def dress(project=None):
    """The chests on the perches, the floating letters over the pads, and ammo on the weapon granters (idempotent via
    DRESS_TAG; the old letter billboards FNM_BM_Label* are removed if a build before this one left them)."""
    project = project or c.project_mount().strip("/")
    old = [a for a in placed() if re.fullmatch(r"FNM_BM_Label[A-D]", a.get("label", ""))]
    for a in old:
        u.call(SCENE, "remove_from_scene", {"actor": ref(a["actorPath"])})
    print("removed", clear(DRESS_TAG), "old dressing actors and", len(old), "letter billboards")
    z0 = FLOOR_Z

    for i, (dx, dy) in enumerate(PAD_SPOTS):
        letter = LETTERS[i]
        x, y, _ = at(dx, dy)
        r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": letter_asset(letter), "name": f"FNM_BM_Letter{letter}",
                                                      "xform": xform(x, y, LETTER_Z, LETTER_SCALE, LETTER_SCALE,
                                                                     LETTER_SCALE, yaw=180)})
        actor = tagged(r["returnValue"]["refPath"], f"FNM_BM_Letter{letter}", DRESS_TAG)
        props(actor, {"bCanBeDamaged": False})
        options(actor, {"color": LETTER_PROP_COLOURS[i], "bNoCollision": True}, f"Letter{letter}")
        verse_tags(actor, project, ["fnm_bm_letter", f"fnm_bm_slot_{i + 1}"])
    print(f"4 floating letters at z {LETTER_Z}, scale {LETTER_SCALE}")

    for k, (px, py, top) in enumerate(PERCHES, 1):
        toward = -1 if px > 0 else 1                     # the stones' side (stones_for)
        x, y, _ = at(px - toward * CHEST_BACK, py)
        r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": CHEST_MESH, "name": f"FNM_BM_Chest{k}",
                                                      "xform": xform(x, y, z0 + top, CHEST_SCALE, CHEST_SCALE,
                                                                     CHEST_SCALE, yaw=180 if toward > 0 else 0)})
        tagged(r["returnValue"]["refPath"], f"FNM_BM_Chest{k}", DRESS_TAG)
        button = u.call(DEV, "PlaceDevice", {"assetPath": ref(BUTTON), "transform": xform(
            x, y, z0 + top + 30 * CHEST_SCALE, yaw=180 if toward > 0 else 0)})["returnValue"]["refPath"]
        tagged(button, f"FNM_BM_Chest{k}_Button", DRESS_TAG)
        verse_tags(button, project, ["fnm_bm_chest", f"fnm_bm_slot_{k}"])
        options(button, CHEST_BUTTON, f"Chest{k}_Button")
        beacon = device(BEACON, f"FNM_BM_Chest{k}_Beacon", px - toward * CHEST_BACK, py, z0 + top + CHEST_BEACON_Z,
                        sx=CHEST_BEACON_SCALE)
        tagged(beacon, f"FNM_BM_Chest{k}_Beacon", DRESS_TAG)
        verse_tags(beacon, project, ["fnm_bm_chest_beacon", f"fnm_bm_slot_{k}"])
        options(beacon, CHEST_BEACON, f"Chest{k}_Beacon")
        light = device(POINT_LIGHT, f"FNM_BM_Chest{k}_Light", px - toward * CHEST_BACK, py, z0 + top + CHEST_LIGHT_Z)
        tagged(light, f"FNM_BM_Chest{k}_Light", DRESS_TAG)
        verse_tags(light, project, ["fnm_bm_chest_light", f"fnm_bm_slot_{k}"])
        options(light, CHEST_LIGHT, f"Chest{k}_Light")
    print("4 weapon chests on the perches (buttons off), each with an arrow beacon and a gold light")

    granters = [a for a in placed() if re.fullmatch(r"FNM_BM_Grant\d_Granter", a.get("label", ""))]
    for a in granters:
        wrong = options(a["actorPath"], {"giveExtraAmmo": 1}, a["label"])
        if wrong:
            sys.exit(f"{a['label']}: extra ammo not taken: {wrong}")
    print(f"{len(granters)} granters give extra ammo")


# ---------------------------------------------------------------- check / probe

def check():
    actors = sorted(placed(), key=lambda a: a.get("label", ""))
    print(len(actors), "boss battle actors")
    for a in actors:
        label, path = a.get("label", ""), a["actorPath"]
        if re.fullmatch(r"FNM_BM_(Boss\d|Gate\d_Spawner)", label):
            want = {**BOSS_SETTINGS, "guardTeamOption": TEAM} if "_Boss" in label else GATE_SETTINGS
            back = get(path, list(want) + ["max Health"])
            lst = get(path, ["itemList"])["itemList"]["refPath"]
            items = [(i.get("itemDefinition") or {}).get("refPath", "").rsplit(".", 1)[-1] for i in get(lst, ["itemListData"])["itemListData"]]
            off = {k: back.get(k) for k, v in want.items() if back.get(k) != v}
            print(f"  {label:28} items {items} health {back.get('max Health')} off-spec {off}")
        elif re.search(r"(_Fx|Strike|Nuke|Anger\d)$", label):
            want = (GATE_FX if "_Gate" in label else PERCH_FX if "_Perch" in label else STRIKE_FX if "Strike" in label
                    else NUKE_FX if "Nuke" in label else ANGER_FX)
            print(f"  {label:28} {get(path, want)}")
        elif re.fullmatch(r"FNM_BM_Creature\d", label):
            print(f"  {label:28} {get(path, ['creature Type', *CREATURE_SETTINGS])}")
        elif re.fullmatch(r"FNM_BM_Blast\d", label):
            print(f"  {label:28} {get(path, BLAST)}")
        elif "Granter" in label:
            lst = get(path, ["pickupItemList"])["pickupItemList"]["refPath"]
            items = [(i.get("itemDefinition") or {}).get("refPath", "").rsplit(".", 1)[-1] for i in get(lst, ["itemListData"])["itemListData"]]
            print(f"  {label:28} items {items} {get(path, GRANT_SETTINGS)}")
        else:
            b = a.get("bounds", {})
            lo, hi = b.get("min", {}), b.get("max", {})
            print(f"  {label:28} ({lo.get('x', 0):.0f}, {lo.get('y', 0):.0f}, {lo.get('z', 0):.0f}) .. "
                  f"({hi.get('x', 0):.0f}, {hi.get('y', 0):.0f}, {hi.get('z', 0):.0f})")


def probe():
    """BOSS_MODE.md 3 UNVERIFIED items answerable in the editor. Temporary devices are tagged fnm_test and removed."""
    for name in ("Creature", "Wildlife", "Sentry"):
        found = u.call(DEV, "ListDeviceAssets", {"nameFilter": name})["returnValue"]
        print(f"ListDeviceAssets {name!r}:", ", ".join(f"{d['displayName']} ({d['assetPath']['refPath']})" for d in found) or "none")
    temp = []

    def place(asset, dx):
        x, y, _ = at(dx, -2000)
        a = u.call(DEV, "PlaceDevice", {"assetPath": ref(asset), "transform": xform(x, y, -3000)})["returnValue"]["refPath"]
        u.call(ACTOR, "add_tag", {"actor": ref(a), "tag": "fnm_test"})
        temp.append(a)
        return a

    try:
        fx = place(VFX, 0)
        schema = json.loads(u.call(OBJ, "list_properties", {"instance": ref(fx)}, timeout=180)["returnValue"])
        effects = schema["visual_Effect"]["enum"]
        print("VFX visual_Effect:", ", ".join(effects))
        print("VFX effectType:", ", ".join(schema["effectType"]["enum"]))
        print("VFX sound_Effect:", ", ".join(schema["sound_Effect"]["enum"]))
        print("nuke effect chosen:", nuke_effect(effects))
        ex = place(EXPLOSIVE, 300)
        knocks = enum_values(ex, "knockback")
        print("explosive knockback:", ", ".join(knocks), "-> chosen", knockback(knocks))
        gr = place(GRANTER, 600)
        lst = get(gr, ["pickupItemList"])["pickupItemList"]["refPath"]
        for weapon in GRANT_WEAPONS:
            props(lst, {"itemListData": [{"itemDefinition": ref(weapon), "itemQuantity": 1}]})
            back = get(lst, ["itemListData"])["itemListData"]
            ok = bool(back) and (back[0].get("itemDefinition") or {}).get("refPath") == weapon
            print("granter", "accepted" if ok else "REFUSED ", weapon.rsplit(".", 1)[1])
        cs = place("/CRD_Creatures/SetupAssets/PID_Device_CreatureSpawner_V2.PID_Device_CreatureSpawner_V2", 900)
        schema = json.loads(u.call(OBJ, "list_properties", {"instance": ref(cs)}, timeout=180)["returnValue"])
        for k, v in schema.items():
            if "enum" in v and any(w in k.lower() for w in ("creature", "type", "team", "spawn")):
                print(f"creature spawner {k}: {', '.join(v['enum'])}")
    finally:
        for a in temp:
            u.call(SCENE, "remove_from_scene", {"actor": ref(a)})
        print(f"removed {len(temp)} probe devices")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="list the placed actors and the devices' read-back options")
    ap.add_argument("--dress", action="store_true", help="(re)place only the chests and floating letters, granter ammo")
    ap.add_argument("--probe", action="store_true", help="answer BOSS_MODE.md 3's UNVERIFIED items (no build)")
    ap.add_argument("--boss", action="store_true", help="(re)place only the Megabrute boss spawner and the cannon beams")
    ap.add_argument("--cannons", action="store_true", help="(re)place only the mega laser cannons, then the boss rig")
    ap.add_argument("--titan", action="store_true", help="(re)place only the titan's clip devices (TITAN_CLIPS)")
    a = ap.parse_args()
    if a.titan:
        retitan()
        u.call(ASSETS, "save_assets", {"asset_paths": []})
    elif a.dress or a.boss or a.cannons:
        if a.cannons:
            cannons()
        dress() if a.dress else boss_rig()
        u.call(ASSETS, "save_assets", {"asset_paths": []})
    else:
        check() if a.check else probe() if a.probe else build()
