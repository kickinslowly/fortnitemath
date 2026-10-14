"""The G9 D2 cues sit where console/AUDIO.md says, and every timeline they join keeps the mix rules: no voice line on the same
instant as a stinger (0.9 s apart), at most two sounds starting in any 1 s window, nothing new stacked on a kill. The timings
are read out of the Verse (the constants and the call sites), so moving a sound in the code moves it here."""
import re
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERSE = ROOT / "console" / "verse"
GAP = 0.9            # PenaltyVoiceDelaySeconds: the measured gap a voice line needs after a stinger (AUDIO.md, 2026-10-07)


def src(name):
    return (VERSE / f"{name}.verse").read_text(encoding="utf-8")


def code(text):
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def const(name, text=None):
    text = text or "\n".join(src(n) for n in ("fnm_director", "fnm_bossmode", "fnm_titan"))
    hits = re.findall(r"^\s+" + name + r" : float = ([\d.]+)$", text, re.M)
    assert len(hits) == 1, (name, hits)
    return float(hits[0])


def body(text, head):
    return text.split(head, 1)[1].split("\n\n", 1)[0]


def check_timeline(events, same_instant_ok=()):
    """events: [(cue, seconds)]. Onsets closer than GAP fail unless the pair is listed in same_instant_ok (two non-voice
    sounds meant to start together); never more than two onsets in a 1 s window."""
    events = sorted(events, key=lambda e: e[1])
    for i, (a, ta) in enumerate(events):
        for b, tb in events[i + 1:]:
            if tb - ta < GAP - 1e-6:
                assert {a, b} in [set(p) for p in same_instant_ok] and abs(tb - ta) < 1e-6, (a, ta, b, tb)
        in_window = [e for e in events if ta - 1e-6 <= e[1] < ta + 1.0 - 1e-6]
        assert len(in_window) <= 2, in_window


def test_new_cues_are_called_where_audio_md_says():
    d, bm = code(src("fnm_director")), code(src("fnm_bossmode"))
    both = d + "\n" + bm
    # music_menu: the picker's bed, stopped at the countdown; music_boss: the race arena and boss mode
    assert "SetMusic(State.Player, FnmBedMenu)" in body(d, "    BeginPicking(State:fnm_player_state):void =")
    assert "SetMusic(State.Player, 0)" in body(d, "    Countdown(State:fnm_player_state)<suspends>:void =")
    assert "if (State.Mode = fnm_mode.Boss or AtArena(State)?) then SetMusic(State.Player, FnmBedBoss)" in body(d, "    Music(State:fnm_player_state):void =")
    assert "Director.SetMusic(State.Player, FnmBedBoss)" in body(bm, "    Start(State:fnm_player_state):void =")
    assert "Director.SetMusic(State.Player, FnmBedBoss)" in body(bm, "    Summon(L:int)<suspends>:void =")
    assert "Clamp(State.Level, 1, 5)" not in both                      # boss mode no longer plays the tier beds by level
    # titan_roar with the jump-slam: the race arena's walk-in and boss mode's summon
    arrival = body(d, "    ArenaArrival(State:fnm_player_state):void =")
    assert "spawn{ RaceTitan.Entrance() }" in arrival
    assert "spawn{ SoundLater(State.Player, fnm_cue.TitanRoar, RaceTitan.SlamLandsSeconds) }" in arrival
    assert "spawn{ Director.SoundLater(State.Player, fnm_cue.TitanRoar, RoarAt) }" in body(bm, "    Summon(L:int)<suspends>:void =")
    assert "spawn{ Arena.Titan.Entrance() }" in body(bm, "    SpawnBoss(L:int):void =")
    # crowd_cheer at the podium arrival, never at the kill; crowd_aww after a penalty's line, in an arena only
    assert "Sound(State.Player, fnm_cue.CrowdCheer)" in body(d, "    PodiumLater(State:fnm_player_state)<suspends>:void =")
    assert "CrowdCheer" not in body(d, "    BossDown():void =")
    lines = body(d, "    PenaltyLines(Player:player, Voice:fnm_cue)<suspends>:void =")
    assert "(State.Mode = fnm_mode.Boss or AtArena(State)?)" in lines and "Sound(Player, fnm_cue.CrowdAww)" in lines
    assert "BM.Taunt(State)" in lines
    assert both.count("fnm_cue.CrowdCheer") == 1 and both.count("fnm_cue.CrowdAww") == 1 and both.count("fnm_cue.TitanRoar") == 2
    # every penalty's voice line goes through PenaltyLines (six kinds), none straight through SoundLater any more
    punish = body(d, "    Punish(Player:player, Station:fnm_station, DoorIndex:int, Kind:fnm_penalty)<suspends>:void =")
    assert len(re.findall(r"spawn\{ PenaltyLines\(Player, fnm_cue\.Penalty\w+\) \}", punish)) == 6
    assert "SoundLater(Player, fnm_cue.Penalty" not in punish
    # the boss's taunt and the scream now follow the aww (no fixed 2.5 s, no stomp at the buzzer in boss mode)
    assert "TauntDelaySeconds" not in bm
    taunt = body(bm, "    Taunt(State:fnm_player_state):void =")
    assert "Director.Sound(State.Player, fnm_cue.BmBossWrong)" in taunt and "spawn{ Arena.Titan.Yell() }" in taunt
    # volt_oops and volt_yay: no free window (AUDIO.md), so nothing plays them
    assert "fnm_cue.VoltOops" not in both and "fnm_cue.VoltYay" not in both


def test_race_arena_entry():
    check_timeline([("boss_fight", 0.0), ("titan_roar", const("SlamLandsSeconds"))])


@pytest.mark.parametrize("voice_at", [0.9, 1.4])           # 1.4: the yeet's line comes after the 0.5 s pull-out
def test_wrong_pad_in_an_arena(voice_at):
    crowd = voice_at + const("CrowdAfterVoiceSeconds")
    race = [("wrong", 0.0), ("penalty_voice", voice_at), ("crowd_aww", crowd)]
    check_timeline(race)
    check_timeline(race + [("bm_boss_wrong", crowd + const("TauntAfterCrowdSeconds"))])
    assert const("PenaltyVoiceDelaySeconds") == voice_at or voice_at == 1.4


def test_race_kill_podium_and_finish_lines():
    podium, voice, gap = const("PodiumSeconds"), const("FinishVoiceSeconds"), const("FinishCueGapSeconds")
    down = const("BossDownVoiceDelaySeconds")
    t = podium + voice
    check_timeline([("boss_dead", 0.0), ("boss_down", down), ("crowd_cheer", podium), ("finish", podium),
                    ("new_record", t), ("medal", t + gap), ("perfect", t + 2 * gap)],
                   same_instant_ok=[("crowd_cheer", "finish")])
    d = code(src("fnm_director"))
    assert "FinishRun(State, PodiumSeconds)" in body(d, "    BossDown():void =")
    sounds = body(d, "    FinishSounds(State:fnm_player_state, Delay:float, NewBest:logic, Record:logic, Medal:string, Perfect:logic)<suspends>:void =")
    assert sounds.index("Sound(Player, fnm_cue.Finish)") < sounds.index("Sleep(FinishVoiceSeconds)") < sounds.index("fnm_cue.NewRecord")


def test_boss_mode_summon():
    """Level line at 0, the jump at 0.3 x Scale, the roar with the slam, the boss's line RoarToLineSeconds later, the gates
    0.9 x Scale after it (Scale 1, no fall to wait out)."""
    summon = code(src("fnm_bossmode")).split("    Summon(L:int)<suspends>:void =", 1)[1].split("\n\n", 1)[0]
    sleeps = re.findall(r"Sleep\(([^)]*)\)", summon)
    assert sleeps[:3] == ["0.3 * Scale", "RoarAt + RoarToLineSeconds", "0.9 * Scale"], sleeps
    assert "RoarAt := Arena.Titan.ReadyIn() + Arena.Titan.SlamLandsSeconds" in summon
    roar = 0.3 + const("SlamLandsSeconds")
    line = roar + const("RoarToLineSeconds")
    check_timeline([("bm_level", 0.0), ("titan_roar", roar), ("bm_boss_line", line), ("bm_gates", line + 0.9)])


def wav_body_end(path, within_db=3.0, frame=0.25):
    """End (s) of the last frame whose RMS is within `within_db` of the loudest frame."""
    np = pytest.importorskip("numpy")
    with wave.open(str(path)) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64).reshape(-1, ch).mean(1) / 32768
    hop = int(sr * frame)
    db = [20 * np.log10(np.sqrt(np.mean(a[i:i + hop] ** 2)) + 1e-12) for i in range(0, len(a), hop)]
    top = max(db)
    return (max(i for i, v in enumerate(db) if v >= top - within_db) + 1) * frame


def test_finish_lines_wait_for_the_fanfare_body():
    """FinishVoiceSeconds against the Mint fanfare itself (git-ignored wav, rebuilt by tools/make_mint_audio.py): the first
    line starts no earlier than 0.1 s before the fanfare's loud body ends (its 0.25 s frames within 3 dB of the peak)."""
    fanfare = ROOT / "tools" / "audio" / "mint" / "finish.wav"
    if not fanfare.exists():
        pytest.skip("tools/audio/mint/finish.wav not built in this checkout")
    end = wav_body_end(fanfare)
    assert 3.5 <= end <= 5.0, end                                   # 4.25 s measured 2026-10-13
    assert const("FinishVoiceSeconds") >= end - 0.1, (const("FinishVoiceSeconds"), end)
