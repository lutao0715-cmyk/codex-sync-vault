# -*- coding: utf-8 -*-
"""户外日报生成器（数据驱动 + 受众加权配比自检，禁止手写 HTML 交付物）"""
import re

DATE = "2026年10月11日"
WEEKDAY = "星期日"
TITLE_DATE = "2026年10月11日 · 星期日"

CARDS = {
"🔥 今日热点": [
 ["hike", "贺兰山超级越野赛收官，两千跑者穿越戈壁", "2026 贺兰山超级越野赛 10 月 10 日在宁夏石嘴山收官，2000 余名选手参加 80、50、20 公里越野及 10 公里徒步。赛道横穿戈壁与岩画区，补给站以烤全羊成为社交媒体话题。", "宁夏体育局"],
 ["run", "芝加哥马拉松今日鸣枪，卫冕双冠重返风城", "第 48 届芝加哥马拉松今天开跑，卫冕冠军 Kiplimo 与 Feysa 双双回归，5 万余名选手穿越 29 个街区。赛事今年首次在补给区设置自带水壶滤水站，成为七大满贯中的环保样板。", "Bank of America Chicago Marathon"],
 ["ride", "本周末砂石赛场最大的悬念：谁能在澳洲林道封王", "世界砾石锦标赛本周末在澳洲 Nannup 开骑，男子赛道 144 公里、累计爬升 3713 米，卫冕者 Vermeersch 面临公路名将的集体挑战。这是该赛事首次走出欧陆，赛道以砂石林道与起伏地形著称。", "UCI"],
 ["ski", "阿尔卑斯冰川雪场进入开板周，多国索道陆续启动", "奥地利 Stubai、Kaprun 与瑞士 Engelberg 在 10 月上旬陆续启动索道，冰川雪场进入开板周。欧洲雪友的秋滑窗口正式打开，早鸟雪票与周中价同步放出。", "PowderGuide"],
 ["multi", "户外运动产业报告：徒步与骑行参与人数双双走高", "最新户外运动产业报告显示，国内徒步与骑行参与人数持续走高，露营之后轻户外成为增长主力。政策端对户外场地与赛事审批的支持力度同步加大。", "户外产业报告"]
],
"🥾 徒步越野": [
 ["hike", "HOKA Kodiak 超级马拉松落幕，国内平台全程免费直播", "由 UTMB 世界系列赛带来的 HOKA Kodiak 超级马拉松 10 月 8 日至 11 日在美国大熊湖举行，Abby Hall 等名将领跑，中国选手陈霖出战百英里。国内观众可经视频平台免费观看全程直播。", "UTMB World Series"],
 ["hike", "UTMB 十月后程赛历：普利亚与库拉曼嫩接连登场", "UTMB 世界系列赛十月剩余赛程密集：意大利 Puglia Terre delle Gravine 10 月 23 至 25 日开跑，瑞典 Kullamannen by UTMB 10 月 30 至 31 日收官。北欧夜间赛道与地中海岩溶地貌反差强烈。", "UTMB World Series"],
 ["hike", "青岛崂山跑山赛收官，两千人竞逐齐鲁越野联赛", "青岛崂山王哥庄跑山赛 10 月 6 至 7 日举行，作为齐鲁越野联赛一站，见山 25 公里与观山 15 公里两个组别共吸引约 2000 名选手。海景山脊赛道成为赛事最大卖点。", "青岛市体育局"],
 ["hike", "四川邻水越野挑战赛完赛，七百跑者闯华蓥山", "四川邻水越野挑战赛 10 月 3 至 4 日举行，700 余名选手在华蓥山间完成多组别竞逐。赛事把乡村振兴与山地越野结合，沿线村落的农家补给获选手一致好评。", "四川省体育局"],
 ["hike", "阿尔卑斯秋季徒步季尾声，多国山屋进入封山倒计时", "随着高海拔降雪提前，阿尔卑斯多国山屋陆续公布冬季闭门时间，法国与奥地利部分路线 10 月中旬起要求携带冰爪。秋季徒步的最后窗口集中在未来两周。", "Alpine Club"],
 ["hike", "国内长线徒步热度攀升，入门级雪山产品化提速", "多个户外平台数据显示，国庆后长距离徒步与穿越线路的报名量同比大幅增长，川西、滇西北与秦岭成为最热门目的地。入门级雪山攀登与高海拔徒步的产品化、标准化程度明显提升。", "户外平台数据"],
 ["hike", "尼泊尔秋季登山季收官，八千米峰登顶率走高", "尼泊尔秋季登山季进入收官阶段，多座八千米级山峰迎来难得的好天气窗口，登顶率明显高于往年同期。旅游部门表示本季许可发放数量与登山者满意度双升。", "Nepal Mountaineering"]
],
"🏃 路跑": [
 ["run", "北京马拉松 10 月 18 日鸣枪，报名 48 分钟破 10 万", "2026 北京马拉松定于 10 月 18 日鸣枪起跑，报名通道开放 48 分钟即突破 10 万人。北马周活动 10 月 11 日启动，赛前博览会与城市配套活动同步展开，中签难度再创历史新高。", "北京马拉松组委会"],
 ["run", "北马周今日启动，参赛者领物与城市活动同步开启", "北京马拉松周今天上午正式启动，参赛包领取、装备展与路跑文化市集在北京同步开放。组委会提醒选手提前完成健康承诺与赛前检录，避免赛事日集中拥堵。", "北京马拉松组委会"],
 ["run", "热门马拉松中签难成常态，赛事名额成稀缺资源", "随着路跑人口持续增长，北京、上海、无锡等热门赛事的中签率持续走低，一签难求成为跑圈常态。多家赛事开始探索慈善名额、成绩达标等多元获取通道。", "新华体育"],
 ["run", "XTERRA 欧洲越野铁三锦标赛落幕，山地三项热度上行", "XTERRA 欧洲越野铁人三项锦标赛在意大利落幕，越野游泳、山地骑行与越野跑组合的赛制吸引大批路跑选手跨界参与。赛事方称报名人群中跑步背景选手占比首次过半。", "XTERRA"],
 ["run", "秋季路跑赛历密集，城市半马成为大众首选", "10 月起国内城市半程马拉松密集开跑，半马因备赛周期短、门槛适中成为大众跑者首选。多地赛事把路线植入城市地标，推动跑一场马、游一座城的体旅融合。", "中国田径协会"]
],
"🚴 骑行与滑雪": [
 ["ride", "UCI 砾石世锦赛前瞻：Van Aert 跨界挑大梁", "本届砾石世锦赛群星云集，Van Aert、Marianne Vos、Gómez Villafañe 均确认出战，卫冕冠军 Vermeersch 力争连庄。澳大利亚 Nannup 的砂石林道与 3700 米级爬升考验选手综合能力。", "UCI"],
 ["ride", "印尼 Banyuwangi 砾石赛落幕，五国选手竞逐 Nggravel", "印尼 Banyuwangi 举办 Nggravel Glenmore 砾石赛，来自五个国家的选手参加 100 公里砾石与 100 公里山地车组。赛事借火山与海岸线地貌，试图打造东南亚砾石赛事新地标。", "Banyuwangi 官方"],
 ["ride", "阿联酋 RAK 山地自行车赛开赛，沙漠赛道考验耐力", "阿联酋哈伊马角山地自行车赛开赛，赛道穿越沙漠岩地与山地干谷，高温与松软沙地成为主要挑战。中东地区正以赛事带动骑行旅游与装备消费。", "RAK Sports"],
 ["ride", "Colnago G5-X 与 LOOK G85 登场，砾石车型竞速化明显", "Colnago 发布 G5-X、LOOK 推出 G85 新一代砾石车，几何更接近公路竞速取向，胎宽容纳与气动设计同步进化。砾石车从舒适长途向快速竞赛演进的趋势在 2026 年愈发清晰。", "Colnago / LOOK"],
 ["ride", "国内骑行赛事密集收官，环湖赛带动地方体旅融合", "10 月国内自行车赛事密集收官，公路赛、山地赛与砾石活动在不同地形接力上演。环湖、环岛类赛事带动沿线住宿与餐饮消费，成为地方体旅融合的重要抓手。", "中国自行车运动协会"],
 ["ski", "Saas-Fee 训练营开营，自由式名将同场磨动作", "瑞士 Saas-Fee 的 Stomping Grounds 公园 10 月 5 日至 26 日迎来 Red Bull 私人训练季，苏翊鸣、Jake Canter 等自由式选手同场磨合新动作，为 12 月世界杯赛季热身。", "Saas-Fee 360"],
 ["ski", "北美雪场同日开板，A-Basin 与 Keystone 争先", "科罗拉多 Arapahoe Basin 与 Keystone 在 10 月 9 日同日开缆车，共享北美最早开板头衔。Keystone 连续第三年提前造雪抢开，早期雪道投入持续前置。", "Keystone"],
 ["ski", "Aspen 用保温毯技术反季开放地形公园", "Aspen Snowmass 借助 Snow Secure 保温毯技术在 10 月 3 日即开放首条地形公园道，把夏季造好的雪量留到秋季使用。北美反季开板的技术竞赛继续升级。", "Aspen Snowmass"],
 ["ski", "国内雪场开板时间表出炉，崇礼与东北陆续迎客", "新雪季国内开板时间表陆续公布：新疆可可托海率先迎客，崇礼万龙 10 月 27 日开板，云顶、太舞与富龙 11 月中旬跟上，吉林北大湖与松花湖预计 11 月 18 日前后开门。", "各雪场公告"]
],
"🌊 水上": [
 ["water", "济南雪野湖国庆水上嘉年华，帆船与桨板轮番登场", "济南雪野湖国庆水上嘉年华举行，OP 帆船赛、桨板嘉年华与中国家庭帆船赛接连上演，覆盖青少年到家庭客群。湖泊型水上运动正成为内陆城市的新消费场景。", "济南市体育局"],
 ["water", "湖北广水楚天桨王桨板公开赛收官", "湖北广水举办楚天桨王桨板公开赛，来自多省的桨板选手在湖面角逐竞速与技巧组别。赛事带动当地水上运动俱乐部与装备租赁业务升温。", "湖北省体育局"],
 ["water", "石家庄水上运动嘉年华举办，市民体验皮划艇", "石家庄水上运动嘉年华 10 月 6 日举办，皮划艇、桨板与龙舟体验项目向市民开放，单日参与人数创当地新高。城市水系治理成效直接转化为水上运动参与度。", "石家庄市体育局"],
 ["water", "青岛与舟山帆船赛事接力，秋季海风成最佳赛期", "10 月青岛与舟山帆船赛事接力举办，秋季稳定海风被视为国内帆船赛季的最佳窗口。多场赛事设置青少年组，帆船后备人才培养体系持续完善。", "中国帆船帆板运动协会"]
],
"🪂 空中与垂钓": [
 ["air", "韩国滑翔伞联赛收官，亚洲选手竞逐越野航线", "韩国滑翔伞联赛收官，参赛选手在半岛山区完成长距离越野航线竞逐。亚洲滑翔伞运动近年规模快速扩张，越野飞行里程纪录不断被刷新。", "FAI"],
 ["air", "欧洲滑翔伞定点锦标赛结束，落地精度成决胜关键", "欧洲滑翔伞定点锦标赛结束，选手需精准落中靶心，厘米级差距决定排名。定点项目因观赏性强、门槛适中，正成为滑翔伞入门的首选竞技形式。", "FAI"],
 ["fish", "北京世园杯岸钓路亚总决赛收官，李伟夺冠", "北京世园杯岸钓路亚总决赛 10 月 6 日收官，选手李伟在决赛中夺冠。岸钓路亚因装备轻便、场地灵活，成为城市钓友增长最快的细分玩法。", "中国钓鱼运动协会"]
],
"🏕️ 综合": [
 ["multi", "始祖鸟进博会首秀在即，雪线与山地系列中国首发", "始祖鸟确认首次参展 11 月上海进博会，雪线与山地系列将设独立展区并带来多款中国首发新品。国际户外品牌对中国市场的投入在装备端持续加码。", "进博会"],
 ["multi", "秋冬季户外装备消费提前启动，冲锋衣成换季第一件", "随着气温下行，秋冬季户外装备消费提前启动，冲锋衣成为换季首选单品。电商平台数据显示，防风机能与三层压胶面料的搜索量显著上升。", "电商平台数据"],
 ["multi", "户外安全提示：秋冬交替是山地事故高发期", "多地救援机构发布提醒，秋冬交替气温骤降、日落提前，是山地迷路与失温事故的高发期。建议出行前核对天气与备案路线，携带保暖层与照明装备。", "应急管理部门"],
 ["multi", "国际户外展秋季档期密集，装备品牌集中发布明年新品", "10 月起国际户外展会进入秋季档期，多家品牌把明年春夏新品提前到秋季发布，轻量化与环保再生面料是共同关键词。渠道商反馈，展会成交重心正从欧美向亚洲转移。", "Outdoor Industry"]
]
}
# ============ 受众加权配置（配额不可改动） ============
SPORT_GROUPS = {"hike": 8, "run": 6, "ride": 6, "ski": 5,
                "water": 4, "air": 2, "fish": 1, "multi": 5}
GROUP_NAMES = {"hike": "徒步越野", "run": "路跑", "ride": "骑行", "ski": "滑雪",
               "water": "水上", "air": "空中", "fish": "垂钓", "multi": "综合"}


# ============ 配比自检 ============
def audit():
    from collections import Counter
    cnt = Counter()
    total = 0
    for sec, lst in CARDS.items():
        for it in lst:
            total += 1
            tag = it[0]
            if tag not in SPORT_GROUPS:
                raise SystemExit(f"[配比错误] 标签 {tag!r} 不是 SPORT_GROUPS 的键（{sec}）")
            cnt[tag] += 1
    print("--- 受众加权配比报告 ---")
    bad = 0
    for k, target in SPORT_GROUPS.items():
        got = cnt.get(k, 0)
        diff = abs(got - target)
        flag = "" if diff <= 1 else "  <== 偏离超标"
        if diff > 1:
            bad += 1
        print(f"  {GROUP_NAMES[k]:<6} 目标 {target}  实际 {got}{flag}")
    print(f"  合计 {total} 条 / 版块 {len(CARDS)} 个")
    print(f"  偏离超1条的组数 = {bad}")
    if bad != 0:
        raise SystemExit("[配比错误] 偏离超 1 条的组数必须为 0，请换题重生成")
    return total, cnt


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


total, cnt = audit()

cards_html = []
num = 0
for sec_name, lst in CARDS.items():
    cards_html.append(f'<div class="section-title">{esc(sec_name)}</div>')
    for it in lst:
        num += 1
        tag, t, p, src = it[0], it[1], it[2], it[3]
        cards_html.append(
            f'<article class="card"><div class="card-head"><span class="card-num">{num:02d}</span>'
            f'<span class="tag tag-{tag}">{esc(GROUP_NAMES[tag])}</span></div>'
            f'<h3>{esc(t)}</h3><p>{esc(p)}</p>'
            f'<div class="src">{esc(src)}</div></article>'
        )

stats = "".join(
    f'<div class="stat">{GROUP_NAMES[k]} <b>{cnt.get(k, 0)}</b></div>'
    for k in SPORT_GROUPS
)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🏕️ 户外日报 {TITLE_DATE}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0f1420; color:#e8ecf4; font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; line-height:1.7; padding:24px 16px 60px; }}
.wrap {{ max-width:1120px; margin:0 auto; }}
.header {{ text-align:center; padding:28px 0 20px; border-bottom:1px solid #232b3d; }}
.header h1 {{ font-size:26px; letter-spacing:2px; }}
.header .sub {{ color:#8fa0b8; margin-top:8px; font-size:14px; }}
.stats-bar {{ display:flex; flex-wrap:wrap; gap:10px; justify-content:center; margin:18px 0 8px; }}
.stat {{ background:#1a2234; border:1px solid #2a3550; border-radius:8px; padding:6px 14px; font-size:12px; color:#aebdda; }}
.stat b {{ color:#7ee0a8; font-size:15px; }}
.section-title {{ font-size:19px; font-weight:700; color:#7ee0a8; margin:34px 0 14px; padding-left:12px; border-left:4px solid #7ee0a8; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(330px,1fr)); gap:14px; }}
.card {{ background:#161e30; border:1px solid #26314a; border-radius:10px; padding:16px 18px; }}
.card-head {{ display:flex; align-items:center; gap:10px; margin-bottom:6px; }}
.card-num {{ color:#7ee0a8; font-weight:700; font-size:13px; }}
.tag {{ font-size:11px; border-radius:20px; padding:2px 10px; background:#1d3a5f; color:#7cc4ff; }}
.tag-hike {{ background:#1f3a2c; color:#8fe0a0; }}
.tag-run {{ background:#3a2c1f; color:#ffc48a; }}
.tag-ride {{ background:#1d3a5f; color:#7cc4ff; }}
.tag-ski {{ background:#2b2450; color:#b3a6ff; }}
.tag-water {{ background:#123a44; color:#6fd8e8; }}
.tag-air {{ background:#3a1f3a; color:#e69ae0; }}
.tag-fish {{ background:#3a3320; color:#e8d27a; }}
.tag-multi {{ background:#2a3550; color:#a8bcdc; }}
.card h3 {{ font-size:16px; margin:4px 0 8px; color:#fff; }}
.card p {{ font-size:13.5px; color:#c3cde0; }}
.card .src {{ margin-top:10px; font-size:11.5px; color:#7c88a0; text-align:right; }}
footer {{ margin-top:40px; padding-top:16px; border-top:1px solid #232b3d; text-align:center; color:#7c88a0; font-size:12px; }}
</style>
</head>
<body>
<div class="wrap">
  <header class="header">
    <h1>🏕️ 户外日报</h1>
    <p class="sub">{TITLE_DATE} · 徒步 · 路跑 · 骑行 · 滑雪 · 水上 · 空中 · 垂钓</p>
    <div class="stats-bar">
      <div class="stat">新闻 <b>{num}</b> 条</div>
      <div class="stat">版块 <b>{len(CARDS)}</b> 个</div>
      {stats}
    </div>
  </header>
  <div class="grid">
{''.join(cards_html)}
  </div>
  <footer>数据来源：UTMB / UCI / FAI / 各赛事组委会与体育局 等 30+ 中外媒体</footer>
</div>
</body>
</html>"""

open("outdoor-adventure-daily.html", "w", encoding="utf-8").write(html)
print("OK: outdoor-adventure-daily.html generated,", num, "cards")
