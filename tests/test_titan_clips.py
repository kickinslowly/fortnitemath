"""The titan's clips (G9 D2): tools/import_boss.py never deletes what the level uses and brings the new clips in as
animations on idle's skeleton; the builders put each clip on the right mesh; fnm_titan.verse plays the one-shots from their
first frame and the director / boss mode call them where AUDIO.md says."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_bossmode as bm  # noqa: E402
import build_race_boss as rb  # noqa: E402
import import_boss as ib  # noqa: E402

PROJECT = "proj"
FOLDER = f"/{PROJECT}/FNM_BossArt"


class FakeEditor:
    def __init__(self, existing):
        self.calls, self.existing = [], set(existing)

    def __call__(self, toolset, tool, args=None, **_):
        args = args or {}
        self.calls.append((tool, args))
        if tool == "exists":
            return {"returnValue": args["path"] in self.existing}
        if tool == "find_assets":
            if args.get("name") == "M_fnm_wall_bm_marble":
                return {"returnValue": [f"/{PROJECT}/FNM_Art/M_fnm_wall_bm_marble.M_fnm_wall_bm_marble"]}
            if args.get("name", "").endswith("_Anim"):
                n = args["name"]
                return {"returnValue": [f"{args['folder_path']}/{n}.{n}"]}
            return {"returnValue": []}
        return {"returnValue": True}

    def tools(self, name):
        return [a for t, a in self.calls if t == name]


def old_clips():
    return {ib.anim_path(FOLDER, s.split("_")[0]) for s in ib.ANIMS}


def run(fake, monkeypatch, own=frozenset()):
    monkeypatch.setattr(ib.u, "call", fake)
    ib.main(own)


def test_a_project_with_every_clip_is_left_alone(monkeypatch):
    every = old_clips() | {ib.anim_path(FOLDER, c) for c in ib.SHARED}
    fake = FakeEditor(every)
    run(fake, monkeypatch)
    assert not fake.tools("delete") and not fake.tools("import_file") and not fake.tools("move")


def test_new_clips_come_in_on_idles_skeleton_and_nothing_in_use_is_deleted(monkeypatch):
    base = f"{FOLDER}/Clip_idle/SK_fnm_titan_idle_Skeleton"
    fake = FakeEditor(old_clips() | {base})
    run(fake, monkeypatch)
    imports = fake.tools("import_file")
    assert [Path(a["source_file"]).name for a in imports] == [f"{s}.fbx" for s in ib.SHARED.values()]
    for a in imports:
        assert a["skeleton"] == {"refPath": f"{base}.SK_fnm_titan_idle_Skeleton"}
        assert a["import_materials"] is False and a["import_textures"] is False
        assert a["folder_path"].startswith(f"{FOLDER}/Tmp_")
    # only the throwaway temp folders are deleted, never FNM_BossArt or a Clip_ folder the devices point into
    assert [a["path"] for a in fake.tools("delete")] == [f"{FOLDER}/Tmp_{c}" for c in ib.SHARED]
    assert [a["new_path"] for a in fake.tools("move")] == [ib.anim_path(FOLDER, c) for c in ib.SHARED]


def test_own_imports_a_shared_clip_with_its_own_mesh(monkeypatch):
    fake = FakeEditor(old_clips() | {f"{FOLDER}/Clip_idle/SK_fnm_titan_idle_Skeleton"} |
                      {ib.anim_path(FOLDER, c) for c in ("scream", "shout")})
    run(fake, monkeypatch, own=frozenset({"jumpslam"}))
    (a,) = fake.tools("import_file")
    assert "skeleton" not in a and a["import_materials"] is True and a["folder_path"] == f"{FOLDER}/Clip_jumpslam"
    assert not fake.tools("delete")


def test_clip_tables_agree():
    assert bm.TITAN_CLIPS == ["idle", "flail", "stomp", "dead", "jumpslam", "scream"]
    assert rb.RACE_TITAN_CLIPS == ["idle", "flail", "stomp", "dead", "jumpslam"]
    assert bm.TITAN_ONCE == {"dead", "jumpslam", "scream"}
    assert set(bm.TITAN_SHARED) == set(ib.SHARED) and set(bm.TITAN_SHARED.values()) == {ib.BASE}
    assert {s.split("_")[0] for s in ib.ANIMS} | set(ib.SHARED) >= set(bm.TITAN_CLIPS)
    p = bm.titan_clip_props(PROJECT, "jumpslam")
    assert p["skeletalMesh"]["refPath"] == f"{FOLDER}/Clip_idle/SK_fnm_titan_idle.SK_fnm_titan_idle"
    assert p["animation"]["refPath"] == f"{FOLDER}/Clip_jumpslam/A_fnm_titan_jumpslam.A_fnm_titan_jumpslam"
    assert p["loop"] is False and p["initialState"] == "Playing"
    flail = bm.titan_clip_props(PROJECT, "flail")
    assert flail["skeletalMesh"]["refPath"].endswith("Clip_flail/SK_fnm_titan_flail.SK_fnm_titan_flail") and flail["loop"] is True


def test_the_verse_titan_matches_the_clip_order():
    titan = (ROOT / "console" / "verse" / "fnm_titan.verse").read_text(encoding="utf-8")
    slots = {name: int(v) for name, v in re.findall(r"^    (Idle|Flail|Stomp|Dead|JumpSlam|Scream) : int = (\d+)$", titan, re.M)}
    assert [n for n, _ in sorted(slots.items(), key=lambda kv: kv[1])] == ["Idle", "Flail", "Stomp", "Dead", "JumpSlam", "Scream"]
    assert len(re.search(r"var Clips : \[\]\?animated_mesh_device = array\{([^}]*)\}", titan).group(1).split(",")) == len(bm.TITAN_CLIPS)
    # the one-shots start from their first frame: Play() then shown, run back (PlayReverse) once shrunk away
    once = titan.split("    Once(K:int, Seconds:float)<suspends>:logic =", 1)[1].split("\n\n", 1)[0]
    assert once.index("Clip.Play()") < once.index("Show(K)") < once.index("Sleep(Seconds)") < once.index("Clip.PlayReverse()")
    assert "for (K : array{Dead, JumpSlam, Scream}" in titan                      # Reset rewinds every one-shot
    # the imported lengths (UEFN sequenceLength 2.733 / 2.767 s, read back 2026-10-13)
    assert "JumpSlamSeconds : float = 2.73" in titan and "ScreamSeconds : float = 2.77" in titan
    d = (ROOT / "console" / "verse" / "fnm_director.verse").read_text(encoding="utf-8")
    b = (ROOT / "console" / "verse" / "fnm_bossmode.verse").read_text(encoding="utf-8")
    assert "spawn{ RaceTitan.Entrance() }" in d and "spawn{ RaceTitan.Arrive() }" in d     # walk-in slam; respawn stomp
    assert "spawn{ Arena.Titan.Entrance() }" in b and "spawn{ Arena.Titan.Yell() }" in b
    assert "Titan.Taunt()" not in b                                                       # boss mode's wrong pad screams now
