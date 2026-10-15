# 户外纪录片讲解剪辑工具链安装清单

## 已在 Mac 端可用

- `video-material-analysis`：本地视频场景切分、代表帧和时间码镜头表。
- `audio-transcription`：最终配音转写为带时间码的旁白槽位。
- `speech-isolate`：需要保留现场声时，分离人声、环境声和背景音乐。
- `script-driven-material-matcher`：根据旁白槽位匹配多视频素材，输出候选表、缺口清单和 `clip_plan.json`。
- `video-download`：下载经授权的素材。

## Windows 端晚上优先检查

1. 同步 Codex 技能后确认上面 5 个技能可被发现。
2. 检查 Python 运行环境是否能导入 `scenedetect` 和 `faster_whisper`。
3. 检查 DaVinci Resolve 已安装并能接收剪辑计划。
4. 如需语音分离，单独检查 Modal CLI 和登录状态；没有登录时不要假装已配置。
5. Twelve Labs 是可选的云端语义检索服务，需要单独账号/API Key和上传素材权限，不能由同步仓库自动带过去。
6. Eagle 是可选的素材资产库，需要下载安装和账号/试用确认；它不是自动语义匹配器。

## 推荐顺序

先用本地分析和转写完成第一版；素材数量达到几十到上百条后，再试 Twelve Labs；素材库长期积累后再装 Eagle。不要安装 Jianying/剪映作为这套 Codex + DaVinci 工作流的素材分析入口。
