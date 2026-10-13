# 版本兼容矩阵与加密草稿处理

## 一、兼容性总表（决定你走哪条路）

| 能力 | 5.9 及以下 | 6.x | 7.0 ~ 10.x | 11.x |
|---|---|---|---|---|
| 从零生成草稿 | ✅ | ✅ | ✅ | ✅ |
| 模板模式（加载已有草稿） | ✅ 明文直读 | ⚠️ 需先解密 | ⚠️ 需先解密 | ⚠️ 需先解密 |
| 自动批量导出 | ✅ | ✅（6.8 已测） | ❌ | ❌ |
| 蒙版等部分特效 | ✅ | ✅ | ⚠️ 个别失效 | ⚠️ |

**记忆口诀：生成全通，改稿要解密，导出看 6.8。**

这不是 pyJianYingDraft 的 bug，是剪映官方的版本行为变化：

1. **6.0 起**：`draft_content.json` / `draft_meta_info.json` 被加密，明文读取失效 → 模板模式断
2. **7.0 起**：窗口控件被隐藏，UI 自动化定位不到 → 自动导出断

## 二、草稿里到底哪些文件重要

一个草稿是一个**文件夹**，核心是：

```
<草稿名>/
├── draft_content.json       # 时间轴：轨道、片段、素材引用  ← 生成的对象
├── draft_meta_info.json     # 元信息：草稿名、时长、版本
├── draft_content.json.bak   # 备份（重要！读不了时可用它顶）
└── ...素材缓存、封面等
```

`draft_content.json` 只记录**素材的绝对路径**，不存文件内容。所以：
- 移动或删除素材 → 剪映里显示红色感叹号
- 换机器要连素材一起搬，且路径要一致

## 三、查版本与草稿目录

**版本**：剪映 → 设置/关于 → 版本号

**草稿目录**：剪映 → 全局设置 → 草稿位置。典型值：
```
C:\Users\<你>\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft
```
**必须以软件里显示的为准**，版本和安装方式都会改这个路径。

命令行兜底（Windows）：
```bash
dir /s /b "%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft" 2>nul
dir /s /b "%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft" 2>nul
```

## 四、6.0+ 加密草稿：三条处理路径

### 路径 A：绕开 —— 改走「从零生成」（推荐）

**模板模式不是必需的。** 模板模式的价值是复用复杂特效/花字，代价是踩加密坑。

如果你的目标是"批量产出结构一致的视频"，直接用 `create_draft` 从零生成即可，**全版本可用、零加密麻烦**。把想复用的东西（字幕样式、转场、音量配比）写进分镜计划，一样能标准化。

> 大多数人的实际需求是"批量出结构一致的片"，不是"必须复用某个特效"。先想清楚自己属于哪种。

### 路径 B：解密 → 改 → 回加密

原理：剪映自己本机就能打开加密草稿，所以加解密函数就在它自己的 `videoeditor.dll` 里。社区工具（如 `jy-draftc`）通过加载该 dll、复用其加解密入口来完成转换——**不是硬猜算法**。

已公开验证的适用版本：剪映国内版 Windows **10.3.0 ~ 10.6.5**；理论上采用 `jianying_draft_encrypt_v2` 方案的版本通用。

基本流程：
```bash
# 1. 解密：加密 JSON -> 明文
jy-draftc.exe -d "草稿目录\draft_content.json"        # 产出 *.dec.json

# 2. 用 pyJianYingDraft 对明文做替换（换素材/换文案/调轨道）

# 3. 回加密：明文 -> 剪映可识别
jy-draftc.exe -e "草稿目录\draft_content.json.dec.json"
```

**合规边界（务必守住）**
- 只对自己创建或有合法授权的草稿做转换
- 不得用于他人草稿、购买的模板、网盘下载的资源
- 不得分发破解工具或破解后的草稿
- 工具本身不提供剪映本体、不触及账号权益

**风险**：依赖特定 dll 导出函数，剪映升级可能失效；不同加密方案（v1 / v2）互不通用。

### 路径 C：降到 5.9 及以下

最省事：装未加密的旧版本，明文 JSON 全套方案直接可用。

- 优点：脚本不用改，模板模式和自动导出都能用
- 缺点：用不了新功能；要**关掉剪映自动更新**，否则一夜回到解放前

适合：脚本已跑成熟、对新功能不敏感、就想稳定量产。

## 五、模板模式的两种接法

### 明文模板（5.9 及以下）

```python
import pyJianYingDraft as draft
df = draft.DraftFolder(FOLDER)

script = df.duplicate_as_template("模板草稿", "新草稿")   # 复制后编辑，不动原稿
script.replace_text(track, 0, "新文案")
script.save()
```

三种替换：
```python
# ① 按名称替换素材（影响所有引用它的片段）
script.replace_material_by_name("audio.mp3", draft.AudioMaterial("new.mp3"))

# ② 按片段替换（可改取用范围与时长处理）
from pyJianYingDraft import trange, ShrinkMode, ExtendMode
track = script.get_imported_track(draft.TrackType.audio, index=0)
script.replace_material_by_seg(
    track, 0, draft.AudioMaterial("new.mp3"),
    source_timerange=trange("0s", "10s"),
    handle_shrink=ShrinkMode.cut_tail,
    handle_extend=ExtendMode.push_tail,
)

# ③ 替换文本（保留全部格式）
script.replace_text(track, 0, "新内容")
```

提取模板里的贴纸/花字元信息（没有名字的特性靠它定位）：
```python
df.inspect_material("模板草稿")
```

### 加密模板（6.0+）

通过 `fallback_loader` 接一个自己的读取器，把解密后的明文喂回去：

```python
def my_loader(path: str) -> dict:
    """返回解密后的明文 dict；失败就抛异常，不要静默返回空"""
    dec = decrypt_with_jy_draftc(path)     # 接你自己的解密流程
    return json.loads(dec)

df = draft.DraftFolder(FOLDER, fallback_loader=my_loader)
```

**注意**：导入的轨道与新建轨道是分离的，导入轨上不能再加片段。

## 六、自动导出的边界

```python
ctrl = draft.JianyingController()          # 前提：剪映已打开且停在目录页
ctrl.export_draft("草稿名", r"D:\out\a.mp4",
                  resolution=draft.ExportResolution.RES_1080P,
                  framerate=draft.ExportFramerate.FR_24)
```

- 底层依赖 `uiautomation`，**仅 Windows**
- 官方测试通过版本：5.9 与 6.8
- **7.0+ 控件隐藏 → 定位失败**，不是代码问题，无解，别浪费时间调试

7.0+ 的现实做法：**脚本批量生成草稿，人在剪映里逐个打开点导出**。剪辑（排轨/对轴/字幕）已自动化，只剩点按钮，仍然比手工剪快一个数量级。

## 七、防止剪映偷偷升级

自动化最怕的不是写不出来，是昨天还能跑今天不能跑。

- 关闭剪映自动更新
- 断网环境下跑批量任务，或升级前先跑一遍回归
- 把剪映版本号写进项目配置，出问题时先比对版本

## 八、升级后失效的排查顺序

1. 版本号变了吗 → 回到总表看该能力是否还支持
2. Python 还是 3.8/3.11 吗 → 否则重建 venv
3. `import` 报 `uiautomation` → 换 3.11 或先装 uiautomation
4. 模板模式报 `JSONDecodeError` → 6.0+ 加密，走路径 B 或改走 A
5. 导出报找不到控件 → 7.0+，改手动导出
6. 草稿打不开 → 检查 `draft_content.json` 是否被覆盖，回退 `.bak`
7. 素材红感叹号 → 路径变了，改绝对路径或把素材放回原位

## 九、彻底脱离剪映的备选

如果版本绑定让你痛不欲生，走独立管线：FFmpeg + moviepy 直接合成，不依赖任何剪映格式。

- 优点：永不版本失效，可控性最强
- 缺点：剪映的特效、花字、贴纸、素材库全部用不了；转场动画要自己写

适合：标准化程度高、不需要剪映素材库的纯批量场景。
