#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热点工作流 · 抖音 + 小红书

服务账号：
  - ski      抖音「滑雪研究院」（滑雪垂类）
  - outdoor  抖音「户外运动号」（陆地/水上/雪上/跑步）

数据来源：
  抖音（自动抓取，无需登录）
    - 综合热榜: douyin.com/aweme/v1/web/hot/search/list/  需先取 __ac_nonce cookie
    - 上海同城榜: 同上 board_type=1
    - 备源: iesdouyin.com/web/api/v2/hotsearch/billboard/word/
  小红书（读本地情报库 xhs_intel.json）
    - 实时热搜需登录态 + x-s 签名，无法自动抓取
    - 改为维护「官方活动 + 平台趋势」情报，由 Agent 定期联网更新

抖音 label 含义（已用官方图标确证）:
  1=新  3=热  9=挑战(官方主推话题)  11=剧集  16=辟谣  0=普通

核心认知:
  - 热榜「事件聚合词」是流量结果，带它没有引流价值 → 只作选题参考
  - 只有「挑战标(label=9)」是平台主动投放的流量入口 → 真正可蹭
  - 小红书反过来：官方活动话题是第一优先级，且「新手/情绪」类选题是最大流量池
"""
import json, subprocess, sys, argparse, datetime, os

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
LABEL_MAP = {0: "", 1: "新", 3: "热", 9: "挑战", 11: "剧集", 16: "辟谣"}
HERE = os.path.dirname(os.path.abspath(__file__))
XHS_INTEL_PATH = os.path.join(os.path.dirname(HERE), "xhs_intel.json")

# ---------- 全局排除规则（所有账号通用） ----------
PLAY_KEYWORDS = ["闪身", "舞", "步", "BGM", "翻唱", "变装", "美少女", "翻跳", "说唱",
                 "配音", "cos", "模仿", "短剧", "剧情", "表情包", "演技", "翻拍"]
EXCLUDE_KEYWORDS = ["去世", "逝世", "辟谣", "谣言", "通报", "被传", "同框", "入驻", "官宣",
                    "恋情", "结婚", "离婚", "复出", "起诉", "警方", "事故", "救援", "火灾",
                    "地震", "元首", "总统", "访问", "外交", "会谈", "会议", "大婚", "明星",
                    "电视剧", "综艺", "演唱会", "发布会", "补贴", "数据采集"]

# ============ 账号配置区 ============
ACCOUNTS = {
    "ski": {
        "name": "滑雪研究院",
        "emoji": "🏔️",
        "desc": "抖音 + 小红书 · 滑雪垂类 · 专业/资讯/教学",
        "niche": [
            "滑雪", "单板", "双板", "雪板", "雪场", "雪道", "雪具", "雪服", "雪镜", "雪盔",
            "开板", "封板", "雪季", "首滑", "粉雪", "野雪", "平花", "刻滑", "搓雪", "换刃",
            "滑雪场", "冰雪", "滑冰", "冰场", "冬奥", "雪山",
            "崇礼", "长白山", "北大湖", "太舞", "万龙", "阿勒泰", "禾木", "可可托海",
            "亚布力", "松花湖", "将军山", "北海道", "二世谷", "富良野", "阿尔卑斯",
        ],
        "scene": ["下雪", "降温", "寒潮", "雪景", "冬天", "冬季", "跨年", "元旦", "寒假",
                  "春节", "假期", "出游", "旅行", "风景", "治愈", "日常", "记录", "穿搭", "look"],
        "base_tags": {
            "核心": ["#滑雪#", "#单板滑雪#", "#双板滑雪#", "#滑雪教学#", "#滑雪装备#"],
            "雪季词": ["#开板#", "#雪季#", "#首滑#", "#粉雪#", "#滑雪穿搭#"],
            "地域词": ["#崇礼#", "#长白山#", "#阿勒泰#", "#新疆滑雪#", "#北海道滑雪#"],
            "圈内词": ["#雪友#", "#滑雪人的快乐#", "#雪场攻略#", "#新手滑雪#"],
        },
    },
    "outdoor": {
        "name": "户外运动号",
        "emoji": "🥾",
        "desc": "抖音 + 小红书 · 泛户外 · 陆地/水上/雪上/跑步 · 生活方式向",
        "niche": [
            "徒步", "登山", "攀岩", "抱石", "溯溪", "露营", "野营", "骑行", "越野", "穿越",
            "飞盘", "滑板", "探洞", "滑翔", "山野", "帐篷", "营地",
            "桨板", "浆板", "皮划艇", "独木舟", "漂流", "潜水", "浮潜", "冲浪", "帆船",
            "尾波", "划船", "游泳", "水上",
            "滑雪", "单板", "双板", "雪场", "雪季", "开板", "雪山", "冰川", "冰雪",
            "跑步", "马拉松", "越野跑", "半马", "全马", "配速", "晨跑", "夜跑", "跑鞋",
            "户外", "野外", "自然", "装备", "户外装备", "运动",
        ],
        "scene": ["下雪", "降温", "秋天", "赏秋", "红叶", "日出", "日落", "星空", "周末",
                  "假期", "出游", "旅行", "风景", "治愈", "露营", "野餐", "遛娃", "团建",
                  "citywalk", "日常", "记录", "中秋", "国庆", "元旦", "春节", "跨年"],
        "base_tags": {
            "核心": ["#户外#", "#户外运动#", "#户外生活#", "#一起去户外#", "#户外装备#"],
            "分项": ["#徒步#", "#露营#", "#登山#", "#跑步#", "#桨板#", "#皮划艇#", "#骑行#"],
            "圈内": ["#户外人#", "#山野#", "#户外日记#", "#周末去哪儿#", "#户外玩家#"],
            "地域": ["#上海户外#", "#江浙沪徒步#", "#淀山湖#", "#周末周边游#"],
        },
    },
}
# ==================================

API_WEB = ("https://www.douyin.com/aweme/v1/web/hot/search/list/"
           "?device_platform=webapp&aid=6383&channel=channel_pc_web&detail_list=1&source=6"
           "&board_type={bt}&board_sub_type=&version_code=170400&version_name=17.4.0&cookie_enabled=true")
API_FALLBACK = "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/"


def curl(url, cookie_file=None, save_cookie=False, referer=None, timeout=15):
    cmd = ["curl", "-s", "-m", str(timeout), "-A", UA]
    if save_cookie:
        cmd += ["-c", cookie_file]
    elif cookie_file:
        cmd += ["-b", cookie_file]
    if referer:
        cmd += ["-H", f"Referer: {referer}"]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    return r.stdout


def get_cookie_file(tmpdir):
    ck = os.path.join(tmpdir, "dy_cookie.txt")
    curl("https://www.douyin.com/hot", cookie_file=ck, save_cookie=True,
         referer="https://www.douyin.com/")
    if os.path.exists(ck) and "__ac_nonce" in open(ck).read():
        return ck
    return None


def fetch_board(board_type, cookie_file):
    raw = curl(API_WEB.format(bt=board_type), cookie_file=cookie_file,
               referer="https://www.douyin.com/hot")
    try:
        return json.loads(raw).get("data", {}).get("word_list") or []
    except Exception:
        return []


def fetch_fallback():
    raw = curl(API_FALLBACK)
    try:
        return json.loads(raw).get("word_list") or []
    except Exception:
        return []


def fmt_wan(n):
    return f"{n/10000:.0f}万" if n and n >= 10000 else (str(n) if n else "-")


def classify(word, label, acc):
    if label in (11, 16):
        return "❌ 跳过", "剧集/辟谣类，与账号无关"
    for k in EXCLUDE_KEYWORDS:
        if k in word:
            return "❌ 跳过", f"社会/娱乐新闻类（{k}）"
    for k in acc["niche"]:
        if k in word:
            return "✅ 直接接", f"命中垂类：{k}"
    for k in PLAY_KEYWORDS:
        if k in word:
            return "❌ 跨垂类接不了", f"特定玩法类（{k}），需特定形式模仿"
    for k in acc["scene"]:
        if k in word:
            return "🟡 可借势", f"开放话题（{k}），找到角度再带"
    return "⚪ 自行判断", "中性话题，看内容能否自然关联"


def load_xhs_intel():
    try:
        with open(XHS_INTEL_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def build_xhs_lines(acc_key, intel):
    """该账号的小红书区块"""
    if not intel:
        return ["> ⚠️ 小红书情报库读取失败（xhs_intel.json）", ""]
    L = []
    acts = [a for a in intel.get("official_activities", []) if acc_key in a.get("fit", [])]
    if acts:
        L += ["**📕 小红书 · 官方活动（可参与）**", "",
              "| 活动 | 时间 | 带什么话题 | 参与方式 |", "|---|---|---|---|"]
        for a in acts:
            L.append(f"| {a['name']} | {a['period']} | {a['tag']} | {a['how']} |")
        for a in acts:
            if a.get("note"):
                L.append(f"- *{a['name']}*：{a['note']}")
        L.append("")

    ins = [i for i in intel.get("trend_insights", []) if acc_key in i.get("fit", [])]
    if ins:
        L += ["**📕 小红书 · 趋势选题方向**", ""]
        for i in ins:
            L.append(f"- **{i['theme']}**")
            L.append(f"  - 数据：{'；'.join(i['data'][:3])}")
            L.append(f"  - 打法：{i['takeaway']}")
        L.append("")

    et = (intel.get("evergreen_tags", {}) or {}).get(acc_key)
    if et:
        L += [f"**📕 小红书 · 常驻话题**：{' '.join(et)}", ""]
    return L


def build_md(main_wl, city_wl, account_keys, intel, city_name="上海"):
    now_dt = datetime.datetime.now()
    L = [f"# 每日热点作战包（{now_dt.strftime('%Y-%m-%d %H:%M')}）", "",
         "> **抖音** = 实时热榜（自动抓取）；**小红书** = 官方活动 + 平台趋势",
         "> （小红书实时热搜需登录态，抓不到；官方活动对垂类账号价值反而更高）", ""]
    challenges = [w for w in main_wl if w.get("label") == 9]

    for key in account_keys:
        acc = ACCOUNTS[key]
        L += [f"## {acc['emoji']} {acc['name']}", f"> {acc['desc']}", ""]

        if key == "ski":
            if now_dt.month in (5, 6, 7, 8, 9, 10):
                L += ["> 🌱 **当前非雪季**（雪季通常 11 月中开板）：抖音侧主攻常驻标签蓄水；小红书侧主攻「新手入门」选题。", ""]
            else:
                L += ["> ❄️ **当前雪季**：雪场/目的地词 + 技术词是主要流量入口，优先带。", ""]

        L += ["**🎵 抖音 · 常驻标签（不依赖热榜，随时可带）**", ""]
        for k, v in acc["base_tags"].items():
            L.append(f"- **{k}**：{' '.join(v)}")
        L.append("")

        rows, skipped = [], 0
        for w in challenges:
            lv, why = classify(w["word"], w.get("label"), acc)
            if lv.startswith("❌"):
                skipped += 1
                continue
            rows.append((w, lv, why))
        L += ["**🎵 抖音 · 今日官方挑战话题 · 可接性**", ""]
        if rows:
            L += ["| 话题 | 热度 | 可接性 | 判断依据 |", "|---|---|---|---|"]
            for w, lv, why in rows:
                L.append(f"| #{w['word']}# | {fmt_wan(w.get('hot_value'))} | {lv} | {why} |")
        else:
            L.append("- 本时段没有可接的挑战话题，用常驻标签即可")
        if skipped:
            L.append(f"- *其余 {skipped} 条为娱乐玩法/新闻类，本号不适用*")
        L.append("")

        L += build_xhs_lines(key, intel)

    L += ["## 📖 抖音借势选题参考（通用 · ⚠️ 不是标签，是情报）", "",
          "> 这些词是流量汇聚的**结果**。带它拿不到额外分发，但可以据此找选题。", "",
          "| 热点 | 标记 | 热度 |", "|---|---|---|"]
    rank = 0
    for w in main_wl:
        word = w["word"]
        if word.startswith("习近平") or "国事访问" in word:
            continue
        rank += 1
        if rank > 10:
            break
        L.append(f"| #{word}# | {LABEL_MAP.get(w.get('label', 0), '') or '-'} | {fmt_wan(w.get('hot_value'))} |")
    L.append("")

    if city_wl:
        L += [f"## 📍 {city_name}同城榜（抖音 · 有本地属性内容才带）", "",
              "| # | 话题 | 热度 |", "|---|---|---|"]
        for i, w in enumerate(city_wl[:8], 1):
            L.append(f"| {i} | #{w['word']}# | {fmt_wan(w.get('hot_value'))} |")
        L.append("")

    L += ["## 使用铁律",
          "1. **带无关热门 = 自杀**：算法会推给不对的人，完播率崩掉，直接死在第一级流量池",
          "2. **蹭的正确姿势是改内容适配话题**，不是改标签适配内容。内容接不上就宁可不带",
          "3. **标签只用 3~5 个**：1 个能自然关联的活动/热点词 + 2 个垂类精准词 + 1 个内容描述词",
          "4. **两号差异化**：滑雪号做专业深度，户外号做生活方式广度，内容别互相复制（矩阵同质会被压制）",
          "5. **两平台逻辑不同**：抖音靠推荐流（标签定方向），小红书靠搜索（关键词定生死），标题正文要比标签更用心",
          "6. **标签只决定起跑位置**，决定生死的是内容能不能在初始流量池跑赢"]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="all", help="账号: all / ski / outdoor，或逗号分隔")
    ap.add_argument("--save", help="保存 markdown 到指定路径")
    ap.add_argument("--json", help="同时保存原始 JSON")
    args = ap.parse_args()

    keys = list(ACCOUNTS.keys()) if args.account == "all" else \
        [k for k in args.account.split(",") if k in ACCOUNTS]
    if not keys:
        print(f"未知账号：{args.account}，可选：{', '.join(ACCOUNTS)} 或 all")
        sys.exit(1)

    ck = get_cookie_file("/tmp")
    main_wl = fetch_board(0, ck) if ck else []
    if not main_wl:
        main_wl = fetch_fallback()
    city_wl = fetch_board(1, ck) if ck else []

    if not main_wl:
        print("抖音抓取失败：数据源均不可用，接口可能已变更")
        sys.exit(1)

    md = build_md(main_wl, city_wl, keys, load_xhs_intel())
    print(md)

    if args.save:
        with open(args.save, "w") as f:
            f.write(md)
        print(f"\n[已存档] {args.save}", file=sys.stderr)
    if args.json:
        with open(args.json, "w") as f:
            json.dump({"main": main_wl, "city": city_wl}, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
