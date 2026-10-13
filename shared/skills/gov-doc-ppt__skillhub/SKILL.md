---
name: gov-doc-ppt
description: >
  Government document summarization and PPT creation. Use this skill when the user
  needs to summarize government/policy documents, leadership speeches, work reports,
  investigation reports, or party-building materials into professional presentation
  slides (PPT), or needs to generate GB/T 9704 standard official documents (hongtou
  wenjian). Triggers on keywords: 政务, 公文, 红头文件, 述职报告, 党建汇报, 工作总结PPT,
  领导讲话, 政策解读, 调研报告PPT, 政府汇报, 党政, 通知(in government context),
  请示, 批复. Suitable for government/public institution staff and consulting firms
  serving government clients.
description_zh: "政务公文写作提炼与 PPT 制作"
description_en: "Government Document Summarization & PPT Creation"
version: 1.0.0
license: Proprietary
agent_created: true
metadata:
  version: "1.0.0"
  category: government-document-processing
  skill_type: free
  target_audience:
    - 政府/事业单位工作人员
    - 党政机关文字秘书
    - 咨询/智库公司（政府项目乙方）
  keywords:
    - 政务
    - 公文
    - 红头文件
    - PPT
    - 述职报告
    - 党建
    - 工作总结
    - 讲话稿
    - 政策解读
    - GB/T 9704
display_name: "政务公文提炼与 PPT"
display_name_en: "Gov Doc to PPT"
visibility: "public"
---

# gov-doc-ppt: 政务公文提炼与 PPT 制作

将政策文件、领导讲话稿、工作总结、调研报告等政务素材，智能提炼为规范的 PPT 汇报演示文稿，并可附带生成 GB/T 9704 标准的红头公文 Word 文档。

---

## Workflow Router

收到用户请求后，首先通过以下决策树确定执行管线：

```
User Task
├─ 用户明确要求"PPT"或"幻灯片"或"演示文稿"
│   └─ 进入 Pipeline P: PPT 汇报制作
│
├─ 用户明确要求"Word"或"docx"或"红头文件"或"公文"或"通知/请示/报告"
│   └─ 进入 Pipeline D: 红头公文生成
│
├─ 用户同时要求 PPT + Word（如"帮我写工作总结和PPT"）
│   └─ 进入 Pipeline C: 联合输出（先PPT后Word）
│
└─ 用户描述模糊（如"帮我提炼这份材料"）
    └─ 追问用户：输出格式偏好（PPT 汇报 / 红头公文 / 两者都要）
```

---

## Pipeline P: PPT 汇报制作

这是主流程——将政务文本材料提炼为专业的汇报 PPT。

### Step 1: 输入获取与解析

根据用户提供的输入类型，选择对应的解析策略：

- **Word 文档 (.docx)**：使用 minimax-docx 的 analyze + preview 功能提取文本结构和内容
- **PDF**：首先尝试使用 python3 从 PDF 提取文本；如为扫描版，提示用户提供可复制版本或使用 OCR
- **纯文本粘贴**：直接接收，按段落分析
- **TXT 文件**：直接读取
- **多文件混合**：合并所有文本后统一分析，标记来源文件

详细策略见 `references/input_parsing_strategy.md`。

### Step 2: 内容分析与提炼

对输入材料进行三阶段分析：

**A. 政务语境识别**

- 识别公文类型：工作总结 / 述职报告 / 领导讲话 / 政策文件 / 调研报告 / 党建材料
- 识别发文机关层级：中央 / 省级 / 市级 / 县级 / 基层
- 识别文本中的关键要素：指导思想、主要做法、取得成效、存在问题、下一步打算

**B. 结构提炼**

- 提取 3-7 个核心观点（用于内容页要点）
- 识别可量化数据（用于图表页，如 GDP 增长、项目完成率、预算执行率）
- 识别时间线内容（用于里程碑/回顾页）
- 保留关键引用（领导人讲话原文、政策条文，用于引用页）

**C. 语言规范化检查**

参考 `references/gov_language_guide.md`：

- 检查禁用词/敏感词
- 确保政治术语表述准确（"两个维护""四个意识""四个自信""两个确立"等）
- 统一单位、数字、日期格式（中文数字用于正式日期：二〇二六年七月二十四日）
- 统一称谓规范

### Step 3: 选择汇报场景与配色方案

根据识别出的公文类型，从 `references/ppt_scene_structures.md` 中选择场景模板：

| 公文类型 | 场景模板 ID | 推荐配色 | 典型页数 |
|---------|------------|---------|---------|
| 工作总结 | work_summary | gov_red_head | 10-15 页 |
| 述职报告 | duty_report | gov_dark_blue | 8-12 页 |
| 领导讲话稿 | leader_speech | gov_warm_red | 12-20 页 |
| 党建汇报 | party_building | gov_red_head | 10-15 页 |
| 政策解读 | policy_briefing | gov_dark_blue | 8-15 页 |
| 调研报告 | research_report | gov_dark_blue | 10-18 页 |

从 `assets/palettes/` 读取对应的颜色方案 JSON 文件。

### Step 4: 生成 PPT slides JSON

按照 `references/ppt_scene_structures.md` 中对应场景的结构模板，生成完整的 slides JSON 数组。

**页面类型规范：**

- **封面页 (cover: centered)**：标题居中 + 副标题（报告人/单位/日期），使用红色主色调
- **目录页 (agenda)**：列出各章节，高亮当前章节
- **章节分隔页 (section)**：纯色背景 + 大标题居中
- **内容页 (content)**：要点式呈现，每页 3-5 个要点，使用序号或项目符号
- **图表页 (chart)**：数据可视化（柱状/折线/饼图）
- **总结页 (summary)**：核心要点回顾 + 结语展望

JSON 结构严格遵循 pptx-generator 的规范（11 种 slide 类型），完整 JSON 写入临时文件 `slides.json`。

可参考 `assets/ppt_templates/` 中的预设模板获取正确的 JSON 结构。

### Step 5: 注入党政配色方案

pptx-generator 内置的 5 套配色方案不含党政风格，需要通过脚本注入。

**推荐方式：脚本注入**

```bash
python3 scripts/patch_pptx_palette.py --palette assets/palettes/<selected_palette>.json
```

该脚本读取 pptx-generator 的 `generate_pptx.py`，在 PALETTES 字典末尾追加自定义配色，生成 `generate_pptx_patched.py` 供后续调用。

**备选方式：直接修改**

如果脚本执行失败，可直接用 python3 读入 `generate_pptx.py`，在 PALETTES 字典的最后一个条目后追加新的配色条目，写入临时文件。

### Step 6: 调用 pptx-generator 生成 PPTX

通过 Skill 工具链式调用：

```
Skill: pptx-generator
Args: --input slides.json --output <output_name>.pptx --style <palette_name>
```

如果使用 patched 脚本：

```bash
python3 <pptx_generator_path>/scripts/generate_pptx_patched.py --input slides.json --output <output_name>.pptx --style <palette_name>
```

### Step 7: 可选——生成信息图附件

如果原始材料包含适合可视化的数据，可选调用 infographic-maker 生成一页信息图：

- 提炼核心 3-5 个关键数据点
- 生成手绘风知识卡片作为 PPT 补充

### Step 8: 文件交付

向用户交付产物清单：

1. **主产物**：`<filename>.pptx`（标准可编辑 PPT，16:9 宽屏）
2. **源文件**：`slides.json`（用户可手动修改后重新生成）
3. **可选附件**：`infographic.png`（关键数据一页图）

---

## Pipeline D: 红头公文生成

### Step 1: 确定公文类型

根据用户输入和内容特征，识别以下公文类型：

- **通知**：下行文，告知事项、部署工作
- **报告**：上行文，汇报工作进展、反映情况
- **请示**：上行文，请求上级批复
- **函**：平行文，商洽工作、询问答复
- **纪要**：会议纪要

详细模板参见 `assets/docx_templates/` 中的对应的 `hongtou_*.md` 文件。

### Step 2: 内容提炼与格式编排

参考 `references/gb_t9704_quick_ref.md` 和 `assets/docx_templates/`：

**A. 生成公文结构（GB/T 9704 标准）**

```
版头（红头部分）
├── 发文机关标志（红色大字，小标宋体）
├── 发文字号（年份用六角括号：〔2026〕X号）
└── 分隔红线
主体
├── 标题（小标宋 二号 22pt 居中）
├── 主送机关（顶格）
├── 正文（仿宋_GB2312 三号 16pt）
│   ├── 一级标题：黑体 三号
│   ├── 二级标题：楷体 三号 加粗
├── 附件说明（如有）
├── 署名 + 成文日期（小写中文数字）
└── 印章位置
版记
├── 抄送机关
├── 印发机关 + 印发日期
└── 页码（- X - 格式）
```

**B. 排版规范速查**

- 页面：A4 (210×297mm)
- 页边距：上 37mm / 下 35mm / 左 28mm / 右 26mm
- 标题：小标宋 二号（22pt）居中
- 正文：仿宋_GB2312 三号（16pt），固定行距 28pt
- 一级标题：黑体 三号
- 二级标题：楷体 三号 加粗
- 数字：正文用小写中文数字书写日期（二〇二六年七月二十四日）

### Step 3: 调用 minimax-docx 生成 DOCX

minimax-docx 内置 ChineseGovernment (GB/T 9704) AestheticRecipe。

通过 Skill 工具链式调用：

```
Skill: minimax-docx
描述: 以 GB/T 9704 ChineseGovernment 模板创建公文
内容: [提炼后的公文内容]
类型: [通知/报告/请示/函/纪要]
```

交付：`<filename>.docx`（GB/T 9704 标准红头公文）

---

## Pipeline C: 联合输出

当用户同时需要 PPT + Word 时：

1. 先确认内容提炼结果（**一次提炼，两种输出**）
2. 按顺序执行 Pipeline P（PPT）→ Pipeline D（Word）
3. 如果用户指定了优先级，按用户要求调整顺序
4. 统一交付：`汇报PPT.pptx` + `红头公文.docx` + `提炼要点.txt`

---

## 安全与质量红线

1. **不使用真实政治图形文件**：不包含党徽、国徽、军徽等矢量/位图文件。使用文字占位符 `[此处放置党徽/国徽]`，由用户自行添加。
2. **模板不做政治表态**：所有模板仅定义结构，不固化任何具体政策内容、领导人讲话或政治立场表述。
3. **不支持生成涉敏内容**：拒绝生成负面、抹黑、歪曲或违法违规的内容。
4. **政治术语实时对齐**：参考 `references/gov_language_guide.md` 中的最新表述，逐一校验。
5. **引用标准使用"参考"表述**：GB/T 9704 标准引用标注为"参考"，不暗示为官方文件或具有法律效力。

---

## 依赖的底层 Skill

本 Skill 编排并复用以下底层能力：

| 底层 Skill | 用途 | 调用时机 |
|-----------|------|---------|
| pptx-generator | 生成 PPTX 文件 | Pipeline P Step 6 |
| minimax-docx | 生成 DOCX 红头公文 | Pipeline D Step 3 |
| infographic-maker | 生成数据信息图 | Pipeline P Step 7（可选） |

以上所有底层 Skill 必须已安装才可正常使用本 Skill。如果检测到缺失，应明确告知用户需要安装对应的 Skill。
