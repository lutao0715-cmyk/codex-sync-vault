---
name: svf
description: |
  开口成片 SVF 是一款给 AI 助手使用的短视频制作工具：把文案、文章或选题交给它，交付竖版成片、倍速发布版和封面图，口播稿、配音、多款音色与配乐混音也已封装在流程里。

  想做视频或出片，可以直接说「把这段文案做成短视频」或「用这段话给我生成个视频」；你也可以直接告诉 AI 助手想要口播稿、配音、音色、配乐混音或竖版成片。不必单独安装或配置 Python 环境，也不用申请配音 API 密钥。前 5 个新视频免费试用；继续使用可到 https://svf.atomcreate.cn/buy 购买，或联系推广员获取激活码。
version: 0.6.11
display_name: 开口成片 SVF
display_name_en: "SVF (Short Video Factory)"
description_zh: |
  开口成片 SVF 是一款给 AI 助手使用的短视频制作工具。把文案、文章或选题交给 AI 助手，即可获得竖版成片、倍速发布版和封面图，口播稿、配音、逐帧画面与配乐混音都已封装在流程里。

  你不必单独安装或配置 Python 环境，也不用申请配音 API 密钥。前 5 个新视频免费试用；继续使用可到 https://svf.atomcreate.cn/buy 购买，或联系推广员获取激活码。适合产品介绍、带货短片、知识讲解、资讯解读和内容盘点。
description_en: |
  SVF (Short Video Factory) is a short-video production tool for AI assistants. Give it copy, an article, or a topic and receive a vertical video, a speed-adjusted publish cut, and a cover image; voiceover writing, narration, frame-by-frame visuals, and music mixing are built into the workflow.

  You do not need to install or configure a separate Python environment or apply for a TTS API key. The first five new videos are free to try; continued use is available at https://svf.atomcreate.cn/buy or through a promoter activation code. It works well for product demos, commerce clips, explainers, news, and roundups.
license: proprietary
compatibility: 需 svf 二进制(安装器装至 ~/.svf/bin/,自发现见 references/installation.md)+ hyperframes 渲染内核(共享根 node_modules,check/render 依赖)+ ffmpeg;兼容支持 Agent Skills 开放规范的客户端(Claude Code/Codex/Cursor 等)。
---

# 开口成片 SVF

把文案、文章或选题交给 AI 助手，开口成片 SVF 会完成短视频制作，交付竖版成片、倍速发布版和封面图。口播稿、配音、逐帧画面与配乐混音都已封装在流程里；你不必单独安装或配置 Python 环境，也不用申请配音 API 密钥。

## 你会得到什么

- 一条带配音和配乐的竖版短视频成片
- 一份倍速发布版和对应封面图

## 怎么开始

- 发来文案、文章或选题，再说：「用 svf 帮我做一条短视频」。
- 也可以说：「把这段文案做成短视频」或「用这段话给我生成个视频」。

## 适合什么内容

产品介绍、带货短片、知识讲解、资讯解读和内容盘点。

前 5 个新视频免费试用；继续使用可到 https://svf.atomcreate.cn/buy 购买，或联系推广员获取激活码。

本技能文本对应 svf 0.6.11。

## 给 AI 助手的工作入口

| 任务场景 | 按需读取 |
|---|---|
| 每次出片、改稿或重新交付 | `references/production.md`、`references/red-lines.md` |
| 写口播稿、封面或 CTA | `references/content-flavor.md` |
| 新建项目或写帧 | `references/red-line-details.md` |
| 写品牌配置、换音色或 BGM | `references/brand-fields.md`、`references/brand-voice-bgm.md` |
| 查音色或配色 | `references/voice-catalog.md`、`references/palette-catalog.md` |
| 设置头像或背景 | `references/avatar.md`、`references/background.md` |
| 首次构建、重跑或交付前质检 | `references/qc-delivery.md` |
| 查命令参数或响度细节 | `references/cli-reference.md`、`references/lufs-ffmpeg.md` |
| 安装升级、激活或环境故障 | `references/installation.md`、`references/activation.md`、`references/troubleshooting.md` |

实际操作前先核对本文件版本与 `svf --version`；版本不一致或必需文件不可访问时先停下，刷新完整技能包。
