---
name: workbuddy-cross-device-sync
description: WorkBuddy 跨设备同步【机制】的搭建、改造与深度排障（macOS ↔ Windows）。只在需要「首次接入新机器、更换远端仓库、调整拉取间隔、修改路径过滤器、日常同步失败的根因排查」时使用。注意：用户说「同步一下」「推一下」「拉一下」「两台一致吗」这类**日常操作**，请改用技能「同步」，不要用本技能。触发词：搭建同步、首次接入、接入脚本、换远端、改拉取间隔、路径过滤器、占位符泄漏、同步机制原理、同步故障排查。
agent_created: true
---

# WorkBuddy 跨设备同步

在两台及以上机器的 WorkBuddy 之间同步技能与记忆文件。

## 先讲清能力边界（别给用户错误预期）

- **官方「多端同步」只覆盖 手机 ↔ 电脑**，PC ↔ PC 不互通。技能是纯本地文件，官方不跨设备同步。
- **会话历史无法跨机同步**：正文在 `~/.workbuddy/projects/**/*.jsonl`，索引在 `workbuddy.db` 的 `sessions` 表，两者分离。而 `workbuddy.db` 是 SQLite，双机同写必损坏，绝不能同步。
- 因此同步目标是 **skill + 记忆文件**，会话靠「重要结论沉淀进 MEMORY.md」间接延续。

## 数据分区（关键，别搞错）

**可同步**：`skills/`、`_disabled_skills/`、`SOUL.md`、`IDENTITY.md`、`USER.md`、`MEMORY.md`、`mcp.json`、自定义的 `sync/` 目录。

**绝对不可同步**：`workbuddy.db`(+`-wal`/`-shm`)、`binaries/`、`plugins/`、`logs/`、`traces/`、`cache/`、`blobs/`、`device-id`、`edge-sync-*.db`。
`binaries` 体积可达 1.5G 且与系统架构绑定；`connectors/` 含 `.master.key` 加密凭证，绑定本机，换机解不开，两台各自重新登录连接器即可。

## 推荐实现：仓库放在 `~/.workbuddy` + 白名单 .gitignore

不移动任何文件，应用零感知。顶层用 `/*` 全排除，再逐项 `!` 白名单：

```
/*
!/.gitignore
!/.gitattributes
!/SOUL.md
!/IDENTITY.md
!/USER.md
!/MEMORY.md
!/mcp.json
!/skills/
!/_disabled_skills/
!/sync/

__pycache__/
*.pyc
.DS_Store
```

## 核心难点：跨平台路径归一化

技能里会有几十处写死的用户目录（如 `~/.workbuddy/binaries/...`）。macOS 是 `/Users/xxx`，Windows 是 `C:/Users/xxx`，直接同步会失效。

**解法：git filter 折叠成占位符 `C:/Users/win`。**

`.gitattributes` 挂 filter：

```
skills/**/*.md filter=wbhome
skills/**/*.py filter=wbhome
skills/**/*.json filter=wbhome
skills/**/*.sh filter=wbhome
MEMORY.md filter=wbhome
```

`.git/config` 指向仓库内脚本（**必须用相对路径** —— git 在仓库根执行 filter，这样两台机器通用）：

```
git config filter.wbhome.clean  "sh sync/path-clean.sh"
git config filter.wbhome.smudge "sh sync/path-smudge.sh"
```

`sync/path-clean.sh`（本机路径 → 占位符）与 `sync/path-smudge.sh`（占位符 → 本机路径）内部用 `uname -s` 判断平台，Windows 走 `cygpath -m "$USERPROFILE"` 拿到 `C:/Users/xxx` 正斜杠形式。

**验证方法（必做）**：往返一致性测试，`clean | smudge` 后与原文件 `diff` 必须为空。

## 仓库内脚本（本方案产出物）

| 文件 | 用途 |
|---|---|
| `sync/wb-status.sh` | **状态速览**（只读）：本地/远端位置、待推/待拉文件数、自动拉取状态。日常排查第一步 |
| `sync/wb-status.ps1` | Windows 薄封装，找到 Git 自带 sh 后调用上面的 .sh（不做第二份实现，避免漂移） |
| `sync/wb-sync.sh` / `.ps1` | 日常同步（提交→拉取→推送→校验 filter） |
| `sync/wb-pull.sh` / `.ps1` | **只拉取**，供自动任务调用（保守：本地脏则跳过、只 ff-only） |
| `sync/setup-auto-pull-mac.sh` | macOS 装/卸 launchd 自动拉取 |
| `sync/setup-auto-pull-windows.ps1` | Windows 装/卸计划任务自动拉取 |
| `sync/wb-auto-join.ps1` | Windows 一键接入（7 步，末步装自动拉取） |
| `sync/1-SETUP.bat` `2-SYNC.bat` `3-AUTO-PULL.bat` | Windows 双击入口 |
| `sync/README.md`、`sync/README-join.md` | 使用说明 |

日常同步命令：
- macOS：`bash ~/.workbuddy/sync/wb-sync.sh`
- Windows：`powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.workbuddy\sync\wb-sync.ps1"`

## 自动拉取（默认开启，推送保持手动）

**拉取自动化 + 推送手动**是最优平衡：登录那一刻用户还没动手编辑，物理上不可能冲突；推送则交给用户判断「什么时候算改完了」。

`wb-pull.sh` / `wb-pull.ps1` 必须遵守的五条：

1. **本地工作区脏 → 直接跳过**，绝不把半成品卷进合并，也不要 stash。
2. **只用 `--ff-only`**。遇到分叉就停下写日志；自动任务里绝不能留下 rebase 中间态（那需要人工介入，等于把定时任务变成故障源）。
3. **不弹交互提示**（launchd / 计划任务无终端），导出 `GIT_TERMINAL_PROMPT=0`。
4. **任何失败都以 0 退出**，只写 `sync/auto-pull.log`，避免系统反复弹错误框。
5. **launchd 的 PATH 极简**，脚本内要显式补 `/opt/homebrew/bin:/usr/local/bin`。

载体与触发：

| 平台 | 载体 | 触发 |
|---|---|---|
| macOS | launchd `~/Library/LaunchAgents/cn.workbuddy.sync-pull.plist` | `RunAtLoad` + `StartInterval=86400`（每天一次） |
| Windows | 计划任务 `WorkBuddy Auto Pull` | `AtLogOn` + `Once` 带 `RepetitionInterval` |

launchd plist 不支持变量，路径要由安装脚本写入绝对路径后生成（每台机器各跑一次 `setup-auto-pull-mac.sh`）。
`sync/auto-pull.log` 是本机状态，必须加进 `.gitignore`。

## 首次接入新机器的正确姿势

**不要直接 clone 覆盖。** 正确流程（见 `sync/wb-auto-join.ps1`）：

1. 备份现有 `skills` / `_disabled_skills` / 记忆文件到 `~/.workbuddy-backup-<时间戳>`
2. 在 `~/.workbuddy` 里 `git init` + `git remote add` + 配 filter
3. `git fetch` 后 `git reset --hard origin/main`

`reset --hard` 只会覆盖**远端已有的同名文件**，本机独有的文件仍是 untracked，会被保留 —— 之后可 `git add -A` 合并push，实现双向合并而非单向覆盖。

## 远程仓库与认证

GitHub 私有仓库最稳（跨平台无差异、不依赖同步盘客户端）。iCloud Drive 慎用：Windows 需装 iCloud for Windows，且 iCloud 对 git 裸仓库的同步会产生冲突副本。

认证走 SSH（比 PAT 好管理）：
- `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_workbuddy -N ""`
- 公钥加到 GitHub → Settings → SSH and GPG keys
- `~/.ssh/config` 指定 `IdentityFile` + `IdentitiesOnly yes`

注意：WorkBuddy 的 github 连接器通常是**只读**权限（`create_repository` 会返回 403 `Resource not accessible by integration`），建仓库和推送必须走 SSH。

## 跨平台技能适配（同步之后的独立工作）

同步完成后，技能文件到位 ≠ 能跑。需按平台分类：

- **纯提示词型**（无脚本目录、无 shell 调用）→ 直接可用
- **含命令/脚本** → macOS 写的 `/Users/` 路径、zsh 语法、`brew`、`$(date)` 在 Windows 上失效，需改成系统自适应写法
- **平台专用**（磁盘清理、CPU 架构排查、界面自动化）→ 在另一平台无意义，接受它的存在即可

排查某技能能否跨平台：`grep -E '\$\(|binaries|#!/bin|/Users/' <skill>/SKILL.md`

## 常见故障

| 现象 | 原因 | 处理 |
|---|---|---|
| 工作区文件里出现 `C:/Users/win` | filter 未生效 | `git config filter.wbhome.smudge "sh sync/path-smudge.sh"`，再 `git rm --cached -r . && git reset --hard` |
| `Repository not found` | 仓库未建 / 名字不符 / key 挂在另一账号 | 用 `git ls-remote git@github.com:<user>/<repo>.git` 逐个探测名字；确认 SSH 返回的 username 与仓库属主一致 |
| `create_repository` 403 | 连接器 token 只读 | 让用户手动建仓库，走 SSH 推送 |
| PowerShell 脚本中文乱码 | PS 5.1 按 ANSI 解析 UTF-8 无 BOM | `.ps1` 存成 **UTF-8 with BOM**，`.bat` 保持纯 ASCII；两者都用 CRLF（`.gitattributes` 固化） |
| Windows 上 filter 静默失效、`sh: command not found` | Git for Windows 的 `usr\bin`（`sh.exe` 所在）不在默认 PATH 里 | 脚本里探测 `$env:ProgramFiles\Git` 等候选目录，把 `usr\bin` 前置进 `$env:PATH` |
| 自动拉取没反应 | 任务未注册 / 工作区一直脏 | 查 `sync/auto-pull.log`；重跑 `setup-auto-pull-mac.sh` 或 `3-AUTO-PULL.bat` |
| pull 冲突 | 两台机器都改过同一文件 | 脚本会停下并列冲突文件，手工处理后 `git rebase --continue` |
| **前台跑同步卡住/被超时杀掉，之后 `reset --hard` 无效** | 大量文件逐个走 filter 超过 120s；被杀后留下 `.git/index.lock`，导致后续 `reset` **静默失败** | 先 `rm -f .git/index.lock`，清 `rebase-merge`/`rebase-apply`，再 `reset --hard HEAD`。恢复前清碎片要先核对 untracked 是否全在远端。**根治：同步一律后台执行** |
| 脚本输出里中文后面缺字、出现半个乱码字符 | `$VAR` 后紧跟全角字符（如 `$IVH）`），bash 把全角字符首字节并入变量名 → 变量展开为空且不报错 | 一律写成 `${VAR}`；新脚本加 `set -u`。**已踩两次（全角冒号、全角括号）** |
| 技能文件「到位但命令跑不通」 | 技能含 macOS 专有路径/命令，拿到 Windows 上失效 | 见下节「跨平台技能适配」，属独立工作 |

## 日常操作去哪个技能

| 用户说什么 | 用哪个 |
|---|---|
| 「同步一下」「推一下」「拉一下」「两台一致吗」 | 技能 **`同步`** |
| 「搭建同步」「接入新机器」「换远端」「改间隔」「同步报错要查根因」 | 本技能 |

## 使用规矩（务必告知用户）

**推送不要两台同时进行。** 交替使用，各自改完推一次。

「实时同步」在两台不同网络的独立机器间做不到，但**拉取侧可以自动化**：登录时 + 每天一次静默拉一次，风险极低（本地有改动就跳过）。推送保留手动，因为只有用户知道什么时候算改完了。

注意：拉取间隔曾被改为 86400（每天一次），理由写的是「省积分」——**该理由不成立，自动拉取是本地脚本，不消耗积分**。代价是另一台的内容最多滞后 24 小时。若用户希望更快拿到对方更新，改回 7200（每 2 小时）即可，重跑 `setup-auto-pull-mac.sh` / `3-AUTO-PULL.bat`。

「多久要跑一次」取决于内容变更频率，不是时间。技能和记忆是低频改动，实际一周 1–3 次；两台都没改就不用跑。
