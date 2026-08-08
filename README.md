# koubo-cut 口播视频剪辑技能

面向中文口播视频（一镜到底 talking-head）的「精剪 + 剪映工程包装」Codex 技能：

- 上传素材自动压缩到统一 1080P（横 1920×1080 / 竖 1080×1920）
- 识别横竖屏，按包装密度生成字幕/花字/标题/音效（低 2 / 中 5 / 高 10 个每分钟，全部配音效）
- 精剪规则：说错立马重说时保留最完整句，气口剪紧
- 剪映工程：每段视频都有独立出入点，可逐段微调；命名「核心信息≤5字-cut」

## 安装

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo MMACH4/koubo-cut --path . --name koubo-cut
```

同时需要安装依赖技能 [jianying-editor](https://github.com/luoluoluo22/jianying-editor-skill)。

## 依赖

- 剪映 Pro（Mac）
- ffmpeg/ffprobe：默认 `/Applications/Televzr.app/Contents/Resources/bin_mac_x64/`，
  其他路径用环境变量 `KOUBO_FFMPEG` / `KOUBO_FFPROBE` 覆盖
- faster-whisper small 模型（`~/.cache/faster-whisper/small`），用带 faster-whisper 的 Python 运行
- 剪映本地字体「极宋」（缺失时回退默认字体）

## 使用流程

1. 给 Codex 一条口播原片路径，说「用 koubo-cut 剪辑」
2. 选择包装密度（默认中）
3. 交付：剪映草稿工程（主视频按剪辑点分段，可逐段精修）
