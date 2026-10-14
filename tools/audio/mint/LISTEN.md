# Mint audio: what to listen to

Written by `tools/make_mint_audio.py` (rerun it to refresh). **Aaron's ear has not judged any of this.** The numbers below
say what could be measured: loop seam, loudness, peak, tempo. They do not say it sounds good. The wavs are not in git
(`.gitignore`); the mp3s in `art/audio/mint/` are, and the script rebuilds every wav byte for byte.

Beds are normalised to -18 LUFS integrated (they play at device volume 0.5), true peak <= -1 dBTP. One-shots to -16 LUFS
short-term (loudest 3 s). To prefer the other take: `python tools/make_mint_audio.py --pick music_t3=b`, reimport.

`rep` is how closely the two bars that get crossfaded resemble each other (1 = identical rhythm); `seam spec` is the spectral
step across the wrap against the music's own bar lines (interior 90th percentile / maximum); FLAG lists what failed.
Whisper = `tools/audio/mint/vocal_check.py` (small.en): `none` heard no speech; `hallucinated` means it printed the same
line every few seconds at no_speech >= 0.8, which is what it does on instruments; it is not evidence of singing.

| file | take in | other take | length s | bars | tempo (found / ask) | rep | seam spec dB (int. p90/max) | LUFS | TP | Whisper | the ask |
|---|---|---|---|---|---|---|---|---|---|---|---|
| music_t1.wav | music_t1_b | music_t1_a | 56.00 | 28 | 120.00 / 120 | 0.99 | 5.56 (8.97/11.25) | -18.0 | -3.46 | none | calmest: bongos, kalimba |
| music_t2.wav | music_t2_a | music_t2_b | 24.00 | 12 | 120.00 / 120 | 0.93 | 2.26 (5.18/6.01) | -18.0 | -2.32 | hallucinated 'I'm going to show you how to' x12 | light kit, synth arp, pizzicato |
| music_t3.wav | music_t3_b | music_t3_a | 16.00 | 8 | 120.00 / 120 | 0.86 | 3.55 (5.43/5.62) | -18.0 | -3.68 | none | icy ridge, bells |
| music_t4.wav | music_t4_b | music_t4_a | 16.00 | 8 | 120.00 / 120 | 0.80 | 3.90 (8.75/9.20) | -18.0 | -2.45 | none | intense: toms, distorted bass |
| music_t5.wav | music_t5_a | music_t5_b | 48.00 | 24 | 120.00 / 120 | 0.78 | 2.56 (3.46/3.66) | -18.0 | -4.69 | none | peak: orchestra, choir pads |
| music_boss.wav | music_boss_a | music_boss_b | 34.29 | 20 | 140.00 / 140 | 0.90 | 2.89 (7.70/8.69) | -18.0 | -1.73 | none | boss fight: taiko, low brass, choir |
| music_menu.wav | music_menu | - | 17.45 | 8 | 110.00 / 110 | 0.60 | 6.69 (23.01/28.07) | -18.0 | -4.68 | none | game-show lobby loop for the grade picker |
| finish.wav | fanfare_a | fanfare_b | 5.46 | - | - | - | - | -16.0 st | -4.28 | - | 7 s victory fanfare, brass + timpani |
| door_open.wav | portal_whoosh | - | 1.13 | - | - | - | - | -16.0 st | -2.85 | - | 1.5 s sparkle whoosh |
| volt_yay.wav | volt_yay | - | 0.38 | - | - | - | - | -16.0 st | -8.72 | - | 1.2 s happy robot chirp |
| volt_hmm.wav | volt_hmm | - | 1.17 | - | - | - | - | -16.0 st | -5.20 | - | 1.5 s thinking robot warble |
| volt_oops.wav | volt_oops | - | 1.14 | - | - | - | - | -16.0 st | -2.52 | - | 1.2 s Volt 'uh-oh' |
| titan_roar.wav | titan_roar_b | titan_roar_a | 2.11 | - | - | - | - | -16.0 st | -5.15 | - | 3 s titan roar |
| crowd_cheer.wav | crowd_cheer | - | 3.99 | - | - | - | - | -16.0 st | -5.87 | - | 4 s crowd cheer |
| crowd_aww.wav | crowd_aww | - | 2.19 | - | - | - | - | -16.0 st | -3.47 | - | 2.5 s crowd 'aww' |
| ice_crack.wav | ice_crack | - | 1.47 | - | - | - | - | -19.0 st | -1.00 | - | 2 s ice crack (no cue yet; not imported) |

## Why each take was chosen

- **music_t1**: music_t1_a score 0.35 (alt); music_t1_b score 0.64 (IN). Rep (repeatability of the crossfaded bars) 0.99 vs 0.82; timbre distance of the two crossfaded bars 1.7 vs 1.1 dB; level steadiness 1.42 vs 1.12 LU; tempo 120.0 vs 120.0 BPM; seam clean vs clean.
- **music_t2**: music_t2_a score 0.60 (IN); music_t2_b score 0.60 (alt). Rep (repeatability of the crossfaded bars) 0.93 vs 0.89; timbre distance of the two crossfaded bars 1.8 vs 1.7 dB; level steadiness 1.70 vs 0.41 LU; tempo 120.0 vs 120.0 BPM; seam clean vs clean. Too close to call by the numbers: treat the pick as a coin flip and listen.
- **music_t3**: music_t3_a score 0.52 (alt); music_t3_b score 0.57 (IN). Rep (repeatability of the crossfaded bars) 0.86 vs 0.86; timbre distance of the two crossfaded bars 2.4 vs 1.1 dB; level steadiness 0.53 vs 0.82 LU; tempo 120.0 vs 120.0 BPM; seam clean vs clean.
- **music_t4**: music_t4_a score -0.33 (alt); music_t4_b score 0.57 (IN). Rep (repeatability of the crossfaded bars) 0.80 vs 0.48; timbre distance of the two crossfaded bars 1.1 vs 0.3 dB; level steadiness 0.90 vs 0.74 LU; tempo 120.0 vs 144.0 BPM; seam clean vs FLAG:rep.
- **music_t5**: music_t5_a score 0.51 (IN); music_t5_b score -0.03 (alt). Rep (repeatability of the crossfaded bars) 0.78 vs 0.40; timbre distance of the two crossfaded bars 0.9 vs 4.8 dB; level steadiness 0.57 vs 0.52 LU; tempo 120.0 vs 120.0 BPM; seam clean vs FLAG:rep.
- **music_boss**: music_boss_a score 0.65 (IN); music_boss_b score 0.58 (alt). Rep (repeatability of the crossfaded bars) 0.90 vs 0.94; timbre distance of the two crossfaded bars 1.8 vs 1.1 dB; level steadiness 0.99 vs 0.90 LU; tempo 140.0 vs 140.0 BPM; seam clean vs clean.
- **finish**: fanfare_a score -5.50 (IN); fanfare_b score -5.50 (alt). Nothing measurable separates them (5.46 s vs 5.42 s, both at the same loudness): listen.
- **titan_roar**: titan_roar_a score -2.50 (alt); titan_roar_b score -2.00 (IN). Shorter effective length (2.11 s vs 2.48 s), so it runs into less of the cue that follows it; the rest is for the ear.
