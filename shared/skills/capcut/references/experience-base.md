# 剪映/CapCut 经验库
> 越用越聪明的核心记忆。每次真实解决问题后把新条目写到最上方"高频/成功"区。
> 同类问题再次出现时，先从这里取经验。

## ✅ 已验证成功（置顶, 优先采用）
- **剪映专业版·草稿/素材整体迁移到其他盘** → 关闭剪映（等 10 个进程全退）→ robocopy 复制 `%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft` 到新盘并校验文件数+字节数 → 注册表 `HKCU\Software\ByteDance\JianyingPro\GlobalSettings\History\currentCustomDraftPath` 指向新盘 → `Modules\Export\ExportPath` 一并改导出盘 → 删 C 原件 → 重开剪映验证 → `✔成功`（2026-09-19, C→E:\剪映草稿）
  - ⚠️剪映运行时改注册表会被退出时覆盖，必须先关；reg.exe 可能被安全策略禁用，用 PowerShell `Set-ItemProperty`
- **剪映/CapCut·抖音口播** → 自动字幕+文本朗读+提词器, 一键成片 → `✔成功`
- **剪映/CapCut·卡点视频** → 自动踩点+热门模板, 几秒出同款 → `✔成功`
- **剪映/CapCut·统一色调** → 先粗调一段再复制调节参数到全片 → `✔成功`

## ⚠️ 慎用/踩雷记录
（暂无 — 遇到翻车时在此登记: 场景/方案/为何失败）

## 👤 用户偏好
- 草稿位置：C 盘剪映默认库（App 配置写死，外部改 E 会被打回，用户已接受）；`E:\剪映草稿` 为完整备份（231文件/51MB，勿删）；若未来要搬 E 盘：先挪空 `E:\剪映草稿` 再让用户在 App 内设置迁移。导出位置：`E:\WorkBuddy\outputs`
- 用户做户外运动员（李方慧等）相关短视频，常从抖音/B站下载素材到 `C:\Users\win\Downloads\Video`
