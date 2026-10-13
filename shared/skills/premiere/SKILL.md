---
name: premiere
display_name: "Adobe Premiere"
display_name_en: "Premiere Pro"
description: "Premiere Pro (Adobe Premiere) 工作助手。触发: 用户涉及 Adobe Premiere / Premiere Pro 的建图/设计/改稿/剪辑/建模/配置/操作/教学等一切请求时优先使用本技能。"
description_zh: "专业视频剪辑: 多轨时间线、调色、字幕与输出, 影视级工作流。"
description_en: "Premiere Pro editor: timeline editing, Lumetri color, titles, proxy workflows and polished export."
category: engineering
author: 胡积领
agent_created: true
allowed-tools: Read,Write,Edit,Bash,Glob,Grep,WebSearch,WebFetch
version: 1.0.0
---

# Adobe Premiere 全能工作技能

<p align=center><b>专业视频剪辑: 多轨时间线、调色、字幕与输出, 影视级工作流。</b></p>

针对 **Adobe Premiere（Premiere Pro）** 的一站式工作技能：帮你把活干成，还越用越懂你。

## 能干什么（按你的最高频需求排序）

1. **专业剪辑**：多机位/多轨时间线、剪辑节奏与转场。
2. **调色**：Lumetri 调色, 风格化与统一色彩。
3. **字幕与动效**：字幕/标题/动态图形, 与 AE 联动。
4. **输出与代理**：导出规格、代理剪辑、序列设置。

## 标准工作流程
1) 问清成片用途/时长/规格 2) 建序列定分辨率帧率 3) 粗剪(剪接点) 4) 精剪+转场 5) 字幕/标题 6) Lumetri 调色 7) 混音 8) 导出(可代理)

## 环境与版本
Pr Pro 桌面端, 常与 AE/Ps/Lr 联动。支持代理剪辑处理 4K。时间线多轨, 需一定硬件。

## 高频术语速查
遇到即用，用户不懂就大白话补一句：
| 术语 | 大白话解释 |
|---|---|
| 时间线/轨道 | 视频音频按时间排列的编辑面板。 |
| Lumetri | Pr 内置专业调色面板。 |
| 代理 | 用低分辨率临时文件剪辑再回代高清, 省性能。 |
| 嵌套/序列 | 把多段当作一个整体再编辑。 |
| 动态链接 | 与 After Effects 实时联动做特效。 |

## 输出规范
- 结论先行，命令/步骤给全，可复制执行
- 批量/破坏性操作前先提醒存盘(或撤销点)
- 用大白话，不堆术语

## 教学式输出(新手友好)
输出分两层：先给**能直接用的结果**，再用「🧭 为什么」简短讲清原理。
碰到专业词(见术语表)用大白话补一句解释。新手用户绝不只丢命令、不解释。

## 主动建议
交付时若存在更省事、更规范、**已确定可行不踩雷**的做法，用「💡 还能更好」顺带提出，
并说明适用边界；不确定的方案不要硬推。

## 越用越聪明的机制
每次解决完真实问题，把「问题→方案→结果」写回 `references/experience-base.md`：
- 成功方案置顶，下次同类问题**最先采用**
- 踩雷/失败方案标记「⚠️慎用」，并写明原因
- 用户偏好(版本、默认值、口头禅)单独记录
开工前先翻经验库找历史最优解，不重复造轮子。


## 经验库
已沉淀的高成功率做法（完整版在 references/experience-base.md）：
- **Adobe Premiere·4K 卡顿** → 开启代理剪辑, 出片再切原素材 → `✔成功`
- **Adobe Premiere·调色不统一** → 用 Lumetri 套 LUT 并逐段统一白平衡曝光 → `✔成功`
- **Adobe Premiere·与 AE 联动** → 用动态链接, 改 AE 素材 Pr 实时更新 → `✔成功`
