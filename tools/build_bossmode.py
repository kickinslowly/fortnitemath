"""Build the BOSS BATTLE mode's arena (BOSS_MODE.md section 3, maps/starter/LAYOUT.md "Boss battle arena") in the open
UEFN project through UEFN MCP.

Aaron (2026-10-09): "an arena fight, just like the boss battle, but it's only a boss battle ... monsters and npcs spawn
at increasing intervals from gates in the walls ... weapons spawn around map each level but in set places the player
must reach, like elevated platforms that must be jumped to". A 40 x 40 m walled arena 140 m east of the course (it reads
no course geometry, so a course rebuild never moves it): four answer pads (fnm_bm + fnm_door_a..d), a steel boss platform
with one guard spawner per level (fnm_bm_boss + fnm_bm_slot_L), four gates in the side walls, each a real opening with a
dark alcove holding a monster spawner (fnm_bm_gate + slot) and a lightning VFX at its mouth (fnm_bm_gate_fx + slot),
four gold perches reached by stepping stones with a hidden trigger and a beacon VFX on each top (fnm_bm_perch /
fnm_bm_perch_fx + slot), one Item Granter per level parked under the floor and bound to its own hidden trigger
(fnm_bm_grant + slot), the cannon rig of the race arena (build_cannon.cannon with the FNM_BM_Cannon prefix and the
fnm_bm_cannon_fx tag) plus a parked strike, two blasts and a nuke VFX, an anger ring of five VFX round the platform
(fnm_bm_anger_fx + slot), and one creature spawner per creature kind in the gate alcoves (fnm_bm_creature + slot = kind;
B5, BOSS_MODE.md 5). The director (console/verse/fnm_bossmode.verse) finds every piece by those Verse tags.

Coordinates are relative to ORIGIN, the south (entry) wall's inner face on the arena's centre line; the player enters
facing +Y, so +X is their LEFT (pad A, like door A). Every actor is labelled FNM_BM_* and tagged TAG.

Idempotent: every actor this script creates is tagged TAG; a run first deletes everything with TAG.
Materials first (once): python tools/import_art.py bm_wall bm_floor bm_perch  (plus steel, glow, pad_a..d).

    python tools/build_bossmode.py            # (re)build the arena
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
import build_cannon as cn  # noqa: E402
import build_course as c  # noqa: E402
import build_guards as g  # noqa: E402
import build_pickups as p  # noqa: E402
from build_course import (ACTOR, ASSETS, BILLBOARD, BOSS_SETTINGS, CUBE, DEV, LETTER_COLOURS, LETTERS, OBJ, PAD_H,  # noqa: E402
                          PAD_SIZE, PAD_TILE_T, SCENE, SIGN_COLOUR, SLAB_T, STEP_BOX, STEP_Z, TELEPORTER, TRIGGER,
                          WALL_T, props, ref, trigger_fit, verse_tags, xform)
from build_rigs import GRANTER, TRIGGER_CLASS  # noqa: E402

TAG = "fnm_bossmode"
ORIGIN = (14000.0, -14000.0, 0.0)   # south wall inner face, centre line; the floor's top is at z 2
FLOOR_Z = 2
ARENA_W = 4000          # between the side walls' inner faces (x -2000 .. +2000)
ARENA_L = 4000          # between the end walls' inner faces (y 0 .. 4000)
WALL_H = 800
ENTRY = (0, 250)        # the entry teleporter (yaw 90): arrival and respawn point
SIGN = (1995, 600, 250)
# Answer pads A..D (x, y): +X is the player's left, so they read A B / C D like the HUD. Tile, trigger and letter board as
# the race arena's (build_course.arena).
PAD_SPOTS = [(900, 1100), (-900, 1100), (900, 2100), (-900, 2100)]
PAD_BOARD_Z = 300
PAD_BOARD_SCALE = 1.5
PAD_TRIGGER = {"timesCanTrigger_Override": False, "triggerDelay": 0.0, "reset Delay": 0.0, "visible in Game": False,
               "triggeredByVehicles": False, "triggeredByWater": False, "triggeredByPhysicsProps": False}
# The boss platform (steel), its centre, size and height; one boss spawner per level stands on it at BOSS_XS.
PLATFORM_X, PLATFORM_Y = 0, 3200
PLATFORM_W, PLATFORM_D, PLATFORM_H = 800, 500, 100
BOSS_XS = (-120, -60, 0, 60, 120)
BOSS_HEALTH_ASK = 100000.0
# Boss weapon per level (BOSS_MODE.md 4); all accepted by the guard spawner (build_guards docstring), none a sniper or
# launcher (no one-shot kills).
_W = "/Game/Athena/Items/Weapons/{0}.{0}"
BOSS_WEAPONS = [_W.format(n) for n in (
    "WID_Pistol_SemiAuto_Athena_R_Ore_T03",
    "WID_Pistol_AutoHeavyPDW_Athena_R_Ore_T03",
    "WID_Pistol_AutoHeavyPDW_Athena_VR_Ore_T03",
    "WID_Shotgun_Combat_Athena_VR_Ore_T03",
    "WID_Assault_Heavy_Athena_VR_Ore_T03")]
# Gates G1..G4 as (side, y): side +1 = the left wall (x +2000), -1 = the right (x -2000). An opening GATE_W wide and GATE_H
# tall, an ALCOVE_D deep alcove behind it (back, sides, roof and its own floor) in steel, the monster spawner at the
# alcove centre facing into the arena, a lightning VFX at the mouth.
GATES = [(-1, 1200), (1, 1200), (-1, 3000), (1, 3000)]
GATE_W, GATE_H = 400, 350
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
# Perches P1..P4 as (x, y, top above the floor): P1 front-right, P2 front-left, P3 back-right, P4 back-left. A PERCH_TOP
# square gold block; stepping stones STONE long (along the climb) and STONE_D wide (as wide as the perch), each STONE_RISE
# lower than the next, STONE_GAP apart edge to edge, laid from the perch toward the arena's centre line (the lowest
# farthest out). B6 keys test 2026-10-09: with 120 x 120 stones, 60 cm rises and 150 cm gaps the player reached the top
# stone but fell into the 150 cm gap before the perch and stood against its 180 cm face (a restart); the stones were
# also as narrow as a player's sideways drift. Now 50 / 100 (the spec's fallback) and stones as wide as the perch.
PERCHES = [(-1600, 500, 180), (1600, 500, 180), (-1600, 3500, 240), (1600, 3500, 240)]
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
GRANT_SETTINGS = {**p.GRANT_SETTINGS, "equipItemOnGrant": 1}
GRANT_X0, GRANT_DX, GRANT_Y, GRANT_TRIGGER_Y = -1200, 300, 600, 300
# The cannon rig: one cannon per side wall CANNON_Y in, aimed at the platform top + build_cannon.BOSS_EYE.
CANNON_Y = 2200
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
STRIKE_FX = {**cn.STRIKE_FX, "visual_Effect": "LightningBolt_03"}
NUKE_FX = {"enabled On Phase": "None", "visual_Effect": "LightningBolt_01", "effectType": "Burst",
           "sound_Effect": "Explosion", "clearParticlesOnDisable": True}
# Fallbacks decided from the device's own enums at build time (nuke_effect, knockback).
NUKE_WORDS = ("Explosion", "Smoke", "Fire", "Blast")
NUKE_FALLBACK = "LightningBolt_01"
KNOCKBACK_WANT, KNOCKBACK_FALLBACK = "High", "Medium"
GLASS = "/Game/Creative/Environments/Meshes/Glass/Materials/Glass_version_02/MI_CP_GlassGallery.MI_CP_GlassGallery"
LID_T, LID_SINK = 40, 20
VFX = cn.VFX
EXPLOSIVE = cn.EXPLOSIVE


# ---------------------------------------------------------------- pure layout (tests read these)

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
    for gate, dy in zip(CREATURE_GATES, CREATURE_DY):
        side, gy = GATES[gate - 1]
        out.append((side * (ARENA_W / 2 + WALL_T + CREATURE_IN), gy + dy, gate))
    return out


def anger_spots():
    return [(PLATFORM_X + ANGER_RADIUS * math.cos(math.radians(a)), PLATFORM_Y + ANGER_RADIUS * math.sin(math.radians(a)))
            for a in ANGER_ANGLES]


def boss_aim():
    """The cannons' aim point, relative to ORIGIN."""
    return PLATFORM_X, PLATFORM_Y, FLOOR_Z + PLATFORM_H + cn.BOSS_EYE


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


def tagged(actor, label):
    u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
    u.call(ACTOR, "set_label", {"actor": ref(actor), "label": label})
    return actor


def paint(actor, material, **extra):
    comp = json.loads(u.call(OBJ, "get_properties", {"instance": ref(actor), "properties": ["staticMeshComponent"]})["returnValue"])
    u.call(OBJ, "set_properties", {"instance": comp["staticMeshComponent"],
                                   "values": json.dumps({"overrideMaterials": [ref(material)], **extra})})


def box(label, x0, x1, y0, y1, z0, z1, material=None, **extra):
    """A solid from a scaled engine cube; x / y relative to ORIGIN, z absolute (the floor's top is FLOOR_Z)."""
    x0, x1, y0, y1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    cx, cy, _ = at((x0 + x1) / 2, (y0 + y1) / 2)
    r = u.call(SCENE, "add_to_scene_from_asset", {"asset_path": CUBE, "name": label, "xform": xform(
        cx, cy, (z0 + z1) / 2, (x1 - x0) / 100, (y1 - y0) / 100, (z1 - z0) / 100)})
    actor = tagged(r["returnValue"]["refPath"], label)
    if material:
        paint(actor, material, **extra)
    return actor


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


def placed():
    found = u.call(SCENE, "find_actors", {"tag": TAG, "collision_channels": []})
    return [a for a in (found if isinstance(found, list) else found.get("returnValue", [])) if isinstance(a, dict)]


# ---------------------------------------------------------------- build

def shell(mat):
    """Floor slab, the four walls with the gate openings, the alcoves, the hidden lid."""
    hw, t, z0 = ARENA_W / 2, WALL_T, FLOOR_Z
    box("FNM_BM_Floor", -hw - t, hw + t, -t, ARENA_L + t, z0 - SLAB_T, z0, mat["bm_floor"])
    box("FNM_BM_WallS", -hw - t, hw + t, -t, 0, 0, WALL_H, mat["bm_wall"])
    box("FNM_BM_WallN", -hw - t, hw + t, ARENA_L, ARENA_L + t, 0, WALL_H, mat["bm_wall"])
    for side, name in ((1, "L"), (-1, "R")):
        gates = sorted(y for s, y in GATES if s == side)
        x0, x1 = side * hw, side * (hw + t)
        y = 0
        for n, gy in enumerate(gates + [None], 1):
            y1 = gy - GATE_W / 2 if gy is not None else ARENA_L
            box(f"FNM_BM_Wall{name}{n}", x0, x1, y, y1, 0, WALL_H, mat["bm_wall"])
            if gy is not None:
                box(f"FNM_BM_Lintel{name}{n}", x0, x1, y1, gy + GATE_W / 2, z0 + GATE_H, WALL_H, mat["bm_wall"])
                y = gy + GATE_W / 2
    for k, (side, gy) in enumerate(GATES, 1):
        a, b, back = side * (hw + t), side * (hw + t + ALCOVE_D), side * (hw + t + ALCOVE_D + t)
        y0, y1 = gy - GATE_W / 2, gy + GATE_W / 2
        box(f"FNM_BM_Gate{k}_Floor", side * hw, back, y0 - t, y1 + t, z0 - SLAB_T, z0, mat["steel"])
        box(f"FNM_BM_Gate{k}_Back", b, back, y0 - t, y1 + t, 0, z0 + GATE_H + t, mat["steel"])
        box(f"FNM_BM_Gate{k}_SideA", a, b, y0 - t, y0, 0, z0 + GATE_H + t, mat["steel"])
        box(f"FNM_BM_Gate{k}_SideB", a, b, y1, y1 + t, 0, z0 + GATE_H + t, mat["steel"])
        box(f"FNM_BM_Gate{k}_Roof", a, back, y0 - t, y1 + t, z0 + GATE_H, z0 + GATE_H + t, mat["steel"])
    lid = WALL_H - LID_SINK
    box("FNM_BM_Lid", -hw - t, hw + t, -t, ARENA_L + t, lid, lid + LID_T, GLASS, bVisible=False, bHiddenInGame=True)
    print(f"shell: floor, 4 walls with {len(GATES)} gate openings, {len(GATES)} alcoves, hidden lid at z {lid}")


def build():
    project = c.project_mount().strip("/")
    art = f"/{project}/FNM_Art"
    keys = ("bm_wall", "bm_floor", "bm_perch", "steel", "glow", "pad_a", "pad_b", "pad_c", "pad_d")
    mat = {k: f"{art}/M_fnm_wall_{k}.M_fnm_wall_{k}" for k in keys}
    missing = [k for k in keys if not u.call(ASSETS, "exists", {"path": f"{art}/M_fnm_wall_{k}"})["returnValue"]]
    if missing:
        sys.exit(f"materials missing: {missing}: python tools/import_art.py {' '.join(missing)}")
    print("removed", clear(), "old boss battle actors;", clear("fnm_test"), "test actors")
    z0 = FLOOR_Z
    shell(mat)

    tp = device(TELEPORTER, "FNM_BM_Entry", *ENTRY, 0, yaw=90)
    props(tp, {"knob_TeleporterGroup": "Group_None", "knob_TargetTeleporterGroup": "Group_None"})
    verse_tags(tp, project, ["fnm_bm", "fnm_entry"])
    sign = device(BILLBOARD, "FNM_BM_Sign", SIGN[0], SIGN[1], SIGN[2], yaw=-90, sx=2)
    c.board(sign, "BOSS BATTLE", SIGN_COLOUR)
    print("entry teleporter and sign placed")

    for i, (dx, dy) in enumerate(PAD_SPOTS):
        letter = LETTERS[i]
        h = PAD_SIZE / 2
        box(f"FNM_BM_Pad{letter}", dx - h, dx + h, dy - h, dy + h, z0, z0 + PAD_TILE_T, mat[f"pad_{letter.lower()}"])
        hidden_trigger(f"FNM_BM_Trigger{letter}", dx, dy, z0, PAD_SIZE, PAD_SIZE, PAD_H, project,
                       ["fnm_bm", f"fnm_door_{letter.lower()}"])
        board = device(BILLBOARD, f"FNM_BM_Label{letter}", dx, dy, PAD_BOARD_Z, yaw=180, sx=PAD_BOARD_SCALE)
        c.board(board, letter, LETTER_COLOURS[i])
    print("4 answer pads placed (A B near, C D far; A on the player's left)")

    box("FNM_BM_Platform", PLATFORM_X - PLATFORM_W / 2, PLATFORM_X + PLATFORM_W / 2, PLATFORM_Y - PLATFORM_D / 2,
        PLATFORM_Y + PLATFORM_D / 2, z0, z0 + PLATFORM_H, mat["steel"])
    kept = []
    for lv, (bx, weapon) in enumerate(zip(BOSS_XS, BOSS_WEAPONS), 1):
        _, health = guard(f"FNM_BM_Boss{lv}", PLATFORM_X + bx, PLATFORM_Y, z0 + PLATFORM_H, -90, project,
                          ["fnm_bm_boss", f"fnm_bm_slot_{lv}"], {**BOSS_SETTINGS, "guardTeamOption": TEAM}, weapon,
                          BOSS_HEALTH_ASK)
        kept.append(health)
    print(f"platform + 5 boss spawners; health kept: {kept}")

    for k, ((side, gy), weapon) in enumerate(zip(GATES, GATE_WEAPONS), 1):
        ax = side * (ARENA_W / 2 + WALL_T + ALCOVE_D / 2)
        guard(f"FNM_BM_Gate{k}_Spawner", ax, gy, z0, 180 if side > 0 else 0, project,
              ["fnm_bm_gate", f"fnm_bm_slot_{k}"], GATE_SETTINGS, weapon)
        vfx(f"FNM_BM_Gate{k}_Fx", side * (ARENA_W / 2 + WALL_T / 2), gy, z0, GATE_FX_SCALE, project,
            ["fnm_bm_gate_fx", f"fnm_bm_slot_{k}"], GATE_FX)
    print("4 gate spawners + 4 gate VFX placed")

    for k, (sx, sy, _) in enumerate(creature_spots(), 1):
        kind = CREATURES[k - 1]
        cs = device(CREATURE, f"FNM_BM_Creature{k}", sx, sy, z0, yaw=180 if sx > 0 else 0)
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

    steel, glow = mat["steel"], mat["glow"]
    ax, ay, az = boss_aim()
    aim = (ORIGIN[0] + ax, ORIGIN[1] + ay, az)
    cn.cannon("L", ORIGIN[0] + ARENA_W / 2, ORIGIN[1], z0, aim, project, steel, glow, prefix="FNM_BM_Cannon",
              fx_tag="fnm_bm_cannon_fx", cannon_y=CANNON_Y, tag=TAG)
    cn.cannon("R", ORIGIN[0] - ARENA_W / 2, ORIGIN[1], z0, aim, project, steel, glow, prefix="FNM_BM_Cannon",
              fx_tag="fnm_bm_cannon_fx", cannon_y=CANNON_Y, tag=TAG)
    vfx("FNM_BM_Strike", PLATFORM_X, PLATFORM_Y, park, STRIKE_SCALE, project, ["fnm_bm_strike"], STRIKE_FX)
    nuke = device(VFX, "FNM_BM_Nuke", PLATFORM_X - 300, PLATFORM_Y, park, sx=NUKE_SCALE)
    verse_tags(nuke, project, ["fnm_bm_nuke_fx"])
    effect = nuke_effect(enum_values(nuke, "visual_Effect"))
    options(nuke, {**NUKE_FX, "visual_Effect": effect}, "Nuke")
    knock = None
    for n in range(cn.BLASTS):
        blast = device(EXPLOSIVE, f"FNM_BM_Blast{n + 1}", PLATFORM_X + 300 * (n + 1), PLATFORM_Y, park)
        verse_tags(blast, project, ["fnm_bm_blast"])
        if knock is None:
            choices = enum_values(blast, "knockback")
            knock = knockback(choices)
        options(blast, {**cn.BLAST, "knockback": knock}, f"Blast{n + 1}")
    print(f"2 cannons, strike, nuke ({effect}), {cn.BLASTS} blasts (knockback {knock}) placed")

    for lv, (fx, fy) in enumerate(anger_spots(), 1):
        vfx(f"FNM_BM_Anger{lv}", fx, fy, z0, ANGER_FX_SCALE, project, ["fnm_bm_anger_fx", f"fnm_bm_slot_{lv}"], ANGER_FX)
    print("5 anger VFX placed")

    u.call(ASSETS, "save_assets", {"asset_paths": []})
    n = len(placed())
    print(f"boss battle arena built at x {ORIGIN[0] - ARENA_W / 2:.0f}..{ORIGIN[0] + ARENA_W / 2:.0f}, "
          f"y {ORIGIN[1]:.0f}..{ORIGIN[1] + ARENA_L:.0f}: {n} actors tagged {TAG}; boss health kept {kept[0]}; "
          f"nuke effect {effect}; blast knockback {knock}")


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
                    else NUKE_FX if "Nuke" in label else ANGER_FX if "Anger" in label else cn.MUZZLE_FX)
            print(f"  {label:28} {get(path, want)}")
        elif re.fullmatch(r"FNM_BM_Creature\d", label):
            print(f"  {label:28} {get(path, ['creature Type', *CREATURE_SETTINGS])}")
        elif re.fullmatch(r"FNM_BM_Blast\d", label):
            print(f"  {label:28} {get(path, cn.BLAST)}")
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
    ap.add_argument("--probe", action="store_true", help="answer BOSS_MODE.md 3's UNVERIFIED items (no build)")
    a = ap.parse_args()
    check() if a.check else probe() if a.probe else build()
