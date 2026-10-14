"""Mint music and sound effects -> UEFN-ready wavs (GOALS G9; console/AUDIO.md "Mint music and SFX").

Reads the mp3s Mint made (art/audio/mint/<stem>.mp3, `SOURCES` below: asset ids and the one-line ask for each), writes
44.1 kHz 16-bit stereo wavs to tools/audio/mint/<cue>.wav and tools/audio/mint/LISTEN.md. Re-runnable and deterministic
(seeded dither). Needs numpy and ffmpeg (decode only). It never plays audio and never talks to UEFN or Mint.

    python tools/make_mint_audio.py                     # every source whose mp3 exists
    python tools/make_mint_audio.py music_t3_a music_t3_b   # only these sources (a tier needs both its takes to pick)
    python tools/make_mint_audio.py --pick music_t3=b   # force a take (Aaron's ear overrides the numbers)
    python tools/make_mint_audio.py --stage             # also copy the chosen wavs to %TEMP%\\fnm_mint (GUI import)
    python tools/make_mint_audio.py --bad-loops music_t3_a   # the disproof: deliberately bad loop points, scored

MUSIC (a bed per tier, the boss and the menu). 1) Tempo: the onset envelope (log spectral flux) is autocorrelated for
the tempo near the ask, then a comb filter refines it to 0.01 BPM and finds the beat phase; the downbeat is the beat of
the four whose low-band onsets are strongest. 2) Loop: candidates are (start S on a bar line, N bars, N a multiple of
4); for each, the true repeat length L is found by cross-correlating the amplitude envelope of the bar at S with the
audio around S + N bars (+-150 ms, 0.5 ms steps; then the bass waveform within +-30 samples), so L is the music's own
repeat length, not N x (2.0 s) on trust. A candidate is rejected when any 125 ms frame of its body falls 15 dB below the
median (a gap or fade), or a bar's level strays more than 6 dB from the median (an intro hit or an ending). The best
envelope correlation ("rep", with a small bonus for length) wins. 3) Seam: the loop is the N bars from S with its first
bar replaced by an equal-power crossfade of the audio that FOLLOWS the loop end (fading out) into the audio at S
(fading in); the wrap is continuous by construction (o[0] continues o[L-1]). The crossfade gains are corrected for the
two bars' correlation rho so a repeated bass does not bump +3 dB. 4) Loudness: integrated LUFS (BS.1770-4, K-weighted,
gated, implemented here and checked against ffmpeg ebur128) to MUSIC_LUFS, true peak (4x, FFT, periodic) <= CEILING_DB
through a look-ahead limiter that wraps around the seam.

SEAM SCORE. Windows of one beat on each side of every bar line of the finished loop: level difference (rms) and
spectral distance (mean |dB| difference over 24 log bands, 50 Hz to 16 kHz). The wrap (bar line 0) is compared with the
N-1 interior bar lines: it passes when its spectral distance is within the interior's 90th percentile (and the level
step is under 3 dB). `rep` is the envelope correlation of the two crossfaded bars, `step` the sample jump at the wrap
over the loop's mean sample step. What the numbers prove: the wrap is statistically no rougher than the music's own bar
lines. What they do not prove: that it sounds right. Nobody has listened yet.

SFX and fanfares: leading silence trimmed to LEAD_KEEP_S, trailing silence trimmed, a cosine tail fade, gain so the loudest
3 s window (or the whole clip when shorter) reads SFX_LUFS short-term, true peak <= CEILING_DB.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import wave
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "art" / "audio" / "mint"
OUT_DIR = ROOT / "tools" / "audio" / "mint"
SR = 44100
MUSIC_LUFS = -18.0       # integrated; the beds play at device volume 0.5, under the voice lines
SFX_LUFS = -16.0         # loudest 3 s window (short-term)
CEILING_DB = -1.0        # true peak
LEAD_KEEP_S = 0.005      # leading silence left (brief: <= 10 ms)
TAIL_FADE_S = 0.25
GAP_DB = 15.0            # a 125 ms frame this far under the median RMS is quiet ...
GAP_RUN = 4              # ... and GAP_RUN of them in a row (half a second) is a gap or a fade; shorter rests are rhythm
BAR_DEV_DB = 6.0         # a bar this far from the median bar level is an intro hit / an ending
XFADE_BARS = 1

# stem -> (cue it feeds, kind, Mint asset id, ask BPM or None, one-line ask). The takes of one cue are the stems that
# share it; the numbers pick one (pick_take) and the other is written as <cue>_alt.wav.
SOURCES = {
    "music_t1_a": ("music_t1", "music", "xd71rr31w3h6m58s4tn7a98wm98g9vf4", 120, "calmest: hand drums, shaker, marimba, half-time"),
    "music_t1_b": ("music_t1", "music", "xd75a5pgczb0k7atgndyqexca58g92dq", 120, "calmest: bongos, kalimba"),
    "music_t2_a": ("music_t2", "music", "xd79dmvtma4dcvjkh8cht8hva58g987w", 120, "light kit, synth arp, pizzicato"),
    "music_t2_b": ("music_t2", "music", "xd78j22dr35cy8j9jarxjy9cg58g8wn7", 120, "bouncy, flute"),
    "music_t3_a": ("music_t3", "music", "xd7f9q8kq4nkvkvrgf7a7jbrm98g9c9c", 120, "kit groove, synth bass, brass stabs"),
    "music_t3_b": ("music_t3", "music", "xd7d2zs2dp982d2g7gz93x4skd8g8dvc", 120, "icy ridge, bells"),
    "music_t4_a": ("music_t4", "music", "xd7cspz53054jb3ennv25r0z258g8x2v", 120, "intense: strings ostinato, brass"),
    "music_t4_b": ("music_t4", "music", "xd7e446ffypgzjhhfx6hr927sh8g993w", 120, "intense: toms, distorted bass"),
    "music_t5_a": ("music_t5", "music", "xd7e5v6x790v11q47rtzahev0n8g8ps7", 120, "peak: orchestra, choir pads"),
    "music_t5_b": ("music_t5", "music", "xd70ypp3gx72rfrh1d0syen6y18g9hgk", 120, "peak: second take for tier 5"),
    "music_boss_a": ("music_boss", "music", "xd74h1mm4r1wk7303r46encc5d8g8xz5", 140, "boss fight: taiko, low brass, choir"),
    "music_boss_b": ("music_boss", "music", "xd70g7p88kpwd9ew45gpes7wvd8g862t", 140, "boss fight: drums, guitar riffs, choir"),
    "music_menu": ("music_menu", "music", "xd758r88qxmn3q5n66kkxj64r58g9e4g", 110, "game-show lobby loop for the grade picker"),
    "fanfare_a": ("finish", "sfx", "xd72am8cq6b154hsfapf2hzny58g901d", None, "7 s victory fanfare, brass + timpani"),
    "fanfare_b": ("finish", "sfx", "xd733f5w0j86zafg92bg3zej558g9awm", None, "7 s victory fanfare, brass + snare"),
    "portal_whoosh": ("door_open", "sfx", "xd7bzyjep5a9xa8pcdghcv6m198g86rr", None, "1.5 s sparkle whoosh"),
    "volt_yay": ("volt_yay", "sfx", "xd7azm9yjv2tf5vaggrm7jj7js8g9vkd", None, "1.2 s happy robot chirp"),
    "volt_hmm": ("volt_hmm", "sfx", "xd7cxvexwrt63zk8md2sx70bw18g854q", None, "1.5 s thinking robot warble"),
    "volt_oops": ("volt_oops", "sfx", "xd77k2e96q235crtepe208h5jh8g8qc4", None, "1.2 s Volt 'uh-oh'"),
    "titan_roar_a": ("titan_roar", "sfx", "xd794dgpg0dr9c0hr1k5cj0nxn8g84gj", None, "3 s titan roar"),
    "titan_roar_b": ("titan_roar", "sfx", "xd7c6mymwatqfyrepabm5zkjds8g9y53", None, "3 s titan roar"),
    "crowd_cheer": ("crowd_cheer", "sfx", "xd78cw1ag57evx9rdx57wnxkw18g9e0n", None, "4 s crowd cheer"),
    "crowd_aww": ("crowd_aww", "sfx", "xd7aej6djnk341d1dwrt95bmm18g82pj", None, "2.5 s crowd 'aww'"),
    "ice_crack": ("ice_crack", "sfx", "xd7d6sbfy7pg6xp32z841r82dh8g9h8h", None, "2 s ice crack (no cue yet; not imported)"),
}


def cue_stems(cue):
    """The source stems (takes) that feed one cue, in table order."""
    return [s for s, v in SOURCES.items() if v[0] == cue]


def cues():
    """Every cue this script writes, in table order."""
    out = []
    for v in SOURCES.values():
        if v[0] not in out:
            out.append(v[0])
    return out


# ----------------------------------------------------------------------------------------------- decode / write

def decode(path, sr=SR):
    """mp3 (or any ffmpeg input) -> float64 array (n, 2) at sr."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(sr), "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype="<f4").reshape(-1, 2).astype(np.float64)


def write_wav(path, x, seed_name):
    """float (n, 2) -> 16-bit stereo wav with seeded TPDF dither (deterministic)."""
    rng = np.random.default_rng(zlib.crc32(seed_name.encode()))
    d = (rng.random(x.shape) - rng.random(x.shape)) / 32768.0
    q = np.clip(np.round((x + d) * 32768.0), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(q.tobytes())


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        assert w.getsampwidth() == 2 and w.getnchannels() == 2 and w.getframerate() == SR
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype="<i2").reshape(-1, 2).astype(np.float64) / 32768.0


# ----------------------------------------------------------------------------------------------- loudness (BS.1770-4)

def k_filter_ir(sr=SR, n=16384):
    """Impulse response of the BS.1770 K-weighting cascade (high shelf + RLB high-pass) at sr."""
    f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    K = math.tan(math.pi * f0 / sr)
    Vh = 10 ** (G / 20)
    Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b1 = [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a1 = [1.0, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = math.tan(math.pi * f0 / sr)
    a0 = 1 + K / Q + K * K
    b2 = [1.0, -2.0, 1.0]
    a2 = [1.0, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]

    def run(b, a, x):
        y = np.zeros(len(x))
        x1 = x2 = y1 = y2 = 0.0
        for i, xi in enumerate(x):
            yi = b[0] * xi + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
            y[i] = yi
            x2, x1, y2, y1 = x1, xi, y1, yi
        return y
    imp = np.zeros(n)
    imp[0] = 1.0
    return run(b2, a2, run(b1, a1, imp))


_IR = {}


def k_weight(x, sr=SR):
    """K-weight each channel of x (n, ch) by FFT convolution with the cascade's impulse response."""
    if sr not in _IR:
        _IR[sr] = k_filter_ir(sr)
    h = _IR[sr]
    n = len(x) + len(h)
    size = 1 << (n - 1).bit_length()
    H = np.fft.rfft(h, size)
    return np.stack([np.fft.irfft(np.fft.rfft(x[:, c], size) * H, size)[:len(x)] for c in range(x.shape[1])], axis=1)


def _block_power(x, block, hop, sr=SR):
    """Mean square of the K-weighted signal per block, summed over channels (all channels weight 1)."""
    y = k_weight(x, sr)
    p = (y ** 2).sum(axis=1)
    cs = np.concatenate([[0.0], np.cumsum(p)])
    starts = np.arange(0, max(len(p) - block, 0) + 1, hop)
    return (cs[starts + block] - cs[starts]) / block


def lufs_of(power):
    return -0.691 + 10 * np.log10(np.maximum(power, 1e-12))


def integrated_lufs(x, sr=SR):
    """BS.1770-4 integrated loudness: 400 ms blocks, 75 % overlap, -70 LUFS absolute gate, -10 LU relative gate."""
    block = int(0.4 * sr)
    if len(x) < block:
        return float(lufs_of(np.array([(k_weight(x, sr) ** 2).sum(axis=1).mean()]))[0])
    z = _block_power(x, block, int(0.1 * sr), sr)
    z = z[lufs_of(z) > -70.0]
    if len(z) == 0:
        return -70.0
    rel = lufs_of(np.array([z.mean()]))[0] - 10.0
    z = z[lufs_of(z) > rel]
    return float(lufs_of(np.array([z.mean()]))[0]) if len(z) else -70.0


def short_term_max(x, win_s=3.0, sr=SR):
    """Loudest window of min(win_s, clip length) seconds (hop 100 ms), no gating, in LUFS."""
    block = min(int(win_s * sr), len(x))
    return float(lufs_of(_block_power(x, block, int(0.1 * sr), sr)).max())


def true_peak_db(x):
    """4x oversampled peak in dBFS (ideal band-limited interpolation by FFT; periodic, which is right for a loop)."""
    n = len(x)
    peak = 0.0
    for c in range(x.shape[1]):
        X = np.fft.rfft(x[:, c])
        Xp = np.zeros(2 * n + 1, dtype=complex)
        Xp[:len(X)] = X
        up = np.fft.irfft(Xp, 4 * n) * 4
        peak = max(peak, float(np.abs(up).max()))
    return 20 * math.log10(max(peak, 1e-9))


def limit(x, ceiling_db=CEILING_DB, loop=False, sr=SR):
    """Transparent look-ahead peak limiter on the 4x-oversampled peak; wraps around when loop. Returns (y, max_gr_db)."""
    ceil = 10 ** (ceiling_db / 20)
    w = int(0.005 * sr) | 1
    y = x
    max_gr = 0.0
    for _ in range(4):
        n = len(y)
        mag = np.zeros(4 * n)
        for c in range(y.shape[1]):
            X = np.fft.rfft(y[:, c])
            Xp = np.zeros(2 * n + 1, dtype=complex)
            Xp[:len(X)] = X
            mag = np.maximum(mag, np.abs(np.fft.irfft(Xp, 4 * n) * 4))
        mag = mag.reshape(n, 4).max(axis=1)
        need = np.minimum(1.0, ceil / np.maximum(mag, 1e-12))
        if need.min() >= 1.0:
            break
        h = w // 2
        mode = "wrap" if loop else "edge"
        mn = np.lib.stride_tricks.sliding_window_view(np.pad(need, (h, h), mode=mode), w).min(axis=-1)   # centred min, n values
        cs = np.concatenate([[0.0], np.cumsum(np.pad(mn, (h, h), mode=mode))])
        g = np.minimum((cs[w:] - cs[:-w]) / w, 1.0)                                                      # centred mean, n values
        y = y * g[:, None]
        max_gr = max(max_gr, float(-20 * np.log10(max(g.min(), 1e-6))))
        if true_peak_db(y) <= ceiling_db + 0.02:
            break
        ceil *= 10 ** (-0.3 / 20)
    return y, max_gr


# ----------------------------------------------------------------------------------------------- tempo and beats

HOP = 128
NFFT = 1024


def onset_env(mono, sr=SR, hop=HOP, nfft=NFFT):
    """Log spectral flux (all bins, and bins under 250 Hz): (env, low_env, frame_rate). Frame i is dated at its centre."""
    win = np.hanning(nfft).astype(np.float32)
    n = (len(mono) - nfft) // hop + 1
    idx = np.arange(nfft)[None, :] + hop * np.arange(n)[:, None]
    S = np.abs(np.fft.rfft(mono[idx].astype(np.float32) * win, axis=1))
    L = np.log1p(S * 100)
    d = np.maximum(L[1:] - L[:-1], 0)
    kmax = int(250 * nfft / sr)
    env = np.concatenate([[0.0], d.sum(axis=1)])
    low = np.concatenate([[0.0], d[:, :kmax].sum(axis=1)])
    return env, low, sr / hop


def _interp(env, t):
    i = np.clip(np.floor(t).astype(int), 0, len(env) - 2)
    f = np.clip(t - i, 0, 1)
    return env[i] * (1 - f) + env[i + 1] * f


def estimate_tempo(env, low, fr, ask=120.0):
    """(bpm, beat_period_s, phase_s, downbeat_phase_s). Autocorrelation near the ask, then a comb refinement to 0.01 BPM.
    phase_s is the time of a beat; downbeat_phase_s the beat of the four with the strongest low-band onsets."""
    e = env - env.mean()
    n = len(e)
    f = np.fft.rfft(e, 2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:n]
    ac /= ac[0]

    def acs(lag):
        return float(_interp(ac, np.array([lag]))[0])
    lo, hi = ask * 0.8, ask * 1.25
    cand = np.arange(lo, hi, 0.1)
    sc = [acs(60 / b * fr) + 0.5 * acs(120 / b * fr) + 0.5 * acs(240 / b * fr) for b in cand]
    b0 = float(cand[int(np.argmax(sc))])

    def comb(bpm):
        step = 60.0 / bpm * fr
        best = (-1.0, 0.0)
        beats = np.arange(0, n / step - 1)
        for ph in np.arange(0, step, 0.5):
            v = _interp(env, ph + beats * step).mean()
            if v > best[0]:
                best = (v, ph)
        return best
    top = max(((comb(b), b) for b in np.arange(b0 - 1.5, b0 + 1.5, 0.01)), key=lambda t: t[0][0])
    (_, ph), bpm = top
    step = 60.0 / bpm * fr
    beats = np.arange(0, n / step - 1)
    lows = [float(_interp(low, ph + (beats[j::4]) * step).mean()) for j in range(4)]
    db = int(np.argmax(lows))
    half = NFFT / 2 / SR     # a flux frame is dated at its start; the attack is near its centre
    return bpm, 60.0 / bpm, ph / fr + half, (ph + db * step) / fr + half


# ----------------------------------------------------------------------------------------------- loop search

EH = 22  # envelope hop in samples (~2 kHz, 0.5 ms)


def amp_env(mono):
    """Rectified, 2 ms smoothed amplitude envelope at ~2 kHz."""
    k = int(0.002 * SR)
    a = np.abs(mono)
    cs = np.concatenate([[0.0], np.cumsum(a)])
    sm = (cs[k:] - cs[:-k]) / k
    return sm[::EH]


def ncc_lags(ref, sig):
    """Zero-normalised cross-correlation of ref against every window of sig (len(sig) - len(ref) + 1 lags)."""
    m = len(ref)
    r = ref - ref.mean()
    rn = np.linalg.norm(r) + 1e-12
    size = 1 << (len(sig) + m).bit_length()
    corr = np.fft.irfft(np.fft.rfft(sig, size) * np.conj(np.fft.rfft(r, size)), size)[:len(sig) - m + 1]
    cs = np.concatenate([[0.0], np.cumsum(sig)])
    cs2 = np.concatenate([[0.0], np.cumsum(sig ** 2)])
    k = len(sig) - m + 1
    s1 = cs[m:m + k] - cs[:k]
    s2 = cs2[m:m + k] - cs2[:k]
    var = np.maximum(s2 - s1 ** 2 / m, 1e-12)
    return corr / (rn * np.sqrt(var))


def bar_samples(n_bars, bar_s, sr=SR):
    """Loop length in samples for n_bars of bar_s seconds."""
    return int(round(n_bars * bar_s * sr))


def repeat_lag(env, s0, l0, w, d):
    """Best repeat length near l0 (all in samples): cross-correlate the envelope window at s0 with the audio near s0 + l0.
    Returns (L_samples, ncc)."""
    a, wn, dn = s0 // EH, w // EH, d // EH
    b = (s0 + l0) // EH
    ref = env[a:a + wn]
    lo = b - dn
    if lo < 0 or b + wn + dn > len(env) or len(ref) < wn:
        return None
    c = ncc_lags(ref, env[lo:b + wn + dn])
    k = int(np.argmax(c))
    return (lo + k) * EH - a * EH, float(c[k])


def refine_waveform(mono, s0, L, w, reach=30):
    """Within +-reach samples of L, the shift that best aligns the bass (under ~700 Hz) of the window at s0 with the one at
    s0 + L. Returns (L, ncc); keeps L when the bass does not correlate (> 0.3)."""
    k = 64
    cs = np.concatenate([[0.0], np.cumsum(mono)])
    lp = (cs[k:] - cs[:-k]) / k
    ref = lp[s0:s0 + w]
    best = (L, -1.0)
    for dl in range(-reach, reach + 1):
        a = s0 + L + dl
        if a + w > len(lp):
            continue
        seg = lp[a:a + w]
        c = float(np.dot(ref - ref.mean(), seg - seg.mean()) / (np.linalg.norm(ref - ref.mean()) * np.linalg.norm(seg - seg.mean()) + 1e-12))
        if c > best[1]:
            best = (L + dl, c)
    return best if best[1] > 0.3 else (L, best[1])


def xfade_gains(n, rho):
    """(fade_out, fade_in) gains of an n-sample equal-power crossfade, corrected for the segments' correlation rho
    (rho 0 = plain equal power; rho 1 = linear): g_out^2 + g_in^2 + 2 rho g_out g_in = 1."""
    t = (np.arange(n) + 0.5) / n
    c, s = np.cos(t * math.pi / 2), np.sin(t * math.pi / 2)
    rho = min(max(rho, 0.0), 1.0)
    k = 1.0 / np.sqrt(1.0 + 2.0 * rho * c * s)
    return c * k, s * k


def make_loop(x, S, L, X, rho):
    """The loop: x[S:S+L] with its first X samples replaced by a crossfade of x[S+L:S+L+X] (out) into x[S:S+X] (in)."""
    o = x[S:S + L].copy()
    go, gi = xfade_gains(X, rho)
    o[:X] = x[S + L:S + L + X] * go[:, None] + x[S:S + X] * gi[:, None]
    return o


def frame_db(mono, frame):
    k = len(mono) // frame
    return 20 * np.log10(np.sqrt((mono[:k * frame].reshape(k, frame) ** 2).mean(axis=1)) + 1e-9)


def timbre_distance(a, b):
    """Mean |dB| difference of the long-term spectra (24 log bands, 50 Hz to 16 kHz) of two equal-length segments: how
    unlike the two bars of a crossfade sound (0 = the same instrumentation; 6+ = a bright bar fading into a sparse one)."""
    edges = np.geomspace(50, 16000, 25)
    size = 1 << (len(a) - 1).bit_length()
    freqs = np.fft.rfftfreq(size, 1 / SR)
    win = np.hanning(len(a))
    norm = (win.sum() / 2) ** 2

    def prof(x):
        P = np.abs(np.fft.rfft(x * win, size)) ** 2 / norm
        return np.array([max(10 * math.log10(P[(freqs >= lo) & (freqs < hi)].mean() + 1e-12), -80.0) for lo, hi in zip(edges[:-1], edges[1:])])
    return float(np.abs(prof(a) - prof(b)).mean())


def longest_run(flags):
    """Length of the longest run of True in a boolean array."""
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def bar_levels(mono, s0, bar, nbars):
    """RMS dB of nbars consecutive bars starting at sample s0 (bar in samples, float)."""
    out = []
    for k in range(nbars):
        a, b = int(s0 + k * bar), int(s0 + (k + 1) * bar)
        seg = mono[a:b]
        out.append(20 * math.log10(math.sqrt(float((seg ** 2).mean())) + 1e-9) if len(seg) else -120.0)
    return np.array(out)


def find_loop(x, ask_bpm, log=None):
    """Pick the loop (S, N bars, L samples, X) for one take. Returns a dict (and the candidate count); None if none passes."""
    mono = x.mean(axis=1)
    env, low, fr = onset_env(mono)
    bpm, beat_s, _, down_s = estimate_tempo(env, low, fr, ask_bpm)
    bar_s = 4 * beat_s
    # onset frames are dated at their centre; the attack sits ~half a window earlier: snap each bar line to the local rise
    aenv = amp_env(mono)
    n = len(mono)
    med_frame = float(np.median(frame_db(mono, SR // 8)))
    frames = frame_db(mono, SR // 8)
    X = int(round(XFADE_BARS * bar_s * SR))
    cands, rejected = [], {}
    first = down_s - bar_s * math.ceil(down_s / bar_s)  # a downbeat at or before 0
    k0 = 0
    while first + k0 * bar_s < 0:
        k0 += 1
    k_max = int((n / SR) / bar_s)
    for k in range(k0, min(k_max, k0 + 12)):
        s_nom = int(round((first + k * bar_s) * SR))
        # snap to the amplitude rise within +-30 ms, 3 ms of pre-roll
        lo, hi = max(s_nom - int(0.03 * SR), 0), s_nom + int(0.03 * SR)
        eo = aenv[lo // EH:hi // EH]
        if len(eo) < 10:
            continue
        rise = np.convolve(eo, np.r_[-np.ones(6), np.ones(6)], mode="valid")
        S = max(lo + (int(np.argmax(rise)) + 6) * EH - int(0.003 * SR), 0)
        for N in range(4, 80, 4):
            l0 = bar_samples(N, bar_s)
            if S + l0 + X + SR // 20 > n:
                break
            if N < 8:
                continue
            rl = repeat_lag(aenv, S, l0, X, int(0.15 * SR))
            if rl is None:
                continue
            L, rep = rl
            if S + L + X > n:
                continue
            L2, wave_c = refine_waveform(mono, S, L, X)
            L = L2
            seg_frames = frames[S // (SR // 8):(S + L + X) // (SR // 8)]
            gaps = longest_run(seg_frames < med_frame - GAP_DB)
            lv = bar_levels(mono, S, L / N, N + 1)
            dev = float(np.abs(lv - np.median(lv[:N])).max())
            ok = gaps < GAP_RUN and dev <= BAR_DEV_DB
            if not ok:
                rejected[(k, N)] = (gaps, round(dev, 1))
                continue
            tim = timbre_distance(mono[S:S + X], mono[S + L:S + L + X])
            score = rep + 0.004 * N - 0.02 * max(0.0, dev - 3.0) - 0.03 * tim
            cands.append(dict(S=S, N=N, L=L, X=X, rep=rep, wave=wave_c, dev=dev, gaps=gaps, tim=tim, score=score, k=k))
    info = dict(bpm=bpm, bar_s=bar_s, down_s=down_s, rejected=len(rejected), candidates=len(cands))
    if not cands:
        return None, info
    ranked = sorted(cands, key=lambda c: -c["score"])
    for c in ranked:
        c["loop_bpm"] = 240.0 * c["N"] / (c["L"] / SR)
    info["ranked"] = ranked
    return ranked[0], info


BAR_STEP_DB = 3.0   # a bar-level loudness step at the wrap above this is a level jump the ear takes as a cut
CLICK_RATIO = 8.0   # the sample jump at the wrap over the local mean sample step
REP_MIN = 0.5       # envelope correlation of the two crossfaded bars below this: they are different music


def seam_report(o, N):
    """Score the wrap of loop o (N bars) against its own interior bar lines.
    spec: mean |dB| difference of 24 log bands (50 Hz to 16 kHz) between the beat before and the beat after a bar line
    (a full-scale sine reads 0 dB; bands are floored at -80 dB). bar_step: |level difference| of the whole bar before and
    after the line. ok = spec within the interior's 90th percentile AND bar_step <= BAR_STEP_DB."""
    L = len(o)
    bar = L / N
    w = int(bar / 4)
    mono = o.mean(axis=1)
    edges = np.geomspace(50, 16000, 25)
    size = 1 << (w - 1).bit_length()
    freqs = np.fft.rfftfreq(size, 1 / SR)
    win = np.hanning(w)
    norm = (win.sum() / 2) ** 2
    masks = [(freqs >= lo) & (freqs < hi) for lo, hi in zip(edges[:-1], edges[1:])]

    def bands(seg):
        P = np.abs(np.fft.rfft(seg * win, size)) ** 2 / norm
        return np.array([max(10 * math.log10(P[m].mean() + 1e-12), -80.0) for m in masks])

    def at(b, n):
        idx = (np.arange(-n, n) + b) % L
        return mono[idx[:n]], mono[idx[n:]]

    def rms_db(seg):
        return 20 * math.log10(math.sqrt(float((seg ** 2).mean())) + 1e-9)
    rows = []
    nb = int(round(bar))
    for k in range(N):
        b = int(round(k * bar))
        a, c = at(b, w)
        a2, c2 = at(b, nb)
        rows.append((abs(rms_db(c2) - rms_db(a2)), float(np.abs(bands(a) - bands(c)).mean()), abs(rms_db(c) - rms_db(a))))
    seam, inner = rows[0], np.array(rows[1:])
    p90 = float(np.percentile(inner[:, 1], 90))
    m10 = int(0.01 * SR)
    near = np.concatenate([np.abs(np.diff(mono[-m10:])), np.abs(np.diff(mono[:m10]))])   # +-10 ms round the wrap, not the wrap step
    step = float(np.abs(o[0] - o[-1]).max()) / (float(near.mean()) + 1e-12)
    out = dict(bar_step_db=seam[0], bar_step_p90=float(np.percentile(inner[:, 0], 90)), spec_db=seam[1], spec_p90=p90,
               spec_max=float(inner[:, 1].max()), spec_med=float(np.median(inner[:, 1])), beat_rms_db=seam[2], step=step)
    out["ok"] = not seam_flags(out)
    return out


def seam_flags(s, rep=None):
    """Why a wrap is flagged (empty = fine): 'spec' the beat after the wrap sounds unlike the beat before it by more than
    anything at the music's own bar lines (x1.1), 'level' a bar-level step over BAR_STEP_DB, 'click' a sample jump at the
    wrap over CLICK_RATIO x the local sample step, 'rep' (when given) the two crossfaded bars barely resemble each other."""
    out = []
    if s["spec_db"] > 1.1 * s["spec_max"]:
        out.append("spec")
    if s["bar_step_db"] > BAR_STEP_DB:
        out.append("level")
    if s["step"] > CLICK_RATIO:
        out.append("click")
    if rep is not None and rep < REP_MIN:
        out.append("rep")
    return out


# ----------------------------------------------------------------------------------------------- music / sfx pipeline

TOP_K = 12


def process_music(x, ask_bpm):
    """x -> (loop float array at MUSIC_LUFS, info); loop is None when no candidate passed. The TOP_K candidates by
    envelope repeatability are each built and seam-scored; the one whose wrap is smoothest (spec distance against the
    interior's p90, then its rep) wins."""
    best, info = find_loop(x, ask_bpm)
    if best is None:
        return None, info
    mono = x.mean(axis=1)
    built = []
    for c in info["ranked"][:TOP_K]:
        S, L, X, N = c["S"], c["L"], c["X"], c["N"]
        a, b = mono[S:S + X], mono[S + L:S + L + X]
        rho = float(np.dot(a - a.mean(), b - b.mean()) / (np.linalg.norm(a - a.mean()) * np.linalg.norm(b - b.mean()) + 1e-12))
        o = make_loop(x, S, L, X, rho)
        sm = seam_report(o, N)
        over = max(0.0, sm["spec_db"] / max(sm["spec_p90"], 0.5) - 1.0)
        final = c["score"] - 0.5 * over - 0.05 * max(0.0, sm["bar_step_db"] - 1.5) - (0.3 if not sm["ok"] else 0.0)
        built.append((final, c, rho, o, sm))
    final, best, rho, o, sm = max(built, key=lambda t: t[0])
    best = dict(best)
    gain = MUSIC_LUFS - integrated_lufs(o)
    o = o * 10 ** (gain / 20)
    gr = 0.0
    if true_peak_db(o) > CEILING_DB:
        o, gr = limit(o, CEILING_DB, loop=True)
        o = o * 10 ** ((MUSIC_LUFS - integrated_lufs(o)) / 20)    # the limiter shaved a little energy: restore, re-limit once
        if true_peak_db(o) > CEILING_DB:
            o, gr2 = limit(o, CEILING_DB, loop=True)
            gr = max(gr, gr2)
    best.update(rho=rho, gain_db=gain, gr_db=gr, final=final, tried=len(built))
    best["seam"] = seam_report(o, best["N"])
    return o, dict(info, **best)


def trim_edges(x):
    """Trim leading silence to LEAD_KEEP_S and trailing silence (envelope 50 dB under the peak, +60 ms). The tail ends at the
    last stretch of at least 30 ms above the threshold, so the one-frame blip some mp3 decodes leave at the very end (volt_yay:
    -31 dBFS after 0.8 s of -77 dBFS) does not hold 0.8 s of silence in the clip."""
    mono = np.abs(x).max(axis=1)
    peak = float(mono.max())
    k = int(0.001 * SR)
    cs = np.concatenate([[0.0], np.cumsum(mono)])
    sm = (cs[k:] - cs[:-k]) / k
    thr_lead = max(peak * 10 ** (-40 / 20), 10 ** (-70 / 20))
    thr_tail = max(peak * 10 ** (-50 / 20), 10 ** (-70 / 20))
    i0 = int(np.argmax(sm > thr_lead))
    run = int(0.03 * SR)
    above = np.concatenate([[0.0], np.cumsum(sm > thr_tail)])
    held = np.nonzero(above[run:] - above[:-run] >= run)[0]                     # starts of 30 ms stretches above the threshold
    i1 = int(held[-1]) + run if len(held) else len(sm) - int(np.argmax(sm[::-1] > thr_tail))
    a = max(i0 - int(LEAD_KEEP_S * SR), 0)
    b = min(i1 + int(0.06 * SR), len(x))
    return x[a:b].copy()


def process_sfx(x):
    """x -> (clip float array at SFX_LUFS short-term, info)."""
    y = trim_edges(x)
    nf = min(int(TAIL_FADE_S * SR), len(y) // 4)
    fade = 0.5 * (1 + np.cos(np.linspace(0, math.pi, nf)))
    y[-nf:] *= fade[:, None]
    nin = min(int(0.003 * SR), len(y) // 8)
    y[:nin] *= np.linspace(0, 1, nin)[:, None]
    gain = SFX_LUFS - short_term_max(y)
    y = y * 10 ** (gain / 20)
    gr = 0.0
    if true_peak_db(y) > CEILING_DB:
        y, gr = limit(y, CEILING_DB, loop=False)
    return y, dict(gain_db=gain, gr_db=gr)


# ----------------------------------------------------------------------------------------------- choosing a take

def loop_quality(info, wav):
    """Numbers that rank the takes of one tier (higher is better) and the plain-words reasons."""
    s = info["seam"]
    ask_err = abs(info["loop_bpm"] - info["ask"]) if info.get("ask") else 0.0
    steady = float(np.std(lufs_of(_block_power(wav, int(3 * SR), SR))))
    ratio = s["spec_db"] / max(s["spec_p90"], 0.5)          # the wrap against the music's own bar lines (1 = as rough as the roughest 10 %)
    score = (info["rep"] - 0.25 * ratio - 0.03 * info["tim"] - 0.02 * ask_err - 0.1 * steady
             - 0.05 * max(0.0, s["bar_step_db"] - 1.5) - (0 if s["ok"] else 0.5) - (1.0 if info.get("vocals") else 0.0))
    return dict(score=score, steady=steady, ask_err=ask_err, ratio=ratio)


def sfx_quality(wav):
    """Fanfare / one-shot ranking: the shorter effective length, in half-second steps (a 40 ms difference is not a
    difference; a tie keeps the table's first take)."""
    return -round(len(wav) / SR * 2) / 2


def vocal_note(stem):
    v = load_vocals().get(stem)
    if v is None:
        return "not run"
    segs = v["segments"]
    if v["vocals"]:
        return "SPEECH? " + "; ".join(s["text"] for s in segs[:2])
    if not segs:
        return "none"
    texts = {s["text"] for s in segs}
    return f"hallucinated '{segs[0]['text'][:28]}' x{len(segs)}" if len(segs) > 2 and len(texts) <= 2 else f"none ('{segs[0]['text'][:20]}')"


def load_vocals():
    p = OUT_DIR / "vocal_check.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def flag_text(seam, rep=None):
    f = seam_flags(seam, rep)
    return " FLAG:" + ",".join(f) if f else ""


def fmt_row(cells, widths):
    return "  ".join(str(c).ljust(w) for c, w in zip(cells, widths))


def run(only=None, picks=None, stage=False):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    picks = picks or {}
    vocals = load_vocals()
    results = {}                     # stem -> dict(cue, kind, wav, info)
    for stem, (cue, kind, asset_id, ask, text) in SOURCES.items():
        if only and stem not in only:
            continue
        mp3 = SRC_DIR / f"{stem}.mp3"
        if not mp3.exists():
            print(f"{stem:14} no mp3 yet ({mp3.name}), skipped")
            continue
        x = decode(mp3)
        if kind == "music":
            wav, info = process_music(x, ask)
            if wav is None:
                print(f"{stem:14} NO LOOP FOUND ({info})")
                continue
            info["ask"] = ask
            info["vocals"] = bool(vocals.get(stem, {}).get("vocals"))
            info["q"] = loop_quality(info, wav)
        else:
            wav, info = process_sfx(x)
            info["q"] = dict(score=sfx_quality(wav))
        results[stem] = dict(cue=cue, kind=kind, wav=wav, info=info, text=text, asset=asset_id)

    # choose a take per cue
    chosen, written = {}, {}
    for cue in cues():
        stems = [s for s in cue_stems(cue) if s in results]
        if not stems:
            continue
        want = picks.get(cue)
        order = sorted(stems, key=lambda s: -results[s]["info"]["q"]["score"])
        if want:
            order = [s for s in stems if s.endswith("_" + want)] + [s for s in order if not s.endswith("_" + want)]
        chosen[cue] = order[0]
        for rank, stem in enumerate(order):
            name = f"{cue}.wav" if rank == 0 else f"{cue}_alt.wav"
            if rank > 1:
                continue
            write_wav(OUT_DIR / name, results[stem]["wav"], name)
            written[name] = stem

    # read every file back and measure THE ARTIFACT
    table = []
    for name, stem in sorted(written.items()):
        r = results[stem]
        w = read_wav(OUT_DIR / name)
        n_samples = len(w)
        r["file"] = name
        r["dur"] = n_samples / SR
        r["tp"] = true_peak_db(w)
        if r["kind"] == "music":
            r["lufs"] = integrated_lufs(w)
            r["seam"] = seam_report(w, r["info"]["N"])
        else:
            r["lufs"] = short_term_max(w)
            mag = np.abs(w).max(axis=1)
            lead = int(np.argmax(mag > mag.max() * 10 ** (-40 / 20)))     # silence before the sound, 40 dB under its peak
            r["lead_ms"] = lead / SR * 1000
        table.append((name, stem, r))
    print_table(table, chosen)
    write_listen(results, chosen, written)
    if stage:
        stage_files()
    return results, chosen


def stage_files():
    """Copy the wavs that get imported (every <cue>.wav, no _alt, no ice_crack) to %TEMP%\fnm_mint, a short path for the
    GUI import dialog. Returns the folder."""
    dst = Path(tempfile.gettempdir()) / "fnm_mint"
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir()
    for cue in cues():
        if cue != "ice_crack" and (OUT_DIR / f"{cue}.wav").exists():
            shutil.copy(OUT_DIR / f"{cue}.wav", dst / f"{cue}.wav")
    print(f"staged {sorted(p.name for p in dst.iterdir())} in {dst}")
    return dst


def print_table(table, chosen):
    print()
    hdr = ["file", "source", "dur s", "bars", "BPM est/loop/ask", "rep", "rho", "bar step dB", "seam spec dB (int. p90/max)", "step", "LUFS", "TP dBTP", "GR dB", "take"]
    rows = []
    for name, stem, r in table:
        i = r["info"]
        if r["kind"] == "music":
            s = r["seam"]
            rows.append([name, stem, f"{r['dur']:.3f}", i["N"], f"{i['bpm']:.2f}/{i['loop_bpm']:.2f}/{i['ask']}", f"{i['rep']:.2f}",
                         f"{i['rho']:.2f}", f"{s['bar_step_db']:.2f}", f"{s['spec_db']:.2f} ({s['spec_p90']:.2f}/{s['spec_max']:.2f})" + flag_text(s, i["rep"]),
                         f"{s['step']:.2f}", f"{r['lufs']:.2f}", f"{r['tp']:.2f}", f"{i['gr_db']:.2f}", "IN" if chosen[SOURCES[stem][0]] == stem else "alt"])
        else:
            rows.append([name, stem, f"{r['dur']:.3f}", "-", "-", "-", "-", "-", f"lead {r['lead_ms']:.1f} ms", "-", f"{r['lufs']:.2f} st",
                         f"{r['tp']:.2f}", f"{i['gr_db']:.2f}", "IN" if chosen[SOURCES[stem][0]] == stem else "alt"])
    widths = [max(len(str(c)) for c in col) for col in zip(hdr, *rows)]
    print(fmt_row(hdr, widths))
    for row in rows:
        print(fmt_row(row, widths))


def write_listen(results, chosen, written):
    lines = ["# Mint audio: what to listen to", "",
             "Written by `tools/make_mint_audio.py` (rerun it to refresh). **Aaron's ear has not judged any of this.** The numbers below",
             "say what could be measured: loop seam, loudness, peak, tempo. They do not say it sounds good. The wavs are not in git",
             "(`.gitignore`); the mp3s in `art/audio/mint/` are, and the script rebuilds every wav byte for byte.", "",
             "Beds are normalised to -18 LUFS integrated (they play at device volume 0.5), true peak <= -1 dBTP. One-shots to -16 LUFS",
             "short-term (loudest 3 s). To prefer the other take: `python tools/make_mint_audio.py --pick music_t3=b`, reimport.", "",
             "`rep` is how closely the two bars that get crossfaded resemble each other (1 = identical rhythm); `seam spec` is the spectral",
             "step across the wrap against the music's own bar lines (interior 90th percentile / maximum); FLAG lists what failed.",
             "Whisper = `tools/audio/mint/vocal_check.py` (small.en): `none` heard no speech; `hallucinated` means it printed the same",
             "line every few seconds at no_speech >= 0.8, which is what it does on instruments; it is not evidence of singing.", "",
             "| file | take in | other take | length s | bars | tempo (found / ask) | rep | seam spec dB (int. p90/max) | LUFS | TP | Whisper | the ask |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for cue in cues():
        if cue not in chosen:
            continue
        stem = chosen[cue]
        r = results[stem]
        others = [s for s in cue_stems(cue) if s != stem and s in results]
        i = r["info"]
        name = f"{cue}.wav"
        if "dur" not in r:
            continue
        if r["kind"] == "music":
            s = r["seam"]
            lines.append(f"| {name} | {stem} | {', '.join(others) or '-'} | {r['dur']:.2f} | {i['N']} | {i['loop_bpm']:.2f} / {i['ask']} | {i['rep']:.2f} | "
                         f"{s['spec_db']:.2f} ({s['spec_p90']:.2f}/{s['spec_max']:.2f}){flag_text(s, i['rep'])} | {r['lufs']:.1f} | {r['tp']:.2f} | {vocal_note(stem)} | {r['text']} |")
        else:
            lines.append(f"| {name} | {stem} | {', '.join(others) or '-'} | {r['dur']:.2f} | - | - | - | - | {r['lufs']:.1f} st | {r['tp']:.2f} | - | {r['text']} |")
    lines += ["", "## Why each take was chosen", ""]
    for cue in cues():
        stems = [s for s in cue_stems(cue) if s in results]
        if len(stems) < 2:
            continue
        lines.append(f"- **{cue}**: " + "; ".join(
            f"{s} score {results[s]['info']['q']['score']:.2f}" + (" (IN)" if chosen[cue] == s else " (alt)") for s in stems)
            + ". " + choice_reason(cue, stems, results, chosen))
    lines += [""]
    (OUT_DIR / "LISTEN.md").write_text("\n".join(lines), encoding="utf-8")


def choice_reason(cue, stems, results, chosen):
    a = results[chosen[cue]]["info"]
    b = results[[s for s in stems if s != chosen[cue]][0]]["info"]
    other = [s for s in stems if s != chosen[cue]][0]
    gap = results[chosen[cue]]["info"]["q"]["score"] - results[other]["info"]["q"]["score"]
    if results[chosen[cue]]["kind"] != "music":
        la, lb = len(results[chosen[cue]]["wav"]) / SR, len(results[other]["wav"]) / SR
        if abs(la - lb) < 0.3:
            return f"Nothing measurable separates them ({la:.2f} s vs {lb:.2f} s, both at the same loudness): listen."
        return f"Shorter effective length ({la:.2f} s vs {lb:.2f} s), so it runs into less of the cue that follows it; the rest is for the ear."
    qa, qb = a["q"], b["q"]
    close = " Too close to call by the numbers: treat the pick as a coin flip and listen." if gap < 0.05 else ""
    return (f"Rep (repeatability of the crossfaded bars) {a['rep']:.2f} vs {b['rep']:.2f}; timbre distance of the two crossfaded bars {a['tim']:.1f} vs {b['tim']:.1f} dB; "
            f"level steadiness {qa['steady']:.2f} vs {qb['steady']:.2f} LU; tempo {a['loop_bpm']:.1f} vs {b['loop_bpm']:.1f} BPM; "
            f"seam {flag_text(a['seam'], a['rep']).strip() or 'clean'} vs {flag_text(b['seam'], b['rep']).strip() or 'clean'}.{close}")


# ----------------------------------------------------------------------------------------------- the disproof

def bad_loops(stem):
    """Score deliberately bad loop points of one take and print what the seam score says. A good loop is shown first."""
    cue, kind, _, ask, _ = SOURCES[stem]
    x = decode(SRC_DIR / f"{stem}.mp3")
    best, info = find_loop(x, ask)
    mono = x.mean(axis=1)
    bar = info["bar_s"] * SR
    print(f"{stem}: tempo {info['bpm']:.2f}, found loop S={best['S'] / SR:.3f}s N={best['N']} L={best['L'] / SR:.4f}s rep={best['rep']:.2f}")
    cases = {
        "good (found)": (best["S"], best["L"], best["N"]),
        "L off by a quarter beat": (best["S"], best["L"] + int(bar / 16), best["N"]),
        "L off by half a beat": (best["S"], best["L"] + int(bar / 8), best["N"]),
        "start in the file's first 0.2 s, end in its last bar": (0, len(x) - int(bar) - int(0.1 * SR) - 0, best["N"]),
        "N-1 bars but the audio runs on (wrong phrase)": (best["S"], best["L"] - int(bar), best["N"] - 1),
    }
    for name, (S, L, N) in cases.items():
        X = best["X"]
        if S + L + X > len(x):
            L = len(x) - S - X
        a, b = mono[S:S + X], mono[S + L:S + L + X]
        rho = float(np.dot(a - a.mean(), b - b.mean()) / (np.linalg.norm(a - a.mean()) * np.linalg.norm(b - b.mean()) + 1e-12))
        o = make_loop(x, S, L, X, rho)
        rep = repeat_lag(amp_env(mono), S, L, X, 1 * EH)   # correlation at THIS L (reach +-1 step)
        s = seam_report(o, N)
        print(f"  {name:55} rep={rep[1] if rep else float('nan'):5.2f} bar step {s['bar_step_db']:5.2f} dB, spec {s['spec_db']:5.2f} dB "
              f"(interior p90 {s['spec_p90']:5.2f}, max {s['spec_max']:5.2f}) -> {flag_text(s, rep[1] if rep else None).strip() or 'ok'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("sources", nargs="*", help="source stems to process (default: all with an mp3)")
    ap.add_argument("--pick", action="append", default=[], metavar="CUE=a|b", help="force a take, e.g. music_t3=b")
    ap.add_argument("--stage", action="store_true", help="copy the chosen wavs to %%TEMP%%\\fnm_mint for the GUI import")
    ap.add_argument("--stage-only", action="store_true", help="just copy the existing chosen wavs to %%TEMP%%\fnm_mint")
    ap.add_argument("--bad-loops", metavar="STEM", help="score deliberately bad loop points of one take (the disproof)")
    a = ap.parse_args()
    if a.bad_loops:
        bad_loops(a.bad_loops)
        return
    if a.stage_only:
        stage_files()
        return
    picks = dict(p.split("=", 1) for p in a.pick)
    run(set(a.sources) or None, picks, a.stage)


if __name__ == "__main__":
    main()
