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
    python tools/build_audio.py --announcer am_michael
                                               # the same, but ANNOUNCER_CUES carry that voice's imported SoundWave
    python tools/build_audio.py --announcer am_michael --boss-voice am_onyx
                                               # ... and BOSS_CUES (the boss's own lines) carry am_onyx's imported waves
    python tools/build_audio.py --announcer am_michael --boss-voice am_onyx --mint
                                               # ... and MINT_CUES (music beds, finish fanfare, door whoosh, Volt, titan,
                                               # crowd) carry the project's imported Mint waves (FNM_Audio/mint/<cue>)
    python tools/build_audio.py --list         # placed devices with their sound, its source (stock / announcer / boss /
                                               # mint) and the read-back options
    python tools/build_audio.py --probe Mud,Countdown_Go
                                               # find_assets matches per name (SoundCue + SoundWave), class, duration
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402
from build_course import ACTOR, DEV, OBJ, SCENE, ref, verse_tags, xform  # noqa: E402

TAG = "fnm_audio"
# Cues the announcer voice pack replaces with --announcer <voice> (console/AUDIO.md "Announcer"). The countdown ticks,
# correct / retry chimes, wrong buzzer, door, boost, finish, music beds and the boss cues stay stock.
ANNOUNCER_CUES = [
    "go", "streak2", "streak3", "streak4", "streak5", "streak6", "streak7", "perfect", "new_best", "new_record",
    "medal_gold", "medal_silver", "medal_bronze", "penalty_freeze", "penalty_spike", "penalty_mud", "penalty_dizzy",
    "penalty_blackout", "penalty_yeet", "no_skip", "guards_up", "welcome", "choose",
    "direct_hit", "hits_left4", "hits_left3", "hits_left2", "hits_left1", "boss_down",
    # Boss battle mode (BOSS_MODE.md section 10): the announcer lines (am_michael style).
    "bm_start", "bm_level2", "bm_level3", "bm_level4", "bm_level5", "bm_mega_nuke", "bm_level_clear", "bm_victory",
]
# The boss's own lines (the deep "boss" mastering profile), put on their devices with --boss-voice <voice>; the
# recommended voice is am_onyx. A separate list because it is a separate voice, wired separately.
BOSS_CUES = [
    "bm_boss_l1", "bm_boss_l2", "bm_boss_l3", "bm_boss_l4", "bm_boss_l5", "bm_boss_wrong", "bm_boss_hit", "bm_boss_dead",
]
# Mint music and sound effects (console/AUDIO.md "Mint music and SFX"): waves made by tools/make_mint_audio.py
# (tools/audio/mint/<cue>.wav), imported into /<mount>/FNM_Audio/mint/<cue>.<cue> and put on their devices with --mint.
# The first seven have a stock sound that stays until the wave is imported; the rest have none (placed only once their
# wave is imported, else a logged "(not wired)" in play). The folder name "mint" is reserved: it is not a voice.
MINT_FOLDER = "mint"
MINT_CUES = [
    "music_t1", "music_t2", "music_t3", "music_t4", "music_t5", "finish", "door_open",
    "volt_yay", "volt_hmm", "music_boss", "music_menu", "titan_roar", "volt_oops", "crowd_cheer", "crowd_aww",
]
# The voice pack's SoundWaves, imported through the UEFN GUI (tools/audio/announcer/<voice>/<cue>.wav).
VO_FOLDER = "FNM_Audio"
# Device volume for a voice line (the property takes values past 1; 2.5 is about +8 dB). 2026-10-07: at volume 1 the
# penalty lines were buried under the wrong buzzer and the effect sounds (matched filter 0.2-0.3 vs 0.88 for a clear GO).
VO_VOLUME = 2.5
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
    # Short (0.77 s): the penalty voice line follows it PenaltyVoiceDelaySeconds later and must not sit under a long buzzer
    # (the 2.28 s Scoring_Point_Subtracted it was until 2026-10-07).
    "wrong": (f"{TOYS}/ShootingTargets/Target_Error_Cue.Target_Error_Cue", {}),
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
    # Announcer-only (Aaron 2026-10-08: "make the hit more clear verbally ... 'direct hit!' and how many hits remaining"):
    # no stock stand-in, so each plays only once its voice line is imported (--announcer), else it is a logged no-op.
    "direct_hit": (None, {}),
    "hits_left4": (None, {}),
    "hits_left3": (None, {}),
    "hits_left2": (None, {}),
    "hits_left1": (None, {}),
    "boss_down": (None, {}),
    # Boss battle mode (BOSS_MODE.md section 10, same order as the fnm_cue enum). A voice-only cue (None) plays only once
    # its wave is imported and wired (--announcer for the announcer lines, --boss-voice for bm_boss_*), else a logged no-op.
    "bm_start": (f"{STING}/Stinger_Threat_01_Cue.Stinger_Threat_01_Cue", {}),        # as boss_fight
    "bm_level2": (f"{CR}/Modes/Match/Match_Round_Change_01_Cue.Match_Round_Change_01_Cue", {}),
    "bm_level3": (f"{CR}/Modes/Match/Match_Round_Change_01_Cue.Match_Round_Change_01_Cue", {}),
    "bm_level4": (f"{CR}/Modes/Match/Match_Round_Change_01_Cue.Match_Round_Change_01_Cue", {}),
    "bm_level5": (f"{CR}/Modes/Match/Match_Round_Change_01_Cue.Match_Round_Change_01_Cue", {}),
    "bm_boss_l1": (None, {}),
    "bm_boss_l2": (None, {}),
    "bm_boss_l3": (None, {}),
    "bm_boss_l4": (None, {}),
    "bm_boss_l5": (None, {}),
    "bm_boss_wrong": (None, {}),
    "bm_boss_hit": (None, {}),
    "bm_boss_dead": (None, {}),
    "bm_nuke": (f"{CR}/Gadgets/ExplodingBarrel/ExplodingBarrel_Explode_01_Cue.ExplodingBarrel_Explode_01_Cue", {}),
    "bm_mega_nuke": (None, {}),
    "bm_level_clear": (f"{STING}/Stinger_Success_03_Cue.Stinger_Success_03_Cue", {}),
    "bm_victory": (f"{CR}/Modes/Match/Match_Win_01_Cue.Match_Win_01_Cue", {}),
    "bm_gates": (f"{CR}/Gadgets/SlidingDoor/SlidingDoor_Open_Cue.SlidingDoor_Open_Cue", {}),
    "bm_weapon": (f"{TOYS}/PowerUp/Creative_PowerUp_Collect_Cue.Creative_PowerUp_Collect_Cue", {}),
    # Mint-only cues (G9, MINT_CUES): no library stand-in, so each plays only once its wave is imported and wired (--mint),
    # else it is a logged no-op. Same order as the fnm_cue enum (fnm_audio.verse).
    "volt_yay": (None, {}),
    "volt_hmm": (None, {}),
}
# Mint-only cues whose Verse side (enum id in fnm_audio.verse, tag class in fnm_tags.verse, the director call) is a later
# round. They live apart from CUES because tests/test_audio_cues.py asserts list(CUES) == the enum. When a cue's Verse
# side lands, move its row into CUES, in enum order, and add the member to that test's MEMBERS. Until then build() skips
# it with a message, so importing its wave early is harmless.
PENDING_CUES = {
    "music_boss": (None, LOOP),       # race arena + Boss Battle mode
    "music_menu": (None, LOOP),       # the grade picker
    "titan_roar": (None, {}),         # the titan appears
    "volt_oops": (None, {}),          # Volt's wag card
    "crowd_cheer": (None, {}),        # the titan dies, the podium
    "crowd_aww": (None, {}),          # a wrong pad
}
ALL_CUES = {**CUES, **PENDING_CUES}

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


def project_id():
    root = u.call("ValkyrieToolset.VerseToolset", "ListFiles", {"path": "", "bRecursive": False})
    return next(e["name"] for e in root["returnValue"] if e["type"] == "Directory" and "(" not in e["name"]).strip("/")


def vo_path(project, voice, cue):
    """The imported announcer SoundWave for a cue: /<mount>/FNM_Audio/<voice>/<cue>.<cue>."""
    return f"/{project}/{VO_FOLDER}/{voice}/{cue}.{cue}"


def is_vo(path, cue=None):
    """True when an audio path is an imported announcer wave (for that cue, when given)."""
    parts = (path or "").split("/")
    if len(parts) != 5 or parts[2] != VO_FOLDER or parts[3] == MINT_FOLDER:
        return False
    return cue is None or parts[4] == f"{cue}.{cue}"


def mint_path(project, cue):
    """The imported Mint SoundWave for a cue: /<mount>/FNM_Audio/mint/<cue>.<cue>."""
    return f"/{project}/{VO_FOLDER}/{MINT_FOLDER}/{cue}.{cue}"


def is_mint(path, cue=None):
    """True when an audio path is an imported Mint wave (for that cue, when given)."""
    parts = (path or "").split("/")
    if len(parts) != 5 or parts[2] != VO_FOLDER or parts[3] != MINT_FOLDER:
        return False
    return cue is None or parts[4] == f"{cue}.{cue}"


def asset_exists(path):
    return u.call(ASSETS, "exists", {"path": path.split(".")[0]})["returnValue"]


def repo_cue_tags():
    """The cue ids whose tag class the repo's console/verse/fnm_tags.verse declares (what the next sync + BuildAll compiles)."""
    text = (Path(__file__).resolve().parents[1] / "console" / "verse" / "fnm_tags.verse").read_text(encoding="utf-8")
    return set(re.findall(r"^fnm_cue_(\w+) := class\(tag\)", text, re.M))


def verse_cue_tags():
    """The cue ids whose Verse tag class (fnm_cue_<id> := class(tag) in fnm_tags.verse) is in the project's Verse root, or
    None when the project cannot be searched. build() places only these: a device cannot be tagged with a class the project
    has not compiled (2026-10-13: set_properties answers "_Verse.fnm_cue_volt_yay is not valid Class for property
    'InternalTag'", and the half-built device is left behind)."""
    try:
        r = u.call("ValkyrieToolset.VerseToolset", "Grep", {"pattern": "/^fnm_cue_\\w+ := class\\(tag\\)/", "pathGlob": "**/fnm_tags.verse"})
    except RuntimeError:
        return None
    hits = r.get("returnValue", []) if isinstance(r, dict) else r
    ids = {m.group(1) for h in hits for m in [re.match(r"fnm_cue_(\w+) := class", h.get("lineText", ""))] if m}
    return ids or None


def sources(project, voice, boss_voice=None, mint=False, exists=None):
    """cue -> asset path to place: the stock CUES path, or for ANNOUNCER_CUES the voice's imported SoundWave (and for
    BOSS_CUES the boss voice's, for MINT_CUES the Mint wave) when it exists. A missing wave keeps the stock sound (or,
    with none, leaves the cue unwired) and is reported. exists(path) -> bool is the asset check (tests pass a fake)."""
    exists = exists or asset_exists
    out = {cue: asset for cue, (asset, _) in ALL_CUES.items() if asset}
    for who, cues, name in ((voice, ANNOUNCER_CUES, "announcer"), (boss_voice, BOSS_CUES, "boss voice")):
        if not who:
            continue
        missing = []
        for cue in cues:
            path = vo_path(project, who, cue)
            if exists(path):
                out[cue] = path
            else:
                missing.append(cue)
        print(f"{name} {who}: {len(cues) - len(missing)} of {len(cues)} lines found under "
              f"/{project}/{VO_FOLDER}/{who}"
              + (f"; NOT IMPORTED, {'stock kept' if name == 'announcer' else 'not wired'}: {', '.join(missing)}"
                 if missing else ""))
    if mint:
        stock, bare, found = [], [], 0
        for cue in MINT_CUES:
            path = mint_path(project, cue)
            if exists(path):
                out[cue] = path
                found += 1
            elif ALL_CUES[cue][0]:
                stock.append(cue)
            else:
                bare.append(cue)
        print(f"mint: {found} of {len(MINT_CUES)} waves found under /{project}/{VO_FOLDER}/{MINT_FOLDER}"
              + (f"; NOT IMPORTED, stock kept: {', '.join(stock)}" if stock else "")
              + (f"; NOT IMPORTED, not wired: {', '.join(bare)}" if bare else ""))
    return out


def build(voice=None, boss_voice=None, mint=False):
    project = project_id()
    chosen = sources(project, voice, boss_voice, mint)
    print("removed", clear(), "old audio players")
    # A cue is placed when it has a sound to carry (its stock asset, or an imported wave on a cue with none) and its
    # Verse tag class is compiled: the director finds a device by that tag, and a dead tag reference is not worth placing.
    declared = repo_cue_tags()
    compiled = verse_cue_tags()
    if compiled is None:             # the project cannot be searched: trust the repo's file
        compiled = declared
    skipped = [cue for cue in chosen if cue not in compiled]
    waiting = [cue for cue in skipped if cue in declared]
    if waiting:
        print(f"SKIPPED, tag class declared in the repo's fnm_tags.verse but not in the project yet (rerun after the next sync + BuildAll): {', '.join(waiting)}")
    if [cue for cue in skipped if cue not in declared]:
        print(f"SKIPPED, no fnm_cue_<id> tag class in any fnm_tags.verse (the cue's Verse side is not built): {', '.join(cue for cue in skipped if cue not in declared)}")
    wired = [(cue, chosen[cue], opts) for cue, (asset, opts) in ALL_CUES.items() if cue in chosen and cue not in skipped]
    problems = 0
    for n, (cue, asset, opts) in enumerate(wired):
        r = u.call(DEV, "PlaceDevice", {"assetPath": ref(PLAYER), "transform": xform(PARK[0] + PITCH * n, PARK[1], PARK[2])})
        actor = r["returnValue"]["refPath"]
        u.call(ACTOR, "add_tag", {"actor": ref(actor), "tag": TAG})
        u.call(ACTOR, "set_label", {"actor": ref(actor), "label": label(cue)})
        # Tag first: adding the tag component rebuilds a device's instanced sub-objects (uefn-mcp skill).
        try:
            verse_tags(actor, project, [f"fnm_cue_{cue}"])
        except RuntimeError as e:    # the class is not compiled after all: do not leave a half-built device behind
            u.call(SCENE, "remove_from_scene", {"actor": ref(actor)})
            print(f"{label(cue):24} SKIPPED, the tag does not resolve ({str(e).splitlines()[0][:90]}); device removed")
            problems += 1
            continue
        want = {**BASE, **opts, **({"volume": VO_VOLUME} if is_vo(asset) else {}), "audio": asset}
        props_set(actor, {k: (ref(v) if k == "audio" else v) for k, v in want.items()})
        _, bad = check(actor, want)
        problems += len(bad)
        source = ("boss" if cue in BOSS_CUES else "announcer") if is_vo(asset) else "mint" if is_mint(asset) else "stock"
        print(f"{label(cue):24} {source:9} {asset.rsplit('/', 1)[-1].split('.')[0]:44} {'OK' if not bad else 'MISMATCH ' + '; '.join(bad)}")
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    missing = [cue for cue in ALL_CUES if cue not in chosen]
    voiced = sum(1 for _, asset, _ in wired if is_vo(asset))
    minted = sum(1 for _, asset, _ in wired if is_mint(asset))
    print(f"{len(wired)} of {len(ALL_CUES)} cues wired ({voiced} announcer, {minted} mint, {len(wired) - voiced - minted} stock), "
          f"{problems} read-back mismatches; no sound: {', '.join(missing) or 'none'}")
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
    """Every placed player: its sound, the sound's source (stock = the CUES path, announcer = an imported voice wave,
    accepted only on ANNOUNCER_CUES), duration, the read-back options, and two checks against CUES: the live
    properties (props) and the saved options cache (cache)."""
    actors = found(TAG)
    by_label = {label(cue): (cue, asset, opts) for cue, (asset, opts) in ALL_CUES.items()}
    rows, problems, voiced, minted = [], 0, [], []
    for a in actors:
        name = u.call(ACTOR, "get_label", {"actor": ref(a)})
        rows.append((name.get("returnValue", name) if isinstance(name, dict) else name, a))
    for name, a in sorted(rows, key=lambda r: str(r[0])):
        cue, asset, opts = by_label.get(name, (None, None, {}))
        live = got_audio(props_get(a, ["audio"])) if cue else ""
        source = "stock"
        if cue in ANNOUNCER_CUES + BOSS_CUES and is_vo(live, cue):
            asset, source = live, "boss" if cue in BOSS_CUES else "announcer"
            voiced.append(cue)
        elif cue in MINT_CUES and is_mint(live, cue):
            asset, source = live, "mint"
            minted.append(cue)
        elif is_vo(live):
            source = "announcer?"   # a voice wave on a cue that should stay stock: check() flags it
        elif is_mint(live):
            source = "mint?"        # a Mint wave on a cue that is not a MINT_CUE, or on the wrong cue
        want = {**BASE, **opts, **({"volume": VO_VOLUME} if is_vo(asset) else {}), "audio": asset}
        got, bad = check(a, want) if cue else (props_get(a, READ_BACK), ["not in CUES"])
        cache = cached(a)
        cache_bad = [k for k, v in want.items() if not same(v, cache.get(k.lower(), "<missing>"))]
        problems += len(bad) + len(cache_bad)
        have = got_audio(got)
        dur = duration(have) if have else None
        opts_text = ", ".join(f"{k}={got.get(k)!r}" for k in BASE)
        verdict = "props OK" if not bad else "props MISMATCH " + "; ".join(bad)
        verdict += ", cache OK" if not cache_bad else ", cache MISMATCH " + ", ".join(cache_bad)
        print(f"{name:24} {source:10} {have.rsplit('/', 1)[-1].split('.')[0] if have else '-':42} "
              f"{dur if dur is None else round(dur, 2):>7} s | {verdict} | {opts_text}")
    print(f"{len(actors)} audio players tagged {TAG}, {problems} mismatches; announcer/boss on {len(voiced)} "
          f"({', '.join(voiced) or 'none'}), mint on {len(minted)} ({', '.join(minted) or 'none'}), "
          f"stock on {len(actors) - len(voiced) - len(minted)}")
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
    ap.add_argument("--announcer", metavar="VOICE", help="put that voice's imported lines on ANNOUNCER_CUES (e.g. am_michael)")
    ap.add_argument("--boss-voice", metavar="VOICE", help="put that voice's imported lines on BOSS_CUES, the boss's own "
                    "lines (e.g. am_onyx)")
    ap.add_argument("--mint", action="store_true", help="put the project's imported Mint waves (FNM_Audio/mint/<cue>) on "
                    "MINT_CUES: the music beds, the finish fanfare, the door whoosh, Volt, the titan and the crowd")
    a = ap.parse_args()
    if a.probe:
        probe([n for n in a.probe.split(",") if n])
    elif a.list:
        list_placed()
    else:
        sys.exit(1 if build(a.announcer, a.boss_voice, a.mint) else 0)
