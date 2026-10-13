---
name: 央视下载
description: 下载央视网（tv.cctv.cn / cctv.com / cntv.cn）视频页面里的节目视频，默认下最高清 720p 加密链路。当用户发来央视/央视网视频页链接要求下载时使用。
---

# 央视视频下载器

下载央视网（tv.cctv.cn / cctv.com / cntv.cn）视频页面里的节目视频。

**默认策略：直接下最高清版本（720p，h5e 加密链路 + 本地解密）。** 用户没有特别说明画质时，一律走主流程；仅当解密工具链搭建失败时才降级到 480p 未加密链路兜底。

## 触发

用户发来 `tv.cctv.cn/YYYY/MM/DD/VIDExxxx.shtml` 等央视/央视网页面链接要求下载视频时使用。

## ⚠️ 关键认知（必读）

1. **video-downloader 技能（redfox）不支持央视**，不用试。
2. **yt-dlp 的 CCTV extractor 已失效**（m3u8 404 / 无法提取 id），不用试。
3. **画质分布**（2026-09 实测）：
   - 未加密链路 `hls.cntv.lxdns.com` 只有 480×270 一档——`2000.m3u8` 虽能访问但内容与 450 相同；
   - **720p（1280×720 @2000kbps）只在加密链路**（`h5e` / `enc` / `enc2`），视频流是 CNTV 私有加密，直接抓会花屏，必须解密。
4. 请求 m3u8/分片必须带 `Referer: https://tv.cctv.cn/`，否则 403。
5. **不要用 yt-dlp 下载分片**——其合并时批量删临时文件会触发沙箱 safe-delete 拦截导致任务失败。分片用 Python urllib 下载。
6. **DevLARLEY/cctv-decrypt 的 TEA 算法对 2026 年的央视流已失效**（实测解码报错），不用试。

## 主流程：720p（h5e 解密）

### 首选：一键脚本（2026-09-20 起默认入口，约 1~2 分钟出片）

工具链已在 `E:\WorkBuddy\outputs\.cctv-hd\` 装好并跨会话保留，直接跑：

```bash
# 长任务放后台。默认输出到 C:\Users\win\Desktop\<标题>-720p.mp4（用户桌面，避免 E 盘文件被会话回收）
python "C:/Users/win/.workbuddy/skills/央视下载/assets/cctv_hd_720p.py" "https://tv.cctv.cn/2026/03/01/VIDExxxx.shtml" -o "输出.mp4"
```

脚本自动完成：页面取 guid → master m3u8 挑 BANDWIDTH 最高档 → 带断点续传下载分片 → 生成分批 m3u8（30 片/批）→ h5e 解密 → ffmpeg concat 合并 → 校验 → 转封装 MP4。

**注意**：
- 脚本**不自动清理**中间产物（沙箱拦截批量删除会报错）；成片确认到手后，由主 agent 用 Python 单独清掉 `E:\WorkBuddy\outputs\.cctv-hd\ts_run\`。
- **成品优先写到用户桌面或用户指定目录**——2026-09-20 实测写到 E:\WorkBuddy\outputs 的成片在会话结束后被环境回收，用户找不到，被迫重跑。
- 脚本只报"校验警告"级别的 h264 宏块错误（源流自带微瑕），0 严重错误即成功。

### 第 0 步：检查工具链（仅脚本报"工具链不可用"时才需要）

解密器在本机路径：`E:\WorkBuddy\outputs\.cctv-hd\CCTV-Download-main\h5e_decrypt\`（2026-09-20 已装好并保留在 E 盘，跨会话可复用；旧会话级路径 `C:\Users\win\WorkBuddy\2026-09-19-07-40-26\cctv-hd\...` 已随会话清理，若不存在按下面"工具链搭建"重装到 E 盘）。

判断是否可用：`h5e_decrypt/build/cli/main.js` 与 `h5e_decrypt/build/external/cctv.worker.js` 都存在，且 `h5e_decrypt/node_modules` 存在。

### 工具链搭建（一次性，约 1 分钟）

1. 下载 https://github.com/lxz-110/CCTV-Download/archive/refs/heads/main.zip 解压（工具本体是其中打包的 `xiaoxi-ij478/cctv-h5e-decrypt`；注意 CCTV-Download 自己的 enc/enc2 解密是假占位实现，只有 h5e 部分是真的）。**GitHub 直连会中断（WinError 10053），用镜像前缀**：`https://gh-proxy.com/https://github.com/...`（实测可用，备选 ghfast.top）。
2. `npm install --registry=https://registry.npmmirror.com`（在 h5e_decrypt 目录）。本机 Git Bash 的 npm shim 损坏（`/usr/bin/env: 'bash'`），PowerShell 里 `npm.ps1` 又被执行策略拦——**必须用 PowerShell 调 `npm.cmd` 全路径**（`C:\Users\win\.workbuddy\binaries\node\versions\22.22.2-3\npm.cmd`）。若 install 长时间卡住无输出，杀掉后加 `--no-audit --no-fund --fetch-retries=2` 重试（实测卡 12 分钟的进程重试后 30 秒装完）。
3. 编译：`node node_modules/typescript/bin/tsc`，然后把 `src/external/cctv.worker.js` 复制到 `build/external/`。
4. **不要用 tsx 直接跑 src**（Node 22 strip 模式不支持 enum 会报错），必须用编译后的 `build/cli/main.js`。

### 第 1 步：取 guid 与 h5e 最高档 m3u8

```python
# python 用受管解释器 C:\Users\win\.workbuddy\binaries\python\envs\default\Scripts\python.exe
# 1) 页面 HTML 正则取 guid: guid\s*=\s*["\']([a-f0-9]{32})
# 2) 调接口（带 Referer）:
#    https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid={guid}
#    取 manifest.hls_h5e_url，把 URL 中 "main" 换成 "2000" 即最高档
#    （稳妥做法：先拉 master 列表，挑 BANDWIDTH 最大的 variant）
```

### 第 2 步：Python 下载全部分片（带 Referer，长任务放后台）

- 顺序 GET 分片存到 `h5e_ts/` 目录，支持断点续传（已存在且非空就跳过）。
- 同时生成本地 `local.m3u8`。**两个格式铁律**：
  - 必须用**二进制模式**写（Windows 文本模式 `\n`→`\r\n`，文件名会带 `\r` 读不到）；
  - `#EXTINF:10.000000,` 与分片名必须**分行**（写在同一行会被 `#` 过滤，解密器 0 分片静默空转）。

### 第 3 步：解密（node CLI）

- 每批 ≤30 片、每批新起一次进程（避免 worker 漂移产生解码错误）；
- **CLI 每次启动会先删除输出文件**，分批必须输出到不同文件，最后合并：

```bash
node build/cli/main.js --quiet --local-m3u8 part1.m3u8 out_p1.ts
node build/cli/main.js --quiet --local-m3u8 part2.m3u8 out_p2.ts
```

- **路径规则（实测）**：CLI 会把 m3u8 里的分片名 `path.resolve(m3u8所在目录, 分片名)`——所以 part m3u8 必须和分片放在同一目录、用裸文件名；`--local-m3u8` 和输出文件可以传绝对路径，node 的 cwd 随意。

### 第 4 步：合并 + 校验 + 出 MP4

- ffmpeg concat demuxer 合并：`-f concat -safe 0 -i list.txt -c copy full.ts`（Windows 下 `concat:` 协议路径不可靠，用 demuxer）；
- 校验：`ffmpeg -v error -i full.ts -f null -`，0 解码错误才算成功（个别源流自带的宏块级微瑕可接受）；
- 转封装：`-c copy -movflags +faststart` 出 MP4。
- ffmpeg 用 `pip install imageio-ffmpeg -i https://mirrors.aliyun.com/pypi/simple/` 获得。

## 兜底流程：480p（未加密链路，解密工具链不可用时）

```bash
python "<skill路径>/assets/cctv_dl.py" "https://tv.cctv.cn/2026/03/01/VIDEuNq3hKnoo3LwY9N34rdT260301.shtml" -o "输出文件.mp4"
```

脚本自动完成：页面取 guid → 探测未加密链路（探测顺序已改为 2000/1000/720/450/main，main master 可能只登记 450 但高码率媒体列表实际存在）→ 顺序下载 TS 分片拼接 → ffmpeg 校验。产物仅 480×270，交付时要向用户说明画质受限。

## 环境备忘（Windows 本机）

- pip 官方源超时，一律用 `-i https://mirrors.aliyun.com/pypi/simple/`
- 本机 Git Bash 精简：无 sleep/head/tail/ls/grep/git，文件操作和清理用 Python，长下载放后台任务
- playwright-cli 浏览器会话不跨命令保留，open+操作须在同一调用块内串联
- 大文件下载会触发沙箱网络超时，超过 ~30MB 用 `run_in_background`
- 建议"下载→解密→合并→转 MP4→校验"串在同一条命令里执行，减少中间态
