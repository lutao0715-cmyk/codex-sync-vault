何时读本文件：需要单环节命令的完整参数与退出码细节时。根入口只给路由和速览，参数以本文件与 `svf <cmd> --help` 为准。

# svf CLI 参数速查

## 命令表

| 命令 | 参数 | 职责 |
|---|---|---|
| `svf build` | `--brand <brand.json 路径>` `--project <项目目录>` | 一条龙:tts(批指纹判环节是否跑+段级指纹判哪些段重打:未变 cached;改稿=拦+报 K/N,force 只重打漂移段)→ check → render → mix → cover;失败退出 1 并点名环节,零参数续跑 |
| `svf clean` | `--project <项目目录>` | 清可再生中间产物(assets/audio/、renders/*.tmp.mp4、.factory/state.json);**不动** renders 历史与 cover.png;clean 后重建因 wav 仍在,tts 重打须 `SVF_FORCE_TTS=1` |
| `svf tts` | `--brand` `--project` `--speed <0.5-100,默认 1>` | TTS 逐条生成 `assets/voice/NN.wav`(48kHz 立体声;走自家配音网关,零凭证,需联网);**重打计费闸(段级)**:wav 已在时逐段对账 `assets/voice/.segments.json` 段指纹——全命中=零计费直返(不碰网关);K 条漂移=拦+报 K/N,`SVF_FORCE_TTS=1`=显式计费同意**只重打漂移段**(其余 wav 逐字节复用);换音色=全量(N/N);全量重打出口=删 wav(段表与 wav 同目录同生命周期,一并失效) |
| `svf probe` | `--project <项目目录>` | 测量 assets/voice/*.wav 时长,输出 JSON——填 index.html 时间轴的依据 |
| `svf check` | `--project <项目目录>` | **CDN 前置硬闸**(扫 index.html 与 compositions/**.html 的 http(s)/协议相对资源引用,命中即拒,build 编排内同闸)→ hyperframes check 透传(语法/对比度/重叠) |
| `svf render` | `--project <项目目录>` | hyperframes render 透传,产出 `renders/<项目>_<时间戳>.mp4` |
| `svf mix` | `--brand` `--project` | 重建人声轨 + loudnorm 两遍 + BGM,输出 `renders/video-vertical.mp4`(tmp+原子改名);**混音前时长校验闸**:wav 实测 vs index 声明偏差 >0.1s 拒混;**BGM 源闸**:源时长不足时自动无缝循环补齐铺满全片,stderr 告警(不拒混),JSON `bgm.looped=true` 标记 |
| `svf cover` | `--project <项目目录>` | 从成片第 0 帧导出 `cover.png` |
| `svf background` | `--project <项目目录>`，配 `--image <本地 PNG/JPEG>`、可选 `--scope <范围>`、可选 `--preview`；或只给 `--scope` 改范围；或 `--clear` 撤销 | 当前项目的一张静态氛围背景图；不发网络、不跑 TTS/check/render/mix/cover，先预览后确认应用 |
| `svf qc` | `--project <项目目录>` `--video <mp4,缺省 renders/video-vertical.mp4>` | 对已成片独立复跑质检(白屏/墨迹/重心双带/时间轴/孤字/响度/时长 + BGM 覆盖观测;wav 只读 ffprobe 测量),stdout 单张 JSON;不写 state、零网络零计费——复核与终检用 |
| `svf timeline` | `--project <项目目录>` `--apply <写回开关,缺省 dry-run>` | 时间轴重排一条龙:wav 实测→成文规则排表(cover 2.0s 固定/场景时长=wav 实测/start 链式累加/**末场景=实测+0.5s 收尾余量归场景窗,root=末场景 end**;audio 声明时长保持 wav 实测不跟场景窗)→补丁 JSON 预览(每场景新 start/duration/root 总长+逐文件编辑数);`--apply` 写回 index.html 四类落点+帧内两处(全部锚定型定位,零数值全局替换)+重解析自校验;**dry-run 即全量校验,index 落点任一未命中=零写入报锚上下文**——换音色/改稿后四处同步的替代命令,不再手改 |
| `svf speedup` | `--project <项目目录>` `--factor <0.5~2.0,缺省=数据根 profile,再缺省 1.15>` | 对既有成片(mix 产物)整体变速出倍速件 `renders/video-vertical-<倍速>x.mp4`(视频 setpts+音频 atempo,音调不变);**内建响度复测**(锚定 -14±3 LU):越带自动 loudnorm 校正后复测,仍越带退出码 1;母带只读、tmp+原子改名;零网络零计费 |

## 通用契约

- 二进制自发现(开工先查,绝不问用户):按序 `which svf` → `~/.svf/bin/svf`;命中即用;两处都无 = 未安装,按失败表末行报人话;
- stdout 只出机器可读 JSON(probe/build/mix/tts 均可管道给 jq);进度日志全走 stderr,`[svf]` 前缀;
- 退出码 0=成功,1=失败(失败原因在 stderr 末行);
- 全参数化、非交互:所有输入来自命令行参数与项目文件,没有问答式输入。
- 文案候选制边界(详规见 `references/production.md`「开工确认轮」):仅封面主/副标题与 CTA 句给候选拍板;口播稿衍生浓缩(帧标题/帧内要点)自决不问,清单进交付汇报「计划承诺对齐」。

## 静态氛围背景

```text
svf background --project <dir> --image <local.png|jpg> [--scope <scope>] [--preview]
svf background --project <dir> --scope <scope> [--preview]
svf background --project <dir> --clear
```

- 输入只接受本地、可读、可由 ffprobe 解码的 PNG/JPEG。带 `--image` 未给 `--scope` 时默认 `all`；无 `--image` 的 `--scope` 复用当前项目已验证的受控图片。
- `scope` 只能为 `all`，或固定顺序的 `cover`、`body`、`cta` 非空组合：`cover`、`body`、`cta`、`cover,body`、`cover,cta`、`body,cta`、`cover,body,cta`。`all` 输出时规范化为 `cover,body,cta`。
- `--preview` 只可与 `--image` 或 `--scope` 一起使用；它只写 `<project>/.factory/background-preview.html`，stdout 输出 `mode:"preview"`、预览路径、canonical `scope` 与 cover/body/cta 代表帧。预览不导入图片、不改帧、不写 `.factory/background.json`。
- 正式应用 stdout 输出 `mode:"applied"`、canonical `scope`、项目内 `asset`、各类 `affected` 数量和 `changed_frames`；`--clear` 输出 `mode:"cleared"`、`cleared_frames` 与 `removed_files`。
- 图片副本只写当前项目 `assets/img/svf-background/`，状态只写 `.factory/background.json`；不写 `brand.json`、品牌资产或用户原图。固定预设为 `cover` 裁切、压暗、色罩和暗角（**不虚化**，图片本身看得清），不能调参；背景不放宽 framecheck 或 QC。
- 背景协议见 `references/background.md`：只在用户主动给图或明确要求背景时触发，先展示三类预览，取得确认后再正式应用。AI 自动配图、搜图、推荐、多图、动态背景不在本技能范围。

## 典型失败与处置

| stderr 特征 | 处置 |
|---|---|
| `build 失败于 <环节>: <原因>` | 修该环节问题后零参数重跑 `svf build`,已成功环节自动 cached |
| `失败于 白屏扫描: N 个空白采样点: [时间点...]` | 对应场景有近空白帧(元素 clip 早于场景窗口过期),修复该帧后重跑 |
| `失败于 墨迹扫描: N 个安全区越界采样点` | 帧内墨迹(含插画)越四边安全区:按质检单 `qc.pixel_scan.violations` 的类别与 bbox 修帧(bbox 为对象 `{x0, x1, y0, y1}`),零参数重跑 |
| `失败于 重心闸: N 个信息帧重心严重偏离`(build/qc) | 信息帧墨迹重心越收工带(带值与定标口径见 `references/red-lines.md`;版式定标不追存量老片,复跑被拦属预期):按质检单 `qc.centroid_scan` 的逐帧重心值把信息区整体下移/上移后重渲染;warnings 为轻度偏离不拦,修正后复检 |
| `失败于 时间轴闸: N 条场景时长与配音实测偏离`(build/qc) | 逐条 `data-duration` 与 wav 实测偏离 >±0.3s,或场景窗终点与窗内**最末条人声**实测终点偏离 >±0.3s(截断/静悬):重排用 **`svf timeline --apply` 一条命令**(实测→排表→四类落点+帧内同步+自校验;可先 dry-run 看补丁),手改四处(场景 data-duration / root 总时长 / gsap tl 锚 / 帧内 duration)仅作命令不可用时的回退手段;**一场景多声条合法**(逐条拼满窗口即可)、窗内片头静默合法;**末个含人声场景片尾收尾 +~1s 是设计自由不拦**(只有截断方向拦);`qc.timeline_gate.warnings`(相邻条重叠/乱序/条数不符/悬空条)不拦但须逐条过目;**自算排布重叠判定 MUST 带 ε≥1e-6 浮点容差**——实测时长累加与逐条解析存在 ~1e-15 量级残差,零容差判定必误报(历史实案 duplicate_audio_track:7e-15 残差误报 overlap,反向修 0.001 又制造真边界,两轮折腾);自检口径 MUST NOT 严于内建闸 0.3s 容差 |
| hyperframes check 的 lint 报「尾首相接疑似重叠」 | (前段 end 与后段 start 数值相等)时,多为 lint 显示层四舍五入伪象——以 svf timeline_gate(±0.3s 口径)为准,timeline_gate 0 告警即无重叠,勿按 lint 值改表(两个历史实案同族) |
| `timeline 补丁校验失败(零写入,先修锚再跑)`(timeline) | index.html 侧落点(root data-duration/场景 div/audio/gsap 锚)有未命中:按报文的文件+锚上下文修该锚后重跑;帧内落点未命中仅报告不阻断(帧内是「该帧自持时长」,agent 手写帧可无 JS 尾) |
| `写后自校验不符`(timeline --apply) | 写回后重 parse 对账排表值不符即 bail(不回滚):报告的期望/实写明细即处置依据,按明细修后重跑 `svf timeline` 复核 |
| `时长预算超限,已拦截`(tts) | 文案预估配音超时长预算,计费前拦截(零计费):按提示砍文案至**报文给出的字数上限**(预算口径见 `references/red-lines.md`),或在 brand.json 上调 `script.target_duration_sec` |
| `倍速因子 X 超合法域`(speedup) | `--factor` 与 profile 值域均为 0.5~2.0:改用带内值;超界在触 ffmpeg 前拒绝,不产生产物 |
| `响度复测仍越带`(speedup) | 变速+自动校正后 I 仍离 -14±3 LU:母带未动可重跑本命令;持续越带=母带人声本身响度异常,先 `svf qc` 复核母带 |
| `重打计费闸`(tts/build) | assets/voice/ 已有 wav 还要重打,CLI 拦截(零计费),逐段对账 `.segments.json` 后三态:**K 条漂移(K<N)**——**先向用户说明计费影响(只计 K 条)**,确认后带 `SVF_FORCE_TTS=1` 重跑=只重打漂移段(其余 wav 复用,不漂时长);**N/N 音色变更**——全部段必重录,说明后 force 全打;**全命中**——零计费直返(不会见到本报文);全量重打出口=删 assets/voice/ 下 wav 后重跑(段表随 wav 一并失效);报文自带 K/N 与两条处置,照抄转述即可 |
| `state.json 状态文件异常,已拒跑`(build) | state 损坏不再静默全量重建(tts 属计费环节):人工修复该文件后重跑;或确认放弃缓存后删除它再全量重建(tts 重打同样受计费闸保护) |
| `混音前时长校验失败`(mix) | wav 实测时长与 index.html 声明偏差 >0.1s:时间轴没跟上新 wav → `svf timeline --apply` 重排(或先 dry-run 看补丁);wav 过旧 → 确认计费后 `SVF_FORCE_TTS=1` 重打(段级:只重打漂移段)再混 |
| `背景范围不合法` | `--scope` 只能用 `all` 或固定顺序的 `cover,body,cta` 非空组合；不要传文件名、DOM selector、乱序、重复项或 `all,body` |
| `--preview 必须与 --image 或 --scope 一起使用` | 预览需要图片输入或已有项目背景；带新图用 `--image <图> --preview`，改范围用 `--scope <范围> --preview` |
| `背景状态无效` / `背景受控副本无效` | 不手改 `.factory/background.json` 或受控副本；按报错修复后重跑同一命令，确认不再需要时用 `svf background --clear` |
| `背景范围请求了 <类别>，但 index.html 未登记此类帧` | 改为项目实际有的范围，或先补齐对应 cover/body/cta 登记帧；命令会零写入失败，不拿其他帧替代 |
| `检测到外网资源引用`(check/build 的 check 环节,渲染零外网依赖闸) | 项目引用了 http(s)/`//` 开头的 CDN 资源(gsap/字体等),断网必炸:按报错清单把引用换成项目内本地文件——gsap 用 `assets/vendor/gsap.min.js`,字体用 `assets/fonts/`,骨架从 `~/.svf/templates/` 整树起手;**旧项目文件不许搬**(存量违规项目重跑被拒是预期行为) |
| `check 失败: npm run check` | 按 stderr 中 hyperframes 输出修 index.html/compositions,error 必改,时间/布局相关 warning 也要处理 |
| `配音服务器暂时连不上`(tts) | 配音网关不可达(多为断网):联网后重跑即好,已成功环节自动 cached;`svf doctor` 的「网关连通」项断网时 WARN 属正常 |
| `免费试用已用完`/`激活已到期`(tts,403) | 服务端拦报原文进 stderr:**照文转述,不加工不猜测**——试用满引导拿码(「想要一直用,找推广员拿激活码,把码发给我即可;也可在线购买:https://svf.atomcreate.cn/buy」,拦报原文照文转述即可),到期报错自带续费指引;本地数字与服务端对不上时以服务端原文为准(激活协议见 `references/activation.md`)。**激活成功后仍被试用拦时先跑 `svf activate --status` 自诊**(只读零计费):unreadable 态=本机读不出硬件标识的环境问题,照文转述并引导联系推广员,不手改授权文件 |
| `音色未收录`(tts,400) | voice_id 不在服务端音色目录(37 条=音色菜单 36 全量+默认):读 `references/voice-catalog.md` 菜单重选,或向发放渠道反馈补录 |
| `svf: command not found`(shell 层) | 先查约定位置 `~/.svf/bin/svf` 兜底(Windows 为 `%USERPROFILE%\.svf\bin\svf.exe`);仍无 = 未安装,按 `references/installation.md` 的**报人话模板**向用户报告(零术语,不问路径) |
| `hyperframes: command not found`(check/render) | 项目不在共享根之下,npm 向上查找没命中:移到 `~/.svf/projects/` 下,或在其祖先目录 `npm i -D hyperframes`,零参数重跑 |
