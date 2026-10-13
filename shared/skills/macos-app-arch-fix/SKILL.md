---
name: macos-app-arch-fix
description: macOS 应用「明明装了却打不开/找不到」时，排查是否为 CPU 架构不匹配（Apple Silicon 的 arm64 包装在 Intel Mac 上，或反之），并定位对应架构的安装包完成替换修复。触发词：应用找不到、装好了找不到、双击没反应、打不开、闪退、bad CPU type、架构不兼容、Apple Silicon、Intel Mac、universal binary。
agent_created: true
---

# macOS 应用架构不匹配：排查与修复

## 适用场景

用户说「我明明装好了 XX，但找不到 / 打不开 / 双击没反应」。

**核心判断**：macOS 应用装上了但无法执行，绝大多数情况不是文件损坏，而是
**二进制架构与本机 CPU 不匹配**。此时应用图标正常存在于 `/Applications`，
但双击毫无反应或提示「无法打开」，用户会误以为「没装」或「找不到」。

## 诊断步骤

### 1. 先确认应用真的存在

```bash
ls -1 /Applications | grep -i <关键词>
ls -1 ~/Applications 2>/dev/null | grep -i <关键词>
```

用 `mdfind -name <关键词>` 做全盘兜底。

### 2. 确认本机架构

```bash
uname -m                                    # x86_64 = Intel；arm64 = Apple Silicon
sysctl -n machdep.cpu.brand_string
sw_vers                                     # macOS 版本
```

### 3. 确认应用二进制架构 —— 关键一步

```bash
file /Applications/Xxx.app/Contents/MacOS/<可执行文件名>
lipo -archs /Applications/Xxx.app/Contents/MacOS/<可执行文件名>
```

可执行文件名从 `Info.plist` 的 `CFBundleExecutable` 取：

```bash
plutil -p /Applications/Xxx.app/Contents/Info.plist | grep -i CFBundleExecutable
```

结果解读：

| 输出 | 含义 |
|---|---|
| `Mach-O 64-bit executable arm64` | 仅 Apple Silicon，Intel Mac 跑不了 |
| `Mach-O 64-bit executable x86_64` | 仅 Intel |
| `Mach-O universal binary with 2 architectures` | 双架构，都能跑 |

### 4. 复现错误，确认判定

```bash
/Applications/Xxx.app/Contents/MacOS/Xxx --version 2>&1 | head -3
```

出现 `bad CPU type in executable` → 架构不匹配，诊断成立。

### 5. 追溯安装包来源

```bash
mdls -name kMDItemWhereFroms ~/Downloads/Xxx.dmg
xattr -p com.apple.quarantine ~/Downloads/Xxx.dmg
```

### 6. 检查应用是否被系统正确索引

```bash
mdls -name kMDItemDisplayName -name kMDItemContentType /Applications/Xxx.app
```

## 修复流程

1. **找到对应架构的安装包**。多数厂商的下载页会自动检测架构，但这个检测**经常不可靠**
   —— 尤其在走代理/VPN 时。优先找明确的 x64 / Intel 直链。
2. **下载后务必先验证架构再安装**（挂载 dmg 后 `file` 检查），不要盲信文件名。
3. **备份旧版**（改名而非删除），保证可回退：
   ```bash
   mv /Applications/Xxx.app ~/Downloads/Xxx.app.bak-<架构>
   ```
4. **安装**（用 `ditto` 而非 `cp -R`，能正确保留签名与扩展属性）：
   ```bash
   hdiutil attach ~/Downloads/Xxx-x64.dmg -nobrowse -mountpoint /tmp/mnt
   ditto /tmp/mnt/Xxx.app /Applications/Xxx.app
   xattr -dr com.apple.quarantine /Applications/Xxx.app
   hdiutil detach /tmp/mnt
   ```
5. **重新注册到 Launch Services**（确保 Launchpad / Spotlight 能搜到）：
   ```bash
   /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f /Applications/Xxx.app
   ```
6. **验证**：`file` 看架构、`codesign -v` 看签名、试运行看是否还报 `bad CPU type`。

## 已验证的案例

### ChatGPT / Codex 桌面版（OpenAI）

- Bundle ID `com.openai.codex`，TeamID `2DC432GLL2`。
- **Apple Silicon 版**：`https://persistent.oaistatic.com/codex-app-prod/ChatGPT.dmg`
- **Intel x64 版**：`https://persistent.oaistatic.com/codex-app-prod/ChatGPT-latest-x64.dmg`
- 版本信息源：`https://persistent.oaistatic.com/codex-app-prod/appcast.xml`
  （注意：该 appcast 只含 arm64 条目，Intel 版无法自动更新，升级需手动重下。）
- 文件名里没有 `x64` 的那个就是 arm64 版 —— 官方下载页会因此把 Intel 用户引到错误的包。

## 注意事项

- `bad CPU type in executable` 与文件损坏、签名失效是**不同**的问题，不要重装或修复权限，直接换架构版本。
- 替换 `/Applications` 下的应用属于系统级改动，**先备份再替换**，并告知用户备份位置。
- 若应用正在运行，先退出再替换。
- 清理旧版应用/旧安装包走**废纸篓**，不要 `rm`。沙箱环境下 `osascript` 调 Finder `delete` 会报
  「权限违例 (-10004)」，回退方案是 `mv <file> ~/.Trash/`（效果等同，但 Finder 的「放回原处」
  可能失效，需提醒用户手动拖回原目录）。
- 若厂商确实不提供 Intel 版，退路依次为：旧版本（如 ChatGPT Classic）、CLI 版本、网页版。
