---
name: migu-gift-vap
display_name: 咪咕礼物
description: Convert live gift animation videos or generated gift concepts into Migu live platform VAP assets.
version: 2.0.0
---

# 咪咕礼物 · 一条龙：设计稿/描述 → VAP 礼物

**端到端链路**：设计帧 / 一句话描述 → AI 生成动效 mp4 → 抠透明 → VAP 打包 → 交付桌面

---

## 一条龙总流程

本技能配合同一次对话完整执行以下步骤：

### 阶段 A — 生成礼物动效 mp4

**输入**：用户提供的一张设计图（或一段文字描述）
**输出**：864×768 / 24fps / 约 5 秒的礼物动效 mp4

参数模板（已验证）：
- 分辨率：**864×768**（便于后续裁成 720 方）
- 帧率：**24fps**
- 时长：**约 5 秒**（124 帧）
- 风格：**黑白漫画风、米白纸质感底**（这样抠透明最干净，白字/牙齿不会误抠）
- 编码：h264 yuv420p（不带 alpha，后续本地抠）
- 音频：无（礼物动效静音）

**执行方式**：调用 AI 视频生成（Frame-to-Video / Image-to-Video），从设计图生成动效短片。
生成后需用户确认效果满意再进入阶段 B。

### 阶段 B — VAP 导出（一键脚本）

**输入**：阶段 A 产出的 mp4
**输出**：`<主题>-礼物N.vap`（720×720 / 24fps / vapc 盒）/ 桌面

```bash
/Users/lutao/.codex/workbuddy-runtime/binaries/python/envs/default/Scripts/python.exe \
  "/Users/lutao/.codex/skills/migu-gift-vap/scripts/vap_export.py" \
  <源视频.mp4> <输出.vap> [边长，默认720]
```

脚本自动完成：抽帧裁方 → 泛洪抠透明 → 按 VapTool 官方算法打包 RGB+alpha 双区帧 → x264 CRF18 编码 → 注入 vapc 盒 → 输出 .vap。

交付位置：E:\WorkBuddy\outputs\ → 再拷到用户桌面。
命名规范：`<主题>-礼物N.vap`（如 "爆炸了兄弟们-礼物1.vap"）

### 阶段 C — 成品校验（自动）

1. vapc 盒解析：确认 `{"info":{"v":2,"fps":24,"w":720,"h":720,...}}` 配置正确
2. 解码抽帧：叠棋盘格检查 — 背景全透、主体边缘干净
3. 文件大小检查：720×720 5 秒 VAP 约 2~4MB 合理

---

## 《一条龙》对话示例

```
用户：帮我做个直播间礼物，这句话叫"扇了"，黑白漫画风
→ 阶段A：生成动效 mp4 → 用户确认
→ 阶段B：vap_export.py 一键导出
→ 交付：扇了-礼物1.vap ✅
```

```
用户：咪咕礼物一条龙，这张图做成礼物
→ 读取设计图 → 阶段A生成 mp4 → 阶段B导出 VAP → 桌面
```

## VAP 格式关键点（踩过的坑）

1. **vapc 盒**：`struct.pack(">I", json长度+8) + b"vapc" + json字节`，用 `mp4edit --insert :vapc.bin:3 tmp.mp4 out.mp4` 注入。
2. **⚠️ mp4edit 按冒号分割参数**，Windows 盘符路径（E:\...）会被劈断 → 报 `cannot open atom file (E)` 且**返回码仍是 0**，必须用 `cwd=work_dir` + 相对路径，并校验 stderr 和输出文件大小。
3. **布局算法**（与官方 CommonArgTool 一致）：gap=4、alpha 区缩放 0.5、自动选横/竖布局（最长边最小）、最终宽高补齐到 16 的倍数。720×720 → 1088×720 横向布局。
4. **RGB 区要 alpha 预乘黑底**（官方 GetAlphaFrame 行为），alpha 区是灰度图双线性缩到 0.5。
5. **配置 JSON**：`{"info":{"v":2,"f":帧数,"w":720,"h":720,"fps":24,"videoW":1088,"videoH":720,"aFrame":[724,0,360,360],"rgbFrame":[0,0,720,720],"isVapx":0,"orien":0}}`，PointRect 序列化成数组 `[x,y,w,h]`。
6. **抠透明**：纯色纸底黑白画用"边缘连通泛洪"（scipy.ndimage.label 取触边连通域），不能全局抠色否则会把画面里的白色/浅灰抠掉。容差欧氏距离 38，羽化 1.2px。AI 生成源视频右下角常有"豆包AI生成"水印，直接把该角 alpha 置 0。
7. **验证**：解码回帧、按 rgbFrame/aFrame 切区、alpha 上采样叠棋盘格检查；确认 vapc 盒存在。
8. 规格要求 720*720 时用 `scale=-1:720,crop=720:720` 短边对齐居中裁方；帧率保持 24fps。
9. 礼物动效一般**不带音频**，编码时不混音。

## 咪咕平台规范参考

- 半屏幕大礼物：720*720 VAP；滑屏幕礼物：200*200 png/GIF/webp（如需面板小图可从视频抽精华帧缩到 200×200）
- 输出 vap 时礼物道具羽化范围不要超出绿色边框太多（平台垫图规范）
