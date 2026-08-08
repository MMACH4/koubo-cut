#!/usr/bin/env python3
"""生成 4 种口播包装音效：whoosh/pop/ding/boom。

用法: make_sfx.py [--out-dir DIR]  默认 ~/.cache/koubo/sfx
"""
import argparse
import os
import subprocess
import sys

FFMPEG = os.environ.get("KOUBO_FFMPEG", "/Applications/Televzr.app/Contents/Resources/bin_mac_x64/ffmpeg")

SFX = {
    "whoosh.wav": [
        "-f", "lavfi", "-i", "anoisesrc=colour=pink:duration=0.6:sample_rate=48000",
        "-af", "highpass=f=400,lowpass=f=8000,afade=t=in:st=0:d=0.2,afade=t=out:st=0.35:d=0.25,volume=0.7",
    ],
    "pop.wav": [
        "-f", "lavfi", "-i", "aevalsrc='0.8*sin(2*PI*900*t)*exp(-25*t)':duration=0.25:sample_rate=48000",
    ],
    "ding.wav": [
        "-f", "lavfi", "-i",
        "aevalsrc='0.55*sin(2*PI*880*t)*exp(-4.5*t)+0.25*sin(2*PI*1320*t)*exp(-6*t)+0.15*sin(2*PI*1760*t)*exp(-8*t)':duration=1.1:sample_rate=48000",
        "-af", "afade=t=out:st=0.9:d=0.2",
    ],
    "boom.wav": [
        "-f", "lavfi", "-i", "aevalsrc='0.9*sin(2*PI*95*t)*exp(-9*t)+0.4*sin(2*PI*50*t)*exp(-7*t)':duration=0.7:sample_rate=48000",
    ],
}


def ensure_sfx(out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    for name, args in SFX.items():
        out = os.path.join(out_dir, name)
        if os.path.exists(out):
            continue
        subprocess.run([FFMPEG, "-y", *args, "-c:a", "pcm_s16le", out],
                       capture_output=True, check=True)
    return out_dir


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.expanduser("~/.cache/koubo/sfx"))
    args = ap.parse_args()
    out = ensure_sfx(args.out_dir)
    print("SFX_DIR=" + out)
    for name in SFX:
        print(" ", name, os.path.getsize(os.path.join(out, name)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
