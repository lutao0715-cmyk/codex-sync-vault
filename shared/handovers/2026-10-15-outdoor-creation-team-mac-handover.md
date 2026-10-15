# `outdoor-creation-team` 2026-10-15 Mac 更新交接

> Mac 拉取 `codex-sync` 后，以共享仓库中的 `outdoor-creation-team` 为准。先 `pull`，确认完成后再 `sync`，避免旧版本回灌。

## 今天改了什么

- 删除全部 ChatCut、剪映、CapCut、Jianying 相关说明和流程。
- 后续剪辑工作流只面向 DaVinci Resolve。
- 删除重复的团队总控文档 `references/agents/outdoor-creation-team-team-lead.md`。
- 清理 TeamCreate、SendMessage 和旧子代理编排残留。
- 合并角色间重复能力，只保留各角色独有职责。
- 删除对已淘汰技能 `ski-video-production`（目录名 `滑雪出片`）的依赖。
- 风格能力统一由内部 `style-bible`、风格指南和项目卡承接。
- 热点角色只读取 `hot-topic-report` 的数据，不再重复生成完整选题方案。

## Mac 端需要删除

这些内容如果仍存在于 Mac 的 `outdoor-creation-team` 中，删除：

- ChatCut 相关提示词、脚本、链接和操作说明
- 剪映、CapCut、Jianying 相关提示词、脚本和操作说明
- `references/agents/outdoor-creation-team-team-lead.md`
- TeamCreate、SendMessage、旧子代理编排内容
- 对 `ski-video-production` / `滑雪出片` 的调用或依赖
- 与 `style-bible`、现有风格指南重复的风格规则
- 与 `hot-topic-report` 重复的热点采集和完整方案生成功能

如果 Mac 直接采用共享仓库中的新版 `outdoor-creation-team`，以上内容会随新版文件自然消失，不需要逐条手改。

## 需要保留的能力归属

| 能力 | 保留位置 |
|---|---|
| 总入口、账号区分、任务路由 | `outdoor-creation-team/SKILL.md` |
| 文案、剪辑、配音、配乐、封面、热点角色职责 | `references/agents/` 对应角色文件 |
| 账号风格总规则 | `references/style-memory/style-bible.md` |
| 好奇罗盘、神秘园、小乔大世界风格 | `references/style-guides/` |
| 历史经验与复用规则 | `references/style-memory/` |
| DaVinci 纪录片剪辑提示 | `references/resolve-documentary-prompts.md` |

## 需要安装或确认的外部能力

`outdoor-creation-team` 本身是规则型总入口，不需要独立 Python 依赖。Mac 只需确认任务涉及的下游能力可用：

- `hot-topic-report`：需要实时热点数据时
- `video-understanding`：需要分析原视频、ASR、场景索引时
- `video-script`：需要生成脚本、分镜和素材映射时
- `video-cut`：需要按原片区间实际裁切时
- `video-downloader`：需要下载公开视频时
- `music-generation-studio`：需要生成原创 BGM 时
- DaVinci Resolve：所有正式剪辑、人声处理和交付

缺少某个下游技能时，只补对应能力；不要恢复 ChatCut、剪映或 `ski-video-production`。

## 已确认不需要补装的重复技能

| 旧技能 | 由谁覆盖 |
|---|---|
| `video-material-analysis` | `video-understanding` |
| `audio-transcription` | `video-understanding` |
| `speech-isolate` | DaVinci Resolve |
| `script-driven-material-matcher` | `outdoor-creation-team` + `video-script` |
| `video-download` | `video-downloader` |

## Mac 验收标准

- 搜索 `outdoor-creation-team` 目录，不应再出现 ChatCut、剪映、CapCut、Jianying、`ski-video-production`。
- `SKILL.md` 能正常加载，角色引用均存在。
- 户外号与“滑雪研究院”的差异化规则仍保留。
- 产出的剪辑执行单只面向 DaVinci Resolve。
- 不把 Mac 本机路径、虚拟环境、二进制、密钥或主机专属插件写入共享仓库。
