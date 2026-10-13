# Adobe Premiere 经验库
> 越用越聪明的核心记忆。每次真实解决问题后把新条目写到最上方"高频/成功"区。
> 同类问题再次出现时，先从这里取经验。

## ✅ 已验证成功（置顶, 优先采用）
- **剪映粗剪"只做包装层"不动剪辑** → 解密旁路：剪映 11.5 草稿 draft_content.json 加密，用 `Timelines/<UUID>/template.json` 明文解析轨道/素材/字幕；花字等云端模板素材正文锁死时，去**原草稿**（复制源）的 materials.texts 里找回原文。交付草稿必须写进剪映当前根目录（2026-09-20 起为 C 盘 AppData 默认目录，注册表 custom path 已丢）+ 注册 root_meta_info.json + draft_info/draft_content 双格式，否则用户首页看不到 → `✔成功`（2026-09-20 大师包装版：语速0.97+11处断句呼吸、8花字原文原位金色重做、5处叠化、BGM原曲微降速0.28-0.5音量）
- **配音"催命感"修复** → 不改文案：整轨 atempo 0.97 + 断句间隙加长 0.3-0.8s（11 处），多出的时长由段落收尾镜头源素材自然延续吸收（锚点延长，不足则 tpad 定格/微降速兜底）→ `✔成功`
- **成片烧录字体与剪映草稿不一致** → ASS Style Fontname 用 fontTools 读出的真实家族名 + `ass=file.ass:fontsdir=.`（字体文件拷到 cwd），渲染端与草稿端统一 GaoZhiGan → `✔成功`
- **无Pr环境下整片精剪重做** → ffmpeg 四段管线（Pass A 逐镜头 CRF16 中间片 → B concat+vignette/noise/unsharp 质感 → C 配音+BGM sidechaincompress 混音+loudnorm -14LUFS → D 封装 faststart），镜头表时间轴=配音时间轴（whisper 转录定章节边界，误差0.0s）→ `✔成功`（2026-09 坦博尔x李方慧 172s 官宣片）
- **花字/字幕/章节卡渲染** → 别用 drawtext（filtergraph 转义地狱），用 PIL 预渲染 1920x1080 透明 PNG 图层 → overlay + fade alpha + enable 窗口挂到镜头 → `✔成功`
- **素材内嵌字幕/台标穿帮** → 先网格抽帧（0.5-6s 步进）排查源素材；干净窗口直接换 tin；躲不开就 punch-in 裁切（scale 1.125x 顶对齐 crop，切掉底部 ~11%）→ `✔成功`（工厂片/羽绒片内嵌旁白字幕全部清除）
- **字幕折行出现单字尾行/词中断行** → 按空格分词打包换行（≤n 字/行，超长词才硬切），绝不在词中间断 → `✔成功`
- **亮背景（雪地）字幕不清** → 字幕 PNG 里画底部渐变暗带（band≈300px，alpha 0→118 曲线），比纯阴影有效 → `✔成功`
- **Adobe Premiere·4K 卡顿** → 开启代理剪辑, 出片再切原素材 → `✔成功`
- **Adobe Premiere·调色不统一** → 用 Lumetri 套 LUT 并逐段统一白平衡曝光 → `✔成功`
- **Adobe Premiere·与 AE 联动** → 用动态链接, 改 AE 素材 Pr 实时更新 → `✔成功`

## ⚠️ 慎用/踩雷记录
- **章节卡叠在素材自带大标题上** → 章节卡（居中 92px）与品牌片片头大标题位置重叠，视觉打架；开剪辑前必须先抽帧看素材自带文字的时段与位置 → `⚠️踩雷已修复`（换 tin 避开）
- **ffmpeg concat 复用旧片段** → 改镜头表后不清空 clips/ 会新旧混杂；删 50+ 文件会触发 WorkBuddy 批量删除保护，需分批（≤30/次）删除 → `⚠️注意`
- **WorkBuddy bash 环境** → 每条命令前 `export PATH="/c/Users/win/.workbuddy/binaries/PortableGit/versions/1.2.0/usr/bin:$PATH"`；python 用 venv（`~/.workbuddy/binaries/python/envs/default/Scripts/python.exe`，含 PIL/fontTools）；ffprobe 传中文文件名会失败，先 cp 成 ASCII 名再探测 → `⚠️注意`

## 👤 用户偏好
- 成片输出：1920x1080 横版 30fps H.264，用于抖音发布；质感方向"高大上"（金色 #E5C88C + 宋体黑 + 章节卡 壹贰叁肆伍 + 英文小字）
- 配音文案神圣不可改；字幕/花字从 whisper 转录稿人工修正（李方慧/U型场地/坦博尔 等专有名词）
