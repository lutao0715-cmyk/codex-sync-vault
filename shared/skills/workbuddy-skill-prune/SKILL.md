---
name: workbuddy-skill-prune
displayName: WorkBuddy 技能精简
description: 审计并精简 WorkBuddy 已安装的 Skill。当用户说「技能太多」「精简一下 skill」「清理没用的技能」「技能瘦身」「重复的技能删掉」时使用。核心方法：读 usage-log.json 拿真实调用频次 + 校验安装时间 + 按同类收敛，把冗余技能移入隔离区（不删除），并生成一键还原脚本。
version: 1.0.0
---

# WorkBuddy 技能精简

把「装了一堆用不上的 Skill」治理成一套精干工具集。**绝不真删，只移入隔离区。**

## 关键路径（macOS）

```
技能本体        ~/.workbuddy/skills/<dir>/          移出此目录 = 停用
真实调用记录    ~/.workbuddy/usage-log.json         skills / mcps / activeDays
官方连接器技能  ~/.workbuddy/connectors/skills/     不受影响，别动
市场来源副本    ~/.workbuddy/buddy-skill-store/     移出后可能被重新同步
隔离区          ~/.workbuddy/_disabled_skills/<批次>/
```

没有官方卸载 CLI。技能本体就是目录，`mv` 出去即停用。

## 执行步骤

### 1. 盘点现状与体量

```bash
ls C:/Users/win/.workbuddy/skills | wc -l
du -sh C:/Users/win/.workbuddy/skills
for d in C:/Users/win/.workbuddy/skills/*/; do
  f="$d/SKILL.md"; [ -f "$f" ] || continue
  echo "$(basename $d) | $(grep -m1 '^description:' $f | cut -c1-80)"
done
```

### 2. 拿真实调用频次（最重要的一步）

```bash
python3 -c "
import json
d=json.load(open('C:/Users/win/.workbuddy/usage-log.json'))
print('activeDays:', d.get('activeDays'))
rows=[(len(v.get('recentDates',[])), v.get('lastUsedDate',''), k) for k,v in d['skills'].items()]
rows.sort(reverse=True)
for n,last,k in rows: print(n, last, k)
"
```

**陷阱**：`usage-log.json` 只覆盖最近一段窗口（看 `activeDays`）。
**「日志里没有」≠「没用过」** —— 必须配合第 3 步的安装时间一起判断。

### 3. 校验安装时间，排除「刚装的」

```bash
for d in C:/Users/win/.workbuddy/skills/*/; do
  printf '%-48s %s\n' "$(basename $d)" "$(stat -f '%Sm' -t '%Y-%m-%d' "$d")"
done | sort -k2
```

安装时间晚于日志窗口的技能 → **刚装的，代表近期意图，不动**。

### 3.5 体检运行依赖（最容易翻车的一步）

技能"装得上"不等于"跑得通"。**先查它依赖的外部程序在不在**，否则会把唯一能用的留下、把能用的砍掉。

```bash
which ffmpeg ffprobe edge-tts designkit
```

本机历史缺口：无 `ffmpeg` / `ffprobe` / `edge-tts`，Python 侧无 PIL / numpy / pydub / pyyaml。
→ 凡靠 ffmpeg 合成、靠 edge-tts 配音的技能都是**摆设**。

**判定逻辑**：
- 纯文本类（写提示词 / 写稿 / 写分镜）→ 不依赖外部程序，**装即用，优先级高**。
- 依赖缺失的本地生产类 → 要么先补依赖再谈去留，要么明确告诉用户"留着也跑不出结果"。
- 依赖**付费 SaaS**（OAuth / 订阅）的 → 用户没订阅就等同不可用。
- ⚠️ SKILL 里写明「AI 自己下载并执行安装脚本」的第三方技能 → 单独点名风险，别默默留着。

### 4. 判定（按优先级）

| 情形 | 处置 |
|---|---|
| 平台不兼容（如 Windows 专用 pywinauto 跑在 macOS 上） | 移出 |
| 纯安装器、且目标工具已就绪 | 移出 |
| 功能被**已连接的官方连接器**完整覆盖 | 移出（连接器带授权，更权威） |
| 同类技能 ≥3 套 | 收敛到 1–2 套主干，其余移出 |
| 与工作无关的娱乐类 | 移出 |
| 依赖缺失 / 依赖付费 SaaS 且用户未订阅，短期跑不通 | 优先移出（比"功能重复"更硬的理由） |
| 纯文本、装即用、且对应用户现有工作流 | **保留**（哪怕"同类多"） |
| 个人习惯类工作流（周报 / 纪要 / 需求文档，体积小） | **保留** |
| 业务专属、重建成本高 | **保留** |
| 排障类小件（<20K，「踩过一次坑」的解法） | **保留** |
| description 字段损坏 / 触发词为空 | 移出（本来也触发不了） |

### 5. 执行隔离（可逆）

```bash
Q=~/.workbuddy/_disabled_skills/$(date +%Y%m%d)-batchN
mkdir -p "$Q" && cd ~/.workbuddy/skills
for s in 技能目录名...; do [ -d "$s" ] && mv "$s" "$Q/" && echo "移出 $s"; done
```

### 6. 生成 / 更新还原脚本

`~/.workbuddy/_disabled_skills/restore.sh`：

```bash
#!/bin/bash
ROOT="$HOME/.workbuddy/_disabled_skills"; DEST="$HOME/.workbuddy/skills"
if [ $# -gt 0 ]; then
  for name in "$@"; do
    src=$(find "$ROOT" -maxdepth 2 -type d -name "$name" | head -1)
    [ -n "$src" ] && mv "$src" "$DEST/" && echo "已还原: $name" || echo "未找到: $name"
  done
else
  for src in "$ROOT"/*/*; do
    [ -d "$src" ] || continue
    mv "$src" "$DEST/" && echo "已还原: $(basename "$src")"
  done
fi
```

注意 `[ -d "$src" ] || continue` 不能删——否则会把 README.md 当技能搬走。

### 7. 写交接文档并告知用户

在隔离区留 README.md：移出清单+原因、保留清单+原因、还原命令。
回复时说明：**移动 ≠ 删除，重启 WorkBuddy 生效，一条命令可整体还原。**

## 硬规则

- 永远用 `mv`，永远不用 `rm -rf`。
- 移出**任何**「疑似用户常用」的东西之前，要么放进保留区，要么在回复里点名让他一句话恢复。
- 别只看日志：新装的技能日志里必然没有。
- **先查依赖再下刀**：把"装即用"的砍掉、把"缺依赖跑不通"的留下，是最典型的失误。
- 分两批走：第一批只动「平台不兼容 / 被官方连接器覆盖 / 明星重复」这类无判断风险的；
  第二批再动需要主观取舍的（视频、个人工作流）。中间留出复核。
- 同一次任务里自己发现的错误，当场回滚并在交接文档里写明"曾移出、已还原、原因"——
  比装作没发生过有用得多。
- 省磁盘不是重点（通常总共才几 MB），重点是**减少描述重叠导致的误触发**。
