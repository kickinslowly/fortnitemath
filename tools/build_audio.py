"""Place the sound layer (console/verse/fnm_audio.verse) in the open UEFN project through UEFN MCP.

One Creative audio player (`PID_CP_Devices_CRD_AudioPlayer`) per wired cue, parked underground on its own row,
Verse-tagged `fnm_cue_<id>` and labelled `FNM_Cue_<Id>`. The director's fnm_audio finds them by tag at OnBegin and
calls `Play(Player)` on them, so every cue is heard by THAT player only (`can Be Heard By` = Instigator Only, which
Verse's Play(Agent) requires), played at the player, non-spatial, with no distance fall-off.

The device's options are plain properties on the ACTOR (not on its `creativeAudio` component, which holds only
`stereoSpreadScaleFactor`): `audio` (the SoundBase), `volume`, `can Be Heard By`, `play Location`,
`enable Spatialization`, `enable Volume Attenuation`, `loopAudio`, `restart Audio When Activated`, `play On Hit`,
`visible In Game`, `autoPlay - *`.

Idempotent: every actor this script creates is tagged TAG; a run first deletes everything with TAG.

    python tools/build_audio.py                # (re)place every wired cue, save
    python tools/build_audio.py --list         # placed devices with their sound and the read-back options
    python tools/build_audio.py --probe Mud,Countdown_Go
                                               # find_assets matches per name (SoundCue + SoundWave), class, duration
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402
from build_course import ACTOR, DEV, OBJ, SCENE, ref, verse_tags, xform  # noqa: E402

TAG = "fnm_audio"
ASSETS = "editor_toolset.toolsets.asset.AssetTools"
PLAYER = "/CRD_AudioPlayer/SetupAssets/PID_CP_Devices_CRD_AudioPlayer.PID_CP_Devices_CRD_AudioPlayer"
# Underground, on a row of its own: tools/build_rigs.py parks its rigs at y = -8000 - 800 * row for rows 0..9
# (down to y = -15200), so this row starts below them.
PARK = (-4000, -17000, -1500)
PITCH = 800

# Island validation ("illegally references", AssetReferenceRestrictions) accepts only the Creative sound library,
# /Game/Sounds/Creative, plus the Creative devices' own sounds that it passed (/CRD_SkilledInteractionDevice). Refused on
# 2026-10-07: Rocket Racing (/DelMarUI, /DelMarCosmetics), /FNGameplayCues, /PoppySoap, /ShockwaveMace, /MudGameplay,
# /SpireSharedAssets, /CRD_HenchmanSpawner, and /Game outside Sounds/Creative (Fort_Traps, Fort_GamePlay_Sounds,
# Fort_Music, Fort_Human_Barks, Athena). find_assets lists them all; only a session start tells.
CR = "/Game/Sounds/Creative"
TOYS = CR + "/Toys"
STING = CR + "/Gadgets/Radio/Stingers"
FAN = CR + "/Gadgets/Radio/Music_Loops/Fantasy"
MX = CR + "/Gadgets/Radio/Music_Loops"
SKILL = "/CRD_SkilledInteractionDevice/Audio"

# Every cue: heard by the player Verse names in Play(Agent) only, at the player, flat (no 3D panning, no fall-off).
BASE = {
    "can Be Heard By": "Instigator Only",
    "play Location": "Instigating Player",
    "enable Spatialization": False,
    "enable Volume Attenuation": False,
    "volume": 1.0,
    "loopAudio": False,
    "restart Audio When Activated": True,
    "play On Hit": False,
    "visible In Game": False,
    "autoPlay - Gameplay": False,
}
# Music beds loop until Stop(Agent).
LOOP = {"loopAudio": True, "volume": 0.5}

# cue id (snake, = fnm_cue_<id> tag) -> (asset path or None = no library sound yet, option overrides)
# The single place the mapping lives. Durations are in console/AUDIO.md (`--list` reads them back).
CUES = {
    # The Creative floor-siren timer: three ticks, then its GO tone.
    "countdown3": (f"{TOYS}/Floor_Siren/Timer_UI_Tick_Minigame_Cue.Timer_UI_Tick_Minigame_Cue", {}),
    "countdown2": (f"{TOYS}/Floor_Siren/Timer_UI_Tick_Minigame_Cue.Timer_UI_Tick_Minigame_Cue", {}),
    "countdown1": (f"{TOYS}/Floor_Siren/Timer_UI_Tick_Minigame_Cue.Timer_UI_Tick_Minigame_Cue", {}),
    "go": (f"{TOYS}/Floor_Siren/Timer_UI_Minigame_Go_Cue.Timer_UI_Minigame_Go_Cue", {}),
    # The skilled-interaction device's success / good chimes.
    "correct": (f"{SKILL}/SkilledInteract_Success_Cue.SkilledInteract_Success_Cue", {}),
    "correct_retry": (f"{SKILL}/SkilledInteract_Good_Cue.SkilledInteract_Good_Cue", {}),
    "wrong": (f"{CR}/Gadgets/Scoring/Scoring_Point_Subtracted_Cue.Scoring_Point_Subtracted_Cue", {}),
    "door_open": (f"{CR}/Gadgets/SlidingDoor/SlidingDoor_Open_Cue.SlidingDoor_Open_Cue", {}),
    "boost": (f"{CR}/Gadgets/SpeedBoost/Trap_Speed_Alt_Increase_Cue.Trap_Speed_Alt_Increase_Cue", {}),
    # A ladder, small to big: target hit, bullseye, power-up collect, capture, two success stingers.
    "streak2": (f"{TOYS}/ShootingTargets/Target_Impact_Success_2D_Cue.Target_Impact_Success_2D_Cue", {}),
    "streak3": (f"{TOYS}/ShootingTargets/Target_Impact_Bullseye_Cue.Target_Impact_Bullseye_Cue", {}),
    "streak4": (f"{TOYS}/PowerUp/Creative_PowerUp_Collect_Cue.Creative_PowerUp_Collect_Cue", {}),
    "streak5": (f"{TOYS}/CaptureDevice/CaptureDevice_Capture_Finish_Cue.CaptureDevice_Capture_Finish_Cue", {}),
    "streak6": (f"{STING}/Stinger_Success_02_Cue.Stinger_Success_02_Cue", {}),
    "streak7": (f"{STING}/Stinger_Success_03_Cue.Stinger_Success_03_Cue", {}),
    "perfect": (f"{FAN}/Music_Fantasy_Sml_Victory_Stinger_03_Cue.Music_Fantasy_Sml_Victory_Stinger_03_Cue", {}),
    "finish": (f"{CR}/Modes/Match/Match_Win_01_Cue.Match_Win_01_Cue", {}),
    "new_best": (f"{FAN}/Music_Fantasy_Sml_Victory_Stinger_01_Cue.Music_Fantasy_Sml_Victory_Stinger_01_Cue", {}),
    "new_record": (f"{FAN}/Music_Fantasy_Lrg_Victory_Stinger_02_Cue.Music_Fantasy_Lrg_Victory_Stinger_02_Cue", {}),
    "medal_gold": (f"{FAN}/Music_Fantasy_Acceptance_Stinger_03_Cue.Music_Fantasy_Acceptance_Stinger_03_Cue", {}),
    "medal_silver": (f"{CR}/Gadgets/Scoring/Scoring_Point_Added_Cue.Scoring_Point_Added_Cue", {}),
    "medal_bronze": (f"{CR}/Modes/Match/Match_Round_Change_01_Cue.Match_Round_Change_01_Cue", {}),
    # One stinger per penalty, at the moment its effect starts.
    "penalty_freeze": (f"{CR}/Gadgets/Traps/Trap_IceBlock_Placed_cue.Trap_IceBlock_Placed_Cue", {}),
    "penalty_spike": (f"{TOYS}/Generic/DestructionObject_Impact_Cue.DestructionObject_Impact_Cue", {}),
    "penalty_mud": (f"{CR}/Gadgets/ExplodingBarrel/ExplodingBarrel_Explode_Stink_Cue.ExplodingBarrel_Explode_Stink_Cue", {}),
    "penalty_dizzy": (f"{CR}/Gadgets/GhostMode/GhostMode_Enter_Cue.GhostMode_Enter_Cue", {}),
    "penalty_blackout": (f"{TOYS}/ActionTrigger/ActionTrigger_PowerOff_Cue.ActionTrigger_PowerOff_Cue", {}),
    "penalty_yeet": (f"{TOYS}/Cube/Cube_LaunchPlayer_Creative_Cue.Cube_LaunchPlayer_Creative_Cue", {}),
    "no_skip": (f"{TOYS}/ShootingTargets/Target_Error_Cue.Target_Error_Cue", {}),
    "guards_up": (f"{TOYS}/ActionTrigger/ActionTrigger_PlayerSpotted_Cue.ActionTrigger_PlayerSpotted_Cue", {}),
    "welcome": (f"{CR}/Modes/Match/Match_Start_01_Cue.Match_Start_01_Cue", {}),
    "choose": (f"{SKILL}/SkilledInteract_Open_Cue.SkilledInteract_Open_Cue", {}),
    # Save the World's music loops, calm to combat (the Creative radio library), one per tier, quieter than the cues.
    "music_t1": (f"{MX}/Music_StW_Ambient_Morning01_Cue.Music_StW_Ambient_Morning01_Cue", LOOP),
    "music_t2": (f"{MX}/Music_StW_Medium_Exploration01_Cue.Music_StW_Medium_Exploration01_Cue", LOOP),
    "music_t3": (f"{MX}/Music_StW_Low_Combat01_Cue.Music_StW_Low_Combat01_Cue", LOOP),
    "music_t4": (f"{MX}/Music_StW_High_Action01_Cue.Music_StW_High_Action01_Cue", LOOP),
    "music_t5": (f"{MX}/Music_StW_High_Combat01_Cue.Music_StW_High_Combat01_Cue", LOOP),
    # The boss arena (G6 item 3). The brief's picks (/PoppySoap announcer "Fight", /Freaky boss-elim stinger) sit outside
    # the paths island validation accepts (PoppySoap is on the refused list above), so these are Creative-library stand-ins:
    # a threat stinger as the fight starts, an exploding barrel as the "cannon" of a right pad, the Black Monday win.
    "boss_fight": (f"{STING}/Stinger_Threat_01_Cue.Stinger_Threat_01_Cue", {}),
    "boss_hit": (f"{CR}/Gadgets/ExplodingBarrel/ExplodingBarrel_Explode_01_Cue.ExplodingBarrel_Explode_01_Cue", {}),
    "boss_dead": (f"{STING}/BlackMonday/Stinger_BlackMonday_Win_01_Cue.Stinger_BlackMonday_Win_01_Cue", {}),
}

READ_BACK = list(BASE) + ["audio"]


def label(cue):
    return "FNM_Cue_" + "".join(part.capitalize() for part in cue.split("_"))


def props_set(actor, values):
    """One property per set_properties call (a combined write can silently keep the old value)."""
    for key, value in values.items():
        try:
            u.call(OBJ, "set_properties", {"instance": ref(actor), "values": json.dumps({key: value})})
        except RuntimeError as e:
            print(f"  could not set {key}: {e}")


def props_get(actor, keys):
    r = u.call(OBJ, "get_properties", {"instance": ref(actor), "properties": keys})
    return json.loads(r["returnValue"])


def found(tag):
    r = u.call(SCENE, "find_actors", {"tag": tag, "collision_channels": []})
    actors = r if isinstance(r, list) else r.get("returnValue", [])
    return [a["actorPath"] if isinstance(a, dict) else a for a in actors]


def clear():
    actors = found(TAG)
    for a in actors:
        u.call(SCENE, "remove_from_scene", {"actor": ref(a)})
    return len(actors)


def duration(asset):
    try:
        return props_get(asset, ["duration"]).get("duration")
    except RuntimeError:
        return None


def check(actor, want):
    """Read back every option set; returns the mismatches."""
    got = props_get(actor, READ_BACK)
    bad = []
    for key, value in want.items():
        have = got.get(key)
        if key == "audio":
            have = (have or {}).get("refPath")
        if isinstance(value, float) or isinstance(have, float):
            ok = have is not None and abs(float(have) - float(value)) < 1e-4
        else:
            ok = have == value
        if not ok:
            bad.append(f"{key}: want {value!r} have {have!r}")
    return got, bad


def build():
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    project = next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).strip("/")
    print("removed", clear(), "old audio players")
    wired = [(cue, asset, opts) for cue, (asset, opts) in CUES.items() if asset]
    problems = 0
    for n, (cue, asset, opts) in enumerate(wired):
        r = u.call(DEV, "PlaceDevice", {"assetPath": ref(PLAYER), "transform": xform(PARK[0] + PITCH * n, PARK[1], PARK[2])})
        actor = r["returnValue"]["refPath"]
        u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
        u.call(ACTOR, "set_label", {"actor": ref(actor), "label": label(cue)})
        # Tag first: adding the tag component rebuilds a device's instanced sub-objects (uefn-mcp skill).
        verse_tags(actor, project, [f"fnm_cue_{cue}"])
        want = {**BASE, **opts, "audio": asset}
        props_set(actor, {k: (ref(v) if k == "audio" else v) for k, v in want.items()})
        _, bad = check(actor, want)
        problems += len(bad)
        print(f"{label(cue):24} {asset.rsplit('/', 1)[-1].split('.')[0]:44} {'OK' if not bad else 'MISMATCH ' + '; '.join(bad)}")
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    missing = [cue for cue, (asset, _) in CUES.items() if not asset]
    print(f"{len(wired)} of {len(CUES)} cues wired, {problems} read-back mismatches; no library sound: {', '.join(missing) or 'none'}")
    return problems


def cached(actor):
    """The device's saved options (toyOptionsComponent.playerOptionData.propertyOverrides): what the Creative options
    panel shows and what a save writes. name (lower case) -> string."""
    comp = props_get(actor, ["toyOptionsComponent"])["toyOptionsComponent"]["refPath"]
    data = props_get(comp, ["playerOptionData"])["playerOptionData"]["propertyOverrides"]
    return {o["propertyName"].lower(): o["propertyData"] for o in data}


def same(value, text):
    if isinstance(value, bool):
        return text == str(value)
    if isinstance(value, (int, float)):
        try:
            return abs(float(text) - value) < 1e-4
        except ValueError:
            return False
    return text == value


def list_placed():
    """Every placed player: its sound, duration, the read-back options, and two checks against CUES: the live
    properties (props) and the saved options cache (cache)."""
    actors = found(TAG)
    by_label = {label(cue): (cue, asset, opts) for cue, (asset, opts) in CUES.items() if asset}
    rows, problems = [], 0
    for a in actors:
        name = u.call(ACTOR, "get_label", {"actor": ref(a)})
        rows.append((name.get("returnValue", name) if isinstance(name, dict) else name, a))
    for name, a in sorted(rows, key=lambda r: str(r[0])):
        cue, asset, opts = by_label.get(name, (None, None, {}))
        want = {**BASE, **opts, "audio": asset}
        got, bad = check(a, want) if cue else (props_get(a, READ_BACK), ["not in CUES"])
        cache = cached(a)
        cache_bad = [k for k, v in want.items() if not same(v, cache.get(k.lower(), "<missing>"))]
        problems += len(bad) + len(cache_bad)
        have = got_audio(got)
        dur = duration(have) if have else None
        opts_text = ", ".join(f"{k}={got.get(k)!r}" for k in BASE)
        verdict = "props OK" if not bad else "props MISMATCH " + "; ".join(bad)
        verdict += ", cache OK" if not cache_bad else ", cache MISMATCH " + ", ".join(cache_bad)
        print(f"{name:24} {have.rsplit('/', 1)[-1].split('.')[0] if have else '-':42} {dur if dur is None else round(dur, 2):>7} s"
              f" | {verdict} | {opts_text}")
    print(f"{len(actors)} audio players tagged {TAG}, {problems} mismatches")
    return problems


def got_audio(got):
    return ((got or {}).get("audio") or {}).get("refPath") or ""


def probe(names):
    for name in names:
        for cls in ("/Script/Engine.SoundCue", "/Script/Engine.SoundWave", "/Script/MetasoundEngine.MetaSoundSource"):
            r = u.call(ASSETS, "find_assets", {"folder_path": "", "name": name, "asset_type": ref(cls), "recursive": True})
            for path in r.get("returnValue", [])[:12]:
                d = duration(path)
                print(f"{name:28} {cls.rsplit('.', 1)[-1]:16} {d if d is None else round(d, 2):>7}  {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--probe", help="comma-separated asset name substrings")
    a = ap.parse_args()
    if a.probe:
        probe([n for n in a.probe.split(",") if n])
    elif a.list:
        list_placed()
    else:
        sys.exit(1 if build() else 0)
