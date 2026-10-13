何时读本文件：QC 质检单的 `audio` 响度三值偏离目标，或需要排查混音、转码和 ffmpeg 参数时。日常出片不需要读。

# LUFS / ffmpeg 参数与排查

## 目标值(固定,不随项目调)

| 项 | 值 |
|---|---|
| 人声响度 | -14 LUFS(integrated) |
| 真峰 | TP -1.5 dB |
| 响度范围 | LRA 4.0 |
| 容差 | final_check.I 落在 -14 ~ -16;低于 -16 视为异常需排查(人声 PLR 偏高时受 TP=-1.5 约束到不了 -14,复核值如实记录即可) |

## 混音链关键参数(排查时对照,勿凭感觉调)

- 人声轨:从 `assets/voice/*.wav` 原始文件按 `data-start` 重建(禁止读成片音频);loudnorm 第一遍测量(`I=-14:TP=-1.5:LRA=4` + `print_format=json`)取 `input_i/input_tp/input_lra/input_thresh` 四字段,第二遍回填 `measured_*` 且 `linear=true` 静态归一;测量值字符串原样透传,不做数值加工。
- BGM:增益 + `lowpass 10kHz` 至 48k 立体声;解析失败走静音兜底。
- 终混:`amix=duration=longest:normalize=0`(成片保住视频全长,不截片尾)+ `alimiter=limit=0.95`。
- 封装:视频流 `-c:v copy`(不重编码)、音频 `aac -b:a 192k`、`-shortest`。
- 写出:先 `renders/video-vertical.tmp.mp4`,成功后原子改名;失败不产出稳定名半成品。

## 常见问题

| 现象 | 排查方向 |
|---|---|
| final_check.I < -16 | 人声轨重建异常:查 index.html 的 audio 时间轴是否与 probe 时长一致、是否有片段 WAV 缺失 |
| 人声被 BGM 压住 | 确认 BGM 增益未手工调大;规范增益见品牌配置 |
| 成片时长比预期短 | 检查 index.html `#root` 的 `data-duration` 与锚点动画(`tl.to({}, {duration: 总时长}, 0)`) |
| mix 报「无合格人声片段」 | 人声 audio 标签必须 `src` 在 `assets/voice/` 下且含 `data-start`;先跑 tts |
