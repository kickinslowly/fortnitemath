"""Import the boss monster (Meshy rig + animations, art/boss/raw/*.fbx) into the UEFN project under FNM_BossArt: one
AnimSequence per clip (A_fnm_titan_<clip>), what build_bossmode.titan_clip_props puts on each Animated Mesh device.

    python tools/import_boss.py                 # import every clip that is missing; an existing one is KEPT
    python tools/import_boss.py --own jumpslam  # a SHARED clip that misplays on idle's skeleton: its own mesh instead

The folder is FNM_BossArt, not a Verse-style name: a content folder becomes a Verse module and `fnm_boss` collided with the
tag class (uefn-mcp skill).

Two ways a clip comes in:
- OWN (ANIMS: idle, flail, stomp, dead; 2026-10-10): the clip FBX with its own mesh and skeleton into
  FNM_BossArt/Clip_<clip> (SK_fnm_titan_<clip> + its skeleton, material, base colour texture + A_fnm_titan_<clip>). Bound
  to the skeleton of Meshy's separate rig file instead, a clip whose hips turn or tip played on the wrong axis (the
  knockdown spun standing, the chest pound tipped flat; play frames 2026-10-10), so the rig file is not used. dead_8 is the
  fall (plays once, BOSS_MODE 15b). Each is a full copy of the 40k-triangle mesh and its 2K texture.
- SHARED (G9 D2, 2026-10-13: the jump-slam, the scream, the shout): animation only, imported against idle's skeleton
  (SK_fnm_titan_idle_Skeleton) the way tools/import_mascot.py brings in Volt's clips; the throwaway mesh the FBX carries is
  deleted with its temp folder and the AnimSequence lands alone in FNM_BossArt/Clip_<clip>. Its devices play it on idle's
  mesh (build_bossmode TITAN_SHARED), so it costs no mesh or texture. All titan clips come from the one Meshy rig task
  (art/boss/meshy_tasks.json), so the bones match.

Never deletes anything that exists. Until G9 D2 every run deleted FNM_BossArt first and re-imported it, and deleting an asset
empties every reference to it (uefn-mcp skill, "Re-importing an asset nulls every reference"): the boss mode titan, the
race titan and the volcano's titan (tools/build_landmarks.py) all point into this folder. To replace a clip, delete its
Clip_<clip> folder by hand and rerun the builders that place it.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

ASSETS = "editor_toolset.toolsets.asset.AssetTools"
SKEL = "editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
RAW = Path(__file__).resolve().parent.parent / "art" / "boss" / "raw"
ART = "FNM_BossArt"
MESH = "SK_fnm_titan"
# Clips imported with their own mesh (build_bossmode TITAN_CLIPS' first four). chestpound_88 and knockdown_187 were bought too
# and sit in art/boss/unused (not committed; Meshy task ids in art/boss/meshy_tasks.json): they misplay on the device
# (BOSS_MODE 15b). dead_8 (Meshy "Dead") is the fall at a level clear.
ANIMS = ["idle_0", "flail_172", "stomp_255", "dead_8"]
# Clips imported as animation only on BASE's skeleton (clip -> Meshy FBX stem; the number is Meshy's action id). jumpslam
# (Jump and Slam Back Down 382) is the entrance, scream (Zombie Scream 386) boss mode's wrong-pad taunt; shout (Shouting
# Angrily 51, 7.2 s) is imported but placed nowhere (build_bossmode TITAN_CLIPS).
SHARED = {"jumpslam": "jumpslam_382", "scream": "scream_386", "shout": "shout_51"}
BASE = "idle"


def mount():
    r = u.call(ASSETS, "find_assets", {"folder_path": "", "name": "M_fnm_wall_bm_marble", "recursive": True})["returnValue"]
    return "/" + r[0].split("/")[1]


def anim_path(folder, clip):
    return f"{folder}/Clip_{clip}/A_fnm_titan_{clip}"


def exists(path):
    return u.call(ASSETS, "exists", {"path": path})["returnValue"]


def _find(folder, name):
    return u.call(ASSETS, "find_assets", {"folder_path": folder, "name": name, "recursive": False})["returnValue"]


def _move_anim(src_folder, mesh_name, dst):
    found = _find(src_folder, f"{mesh_name}_Anim")
    if len(found) != 1:
        sys.exit(f"expected one {mesh_name}_Anim under {src_folder}, found {found}")
    u.call(ASSETS, "move", {"path": found[0].split(".")[0], "new_path": dst})


def import_own(folder, clip, stem):
    """The clip with its own mesh, skeleton, material and texture (the 2026-10-10 way)."""
    sub = f"{folder}/Clip_{clip}"
    mesh = f"{MESH}_{clip}"
    u.call(SKEL, "import_file", {"folder_path": sub, "asset_name": mesh, "source_file": str(RAW / f"{stem}.fbx"),
                                 "import_materials": True, "import_textures": True, "import_animations": True})
    _move_anim(sub, mesh, anim_path(folder, clip))
    # Full-size textures in play: the import's LOD bias 1 drops the top mip (2048 -> 1024) on a 12 m monster.
    for t in u.call(ASSETS, "find_assets", {"folder_path": sub, "name": "baseColor", "recursive": True})["returnValue"]:
        u.call(OBJ, "set_properties", {"instance": {"refPath": t}, "values": json.dumps({"lODBias": 0})})


def import_shared(folder, clip, stem):
    """The clip's animation alone, bound to BASE's skeleton; the throwaway mesh goes with its temp folder."""
    skeleton = {"refPath": f"{folder}/Clip_{BASE}/{MESH}_{BASE}_Skeleton.{MESH}_{BASE}_Skeleton"}
    if not exists(skeleton["refPath"].split(".")[0]):
        sys.exit(f"{skeleton['refPath']} is missing: the base clip {BASE} must be imported first")
    tmp = f"{folder}/Tmp_{clip}"
    name = f"{MESH}_tmp_{clip}"
    u.call(SKEL, "import_file", {"folder_path": tmp, "asset_name": name, "source_file": str(RAW / f"{stem}.fbx"),
                                 "skeleton": skeleton, "import_materials": False, "import_textures": False,
                                 "import_animations": True})
    _move_anim(tmp, name, anim_path(folder, clip))
    u.call(ASSETS, "delete", {"path": tmp})


def main(own=frozenset()):
    folder = f"{mount()}/{ART}"
    done = []
    for stem in ANIMS:
        clip = stem.split("_")[0]
        if exists(anim_path(folder, clip)):
            print(f"  kept {clip} (own mesh)")
            continue
        import_own(folder, clip, stem)
        done.append(clip)
    for clip, stem in SHARED.items():
        if exists(anim_path(folder, clip)):
            print(f"  kept {clip}")
            continue
        if not (RAW / f"{stem}.fbx").is_file():
            print(f"  skipped {clip}: {stem}.fbx not in art/boss/raw")
            continue
        (import_own if clip in own else import_shared)(folder, clip, stem)
        done.append(clip + (" (own mesh)" if clip in own else " (on idle's skeleton)"))
    u.call(ASSETS, "save_assets", {"asset_paths": []})
    print("imported:", ", ".join(done) or "nothing (every clip was there)")
    for a in u.call(ASSETS, "find_assets", {"folder_path": folder, "name": "", "recursive": True})["returnValue"]:
        print(" ", a)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--own", default="", help="comma list of SHARED clips to import with their own mesh instead")
    args = ap.parse_args()
    chosen = frozenset(x for x in args.own.split(",") if x)
    bad = chosen - set(SHARED)
    if bad:
        sys.exit(f"--own takes SHARED clips only ({sorted(SHARED)}), not {sorted(bad)}")
    main(chosen)
