"""The sound layer's cue ids agree everywhere they are spelled: the fnm_cue enum (console/verse/fnm_audio.verse), its
snake ids (FnmCueIds), the Verse tag classes and FnmCueTags (fnm_tags.verse), and tools/build_audio.py CUES. Every wired
sound sits where island validation accepts it."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSE = ROOT / "console" / "verse"
sys.path.insert(0, str(ROOT / "tools"))

# Fixed by the G6 brief: other builders and the announcer pack use these ids.
MEMBERS = ("Countdown3 Countdown2 Countdown1 Go Correct CorrectRetry Wrong DoorOpen Boost Streak2 Streak3 Streak4 "
           "Streak5 Streak6 Streak7 Perfect Finish NewBest NewRecord MedalGold MedalSilver MedalBronze PenaltyFreeze "
           "PenaltySpike PenaltyMud PenaltyDizzy PenaltyBlackout PenaltyYeet NoSkip GuardsUp Welcome Choose MusicT1 "
           "MusicT2 MusicT3 MusicT4 MusicT5 BossFight BossHit BossDead DirectHit HitsLeft4 HitsLeft3 HitsLeft2 "
           "HitsLeft1 BossDown").split()


def snake(member):
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", member).lower()


def audio_src():
    return (VERSE / "fnm_audio.verse").read_text(encoding="utf-8")


def test_enum_members_exact():
    src = audio_src()
    body = src.split("fnm_cue := enum:\n", 1)[1].split("\n\n", 1)[0]
    members = [line.strip() for line in body.splitlines() if line.strip() and not line.strip().startswith("#")]
    assert members == MEMBERS


def test_snake_ids_follow_enum():
    ids = re.findall(r'"([a-z0-9_]+)"', re.search(r"FnmCueIds\(\)<transacts>:\[\]string = array\{(.*)\}", audio_src()).group(1))
    assert ids == [snake(m) for m in MEMBERS]
    assert ids[:6] == ["countdown3", "countdown2", "countdown1", "go", "correct", "correct_retry"]
    assert "penalty_freeze" in ids and "music_t1" in ids
    cues = re.findall(r"fnm_cue\.(\w+)", re.search(r"FnmCues\(\)<transacts>:\[\]fnm_cue = array\{(.*)\}", audio_src()).group(1))
    assert cues == MEMBERS


def test_tags_declared_in_enum_order():
    tags = (VERSE / "fnm_tags.verse").read_text(encoding="utf-8")
    ids = [snake(m) for m in MEMBERS]
    for i in ids:
        assert f"fnm_cue_{i} := class(tag){{}}" in tags
    order = re.search(r"FnmCueTags\(\)<transacts>:\[\]castable_subtype\(tag\) = array\{(.*)\}", tags).group(1)
    assert [t.strip() for t in order.split(",")] == [f"fnm_cue_{i}" for i in ids]


def test_builder_table_matches_and_is_allowed():
    import build_audio
    ids = [snake(m) for m in MEMBERS]
    assert list(build_audio.CUES) == ids
    for cue, (asset, opts) in build_audio.CUES.items():
        if asset is None:
            continue
        assert asset.startswith(("/Game/Sounds/Creative/", "/CRD_SkilledInteractionDevice/")), (cue, asset)
        package, name = asset.rsplit("/", 1)[1].split(".")
        assert package.lower() == name.lower(), (cue, asset)
    for t in range(1, 6):
        assert build_audio.CUES[f"music_t{t}"][1].get("loopAudio") is True
    assert build_audio.label("correct_retry") == "FNM_Cue_CorrectRetry"
    assert build_audio.BASE["can Be Heard By"] == "Instigator Only"
