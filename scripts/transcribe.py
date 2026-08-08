#!/usr/bin/env python3
"""faster-whisper 转写（中文、字级时间戳）。

用法: transcribe.py <视频> --out-dir DIR
产出: transcript.json（含 words 字级时间戳）、transcript.srt
"""
import argparse
import json
import os
import subprocess
import sys

FFMPEG = os.environ.get("KOUBO_FFMPEG", "/Applications/Televzr.app/Contents/Resources/bin_mac_x64/ffmpeg")
MODEL_DIR = os.environ.get("KOUBO_WHISPER_MODEL", os.path.expanduser("~/.cache/faster-whisper/small"))


def fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    wav = os.path.join(args.out_dir, "audio_16k.wav")
    subprocess.run([FFMPEG, "-y", "-i", args.video, "-ac", "1", "-ar", "16000", "-vn", wav],
                   capture_output=True, check=True)

    from faster_whisper import WhisperModel
    model = WhisperModel(MODEL_DIR, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        wav, language="zh", beam_size=5, vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=400),
        word_timestamps=True, condition_on_previous_text=True,
    )
    items = []
    for seg in segments:
        words = [{"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3)}
                 for w in (seg.words or [])]
        items.append({"start": round(seg.start, 3), "end": round(seg.end, 3),
                      "text": seg.text.strip(), "words": words})
    with open(os.path.join(args.out_dir, "transcript.json"), "w", encoding="utf-8") as f:
        json.dump({"language": info.language, "segments": items}, f, ensure_ascii=False, indent=1)
    lines = []
    for i, seg in enumerate(items, 1):
        lines += [str(i), f"{fmt_ts(seg['start'])} --> {fmt_ts(seg['end'])}", seg["text"], ""]
    with open(os.path.join(args.out_dir, "transcript.srt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    for seg in items:
        print(f"[{seg['start']:7.2f} -> {seg['end']:7.2f}] {seg['text']}")
    print(f"segments: {len(items)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
