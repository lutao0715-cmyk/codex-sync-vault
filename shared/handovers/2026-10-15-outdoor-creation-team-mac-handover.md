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
- 删除过期的 `video-toolchain-setup.md`，改为 `media-tool-routing.md`。
- TwelveLabs Jockey MCP 已接入，负责大量、多视频的语义检索；少量、敏感或本地素材仍走 `video-understanding`。
- DaVinci Resolve MCP 负责正式剪辑、人声处理、字幕、混音、导出和实际时间线验收。
- 新增 `evidence-and-rights.md`，补齐事实来源、可信度和素材授权核验。
- 删除重复的 `project-memory-archive.md`，项目记忆统一使用 `style-memory/project-cards/`。
- 项目卡新增播放量、5秒留存、完播率、互动率和搜索流量的数据回流。
- 封面需要成图时可调用 `imagegen`。
- AI 视频补画面只输出 Seedance 官网任务单与提示词，不再调用其他视频生成服务。

## Mac 端需要删除

这些内容如果仍存在于 Mac 的 `outdoor-creation-team` 中，删除：

- ChatCut 相关提示词、脚本、链接和操作说明
- 剪映、CapCut、Jianying 相关提示词、脚本和操作说明
- `references/agents/outdoor-creation-team-team-lead.md`
- TeamCreate、SendMessage、旧子代理编排内容
- 对 `ski-video-production` / `滑雪出片` 的调用或依赖
- 与 `style-bible`、现有风格指南重复的风格规则
- 与 `hot-topic-report` 重复的热点采集和完整方案生成功能
- `references/video-toolchain-setup.md`
- `references/project-memory-archive.md`
- “本机无 edge-tts”等单机状态描述
- 固定“单镜5-30秒”“AI生成不超过40%”等互相冲突的硬规则

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
| 本地/Jockey/DaVinci/Seedance工具选择 | `references/media-tool-routing.md` |
| 事实来源与素材版权 | `references/evidence-and-rights.md` |
| 项目复盘与发布数据回流 | `references/style-memory/project-cards/` |

## 需要安装或确认的外部能力

`outdoor-creation-team` 本身是规则型总入口，不需要独立 Python 依赖。Mac 只需确认任务涉及的下游能力可用：

- `hot-topic-report`：需要实时热点数据时
- `video-understanding`：需要分析原视频、ASR、场景索引时
- `video-script`：需要生成脚本、分镜和素材映射时
- `video-downloader`：需要下载公开视频时
- `music-generation-studio`：需要生成原创 BGM 时
- TwelveLabs Jockey MCP：大量、多视频素材的语义检索
- DaVinci Resolve MCP：所有正式剪辑、人声处理、字幕、混音、导出和验收
- `imagegen`：需要直接生成或修改封面时

缺少某个下游技能时，只补对应能力；不要恢复 ChatCut、剪映或 `ski-video-production`。

## 已确认不需要补装的重复技能

| 旧技能 | 由谁覆盖 |
|---|---|
| `video-material-analysis` | `video-understanding` |
| `audio-transcription` | `video-understanding` |
| `speech-isolate` | DaVinci Resolve |
| `script-driven-material-matcher` | `outdoor-creation-team` + `video-script` |
| `video-download` | `video-downloader` |
| `video-cut`（户外正式项目） | DaVinci Resolve MCP |

## Mac 验收标准

- 搜索 `outdoor-creation-team` 目录，不应再出现 ChatCut、剪映、CapCut、Jianying、`ski-video-production`。
- `SKILL.md` 能正常加载，角色引用均存在。
- 户外号与“滑雪研究院”的差异化规则仍保留。
- 产出的剪辑执行单只面向 DaVinci Resolve。
- 大型素材检索能够路由到 Jockey，且保留 knowledge store、item id 和片段时间码。
- 人物、事故、历史和第三方素材任务会生成事实核验表与素材权利表。
- AI 视频补画面只指向 Seedance 官网工作流。
- 不把 Mac 本机路径、虚拟环境、二进制、密钥或主机专属插件写入共享仓库。
