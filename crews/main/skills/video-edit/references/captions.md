# 中文旁白字幕

## 时间轴

- 使用 `awk-tts --enable-subtitle` 产出的 `.subtitle.json`，遍历全部 `sentences[].words`，时间单位是秒。旁白从视频 0 秒起对齐时用 `video-edit caption-ass`；拼接、裁切、变速或延迟入场的旁白先按实际成片重新对齐。
- `--text-file` 只放实际口播稿。脚本忽略空白和标点后逐字比对 TTS；中文数字与阿拉伯数字等字词差异须先核实，不自动替换。分句文本拼回须与原稿一致，不用 ASR utterance 的粒度代替字幕分句。
- 按逗号、句号、问号、感叹号、分号和换行切小句；小数与千分位不切。每句时间取对应首末字词，不按字数推算；分句落在一个多字 TTS 词块内部时停止，请调整该处标点。
- 默认句首/尾各扩展 0.10 秒，相邻字幕至少留 0.02 秒。相邻扩展冲突时在交界处收缩双方，再向内量化到百分秒，不把后续句子不断向后推。句子过短无法显示、时间码倒序或旁白超出画面时停止，不跳句或裁末句。
- `--padding` / `--gap` 可调。缺少有效字级时间码时先获取真实对齐结果；本工具不自动调用外部 ASR。

## 排版

- ASS 显式写入 `PlayResX/PlayResY`，默认等于视频画布，字号和边距可按画布像素设置。这是本工具的约定；其他 ASS 的脚本分辨率可以不同，不能把“与画布不同”直接判为错误。
- 1080 宽默认字号 47，其他宽度等比缩放；默认每行最多 19 个字符、每屏最多 3 行。数字加常见单位和英文单词整体保留，禁止标点落在新行行首；过长小句报错，先在语义停顿处补标点。自动断行只做长度平衡与标点保护，语义仍需人工核对。
- 默认白字、半透明黑底框。`BorderStyle=3` 的底框使用 `OutlineColour=&H80000000`，`BackColour` 是阴影色；`Shadow=0` 时改 BackColour 不能控制底框透明度。`--no-box` 改为白字黑描边；单个 BorderStyle=3 样式不能同时提供独立黑描边。
- 默认底部居中、距底边画高 13%（1080×1920 约 250px），作为短视频初始排版。主体位置、平台 UI 与发布文案会改变遮挡范围，不能把 13% 当成所有平台的固定安全区。按预览调整 `--font-size` / `--margin-v` / `--columns` / `--max-lines` / `--font`。
- 自动断行拆开中文词语或语义时，创建 JSON 二维数组，用 `--layout layout.json` 重新生成并试渲。每项对应一个分句，每项内是该句的各行，例如 `[["你好，"], ["这条长句的前半段", "以及后半段。"]]`；不能改字、漏字、超宽或拆开数字单位/英文词。字幕的分句和时间码保持原样。
- 换行写为 ASS 字面量 `\N`。原稿禁止含 ASS 控制字符 `{`、`}`、反斜杠，避免被解释为样式命令。
- SRT 经 FFmpeg 转换后使用 ASS 脚本单位；不能无条件套用 `×288/画布高`。需要精确像素排版时使用显式画布的 ASS，不让 agent 猜测隐藏的脚本分辨率。

## 试渲与验收

```bash
video-edit caption-ass input.mp4 audio/voiceover.subtitle.json \
    --text-file narration.txt --output subtitles.ass --preview-dir review/captions
```

脚本保存 ASS、同名 JSON（分句、百分秒起止、排版与试渲图片路径），自动选择最多 10 个句中点，包含首末句、最短句和最长句。检查图片中的句子、换行、底框、裁切与主体遮挡。改字号或位置后重新生成并看图，再烧录。

单点试渲统一用 wrapper：

```bash
video-edit subtitles input.mp4 subtitles.ass --preview-at 2.5 --output review/caption.png
```

工具在输出端 seek，保留字幕滤镜的原始时间轴。不自行拼接 FFmpeg 命令；单纯把输入端 `-ss` 提前会改变滤镜看到的时间，可能渲出片头字幕。

烧录与检查是人工看图后的独立步骤：

```bash
video-edit subtitles input.mp4 subtitles.ass --output video-final.mp4
```

烧录后用 `video-edit frames video-final.mp4 --interval 3 --output-dir review/burned` 抽样查看。对最短句和末句按已检查的句中点精确抽帧，例如 `video-edit frames video-final.mp4 --at 2.5 --at 28.4 --width 1080 --output-dir review/boundaries`；`--at` 可重复。已烧录视频只抽帧，不再叠同一份字幕。另跑 `video-review video-final.mp4`；它检查媒体质量，不证明字幕语义、时序或排版合格。字幕、口播稿与成片一起保留。

实现参数参见 [FFmpeg subtitles](https://ffmpeg.org/ffmpeg-filters.html#subtitles-1) 与 [libass 渲染实现](https://github.com/libass/libass/blob/master/libass/ass_render.c)。
