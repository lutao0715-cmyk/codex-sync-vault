---
name: sync
description: 本地“同步”技能入口；当用户说同步、同步配置、同步 Codex、同步两台电脑、同步插件或同步技能时，运行 Codex portable sync 流程。
---

# 同步

这是用户日常使用的本地同步技能，中文名称是“同步”。

当用户要求同步 Codex、同步两台电脑配置、同步插件、同步 skills、或“跑一下同步”时，使用现有 `codex-sync` 实现，不要重新发明同步逻辑。

## 执行方式

默认运行：

```bash
python3 ~/.codex/skills/codex-sync/scripts/codex_sync.py sync
```

如果用户只想查看状态：

```bash
python3 ~/.codex/skills/codex-sync/scripts/codex_sync.py status
```

## 注意

- 同步仓库是 `git@github.com:lutao0715-cmyk/codex-sync-vault.git`。
- 本地 vault 是 `~/.codex/sync-vault`。
- 底层脚本会避开 `auth.json`、`.env`、sqlite、sessions、logs、cache、IPC 等不该跨设备同步的本地状态。
- 如果 Git 出现冲突，停止并告诉用户冲突文件和 vault 路径；不要删除用户本地 Codex 数据。
