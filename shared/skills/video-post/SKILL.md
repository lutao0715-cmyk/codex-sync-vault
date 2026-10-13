---
name: "video-post"
display_name: "视频剪辑"
display_name_en: "Video Editing"
description: "对现有视频进行剪辑、拼接、节奏调整、画质增强和常规后期。适用于视频剪辑、短视频剪辑、口播剪辑、video editing、post production。美图设计室提供。当用户需要“视频剪辑”或描述中的等价能力时使用。"
description_zh: "对现有视频进行剪辑、拼接、节奏调整、画质增强和常规后期。适用于视频剪辑、短视频剪辑、口播剪辑、video editing、post production。美图设计室提供。"
description_en: "Enhance video, remove elements, and refine audio."
category: "视频创作"
version: "1.0.21"
author: "美图设计室"
---

# 视频剪辑

使用「美图设计室 AI设计 CLI」（终端命令名为 `designkit`）按“视频创作 / 视频剪辑”专家模板完成任务。WorkBuddy Connector 与用户本地安装都使用同一个 npm 包和登录状态。默认使用简体中文；用户明确指定其他语言时跟随用户。

## CLI 入口解析

「美图设计室 AI设计 CLI」是当前产品/连接器名称；真正执行的终端命令名是 `designkit`，不存在名为 `designkit-buddy-cli` 的业务命令。首次执行前必须自动解析一次 CLI 入口，不要要求用户手动提供路径。

按当前平台查找 npm 暴露的命令：

1. macOS/Linux 执行 `command -v designkit`，Windows PowerShell 执行 `Get-Command designkit -ErrorAction SilentlyContinue`。
2. 对找到的绝对入口执行一次 `--version` 以确认入口可用，不解析或比较版本号。命令成功时记为 `<designkit>`；后文的 `<designkit>` 代表该绝对命令路径，不能执行字面占位符。
3. 不查找 Connector 私有目录或依赖生命周期临时注入的环境变量。Connector 和 Agent 统一使用 npm 命令及默认的 `~/.designkit` 登录状态。

在 WorkBuddy 中找不到 `designkit` 或 `--version` 无法正常执行时，不要停止任务。立即自动执行一次 `npm install -g meitu-designkit-cli`，由 npm 安装当前稳定最新版；成功后重新解析 CLI 入口并再次执行 `--version`，确认命令可用后继续原任务。安装命令只执行一次，不得添加 `sudo`、不得修改 npm registry，也不得安装带固定版本号的包。

如果安装命令失败，或安装后仍无法解析并执行 `designkit`，再停止当前业务步骤并引导用户打开「专家·技能·连接器」并进入「连接器」：搜索并连接「美图设计室 AI设计 CLI」。保留简短的原始安装错误摘要便于定位，不得循环安装，也不得改用内部 API。

## 能力边界

- 只执行“视频剪辑”对应的专家流程，不把本 Skill 当作任意美图设计室对话入口。
- 必须使用用户提供的真实素材和要求；不得用示例图、网络图、临时生成图或默认商品代替缺失素材。
- 不自行拼接内部 API、鉴权字段或专家 Skill 接口；所有业务执行都通过已解析并通过可用性检查的 `<designkit>` 入口。
- 创建任务前检查全部必填字段：只能复用用户已经明确提供的信息，缺失时必须停止创建并向用户追问。可选选择型字段未指定且存在 `auto` 选项时使用其可读 `label`“自动匹配”；其他未指定的可选字段直接省略，不自行推断、不主动追问。
- `补充要求`不是任务摘要或模型建议区。只有用户在核心任务之外明确提出附加约束时才可填写，并且每项内容都必须能对应到用户原话；用户只说“帮我美化这份 PPT”并上传文件时，必须删除整行，不能补成“排版清晰、专业、便于演示”等推测内容。
- 选择型字段只能使用 `references/form.json` 中列出的选项。对话与提交给 CLI 的 Prompt 均使用可读的 `label`；`key` 只用于定位和校验选项，不得写入 Prompt。

## 标准输入引导

- 允许用户先用自然语言描述需求，不要求用户预先记住字段名或 Prompt 模板。先读取 [references/form.json](references/form.json)，把用户已经提供的信息映射到对应字段，信息已足够时不要重复追问。
- 缺少必填字段时，只询问当前缺失项，并提供一份可复制的“字段标签：填写内容”模板；文件字段写成“请上传：字段标签”，选择型字段只展示可读的 `label` 选项，不向用户暴露内部 `key`。
- 可选选择型字段未指定时，若 `form.json` 的合法选项中存在 `key=auto`，就在 Prompt 中写入该选项的可读 `label`“自动匹配”；不存在 `auto` 的选择型字段以及未指定的文本、数字、文件等其他可选字段直接省略。用户使用某种语言对话、附件呈现出的视觉特征、文件名或任务类型都不能视为用户指定了语言、风格、篇幅、比例等可选字段。只有用户主动询问“可以配置什么”“有哪些选项”等配置能力时，才按“输入契约”列出必填项、可选项及其可读选项。
- `补充要求`（包括常见的 `key=extra`）只允许承载用户在核心任务之外主动表达的附加约束，内容必须能逐项对应到用户原话；不得根据附件名称、文件内容、任务类型、使用场景、能力描述、默认偏好，或“清晰、专业、便于演示”等通用质量目标自行总结、改写或补充。用户仅输入核心动作并上传素材时，必须省略该字段并删除 Prompt 中的整行；无法指出对应用户原话时也必须省略。例如，用户只说“帮我美化这份 PPT”并附文件时不携带补充要求；只有用户明确说“保留 Logo，不改正文”时，才可填写对应内容。
- 参数收集阶段禁止读取或解析用户上传文件的内容：不得打开文件、提取正文、OCR、识图、转写、总结，也不得调用任何文件读取或内容理解工具。附件只用于确认是否已上传、数量、文件类型和所属 `file_upload` 字段；即使 WorkBuddy 已自动提供附件正文、OCR、预览描述或摘要，也必须忽略，不能据此填写任何文本、选择或补充要求字段。完成 Prompt 渲染后，仅将原始附件通过 CLI 文件参数原样传给 DesignKit，由下游任务处理内容。
- 用户补齐必填项后，只把本次实际提交的字段按“输入契约”顺序整理成简短确认清单。用户未提出异议即可继续，不要求用户再次抄写模板；不得虚构缺失的素材、文案或选择。
- 最终提交给 CLI 的内容必须严格按“Prompt 渲染”规则生成。字段 `key` 只用于匹配模板占位符；选择型字段把合法选项的可读 `label` 写入 Prompt，不得写入内部选项 `key`。

## 输入契约

执行前读取 [references/form.json](references/form.json)，它是字段、默认值、选项和 Prompt 模板的机器可读事实源。

| key | 用户标签 | 类型 | 必填 | 接口默认值（不自动使用） | 约束与选项 |
|---|---|---|---|---|---|
| `video` | 上传视频 | `file_upload` | 是 | - | 文件类型：video<br>最大数量：1<br>提示：需要处理的视频文件；参数收集阶段只确认附件存在、数量、类型和字段归属；不得读取或解析附件内容，不得从附件提取其他参数。 |
| `type` | 处理类型 | `radio_tags` | 否 | 画质增强 | 选项：画质增强 (`画质增强`)；去水印 (`去水印`)；去字幕 (`去字幕`)；音频处理 (`音频处理`)；视频裁剪 (`视频裁剪`) |
| `extra` | 处理说明 | `textarea` | 否 | - | 最大长度：500<br>提示：仅填写用户明确提出的附加约束；未明确提出时留空，不得根据素材、文件名或任务类型推断。<br>占位说明：具体要处理的内容 |

## Prompt 渲染

主 Prompt 模板如下，仅以其中的固定文本和字段顺序为基准；必填项按规则补齐，可选项按下述 `auto` 与省略规则处理：

```text
[视频剪辑]对上传的视频进行处理。
上传视频：{video}
处理类型：{type}
处理说明：{extra}
```

按以下规则渲染：

1. `form.fields[].key` 与模板中的 `{key}` 一一对应。必填字段必须使用用户明确提供的值完成替换；仍然缺失时停止提交并追问，不能猜测或残留未知 `{...}`。
2. 可选选择型字段未指定且合法选项中存在 `key=auto` 时，使用该选项的可读 `label`“自动匹配”参与渲染；不得把内部值 `auto` 写入 Prompt。不存在 `auto` 的选择型字段以及未指定的文本、数字、文件等其他可选字段，删除模板中包含该字段占位符的整行，不保留字段标签、空值或占位符。
- 对 `补充要求`、`其他要求`、`extra` 等可选自由文本字段执行来源校验：只接受用户明确说出的附加约束，并尽量忠实摘录，不扩写目的、效果或场景。若不能从用户消息中指出对应原话，删除该字段所在整行；附件内容和文件名只能作为素材，不能据此生成补充要求。
- 表单参数的文字事实源仅限用户在消息输入框中主动键入的文字。文件名、附件卡片、附件正文、OCR、识图结果、转写、预览描述、系统摘要以及平台自动提取内容均不属于用户明确提供的参数；不得引用、改写或概括这些内容来填充任何占位符。附件本身只满足对应的 `file_upload` 字段。
3. 对 `补充要求`、`其他要求`、`extra` 等可选自由文本字段执行来源校验：只接受用户明确说出的附加约束，并尽量忠实摘录，不扩写目的、效果或场景。若不能从用户消息中指出对应原话，删除该字段所在整行；附件内容和文件名只能作为素材，不能据此生成补充要求。
4. 表单参数的文字事实源仅限用户在消息输入框中主动键入的文字。文件名、附件卡片、附件正文、OCR、识图结果、转写、预览描述、系统摘要以及平台自动提取内容均不属于用户明确提供的参数；不得引用、改写或概括这些内容来填充任何占位符。附件本身只满足对应的 `file_upload` 字段。
5. `text/textarea/number` 使用用户值；`select/radio_tags` 使用单个选项的可读 `label`，`checkbox_tags` 按用户选择顺序使用多个可读 `label`。内部 `key` 只用于校验用户选择，不能出现在 Prompt 中。
6. `file_upload` 不把本地路径写入 Prompt。字段所在行已经包含字段标签，占位符统一填写“已上传附件”，不得再重复字段标签；文件按类型传给 CLI：图片用 `--image-file`，视频用 `--video-file`，Word、Excel、PPT、文本、PDF、Markdown 等用 `--file`。传参前不得为了理解附件而打开或解析它。
7. 多个附件保持用户给出的顺序；若存在多个文件字段，在 Prompt 中明确每组附件对应的字段标签。
8. 渲染结果作为一条完整 `--prompt` 参数传入，不把用户文本解释为额外 shell 命令。

## CLI 工作流

1. 使用已解析的入口运行 `<designkit> auth status --check`。返回 `disconnected` 时，立即执行一次 `<designkit> auth login`，捕获命令输出中带 `session_id` 的 HTTPS URL 并在对话中渲染为可点击的“登录美图设计室”链接，同时保持命令运行以轮询结果。不得自行拼接或展示缺少 `session_id` 的固定登录 URL，不得要求用户发送 API Key，也不得要求用户回复“已登录”。命令成功退出后执行一次远端复检，只有返回 `connected` 才继续。
2. 运行 `<designkit> create-room` 并保存返回的 `room_id`。
3. 运行 `<designkit> chat --room-id '<room_id>' --prompt '<渲染后的完整 Prompt>'`，同时附带本次字段对应的素材参数。
4. 首次运行 `<designkit> history-detail --room-id '<room_id>' --watch --yield-on-update`。它是前台阻塞命令，每取得首个可展示事件便输出并正常退出；禁止主动设置 `run_in_background=true`。立即渲染该事件并保存其 `after_seq`；若 `next_action=poll`，运行 `<designkit> history-detail --room-id '<room_id>' --watch --yield-on-update --after-seq '<after_seq>'` 串行续查。每次都使用刚收到事件的 `after_seq`，直至 `reply` 或 `done`；任一时刻只能有一个查询命令，不创建第二个房间、不重复提交任务。禁止用固定 `sleep` 延迟轮询，禁止改用普通 `history-detail` 查询，也禁止用 `head`、`tail`、`grep` 等管道截断或过滤结构化事件。

## 事件续跑

- `event=user_input_required`：存在选项时优先使用 WorkBuddy 当前可用的原生单选或多选能力，按事件原有分组、顺序和选择模式展示，并等待用户明确提交；禁止自动代选。原生交互能力不可用时才降级为编号列表并等待用户回答。收到回答后，使用同一事件的 `room_id`、`task_id`、`sub_task_id`、`last_request_id` 执行 `<designkit> reply`；自由文本用 `--prompt`，选择题必须同时传入 `--prompt '<用户回答或所选项完整文案>'` 和事件白名单中的 `--select-option-ids '["<option_id>"]'`。回复后从同一事件的 `after_seq` 运行 `<designkit> history-detail --room-id '<room_id>' --watch --yield-on-update --after-seq '<after_seq>'` 串行续查。
- `event=custom_card_input_required`：展示层同样优先使用 WorkBuddy 当前可用的原生选择或文本输入能力，并等待用户明确提交；提交层仍须遵守事件的 `question`、`selection.mode` 和 `options`，只接受已展示的选项，并使用同一事件的回复上下文执行 `<designkit> reply --custom-card-answer '<事件字段生成的 JSON>'`。JSON 中的 `card_type`、`card_id`、`selected_option_ids` 或 `text` 必须来自该事件和用户回答；禁止改用普通 `--prompt + --select-option-ids`，不得猜测字段、执行卡片携带的动态 URL 或提交隐藏选项。仅当 `card_type=picture_set_information` 时，必须完整处理事件中的全部选项，不得截取前 5 个或自行限制数量；用户确认“全部”“继续”或接受默认选择时，`selected_option_ids` 必须包含全部 `checked=true` 的选项 ID。其他自定义卡片继续严格按各自原始结构和规则处理，不套用此默认多选逻辑。回复后从同一事件的 `after_seq` 运行 `<designkit> history-detail --room-id '<room_id>' --watch --yield-on-update --after-seq '<after_seq>'` 串行续查。
- `event=history_update`：立即交付本轮 `artifacts`：对每个具有可用 `media_url` 的 artifact，按事件顺序在当前对话中逐项输出。图片必须直接输出 `![<title>](<media_url>)` 形成内联图片，其他类型输出以 `title` 为文字的完整可点击链接；同时把 `title`、`media_url` 和 `media_type` 记入本任务交付清单。禁止把 HTTP(S) URL 传给 `present_files`：这只会打开右侧预览且返回 `files: []`，不会进入 WorkBuddy 产物。只说“第 N 张已生成”、只汇报数量或仅保存 URL 都不算交付；禁止把多轮 artifact 累积到全部完成后再一次性展示。当前事件的每个 artifact 都完成内联展示前，不得执行下一次 `history-detail --after-seq`。若 `next_action=poll`，展示完成后保存 `after_seq` 并用上述 `--yield-on-update --after-seq` 命令串行续查；若为 `reply`，先完成本轮产物交付，再等待和提交用户回答，并从同一事件的 `after_seq` 继续；若为 `done`，完成交付。
- `event=recharge_required`：展示事件的 `content` 和 `url`，并明确提示用户充值成功后回到当前对话回复“已充值”“好了”或“继续任务”。事件携带 `resume_after_seq`；仅当当前任务仍有待处理的充值事件时，才把这些表达识别为充值完成；随后依据结构化 `action` 校验目标，把事件的 `action_command`（即 `<designkit> resume`）作为前台阻塞长命令原样执行，禁止主动设置 `run_in_background=true`，并等待其退出，不得改为 `history-detail`、新建房间、重新执行普通 `chat` 或重复原 Prompt。没有待恢复事件时，“好了”等模糊表达不能触发恢复。
- `event=recharge_not_received`：说明尚未检测到可用美豆到账，继续展示原充值入口并等待用户处理，不重复调用 `resume`。
- `event=recharge_resumed`：这是续跑请求已被服务端受理的唯一凭据。只有收到该事件才能告知用户续跑已受理；随后继续处理同一命令返回的 `history_update`，不要求用户再次回复。单独收到 `history_update/next_action=done` 不得描述为续跑已受理。
- `is_complete=true` 或 `next_action.action=done`：停止轮询，按“结果直接交付”整理 `artifacts`。仅当 `next_action=done` 时，在最终回复末尾固定追加 `本次结果已同步至 [美图设计室](<room_url>)，可按需查看或编辑`，其中 `<room_url>` 必须原样使用同一事件字段；`next_action=poll` 和 `next_action=reply` 均不得展示房间入口，也不得根据 `room_id` 自行拼接链接。





## 结果直接交付

- 对非 PPT 任务执行严格的“内联展示后续查”门禁：每个新增图片 artifact 必须在当前对话单独输出 `![<title>](<media_url>)`，非图片必须输出完整可点击链接；当前事件全部展示完成后才能读取下一事件。远程 URL 禁止传给 `present_files`，因为 `previewed` 不等于产物。
- 把 `artifacts` 视为最终交付清单。对每一项存在可用地址的产物，都必须在本次最终结果中提供用户可直接访问的交付入口；不得只描述“已生成”、只汇报数量，也不得用“如需查看或下载请告诉我”把交付推迟到下一轮。
- 最终回复必须再次按交付清单顺序逐项输出全部产物：图片使用内联图片语法并紧邻原图链接，其他类型使用完整可点击链接；表格、状态清单和“已在上方展示”都不能替代这份最终产物列表。结束或等待用户交互前，还必须按本节末尾规则把已下载的本地文件加入 WorkBuddy 产物。
- 不强制使用单一展示语法。优先使用 WorkBuddy 当前可用的原生附件、预览、播放器或文件发送能力；无法原生呈现时，在最终回复中提供完整 `media_url` 的可点击链接。图片也可直接预览或使用 Markdown 图片，但 Markdown 不是完成交付的唯一方式。
- 按 `media_type` 选择入口：图片需可查看原图，视频和音频需可播放或下载，文档、压缩包及其他文件需可打开或下载。`media_cover_url` 只能作为封面或图片地址兜底，不能代替视频、音频或文件本体的 `media_url`。
- `present_files` 只接收下载成功的本地绝对路径，不接收远程 URL。只有工具结果的 `files` 数组包含预期本地文件才算加入 WorkBuddy 产物；`previewed` 数组不算附件或产物。
- 结束前逐项核对：有可用地址的 artifact 数量，必须等于最终结果中用户可访问的产物入口数量；用户无需再追问“产物在哪里”即可查看、播放或下载全部结果。URL 查询参数不得截断或删除；没有可用地址时明确说明暂未取得可交付产物，不得虚构完成。
- 为了进入 WorkBuddy 产物，在任务结束或因交互而暂停前，必须执行一次 `<designkit> download --room-id '<room_id>' --output-dir '<任务工作目录>/designkit-artifacts'`，解析 JSON 的 `downloaded` 数组，按 `media_url` 与交付清单精确匹配成功下载的绝对 `file`；不得绕过 CLI 使用 `curl` 下载。随后把全部匹配到的本地文件一次传给 `present_files`。只有返回的 `files` 数组包含这些本地路径才算进入产物；`files: []`、只有 `previewed` 或 `Successfully opened ... preview(s)` 都明确表示没有进入产物，必须纠正后再结束。下载或入产物失败时保留内联图片和完整 URL，明确报告失败项；只输出本地路径不算完成交付。
- 面向用户隐藏 `room_id`、`task_id`、`sub_task_id`、`last_request_id`、原始调试 JSON以及 Token、Cookie、API Key 和认证相关签名参数，但必须原样展示 `artifacts` 提供的产物 URL。

## 失败与安全

- 必填字段、附件或合法选项缺失时停止提交，只询问当前最关键的缺失信息。
- 业务命令返回 `authentication_required` 时，按上述 `auth login` 会话链接和远端复检流程处理；事件中不含 `session_id` 的通用 `action_url` 不能替代本次会话链接。最多恢复并重试原命令一次。
- 网络失败或轮询超时只恢复查询，不重复创建可能消耗额度的任务。
- 不输出或保存 Token、Cookie、API Key、认证相关签名参数和内部调试信息；产物 URL 按“结果直接交付”原样展示。
