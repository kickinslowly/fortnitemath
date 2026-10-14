"""Is there singing or speech in the Mint music beds? A Whisper pass over every music mp3 in art/audio/mint/.

Needs faster-whisper, which the repo's venv does not have; use the michael project's:

    "D:/PyCharm Projects/michael/.venv/Scripts/python" tools/audio/mint/vocal_check.py

Writes tools/audio/mint/vocal_check.json (read by tools/make_mint_audio.py when it ranks the takes of a tier). Whisper
invents words for music ("Thank you.", "Oh."), so a segment only counts as vocals when it is confident it is speech
(no_speech_prob < 0.4), has an average log-probability above -1.0 and at least two words of three letters or more. A
wordless choir ("ahh") therefore does not count; what Whisper heard is kept in the json for the ear to check.
CPU, int8: it never touches the GPU the editor is using.
"""
import json
import re
import sys
from pathlib import Path

from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "art" / "audio" / "mint"
OUT = Path(__file__).with_name("vocal_check.json")


def main():
    stems = sorted(p.stem for p in SRC.glob("music_*.mp3"))
    if len(sys.argv) > 1:
        stems = [s for s in stems if s in sys.argv[1:]]
    result = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    for stem in stems:
        segments, _ = model.transcribe(str(SRC / f"{stem}.mp3"), language="en", condition_on_previous_text=False,
                                       vad_filter=False, temperature=0.0)
        segs = [dict(start=round(s.start, 1), end=round(s.end, 1), text=s.text.strip(), no_speech=round(s.no_speech_prob, 2),
                     logprob=round(s.avg_logprob, 2)) for s in segments]
        voiced = [s for s in segs if s["no_speech"] < 0.4 and s["logprob"] > -1.0
                  and len(re.findall(r"[A-Za-z]{3,}", s["text"])) >= 2]
        result[stem] = dict(vocals=bool(voiced), segments=segs)
        print(f"{stem:14} vocals={bool(voiced)}  segments={len(segs)}  " + " | ".join(s["text"] for s in segs[:4]), flush=True)
        OUT.write_text(json.dumps(result, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
