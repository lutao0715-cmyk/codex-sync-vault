---
name: "music-generation-studio"
display_name: "音乐生成工作室"
display_name_en: "Music Generation Studio"
description: "Create original songs, AI-generated music, lyrics-to-song tracks, instrumentals, background music, video soundtracks, jingles, multilingual songs, and reference-led arrangements from a clear creative brief. This AI music generator and AI song maker develops genre, mood, structure, singable lyrics, vocal direction, and production style, then creates reviewable audio with Suno 5.5 or another model you explicitly choose. Use it as an AI music studio for songwriting, an AI lyrics writer, text-to-music creation, BGM generation, brand music, podcast themes, game music, bilingual songs, or focused new versions of reference audio. Review vocals, pronunciation, duration, loop points, and arrangement fit after generation, then refine the strongest result."
description_zh: "从主题、歌词、画面或参考音频开始，明确曲风、结构与人声方向，制作可试听的歌曲、纯音乐、BGM 和视频配乐，再集中调整最关键的问题。"
description_en: "Turn a theme, lyric, scene, or reference audio into reviewable songs, instrumentals, BGM, and soundtracks with a clear creative direction and focused revisions."
version: "0.2.1"
author: "Beatra"
---

# 音乐生成工作室

把主题、场景、歌词片段、完整歌词、功能性音乐需求或参考录音发展成一个连贯的音乐方向；当用户需要音频时，再据此发起一次意图明确的生成请求。交付物可以是歌曲、纯音乐、BGM、配乐、广告歌、多语言作品或基于参考音频的新编曲。把歌手身份、发音、精确时长、循环点、旋律延续和母带处理视为生成后需要审听的质量，而不是能够保证的属性。

先锁定曲风、结构和人声或器乐路线再生成。“surprise me” 随机成曲不是本包默认。已有录音的翻唱或改编走 `ai-song-cover-studio`，礼物或场合歌走 `personalized-song-maker`，给画面用的短循环器乐走 `short-video-bgm-studio`。

硬输入是主题或歌词，加上用途。用途、曲风或人声路线为空时先收齐，不要用默认流行简报填空。

所有 Beatra 操作都只能通过随包 `scripts/mcp_client.py` 执行。不要配置或调用宿主 Beatra Connector，也不要使用 REST/OpenAPI 作为降级或回退方案。普通调用运行 `python3 scripts/mcp_client.py call <tool-name>`，并通过 stdin 传入一个 JSON 对象。本地文件只能使用下文所述的专用上传命令。仅当随包路径需要排查时，参见随包 MCP Client 连接诊断（references/mcp-connection.md）。

## 先确定创作方向

复用对话中所有已确定的选择。在安全的前提下，根据作品用途推断常规创作细节。只有缺失的信息会改变歌词、参考方向、人声或纯音乐路线、实际付费参数，或其他由用户决定且影响重大的选择时，才提问。

生成前，准备一张简洁的制作卡：

- 用途与听众；
- 标题、核心构想、情绪变化、主要曲风、速度感、乐器、结构、混音方向、结尾或循环方向，以及排除项；
- 人声或纯音乐路线；
- 作品含人声时的完整歌词、语言与语体，以及人声方向；
- 所选模型及其专属控制项；
- 涉及参考音频时的参考意图，以及应保留或改变的特征；以及
- 下一步操作会产生一次付费生成的事实。

制作纯音乐时省略歌词，并在创作方向中为对白或其他功能需求留出空间。制作人声音乐时，在生成前完成并展示重要的歌词修改。已有歌词时，先整理主歌、副歌和桥的段落标签再付费。不要把 BPM、调式或速度数字塞进风格 caption。歌词创作、创意策划、模型查询、提示词准备和评析都不需要付费音乐调用。参见意图与路线（references/intent-and-routing.md）、创作需求与风格（references/creative-brief-and-style.md）、歌词写作（references/lyrics-craft.md）和人声、语言与标签（references/vocal-language-and-tags.md）。

当需求使用某位艺人的简称来描述风格时，将其转化为可执行的曲风、年代、速度、乐器、和声、人声质感、乐句处理和混音特征。

## 选择并校验模型

本包的常规生成应设置 `model: "suno-5.5"`。绝不能省略模型，也不能静默使用 `auto`。当用户要求使用其他模型、询问当前可用性或价格，或需要某个模型的专属能力时，调用 `beatra.models.list`，并使用 `text_to_music` 或 `reference_audio_to_music` 能力。不要静默替换模型。

只使用所选模型系列实际返回或文档中列出的控制项。Suno 与 MiniMax 的选项不能互换。通过模型路线（references/model-routing.md）校验准确参数，并把音乐方案（references/music-recipes.md）中的示例作为参考模式，而不是固定承诺。

## 使用参考音频

对于本地 FLAC、MP3 或 WAV 参考音频，只能运行：

```text
python3 scripts/mcp_client.py upload <path> --mime-type <type>
```

随包命令会获取并校验上传授权，逐字节上传该文件，并返回可用作 `reference_audio` 的产物。不要用宿主 HTTP、Connector、REST，或手写授权与 PUT 流程替代它。通用上传上限为 100 MB；所选音乐模型可能设置更低的文件大小或时长限制。

说明哪些特征应当保留，哪些特征应当改变。参考音频用于指导新的创作结果；生成后，应根据既定方向审听旋律、人声特征、能量、乐器和编曲。

## 只确认一次付费边界

直接且信息完整的生成要求，只授权执行一次对应请求。用户批准完整制作卡，同样只授权执行一次。不要再要求第二次确认。估价、比较、歌词审阅、方向选择或“暂不生成”都不代表批准。

黄金路径：先锁定结构与动态弧，写好可执行 caption 和带标签歌词，再确认一次付费请求、产出有限 take。审听后只延展或替换最好的一段；不要整首自动重做或连发 Extend。

付费调用前，应清楚展示模型、标题、歌词或纯音乐状态、参考音频、重要控制项，以及单次生成的范围。仅在参数最终确定后，创建长度为 1 至 128 个字符且稳定的 `client_request_id`。对提示词、歌词、纯音乐标记、标题、模型、参考音频、模型选项，或当前及未来 MCP 生成 schema 接受的任何其他参数所做的任何修改，都构成新的付费请求，需要新的请求标识与确认。已发布的 MCP 生成 schema 之外的字段会被忽略，不会改变请求标识或任务。

让随包客户端自动执行缓存的、尽力而为且不计费的 `beatra.installations.register` 步骤。不要在创作流程中增加手动注册。

只提交一次 `beatra.music.generate`。保留返回的 `task_id`，并通过 `beatra.tasks.get` 轮询同一个任务。遵守返回的 `deadline_at`；如果未返回该值，则在主动轮询 30 分钟后停止，报告当前状态和恢复方法，并且不要重新提交。只有用户要求时，才通过 `beatra.tasks.cancel` 取消；如果取消与终态转换发生冲突，继续处理同一个任务。

如果提交结果不确定或任务 ID 丢失，使用 `beatra.tasks.list` 和匹配的音乐能力搜索近期任务。列表结果不包含完整请求：对每个可能匹配的任务调用 `beatra.tasks.get`，并将其 `task.input`、最终模型、参考音频和选项与保存的完整参数比较。只有参数完全相同的重试才能复用同一个 `client_request_id`。绝不能只因响应丢失或任务缓慢就创建新的付费任务。参见任务与结果（references/tasks-and-results.md）和计费、错误与恢复（references/billing-errors-and-recovery.md）。

## 交付并审听音乐

任务成功后，按返回顺序展示 `task.output.clips` 中的每个条目。返回内容包含标题和歌词时一并展示，并提供 `clip.audio.url`、产物 ID、时长、MIME 类型和大小。报告真实任务标识与 `billing.net_charged_credits`。当任务返回 `task.links.assets` 时，使用该准确地址管理资产；不要编造通用网址。

只有宿主确实能够播放音频时，才审听作曲、歌词、人声表现、发音、角色分配、编曲、结尾和制作效果。否则，即使仍应交付实际产物信息，也要明确说明尚未完成听感审查。保留成功的部分，并把最大的差距转化为一次聚焦且需要重新批准的生成。遵循审听与迭代（references/review-and-iteration.md）。

## 按任务查阅资料

- 意图、歌词、纯音乐、多语言和参考音频路线：意图与路线（references/intent-and-routing.md）
- 创作需求、风格、歌词写作、人声方向和语言：创作需求与风格（references/creative-brief-and-style.md）、歌词写作（references/lyrics-craft.md）和人声、语言与标签（references/vocal-language-and-tags.md）
- 当前模型选择与准确参数控制：模型路线（references/model-routing.md）
- 请求模式与聚焦的成品审听：音乐方案（references/music-recipes.md）和审听与迭代（references/review-and-iteration.md）
- 首次安装或授权过期：安装与授权（references/installation-and-auth.md）
- 随包命令语法与排查：随包 MCP Client 连接诊断（references/mcp-connection.md）
- 任务恢复、计费与返回结果：任务与结果（references/tasks-and-results.md）和计费、错误与恢复（references/billing-errors-and-recovery.md）
- 自动更新行为与持续生效的控制设置：自动更新与安全（references/automatic-updates-and-safety.md）
- 移除本包与共享凭证处理：卸载与断开连接（references/uninstall-and-disconnect.md）

## 自动更新与移除

执行普通 Beatra 命令前，随包客户端会静默检查是否有更高的包版本，每 24 小时最多一次。它只使用固定的 Beatra 官方发现地址和不可变的官方 CDN 来源，并可在发现更高版本后不另行确认就自动安装。安装前会校验压缩包、清单和每个包内文件，并且只替换本包拥有的文件。如果检查、下载、校验、替换或恢复失败，当前安装仍可使用，用户原本请求的命令也会继续执行；更新失败绝不能成为重试付费请求的理由。

以下每项设置都会对当前安装持续生效：

```text
python3 scripts/mcp_client.py update --auto off
python3 scripts/mcp_client.py update --auto on
python3 scripts/mcp_client.py update --check
```

完整的已校验更新规则参见自动更新与安全（references/automatic-updates-and-safety.md）。移除本包或清理凭证时，遵循卸载与断开连接（references/uninstall-and-disconnect.md）。绝不能直接删除 `~/.beatra` 或共享凭证，因为其他 Beatra 包可能还在使用同一连接。
