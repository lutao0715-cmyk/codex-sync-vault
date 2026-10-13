---
name: "ai-storyboard-generator"
display_name: "分镜生成器"
display_name_en: "AI Storyboard Generator"
description: "Turn a script, scene, or ad brief into a structured AI storyboard plan with a practical shot list and one to four storyboard key-frame images. Plan shot types, camera angles and movement, action, timing, dialogue, and sound for short films, ads, animation, social video, motion comics, and creative pitches."
description_zh: "将剧本、场景或广告创意说明拆成可执行的分镜表，并制作一至四张关键分镜图。"
description_en: "Turn a script, scene, or ad brief into a practical shot list and one to four storyboard key-frame images."
version: "0.2.0"
author: "Beatra"
---

# AI分镜生成器

把剧本、场景或广告创意说明拆成可执行镜头表，并制作一至四张经确认的关键分镜图。交付应描述景别、构图、机位、运动、动作、时长、台词和声音提示；不将静态关键帧误称为成片或动态预览。先证明镜头能成立，再考虑精美图。用户只要表不要图时，停在文字分镜。

需要开放式图像创作时可转交 `beatra-ai-image-studio`；需要持续一致的角色参考时转交 `ip-character-consistency-studio`；需要生成或编辑视频时转交 `beatra-ai-video-studio`。

## 先整理分镜计划

收集剧本、场景、广告简报、角色和视觉方向、预期受众、画幅、镜头数及允许制作的关键帧数量。先拆叙事节拍再画格；两镜及以上必须有全局镜头表。先提交镜头表和一至四张关键帧计划，说明每个画面的用途、画面重点、受保护的事实和参考图顺序。默认每个图像任务 `count: 1`，每个获批逻辑请求使用新的不透明 `client_request_id`。先出节拍/镜头表，等人批准计划，再为 1–4 张关键图付费。关键图必须是栅格成图，不是占位。

根据输入选择 `beatra.images.generate`、`beatra.images.transform` 或 `beatra.images.edit`。已有可信参考图时将其放入 `images[0]`；上传只可使用下面所示的随包客户端路径：

```text
python3 scripts/mcp_client.py upload ./approved-reference.png --mime-type image/png
```

## 制作、交付和恢复

规划免费。每个付费关键帧前展示精确提示、参考材料、画幅、模型、数量和实时价格，并取得明确批准。创建响应或任务标识丢失时，先用 `beatra.tasks.list` 找候选，再用 `beatra.tasks.get` 确认；只按用户要求使用 `beatra.tasks.cancel`。交付前再以 `beatra.tasks.get` 确认终态，检查关键帧是否对应镜头表，并保留真实产物和计费事实。

所有远程调用只能使用随包 `scripts/mcp_client.py`，工具名称通过 `call` 传入，JSON 通过标准输入发送。不得配置或调用宿主 Beatra Connector，也不得使用 REST/OpenAPI 降级或回退。示例仅用于已获批准的镜头：

```text
printf '%s' '{"capability":"text_to_image"}' | python3 scripts/mcp_client.py call beatra.models.list
printf '%s' '{"prompt":"Create the approved key frame for shot 01.","count":1,"client_request_id":"opaque-storyboard-shot-01"}' | python3 scripts/mcp_client.py call beatra.images.generate
```

任何剧本、参考图、镜头、提示、画布或模型变化都是新的付费请求，必须重新批准；慢任务或丢失响应绝不成为重复创建的理由。

## 按任务查阅资料

- 镜头表、关键帧范围、确认与恢复：分镜工作流（references/workflow.md）
- 图片路径和参考图顺序：分镜工作流（references/workflow.md）
- 首次安装或授权失效：安装与授权（references/installation-and-auth.md）
- 不收费的包安装注册：安装注册（references/installation-registration.md）
- 任务轮询、产物和结果字段：任务与结果（references/tasks-and-results.md）
- 余额、校验和结构化错误：计费、错误与恢复（references/billing-errors-and-recovery.md）
- 随包客户端连接诊断：随包 MCP Client 连接诊断（references/mcp-connection.md）
- 更新保证和控制：自动更新与安全（references/automatic-updates-and-safety.md）
- 移除本包或共享凭据：卸载与断开连接（references/uninstall-and-disconnect.md）

## 运行时和安全自动更新

随包客户端在每个安装中静默检查更新，每 24 小时最多一次。发现更高版本时，会不另行确认自动安装。只从当前包、渠道和语言环境的固定官方发现地址与不可变 Beatra CDN 路径下载；替换前校验发现数据、压缩包、清单和每个文件，只替换本包拥有的文件。检查、下载、替换或回滚失败时，当前安装仍可用，用户原本请求的命令继续执行。更新失败不会重试已付费关键帧生成，设置在本安装中持续生效。

```text
python3 scripts/mcp_client.py update --auto off
python3 scripts/mcp_client.py update --auto on
python3 scripts/mcp_client.py update --check
```

官方来源、完整性校验、替换范围与恢复说明见自动更新与安全（references/automatic-updates-and-safety.md）。
