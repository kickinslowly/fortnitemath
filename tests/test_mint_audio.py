"""Mint music and sound effects (GOALS G9): the cue lists agree between tools/make_mint_audio.py and tools/build_audio.py,
`--mint` composes with `--announcer` / `--boss-voice` without touching their cues, a missing wave keeps stock for that cue
only, and the loop maths (bar lengths, crossfade gains, loudness, true peak, the seam score) behave on synthetic signals.
Pure Python: no UEFN, no Mint (the one ffmpeg cross-check skips itself when ffmpeg is missing)."""
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_audio as ba  # noqa: E402
import make_mint_audio as mm  # noqa: E402

SR = mm.SR
PROJECT = "c498eed2-96c5-4757-91a1-edb374b16d67"


# ---------------------------------------------------------------------------------------------------- cue lists

def test_mint_cues_are_the_cues_the_script_writes():
    written = [c for c in mm.cues() if c != "ice_crack"]       # ice_crack has no cue yet
    assert sorted(written) == sorted(ba.MINT_CUES)
    assert len(set(ba.MINT_CUES)) == len(ba.MINT_CUES)


def test_every_mint_cue_has_a_build_audio_row():
    for cue in ba.MINT_CUES:
        assert cue in ba.ALL_CUES, cue
        asset, opts = ba.ALL_CUES[cue]
        if cue.startswith("music_"):
            assert opts.get("loopAudio") is True, cue          # beds loop until Stop(Agent)
    stock = [c for c in ba.MINT_CUES if ba.ALL_CUES[c][0]]
    assert stock == ["music_t1", "music_t2", "music_t3", "music_t4", "music_t5", "finish", "door_open"]
    for cue in ba.MINT_CUES:                                    # the rest have no stock stand-in
        if cue not in stock:
            assert ba.ALL_CUES[cue][0] is None, cue
    # the Verse-known rows stay in CUES (tests/test_audio_cues.py), the rest wait in PENDING_CUES, none in both
    assert not set(ba.CUES) & set(ba.PENDING_CUES)
    assert list(ba.ALL_CUES) == list(ba.CUES) + list(ba.PENDING_CUES)
    assert set(ba.PENDING_CUES) <= set(ba.MINT_CUES)


def test_the_repo_declares_a_tag_class_for_every_cue_and_none_for_the_pending_ones():
    declared = ba.repo_cue_tags()
    assert set(ba.CUES) <= declared                      # every Verse-known row has its class (volt_yay / volt_hmm included)
    for cue in ba.PENDING_CUES:                          # a pending cue whose Verse side has landed must move into CUES
        assert cue not in declared, f"{cue} now has a tag class: move its row from PENDING_CUES into CUES (enum order)"


def test_sources_table_is_well_formed():
    ids = [v[2] for v in mm.SOURCES.values()]
    assert len(set(ids)) == len(ids)
    assert all(len(i) == 32 and i.isalnum() for i in ids)
    for cue in mm.cues():
        assert 1 <= len(mm.cue_stems(cue)) <= 2, cue            # at most a pick and an alt
    for stem, (cue, kind, _, ask, text) in mm.SOURCES.items():
        assert kind in ("music", "sfx") and text
        assert (ask is not None) == (kind == "music"), stem
        if kind == "music":
            assert cue.startswith("music_")
    # a take ends in _a / _b and the cue is the stem without it; a lone source is its own cue or maps explicitly
    for stem in ("music_t1_a", "music_t1_b", "music_t5_b", "music_boss_a", "titan_roar_b"):
        assert mm.SOURCES[stem][0] == stem.rsplit("_", 1)[0]


# ---------------------------------------------------------------------------------------------------- paths

def test_mint_path_and_classifiers():
    p = ba.mint_path(PROJECT, "finish")
    assert p == f"/{PROJECT}/FNM_Audio/mint/finish.finish"
    assert ba.is_mint(p) and ba.is_mint(p, "finish") and not ba.is_mint(p, "door_open")
    assert not ba.is_vo(p)                                      # a mint wave must never get the voice volume (2.5)
    v = ba.vo_path(PROJECT, "am_michael", "go")
    assert ba.is_vo(v, "go") and not ba.is_mint(v)
    assert not ba.is_mint(None) and not ba.is_mint("/Game/Sounds/Creative/Toys/x.x")


# ---------------------------------------------------------------------------------------------------- the flag's composition

def fake_exists(present):
    present = set(present)
    return lambda path: path.split(".")[0] in {p.split(".")[0] for p in present}


def all_waves(voice="am_michael", boss="am_onyx"):
    out = [ba.mint_path(PROJECT, c) for c in ba.MINT_CUES]
    out += [ba.vo_path(PROJECT, voice, c) for c in ba.ANNOUNCER_CUES]
    out += [ba.vo_path(PROJECT, boss, c) for c in ba.BOSS_CUES]
    return out


def test_flag_groups_do_not_overlap():
    a, b, m = set(ba.ANNOUNCER_CUES), set(ba.BOSS_CUES), set(ba.MINT_CUES)
    assert not (a & b) and not (a & m) and not (b & m)


def test_no_mint_flag_leaves_stock_even_when_waves_exist():
    out = ba.sources(PROJECT, None, None, False, fake_exists(all_waves()))
    for cue in ba.MINT_CUES:
        assert out.get(cue) == ba.ALL_CUES[cue][0]              # stock path, or absent for the Mint-only cues
    assert not any(ba.is_mint(p) for p in out.values())


def test_mint_alone_replaces_exactly_its_cues():
    out = ba.sources(PROJECT, None, None, True, fake_exists(all_waves()))
    for cue in ba.MINT_CUES:
        assert out[cue] == ba.mint_path(PROJECT, cue)
    stock = {c: a for c, (a, _) in ba.ALL_CUES.items() if a and c not in ba.MINT_CUES}
    for cue, asset in stock.items():
        assert out[cue] == asset                                # nobody else was touched
    assert not any(c in out for c in ba.ANNOUNCER_CUES + ba.BOSS_CUES if ba.ALL_CUES[c][0] is None)


def test_all_three_flags_compose():
    out = ba.sources(PROJECT, "am_michael", "am_onyx", True, fake_exists(all_waves()))
    for cue in ba.ANNOUNCER_CUES:
        assert ba.is_vo(out[cue], cue) and "am_michael" in out[cue]
    for cue in ba.BOSS_CUES:
        assert ba.is_vo(out[cue], cue) and "am_onyx" in out[cue]
    for cue in ba.MINT_CUES:
        assert ba.is_mint(out[cue], cue)
    assert len(out) == len(ba.ALL_CUES)                         # every cue has a sound


def test_missing_wave_keeps_stock_for_that_cue_only(capsys):
    present = [p for p in all_waves() if not p.endswith(("/finish.finish", "/volt_yay.volt_yay"))]
    out = ba.sources(PROJECT, "am_michael", "am_onyx", True, fake_exists(present))
    assert out["finish"] == ba.ALL_CUES["finish"][0]            # stock kept
    assert "volt_yay" not in out                                # no stock stand-in: not wired
    assert ba.is_mint(out["door_open"], "door_open") and ba.is_mint(out["music_t3"], "music_t3")
    text = capsys.readouterr().out
    assert "NOT IMPORTED, stock kept: finish" in text
    assert "NOT IMPORTED, not wired: volt_yay" in text
    assert f"{len(ba.MINT_CUES) - 2} of {len(ba.MINT_CUES)} waves found" in text


def test_mint_flag_with_nothing_imported_changes_nothing(capsys):
    out = ba.sources(PROJECT, None, None, True, fake_exists([]))
    assert out == {c: a for c, (a, _) in ba.ALL_CUES.items() if a}
    assert "0 of" in capsys.readouterr().out


# ---------------------------------------------------------------------------------------------------- loop maths

def test_bar_samples():
    assert mm.bar_samples(28, 2.0) == 28 * 2 * SR == 2469600       # 120 BPM, 56 s
    assert mm.bar_samples(48, 240 / 140) == 48 * 3 * SR * 4 // 7 == 3628800    # 140 BPM
    assert mm.bar_samples(8, 240 / 110) == round(8 * 240 / 110 * SR)


@pytest.mark.parametrize("rho", [0.0, 0.3, 0.8, 1.0])
def test_crossfade_gains_hold_the_power(rho):
    go, gi = mm.xfade_gains(4410, rho)
    total = go ** 2 + gi ** 2 + 2 * rho * go * gi                 # power of two segments correlated rho
    assert np.allclose(total, 1.0, atol=1e-9)
    assert go[0] > 0.99 and gi[0] < 0.05 and go[-1] < 0.05 and gi[-1] > 0.99
    assert np.all(np.diff(go) <= 1e-12) and np.all(np.diff(gi) >= -1e-12)


def test_make_loop_is_continuous_at_the_wrap():
    rng = np.random.default_rng(1)
    x = rng.standard_normal((SR * 10, 2)) * 0.1
    S, L, X = 5000, SR * 6, SR // 2
    o = mm.make_loop(x, S, L, X, 0.0)
    assert len(o) == L
    assert np.allclose(o[0], x[S + L] * mm.xfade_gains(X, 0.0)[0][0] + x[S] * mm.xfade_gains(X, 0.0)[1][0])
    assert np.allclose(o[X:], x[S + X:S + L])                    # past the crossfade the loop is the source
    # o[0] is (almost) x[S+L], the sample that follows o[-1] = x[S+L-1]: the wrap is the source's own step
    assert np.abs(o[0] - x[S + L]).max() < 0.02 * np.abs(x).max() + 0.01
    assert np.allclose(o[-1], x[S + L - 1])


# ---------------------------------------------------------------------------------------------------- loudness, peak, limiter

def sine(db, seconds=20.0, f=1000.0, ch=2):
    t = np.arange(int(seconds * SR)) / SR
    return np.stack([10 ** (db / 20) * np.sin(2 * np.pi * f * t)] * ch, axis=1)


def test_integrated_lufs_matches_ebu_tech_3341_case_1():
    assert abs(mm.integrated_lufs(sine(-23.0)) - (-23.0)) < 0.05      # stereo 1 kHz at -23 dBFS reads -23.0 LUFS


def test_gating_ignores_silence():
    x = np.concatenate([sine(-23.0, 10.0), np.zeros((SR * 10, 2))])
    assert abs(mm.integrated_lufs(x) - (-23.0)) < 0.1


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not on PATH")
def test_integrated_lufs_agrees_with_ffmpeg_ebur128_on_a_real_bed():
    mp3 = ROOT / "art" / "audio" / "mint" / "music_t3_b.mp3"
    if not mp3.exists():
        pytest.skip("mp3 not present")
    x = mm.decode(mp3)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp3), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    summary = r.stderr.split("Summary:")[1]
    i = float(summary.split("I:")[1].split("LUFS")[0])
    tp = float(summary.split("Peak:")[1].split("dBFS")[0])
    assert abs(mm.integrated_lufs(x) - i) < 0.15
    assert abs(mm.true_peak_db(x) - tp) < 0.3


def test_true_peak_sees_intersample_peaks():
    n = np.arange(SR)
    x = np.sin(2 * np.pi * (SR / 4) * n / SR + np.pi / 4)           # samples 0.707, 0.707, -0.707, -0.707: peak -3 dBFS
    stereo = np.stack([x, x], axis=1) * 1.0
    assert abs(20 * np.log10(np.abs(stereo).max()) + 3.01) < 0.05
    assert abs(mm.true_peak_db(stereo) - 0.0) < 0.1                 # but the waveform between the samples reaches 0 dBTP


def test_limiter_holds_the_ceiling_and_leaves_the_rest_alone():
    x = sine(-12.0, 3.0, f=440.0)
    x[SR + 7] = 1.0                                                 # one 0 dBFS spike on a -12 dBFS tone
    y, gr = mm.limit(x, -1.0, loop=False)
    assert mm.true_peak_db(y) <= -1.0 + 0.05
    assert 0.9 < gr < 1.6                                           # 0 dBFS down to -1 dBFS
    assert np.allclose(y[:SR // 2], x[:SR // 2])                    # far from the spike nothing changed
    assert np.allclose(y[-SR // 2:], x[-SR // 2:])


def test_limiter_wraps_around_a_loop():
    x = sine(-12.0, 2.0, f=440.0)
    x[0] = 1.0
    y, _ = mm.limit(x, -1.0, loop=True)
    assert mm.true_peak_db(y) <= -1.0 + 0.05
    assert np.abs(y[-5:] - x[-5:]).max() > 1e-6                      # the gain dip reaches the end of the loop


# ---------------------------------------------------------------------------------------------------- one-shots

def test_process_sfx_trims_the_lead_fades_the_tail_and_hits_the_target():
    rng = np.random.default_rng(2)
    t = np.arange(SR) / SR
    burst = np.sin(2 * np.pi * 800 * t) * np.exp(-3 * t) * 0.05
    x = np.zeros((SR * 2, 2))
    x[int(0.3 * SR):int(1.3 * SR)] = np.stack([burst, burst], axis=1)
    x += rng.standard_normal(x.shape) * 1e-5
    y, info = mm.process_sfx(x)
    first = int(np.argmax(np.abs(y).max(axis=1) > np.abs(y).max() * 0.01))
    assert first / SR <= 0.010                                       # at most 10 ms of lead left
    assert len(y) / SR < 1.4                                         # the 0.7 s of silence either side is gone
    assert np.abs(y[-1]).max() < 1e-3                                # the tail ends faded
    assert abs(mm.short_term_max(y) - mm.SFX_LUFS) < 0.1 or info["gr_db"] > 0
    assert mm.true_peak_db(y) <= mm.CEILING_DB + 0.05


def test_wav_roundtrip_is_deterministic(tmp_path):
    x = sine(-12.0, 0.5, f=330.0)
    a, b = tmp_path / "a.wav", tmp_path / "b.wav"
    mm.write_wav(a, x, "cue.wav")
    mm.write_wav(b, x, "cue.wav")
    assert a.read_bytes() == b.read_bytes()
    back = mm.read_wav(a)
    assert back.shape == x.shape and np.abs(back - x).max() < 2.5 / 32768


# ---------------------------------------------------------------------------------------------------- tempo, loop search, seam score

def synthetic_bed(bars=20, bpm=120.0, tile_bars=4, seed=3):
    """A drum + chord bed: a tile_bars pattern (kick on every beat, snare on 2 and 4, 8th hats, chord per bar) repeated,
    so the music repeats exactly every tile_bars bars."""
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm
    bar = 4 * beat
    out = np.zeros((int(bars * bar * SR) + SR, 2))
    chords = [(220.0, 277.2, 329.6), (196.0, 246.9, 293.7), (174.6, 220.0, 261.6), (196.0, 246.9, 311.1)]
    hat = rng.standard_normal(int(0.04 * SR)) * np.exp(-np.arange(int(0.04 * SR)) / (0.008 * SR))
    snare = rng.standard_normal(int(0.2 * SR)) * np.exp(-np.arange(int(0.2 * SR)) / (0.04 * SR))
    kt = np.arange(int(0.25 * SR)) / SR
    kick = np.sin(2 * np.pi * (50 + 80 * np.exp(-kt * 30)) * kt) * np.exp(-kt * 14)
    for b in range(bars):
        t0 = b * bar
        for f in chords[(b % tile_bars) % 4]:
            t = np.arange(int(bar * SR)) / SR
            seg = 0.04 * np.sin(2 * np.pi * f * t) * np.minimum(1, t * 20) * np.minimum(1, (bar - t) * 20)
            i = int(t0 * SR)
            out[i:i + len(seg), 0] += seg
            out[i:i + len(seg), 1] += seg
        for k in range(4):
            i = int((t0 + k * beat) * SR)
            out[i:i + len(kick)] += 0.5 * kick[:, None]
            if k in (1, 3):
                out[i:i + len(snare)] += 0.25 * snare[:, None]
        for k in range(8):
            i = int((t0 + k * beat / 2) * SR)
            out[i:i + len(hat)] += 0.08 * hat[:, None]
    return out[:int(bars * bar * SR)]


@pytest.fixture(scope="module")
def bed():
    return synthetic_bed()


def test_tempo_and_downbeat_of_a_synthetic_bed(bed):
    mono = bed.mean(axis=1)
    env, low, fr = mm.onset_env(mono)
    bpm, beat_s, phase, down = mm.estimate_tempo(env, low, fr, ask=120.0)
    assert abs(bpm - 120.0) < 0.1
    assert abs(beat_s - 0.5) < 0.001
    # the kick sits on every half second; the downbeat is one of them, so it is a multiple of 0.5 s (within the 12 ms
    # the onset detector dates an attack late) and the phase is on the same grid
    assert abs(down / 0.5 - round(down / 0.5)) * 0.5 < 0.03
    assert abs(phase / 0.5 - round(phase / 0.5)) * 0.5 < 0.03


def test_find_loop_on_a_synthetic_bed(bed):
    best, info = mm.find_loop(bed, 120.0)
    assert best is not None
    assert abs(info["bpm"] - 120.0) < 0.1
    assert best["N"] % 4 == 0
    assert abs(best["L"] / SR - best["N"] * 2.0) < 0.003            # the repeat length is N bars of 2 s
    assert best["rep"] > 0.85                                        # the pattern repeats exactly
    assert best["L"] + best["S"] + best["X"] <= len(bed)


def test_good_loop_passes_the_seam_score_and_a_bad_one_fails(bed):
    best, info = mm.find_loop(bed, 120.0)
    S, L, X, N = best["S"], best["L"], best["X"], best["N"]
    mono = bed.mean(axis=1)
    good = mm.make_loop(bed, S, L, X, 0.0)
    assert not mm.seam_flags(mm.seam_report(good, N), best["rep"])
    env = mm.amp_env(mono)
    # DISPROOF 1: shift the repeat length by a quarter beat; the repeatability at that length collapses
    rep_good = mm.repeat_lag(env, S, L, X, mm.EH)[1]
    rep_bad = mm.repeat_lag(env, S, L + SR // 8, X, mm.EH)[1]
    assert rep_good > 0.85 and rep_bad < 0.5
    # DISPROOF 2: cut straight from a loud bar into silence (the file's end): the wrap is a level step the score flags
    tail = bed.copy()
    tail[-SR * 2:] = 0.0
    loop = tail[len(tail) - SR * 8:].copy()
    assert "level" in mm.seam_flags(mm.seam_report(loop, 4))
    # and the flag text reaches the table
    assert "level" in mm.flag_text(mm.seam_report(loop, 4))
    assert mm.flag_text(mm.seam_report(good, N), best["rep"]) == ""
    assert "rep" in mm.flag_text(mm.seam_report(good, N), rep_bad)


def test_a_gap_is_found_by_its_run_length():
    flags = np.array([0, 1, 1, 0, 1, 1, 1, 1, 0, 1], dtype=bool)
    assert mm.longest_run(flags) == 4
    assert mm.longest_run(np.zeros(5, dtype=bool)) == 0
    assert mm.GAP_RUN == 4


def test_bad_loops_demo_runs_on_a_real_take_if_present(capsys):
    mp3 = ROOT / "art" / "audio" / "mint" / "music_t3_b.mp3"
    if not mp3.exists():
        pytest.skip("mp3 not present")
    mm.bad_loops("music_t3_b")
    out = capsys.readouterr().out
    assert "good (found)" in out and "FLAG" in out                   # at least one deliberately bad loop point is flagged


# ---------------------------------------------------------------------------------------------------- build() against a fake editor

def test_build_removes_a_device_whose_tag_class_is_not_compiled_and_carries_on(monkeypatch, capsys):
    """2026-10-13: set_properties answered "_Verse.fnm_cue_volt_yay is not valid Class" and build() died with a half-built device
    and nothing saved. Now the device is removed, the cue skipped, the others placed, the assets saved."""
    calls = []
    placed = []

    def fake_call(toolset, tool, args=None, **kw):
        calls.append((tool, args))
        if tool == "PlaceDevice":
            placed.append(f"actor{len(placed)}")
            return {"returnValue": {"refPath": placed[-1]}}
        return {"returnValue": True}

    def fake_tags(actor, project, names):
        if names == ["fnm_cue_volt_yay"]:
            raise RuntimeError("/x/_Verse.fnm_cue_volt_yay is not valid Class for property 'InternalTag'\nmore")

    monkeypatch.setattr(ba.u, "call", fake_call)
    monkeypatch.setattr(ba, "project_id", lambda: PROJECT)
    monkeypatch.setattr(ba, "clear", lambda: 0)
    monkeypatch.setattr(ba, "verse_cue_tags", lambda: {"volt_yay", "countdown3"})   # the root declares it, the compile did not happen
    monkeypatch.setattr(ba, "verse_tags", fake_tags)
    monkeypatch.setattr(ba, "props_set", lambda *a, **k: None)
    monkeypatch.setattr(ba, "check", lambda actor, want: (None, []))
    monkeypatch.setattr(ba, "sources", lambda *a, **k: {"countdown3": ba.CUES["countdown3"][0], "volt_yay": ba.mint_path(PROJECT, "volt_yay")})
    problems = ba.build(mint=True)
    out = capsys.readouterr().out
    assert placed == ["actor0", "actor1"]                                  # countdown3 then volt_yay were placed
    removed = [a for t, a in calls if t == "remove_from_scene"]
    assert removed == [{"actor": ba.ref("actor1")}]                        # only the half-built volt_yay device was removed
    assert any(t == "save_assets" for t, _ in calls)                       # and the run got to its save
    assert "SKIPPED, the tag does not resolve" in out and "FNM_Cue_VoltYay" in out
    assert problems == 1


def test_build_skips_cues_the_project_has_no_tag_class_for(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(ba.u, "call", lambda toolset, tool, args=None, **kw: calls.append(tool) or {"returnValue": {"refPath": "a"}})
    monkeypatch.setattr(ba, "project_id", lambda: PROJECT)
    monkeypatch.setattr(ba, "clear", lambda: 0)
    monkeypatch.setattr(ba, "verse_cue_tags", lambda: {"countdown3"})
    monkeypatch.setattr(ba, "verse_tags", lambda *a: None)
    monkeypatch.setattr(ba, "props_set", lambda *a, **k: None)
    monkeypatch.setattr(ba, "check", lambda actor, want: (None, []))
    # (music_boss was the undeclared example until G9 D2 gave it a tag class: a made-up id stands in for one now)
    monkeypatch.setattr(ba, "sources", lambda *a, **k: {"countdown3": ba.CUES["countdown3"][0], "zz_undeclared": ba.mint_path(PROJECT, "zz_undeclared"),
                                                         "volt_hmm": ba.mint_path(PROJECT, "volt_hmm")})
    assert ba.build(mint=True) == 0
    out = capsys.readouterr().out
    assert calls.count("PlaceDevice") == 1                                  # only countdown3
    assert "no fnm_cue_<id> tag class in any fnm_tags.verse" in out and "zz_undeclared" in out
    assert "declared in the repo's fnm_tags.verse but not in the project yet" in out and "volt_hmm" in out
