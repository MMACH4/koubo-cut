#!/usr/bin/env python3
"""压缩到统一 1080P：横版 1920x1080 / 竖版 1080x1920。

用法: preprocess.py <原片> [--out-dir DIR]
输出: 压缩片路径 + 方向（H/V），供下游使用。
"""
import argparse
import os
import subprocess
import sys

FFMPEG = os.environ.get("KOUBO_FFMPEG", "/Applications/Televzr.app/Contents/Resources/bin_mac_x64/ffmpeg")
FFPROBE = os.environ.get("KOUBO_FFPROBE", "/Applications/Televzr.app/Contents/Resources/bin_mac_x64/ffprobe")


def probe(path: str) -> dict:
    cmd = [FFPROBE, "-v", "error", "-show_entries",
           "format=duration:stream=codec_type,width,height,r_frame_rate,rotation",
           "-of", "json", path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-1000:])
    import json
    d = json.loads(r.stdout)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    # 手机竖拍常带旋转元数据：旋转 ±90° 时实际显示尺寸是宽高互换
    try:
        rot = int(v.get("rotation", 0) or 0) % 360
    except (TypeError, ValueError):
        rot = 0
    if rot in (90, 270):
        v["width"], v["height"] = v["height"], v["width"]
    fps_s = v.get("r_frame_rate", "25/1")
    try:
        num, den = fps_s.split("/")
        fps = float(num) / max(float(den), 1)
    except Exception:
        fps = 25.0
    return {"width": int(v.get("width", 1920)), "height": int(v.get("height", 1080)),
            "duration": float(d.get("format", {}).get("duration", 0)), "fps": fps}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()
    info = probe(args.video)
    orientation = "V" if info["height"] >= info["width"] else "H"
    stem = os.path.splitext(os.path.basename(args.video))[0]
    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.video))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{stem}-{'1080x1920' if orientation == 'V' else '1920x1080'}.mp4")
    scale = "1080:1920" if orientation == "V" else "1920:1080"
    fps = round(info["fps"], 3)
    cmd = [FFMPEG, "-y", "-i", args.video,
           "-vf", f"scale={scale}:flags=lanczos",
           "-c:v", "libx264", "-preset", "faster", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-r", str(fps), out]
    print("compressing...", " ".join(cmd[-9:]))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:])
        return 1
    print(f"ORIENTATION={orientation}")
    print(f"OUTPUT={out}")
    print(f"INFO={info}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
