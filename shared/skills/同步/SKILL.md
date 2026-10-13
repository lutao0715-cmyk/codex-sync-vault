---
name: 同步
description: 在公司 Mac 与家里 Windows 之间推拉 WorkBuddy 的技能与记忆文件。触发词：同步、同步一下、同步下、帮我同步、两台同步、跨设备同步、同步技能、同步记忆、推一下、拉一下、把改动推上去、拉最新、看看同步状态、同步了吗、wbsync、sync。
agent_created: true
---

# 同步 · 两台机器的技能与记忆互推

## 一句话

在任一台改完东西，跑一次同步即可。**Mac 端已实现打开 WorkBuddy 后自动同步**（launchd 每 5 分钟侦测一次，检测到 WorkBuddy 运行且当天未同步过，则自动完成完整同步——提交→拉取→推送→校验），**Windows 端自动拉取仍通过计划任务执行**，**推送需要手动触发**——本技能就是那个触发器。

「多久跑一次」取决于内容有没有变，不是时间。技能和记忆是低频改动，实际一周 1–3 次；两台都没改就不用跑。

## 触发场景

- 用户说「同步」「同步一下」「推一下」「拉一下」
- 用户问「两台一致吗」「Windows 那边的东西我这边有了吗」
- 在任一台新增/修改了技能、更新了 `MEMORY.md` 等记忆文件，需要让另一台看到
- 排查「刚在另一台改的东西怎么没生效」

## 执行流程（四步，别跳步）

### 第 1 步 · 先看状态，别盲跑

| 平台 | 命令 |
|---|---|
| macOS | `sh ~/.workbuddy/sync/wb-status.sh --fetch` |
| Windows | `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.workbuddy\sync\wb-status.ps1" --fetch` |

**`--fetch` 不能省。** 脚本报告的「远端」读的是**本地缓存的远端引用**，这个缓存可能停在几小时甚至几天前——最典型的场景是自动拉取因为「本地有未提交改动」反复跳过，连 fetch 都没做过一次。此时不带 `--fetch` 会看到「待拉取 0」而误判成「两台已一致，不用跑」，**而远端其实早就有新提交**。这个坑实测踩过。

`--fetch` 会先静默更新远端引用再报告：只读、20 秒超时兜底，慢也就慢 20 秒。脚本另有兜底提示——若引用超过 30 分钟未更新，会在末尾提醒你补 fetch。

输出会给出：本地/远端提交号、未提交项数、待推送与待拉取的**文件数**、自动拉取任务状态、上次拉取时间。脚本只读，不产生任何副作用。

**为什么必须先看**：状态决定要不要跑、以及跑的时候要不要特别小心。尤其「待拉取文件数」——它预示了下一步的耗时风险。

### 第 2 步 · 判断

| 状态 | 动作 |
|---|---|
| 待推送 0、待拉取 0、无未提交 | 两台已一致，**不用跑**，直接告诉用户 |
| 有未提交改动 或 待推送 > 0 | 需要跑（推送方向） |
| 待拉取 > 0 | 需要跑（拉取方向） |
| 状态脚本报「未完成的 rebase」 | **先处理冲突**，见下文 |

### 第 3 步 · 执行

| 平台 | 命令 |
|---|---|
| macOS | `bash ~/.workbuddy/sync/wb-sync.sh` |
| Windows | `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.workbuddy\sync\wb-sync.ps1"` |

脚本内部依次做：提交本地改动 → 拉取远端（rebase）→ 推送 → 校验路径过滤器。

**⚠️ 必须后台执行，不要前台等。** 原因见下节第 1 条。在工具里用 `run_in_background: true`，完成后再收结果。

用户也可以自己跑：Mac 上已配好别名 `wbsync`（写在 `~/.zshrc`）；Windows 上双击 `2-SYNC.bat`。

### 第 4 步 · 汇报（简短，别贴日志）

只讲三件事：
1. 这台推了什么 / 拉到了什么（几个提交、几处改动）
2. 两台现在是否一致（同一个提交号 = 一致）
3. 有没有需要人处理的（冲突、失败）

没有异常就别展开讲原理，用户要的是「同步好了」。

## 踩过的坑（都真踩过，按顺序看）

### 1. 前台执行会被超时杀掉 → 留下烂摊子

拉取涉及大量文件时，每个文件都要过一次路径过滤器（逐个 fork `sed`），3000+ 文件实测超过 120 秒。前台跑会被超时中断，后果比慢更糟：

- 留下 `.git/index.lock` → 之后所有 `git reset` **静默失败**（报错被吞掉你会以为恢复了，其实没有）
- 留下几百到几千个「半检出」的碎片文件（untracked）

**所以：一律后台跑。** 已经中断了，按下面顺序救：

```sh
cd ~/.workbuddy
ps aux | grep -E "git (rebase|merge|pull)" | grep -v grep   # 1. 确认没有 git 进程还在跑
rm -f .git/index.lock                                       # 2. 清锁（关键，否则后面全是白做）
rm -fr .git/rebase-merge .git/rebase-apply                  # 3. 清 rebase 临时目录
git status --short                                          # 4. 确认 HEAD 完好、看残留
git reset --hard HEAD                                       # 5. 工作区回到 HEAD
```

`git clean -fd` **用之前必须先验证**：把每个 untracked 路径拿去 `git cat-file -e origin/main:<path>` 核对，确认远端都有（即它们只是碎片、不是本机独有文件）才能清。否则会删掉本机独有的东西。

### 2. 别吞掉报错

第 1 条里 `git reset --hard HEAD` 失败时如果写成 `>/dev/null 2>&1`，你会看到「工作区依然脏」却找不到原因。**诊断阶段绝不重定向 stderr**。

### 3. 冲突的正确解法

两台都改了同一文件才会冲突，脚本会停下并列出文件。逐个看两边版本再决定：

```sh
git show <本地提交>:<文件>      # 本机版
git show <远端提交>:<文件>      # 远端版
```

取某一版并继续（**用 `git show >` 重定向比 `git checkout --theirs` 稳**——后者在批量循环里会个别失败）：

```sh
git show <要保留的提交>:<文件> > <文件>
git add <文件>
GIT_EDITOR=true git rebase --continue
```

本仓库的冲突几乎都出在 `_skillhub_meta.json` 这类**安装元数据**上（技能安装版本号），内容更新的一方优先。

### 4. `$变量` 后面紧跟全角字符会被吞字节（静默 bug，踩过两次）

`echo "登录时 + $IVH）"` 里的 `）` 是全角括号，bash 会把它的首字节并入变量名，结果变量展开成空（或取到不存在的变量）、全角符号也残缺，**而且不报任何错**——只是输出悄悄少了一段。

- 第一次踩：`$PLIST` 紧跟全角冒号 → `set -u` 下报 unbound variable
- 第二次踩：`$IVH）` → 没开 `set -u`，静默丢内容，表现为终端里半个乱码字符

**规矩：脚本里 `$变量` 后面只要不是 ASCII 字母数字下划线，一律写成 `${变量}`。**

新增/修改 `.sh` `.ps1` 后自查一遍：

```sh
python3 -c "
import re,pathlib
bad=re.compile(rb'\\\$[A-Za-z_][A-Za-z0-9_]*[\x80-\xff]')
for p in list(pathlib.Path('sync').glob('*.sh'))+list(pathlib.Path('sync').glob('*.ps1')):
    for m in bad.finditer(p.read_bytes()):
        print(p, p.read_bytes()[:m.start()].count(b'\n')+1)
"
```

写新脚本时顺便加 `set -u`——能让这类静默问题当场暴露，而不是靠肉眼发现乱码。

### 5. 跨平台 `stat`：`stat -f %m` 在 GNU 下不报错，却返回垃圾（Windows 端实测）

取文件 mtime 的常见写法 `stat -f %m file || stat -c %Y file` **只在 macOS（BSD stat）上成立**。Git Bash 用的是 GNU stat，而 GNU 的 `-f` 是「filesystem 模式」——`stat -f %m .git/FETCH_HEAD` 既不报错、也不给 mtime，而是返回一大段多行文件系统信息（含 `File: ".git/FETCH_HEAD"` 行）。这段字符串被塞进 `$(( ... ))` 整数运算时，bash 把首词 `File` 当变量名 → `set -u` 下报 `File: unbound variable`；不开 `set -u` 则静默算错。

**正确写法：先 GNU（`-c %Y`）后 BSD（`-f %m`），并校验输出是纯数字才算数。**

```sh
FETCH_EPOCH=""
for _fmt in "-c %Y" "-f %m"; do
  _v=$(stat $_fmt .git/FETCH_HEAD 2>/dev/null) || continue
  case "$_v" in ''|*[!0-9]*) continue ;; esac
  FETCH_EPOCH=$_v; break
done
unset _fmt _v
```

判据：**凡是「靠报错来切换平台」的写法，都要先确认该写法在另一个平台上真的会报错。** 不报错却返回错误内容 = 最阴险的一类。（2026-10-11 修复于 `sync/wb-status.sh`。）

### 6. 其他常见现象

| 现象 | 原因 | 处理 |
|---|---|---|
| 自动拉取一直「跳过」 | 本地有未提交改动（设计如此，不把半成品卷进合并） | 先跑一次手动同步推送 |
| Mac 上自动拉取显示「已配置·未加载」 | plist 已就位但 launchd 未加载 | 登录/重启后自动生效；期间拉取手动跑即可 |
| Windows 上「自动拉取」误显示「未安装」 | 状态脚本靠 `schtasks` 查计划任务；在某些受限/沙箱环境里 `schtasks.exe` 被禁止执行，读不到任务 | 别只看这一行，以「上次拉取」时间和 `git rev-list --left-right --count HEAD...origin/main` 为准 |
| 工作区文件里出现 `__WB_HOME__` 或 `C:/Users/win` | 路径过滤器没生效 | 跑 `sync/verify.sh` 看提示；脚本开头已内置自愈配置 |
| `Repository not found` | 远端仓库名/属主不符，或 SSH key 挂在另一个账号 | `ssh -T git@github.com` 看返回的用户名是否与仓库属主一致 |
| 推送认证失败 | SSH 配置问题 | 检查 `~/.ssh/config` 里的 `IdentityFile` + `IdentitiesOnly yes` |

## 绝对不要做的事

- **不要在两台同时跑同步。** 交替使用，各自改完推一次。
- **不要同步 `workbuddy.db`。** SQLite 双机同写必损坏，那是 134 条会话 + 8 个工作区 + 8 个自动化的索引。仓库的 `.gitignore` 已经排除，别手工加回来。
- **不要指望对话历史跟着走。** 会话正文在 `projects/**/*.jsonl`，索引在 db 里，两者分离；db 又不能同步。跨机延续只能靠重要结论沉淀进 `MEMORY.md`。
- **不要把 `binaries/` `plugins/` 缓存 `logs/` `traces/` 纳入仓库。** 体积大且是机器本地状态。插件目录只精确放行专家包（`plugins/marketplaces/my-experts/`）。
- **不要图省事在仓库里扩大 `plugins` 白名单**——`!/plugins/` 这种写法会放进几百 MB 插件缓存，之前踩过。

## 底层原理与首次搭建

日常同步只看本技能即可。**首次接入新机器**、或要改同步机制本身（换远端、调间隔、改过滤器），看技能 `workbuddy-cross-device-sync`，那里有完整的数据分区结论、路径归一化实现、接入脚本说明。

仓库位置：`~/.workbuddy`（就是一个 git 仓库，`.gitignore` 白名单式纳管）。远端是 GitHub 私有仓库 `workbuddy-sync`，认证走 SSH。
