---
name: hot-topic-report
description: Generate the daily hotspot action pack for「滑雪研究院」and the outdoor account, covering Douyin trend tags and Xiaohongshu official activities.
---

# 热点 · 每日作战包

> **服务账号**
> - `ski` = 抖音「滑雪研究院」（滑雪垂类 · 专业/资讯/教学）
> - `outdoor` = 户外运动号（泛户外 · 陆地/水上/雪上/跑步 · 生活方式向）
>
> 每个账号一节，节内含 **抖音**（实时标签）+ **小红书**（官方活动/趋势）两部分。

## 触发场景

- 「今天有哪些适合我的话题 / 标签 / 活动」
- 「今天热点」「今日热点」「热点报一下」
- 「今天抖音哪些标签热门」「小红书有什么活动能参加」

## 执行步骤

1. 运行脚本：

```bash
C:/Users/win/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe \
  "C:/Users/win/.codex/skills/热点/scripts/hot_report.py" \
  --save E:/Codex/hot-report/$(date +%Y-%m-%d).md
# 只要某一个号： --account ski  或  --account outdoor
```

2. 检查小红书情报库新鲜度：读 `C:/Users/win/.codex/skills/热点/xhs_intel.json` 的 `updated` 字段。
   **若距今超过 30 天，或用户明确要「最新小红书热点」，先用 WebSearch 搜一轮官方活动再更新该文件**，然后才跑脚本。
   搜索方向：`小红书 <垂类> 官方活动 话题`、`小红书 户外薯 活动`、`小红书 <季节> 活动 话题`。
3. 脚本输出即 Markdown，整理后直接回复，不要复述原始 JSON。
4. 补 1~2 句针对性建议（今天最值得带的 2~3 个、哪个活动该参加）。
5. 存档按天落一份到 `<workspace>/hot-report/`，同名覆盖当天。

## 两个平台的数据来源与限制

### 抖音 —— 自动抓取 ✅
- 主源：`douyin.com/aweme/v1/web/hot/search/list/`，需先 GET `douyin.com/hot` 拿 `__ac_nonce` cookie
- 备源：`iesdouyin.com/web/api/v2/hotsearch/billboard/word/`（无 cookie）
- board_type：0=综合热榜，1=上海同城榜；其余值无效
- label 含义（已用官方图标确证）：**9=挑战（官方主推话题）**，3=热，1=新，11=剧集，16=辟谣
- 热榜约 10 分钟刷新，要「最新」就重跑

### 小红书 —— 实时热搜抓不到 ⚠️
- 实测结论（2026-09-24）：热搜页 302 跳登录；web API 需 `x-s` 签名（返回 500）；未登录 SSR 数据里只有配置项（`loggedIn:false`）
- **替代方案**：维护「官方活动 + 平台趋势」情报库 `xhs_intel.json`
- 对垂类账号来说这个替代品**价值反而更高**——官方活动有真实流量扶持，趋势数据能定选题方向
- 若将来要拿实时热搜：需要浏览器自动化 + 用户登录态（可作为升级路径，成本较高）

## 核心认知

1. 抖音热榜里的**事件聚合词是流量结果**，带它没有引流价值，只作选题参考
2. 抖音只有**挑战标（label=9）**是平台主动投放的流量入口，参与内容有专属流量池
3. 但挑战话题**不是都该带**——硬蹭会打散人群精准度，完播率崩掉反而限流
4. 蹭的正确姿势是**改内容适配话题**，不是改标签适配内容
5. **两平台逻辑不同**：抖音靠推荐流（标签定方向），小红书靠搜索（关键词定生死，标题正文比标签更关键）
6. 小红书最大的流量池是**「新手入门」**和**「情绪价值」**两条线：搜「怎么开始」的人远多于搜「怎么变强」的人
7. **两号必须差异化**：滑雪号做深度，户外号做广度，内容互相复制会被矩阵同质压制

## 可接性判断（抖音，四档）

- ✅ **直接接**：命中该账号 `niche` 词表
- 🟡 **可借势**：命中 `scene` 开放场景词，需找到角度
- ⚪ **自行判断**：中性话题，少量
- ❌ **跳过**：影视辟谣类（label 11/16）、社会娱乐新闻类、特定玩法类（舞蹈/BGM/翻唱/变装）

## 文件结构

```
C:/Users/win/.codex/skills/热点/
├── SKILL.md
├── xhs_intel.json          # 小红书情报库（需定期更新，见 updated 字段）
└── scripts/hot_report.py   # 主脚本（抖音抓取 + 小红书情报渲染）
```

## 自定义

- `ACCOUNTS`（脚本内）：账号配置，含 `niche` / `scene` / `base_tags`；新增账号加一个 key 即可
- `xhs_intel.json`：`official_activities`（官方活动）/ `trend_insights`（趋势，带 `fit` 适配账号）/ `evergreen_tags`（常驻话题）
- `PLAY_KEYWORDS` / `EXCLUDE_KEYWORDS`：全局排除词
- 接口失效时先用备源；仍失败则提示用户接口可能变更，勿反复重试

## 注意

- 时政置顶词条已在脚本中过滤
- 常驻标签是**非雪季的保底方案**：热榜常年无滑雪词时，靠它维持垂类权重
- 不做任何发布操作，只提供标签与选题建议
