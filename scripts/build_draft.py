#!/usr/bin/env python3
"""生成剪映粗剪工程：原片按剪辑点切段（每段独立出入点）+ 字幕/标题/花字/音效。

用法: build_draft.py --plan plan.json --work-dir DIR
plan.json 结构:
{
  "name": "2万打卡-cut",
  "orientation": "V",
  "video": "/abs/compressed.mp4",
  "segments": [{"src": 1.58, "end": 3.04, "text": "..."}],   // src=源片开始秒
  "titles":  [{"text": "...", "start": 55.0, "end": 60.5}],
  "huas":    [{"text": "...", "highlights": [{"word": "...", "color": "red"}],
               "start": 38.0, "end": 41.0, "size": 10.0}],
  "emphases": [{"keyword": "...", "color": "red"}]
}
所有包装自动配音效：标题→whoosh，花字→boom/ding，重点字幕→ding。
"""
import argparse
import json
import os
import shutil
import sys

# jianying-editor skill 环境
SKILL_ROOT = os.getenv("JY_SKILL_ROOT", os.path.expanduser("~/.codex/skills/jianying-editor"))
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts", "vendor"))

from pyJianYingDraft import (  # noqa: E402
    ClipSettings, FilterType, FontType, Keyframe as KF, KeyframeProperty as KP,
    TextBorder, TextShadow, TextStyle, Timerange, TrackType,
)
from jy_wrapper import JyProject  # noqa: E402

GOLD = (1.0, 0.8, 0.22)
WHITE = (1.0, 1.0, 1.0)
RED = (1.0, 0.22, 0.22)
COLORS = {"red": RED, "gold": GOLD, "white": WHITE}


def us(sec: float) -> int:
    return int(sec * 1_000_000)


SUB_BREAK = set("，。、！？；：,.!?;: 的了在是就你我他这那和与")


def split_sub(text: str, max_len: int, keep: str = None) -> list:
    text = text.strip()
    if len(text) <= max_len:
        return [text]
    if keep and keep in text:
        wi = text.find(keep)
        if 0 < wi < max_len:
            return split_sub(text[:wi], max_len) + split_sub(text[wi:], max_len, keep)
        if wi >= max_len:
            return split_sub(text[:wi], max_len) + split_sub(text[wi:], max_len, keep)
    parts = []
    while len(text) > max_len:
        seg = text[:max_len]
        cut, mid = -1, max_len // 2
        for i in range(mid, len(seg)):
            if seg[i] in SUB_BREAK:
                cut = i
                break
        if cut < 0:
            for i in range(len(seg) - 1, mid - 1, -1):
                if seg[i] in SUB_BREAK:
                    cut = i
                    break
        if cut > 0:
            parts.append(seg[: cut + 1])
            text = text[cut + 1:]
        else:
            parts.append(seg)
            text = text[max_len:]
    if text:
        parts.append(text)
    return parts


def add_hua(project, text, highlights, start, end, size, y):
    # 统一字号：去掉 highlight 里的 size 覆盖，避免同一行文字大小不一/变形
    # 全句先铺一层基础金色样式，未高亮文字才不会丢失样式/撑大换行
    hl = [{"word": text, "color": GOLD}] + [{k: v for k, v in h.items() if k != "size"} for h in highlights]
    seg = project.add_rich_text(
        text, highlights=hl,
        start_time=us(start), duration=us(end - start), track_name="HuaZi",
        style=TextStyle(size=size, color=GOLD, bold=True, align=1, auto_wrapping=True, max_line_width=0.92),
        font=FontType.三极极宋超粗,
        border=TextBorder(color=(0, 0, 0), alpha=1.0, width=46),
        shadow=TextShadow(color=(0, 0, 0), alpha=0.9, diffuse=40, distance=6, angle=-45),
        clip_settings=ClipSettings(transform_y=y),
    )
    if seg is None:
        return
    seg.add_keyframe(KP.alpha, 0, 0.0)
    seg.add_keyframe(KP.alpha, us(0.12), 1.0, **KF.EASE_OUT)
    for t, v in ((0, 1.9), (0.3, 0.92), (0.5, 1.05), (0.7, 1.0)):
        seg.add_keyframe(KP.uniform_scale, us(t), v, **KF.EASE_OUT)
    seg.add_keyframe(KP.rotation, 0, -6, **KF.EASE_OUT)
    seg.add_keyframe(KP.rotation, us(0.45), 0, **KF.EASE_OUT)


def add_title(project, text, start, end, size, y):
    seg = project.add_text_simple(
        text, start_time=us(start), duration=us(end - start), track_name="Titles",
        style=TextStyle(size=size, color=GOLD, bold=True, align=1, auto_wrapping=True, max_line_width=0.9),
        font=FontType.三极极宋超粗,
        border=TextBorder(color=(0, 0, 0), alpha=1.0, width=34),
        shadow=TextShadow(color=(0, 0, 0), alpha=0.8, diffuse=10, distance=4, angle=-45),
        clip_settings=ClipSettings(transform_y=y),
        anim_in="向上滑动", anim_out="向上溶解",
    )
    if seg is not None:
        for t, v in ((0, 1.35), (0.25, 0.97), (0.45, 1.0)):
            seg.add_keyframe(KP.uniform_scale, us(t), v, **KF.EASE_OUT)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--work-dir", required=True)
    args = ap.parse_args()
    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)

    vertical = plan.get("orientation", "V") == "V"
    w, h = (1080, 1920) if vertical else (1920, 1080)
    project = JyProject(plan["name"], width=w, height=h, overwrite=True)
    assets_dir = os.path.join(project.draft_dir, "素材")
    os.makedirs(assets_dir, exist_ok=True)
    video_local = os.path.join(assets_dir, os.path.basename(plan["video"]))
    shutil.copy(plan["video"], video_local)

    # 音效
    sfx_dir = plan.get("sfx_dir") or os.path.expanduser("~/.cache/koubo/sfx")
    if not os.path.exists(os.path.join(sfx_dir, "whoosh.wav")):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from make_sfx import ensure_sfx
        ensure_sfx(sfx_dir)
    local_sfx = os.path.join(assets_dir, "sfx")
    os.makedirs(local_sfx, exist_ok=True)
    for name in os.listdir(sfx_dir):
        if name.endswith(".wav"):
            shutil.copy(os.path.join(sfx_dir, name), os.path.join(local_sfx, name))

    # 1. 主视频：按剪辑点切段（每段独立出入点）
    segs = plan["segments"]
    t = 0.0
    video_segs = []
    for s in segs:
        dur = s["end"] - s["src"]
        seg = project.add_media_safe(
            video_local, start_time=us(t), duration=us(dur),
            track_name="VideoTrack", source_start=us(s["src"]),
        )
        if seg is not None:
            video_segs.append({"start": t, "end": t + dur})
        t += dur
    print(f"video segments: {len(video_segs)} total {t:.2f}s")
    # 固定滤镜（亮肤，综艺感提亮；剪映打开时联网加载，可手动调强度）
    project.script.add_track(TrackType.filter, "滤镜")
    project.script.add_filter(FilterType.亮肤, Timerange(0, us(t)), intensity=45)

    # 2. 字幕（拆段 + 重点高亮）
    sub_size, sub_y = (8.5, -0.536) if vertical else (6.5, -0.8)
    emph_size, max_len = (9.5, 12) if vertical else (7.5, 15)
    sub_shadow = TextShadow(color=(0, 0, 0), alpha=1.0, diffuse=50, distance=3, angle=-45)
    sub_clip = ClipSettings(transform_y=sub_y)
    emph_map = plan.get("emphases") or []
    hua_windows = [(hua["start"], hua["end"]) for hua in plan.get("huas", [])]

    def _overlap(a, b):
        return a[0] < b[1] and b[0] < a[1]

    # 用累计时间轴重算（segments 顺序即时间轴顺序）
    tt = 0.0
    entries = []
    for s in segs:
        text = s["text"]
        emph = next((e for e in emph_map if e["keyword"] in text), None)
        keep = emph["keyword"] if emph else None
        parts = split_sub(text, max_len, keep)
        total = max(len(text), 1)
        dur = s["end"] - s["src"]
        for part in parts:
            pdur = dur * len(part) / total
            e = emph if (emph and emph["keyword"] in part) else None
            entries.append({"text": part, "start": tt, "end": tt + pdur, "emph": e})
            tt += pdur
    # 花字出现时隐藏重叠的常规字幕
    entries = [e for e in entries if not any(_overlap((e["start"], e["end"]), w) for w in hua_windows)]
    emph_times = []
    for e in entries:
        if e["emph"]:
            color = COLORS.get(e["emph"]["color"], GOLD)
            seg = project.add_rich_text(
                e["text"], highlights=[
                    {"word": e["text"], "color": WHITE},
                    {"word": e["emph"]["keyword"], "color": color, "bold": True, "size": emph_size + 1.5},
                ],
                start_time=us(e["start"]), duration=us(e["end"] - e["start"]),
                track_name="Subtitles",
                style=TextStyle(size=emph_size, color=WHITE, bold=True, align=1,
                                auto_wrapping=True, max_line_width=0.86),
                font=FontType.三极极宋超粗, border=None, shadow=sub_shadow, clip_settings=sub_clip,
            )
            if seg is not None:
                seg.add_keyframe(KP.uniform_scale, 0, 1.1, **KF.EASE_OUT)
                seg.add_keyframe(KP.uniform_scale, us(0.35), 1.0, **KF.EASE_OUT)
            emph_times.append(e["start"])
        else:
            project.add_text_simple(
                e["text"], start_time=us(e["start"]), duration=us(e["end"] - e["start"]),
                track_name="Subtitles",
                style=TextStyle(size=sub_size, color=WHITE, bold=True, align=1,
                                auto_wrapping=True, max_line_width=0.86),
                font=FontType.三极极宋超粗, border=None, shadow=sub_shadow, clip_settings=sub_clip,
            )
    print(f"subtitles: {len(entries)}, emphasis: {len(emph_times)}")

    # 3. 标题 + 花字
    title_size, title_y = (7.5, -0.453) if vertical else (6.5, -0.60)
    hua_y = -0.430 if vertical else -0.60  # 竖版 UI y=-826，比字幕高
    def_hua_size = 13.0 if vertical else 10.0
    sfx_plan = []
    for ttl in plan.get("titles", []):
        add_title(project, ttl["text"], ttl["start"], ttl["end"], title_size, title_y)
        sfx_plan.append((ttl["start"], "whoosh.wav", 0.55))
    for i, hua in enumerate(plan.get("huas", [])):
        hl = [{"word": x["word"], "color": COLORS.get(x.get("color", "red"), RED),
               "bold": True, "size": hua.get("size", def_hua_size) + 1.5} for x in hua["highlights"]]
        add_hua(project, hua["text"], hl, hua["start"], hua["end"], hua.get("size", def_hua_size), hua_y)
        sfx_plan.append((hua["start"], "boom.wav" if i % 2 == 0 else "ding.wav", 0.7))
    for ts in emph_times:
        sfx_plan.append((ts, "ding.wav", 0.6))

    # 4. 音效
    for ts, name, vol in sorted(sfx_plan):
        seg = project.add_media_safe(os.path.join(local_sfx, name),
                                     start_time=us(ts), track_name="SFX")
        if seg is not None:
            seg.volume = vol
    print(f"sfx: {len(sfx_plan)}")

    project.save()
    print("DRAFT_PATH", os.path.join(project.root, project.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
