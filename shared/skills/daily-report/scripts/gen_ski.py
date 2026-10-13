# -*- coding: utf-8 -*-
"""滑雪晨报生成器（数据驱动，禁止手写 HTML 交付物）"""
import re, json

DATE = "2026年10月11日"
WEEKDAY = "星期日"
TITLE_DATE = "2026年10月11日 · 星期日"

SECTIONS = '''
[
{"name": "🔥 今日热点", "items": [
 {"t": "阿尔卑斯冰川雪场抢跑开板，Pitztal 已迎客 Stubai 本周跟上", "p": "奥地利 Pitztal 冰川雪场领跑新雪季率先开门，Stubai 冰川计划 10 月 9 日、Kaprun 紧随其后，瑞士 Engelberg 也在本周启动索道。各大冰川雪场用「抢跑式开板」锁定最早一批雪友，周中价与早鸟票同步放出。", "tag": "intl", "src": "PowderGuide / snow-forecast"},
 {"t": "平野海舟刷出半管最高滞空，Snow League 再添一项吉尼斯纪录", "p": "日本单板滑手平野海舟（Kaishu Hirano）在 Snow League 赛场完成超高滞空半管动作，经测量刷新「单板半管最高空气时间」吉尼斯纪录。这也为 11 月 Snow League 新赛季首战的关注度再添一把火。", "tag": "intl", "src": "Snow League / Guinness"},
 {"t": "MoonPay X Games 联赛公布 2027 赛季日程，虚拟战队制延续", "p": "X Games 官方公布 2027 赛季联赛时间表：1 月底阿斯彭、2 月卡尔加里、4 月鲁卡三站连轴。上赛季摘得选秀状元的位置在谷爱凌名下，麦克莫里斯紧随其后，虚拟战队玩法继续贯穿全年。", "tag": "intl", "src": "X Games"},
 {"t": "Saas-Fee Stomping Grounds 训练营开营，苏翊鸣受邀参训", "p": "瑞士 Saas-Fee 的 Stomping Grounds 滑雪公园从 10 月 5 日到 26 日迎来 Red Bull 组织的私人训练季，苏翊鸣、Jake Canter 等自由式名将同场磨合新动作，为 12 月世界杯赛季热身。", "tag": "intl", "src": "Saas-Fee 360 / Red Bull"},
 {"t": "可可托海 12 日率先开板，全国最早雪场带 240 天超长雪季", "p": "新疆可可托海国际滑雪度假区定于 10 月 12 日开门迎客，延续「全国最早开板」标签。本雪季 23 条雪道完成整修、雪道总长 61 公里，官方宣称雪季长达 240 天，早鸟季卡已率先售罄。", "tag": "china", "src": "富蕴零距离 / 可可托海官方"}
]},
{"name": "⚔️ 竞技赛场", "items": [
 {"t": "世界杯索尔登站月底揭幕：女子大回转 24 日、男子 25 日开赛", "p": "2026-27 高山滑雪世界杯将于 10 月底在奥地利索尔登开战：女子大回转 10 月 24 日、男子 25 日，冰川赛道如往年一样率先打响新赛季积分战。各队已公布揭幕站参赛阵容。", "tag": "intl", "src": "FIS"},
 {"t": "北美站赛程确定：Killington 旋转门之后 Copper 接档", "p": "世界杯北美双站确认：11 月底 Killington 女子技术赛打响，随后科罗拉多 Copper Mountain 接档男女子项目，12 月初 Beaver Creek 速降回归。北美雪友将在一个月内连看三场世界杯。", "tag": "intl", "src": "FIS Alpine"},
 {"t": "2027 年霞慕尼—克莱恩蒙塔纳世锦赛赛程公布，二月开赛", "p": "2027 年高山滑雪世锦赛将落户瑞士 Crans-Montana，赛程 2 月 1 日至 14 日横跨两个周末，速降、回转与团体项目全部覆盖。这将是瑞士时隔多年再度承办高山世锦赛。", "tag": "intl", "src": "FIS / Ski Racing"},
 {"t": "Stifel 美国队公布 49 人名单，希夫林、冯恩领衔", "p": "Stifel 美国高山滑雪队公布新赛季 49 人名单，米凯拉·希夫林与复出的林赛·冯恩均在列，多名 U 系列新人拿到世界杯门票。队内目标是冲击 2027 世锦赛与 2028 冬奥积分。", "tag": "intl", "src": "US Ski Team"},
 {"t": "国家高山滑雪集训队选拔方案公示，向全国开放报名", "p": "国家高山滑雪队新周期选拔方案公示，首次向省市队与俱乐部选手开放报名通道，聚焦速度项目与技术项目梯队建设。选拔将结合世界杯积分与国内测试赛成绩综合评定。", "tag": "china", "src": "国家体育总局冬季运动管理中心"}
]},
{"name": "🏆 人物", "items": [
 {"t": "希夫林宣布新赛季主攻回转，剑指世界杯第 100 胜", "p": "米凯拉·希夫林确认新赛季以回转为主项，距离历史性第 100 个世界杯冠军只差临门一脚。她同时表态会参加 2027 世锦赛全部技术项目。", "tag": "intl", "src": "Ski Racing"},
 {"t": "林赛·冯恩康复提速，11 月 Killington 复出计划不变", "p": "林赛·冯恩术后康复进展顺利，团队确认复出首站仍锁定 11 月 Killington 世界杯速降。43 岁的她将再次改写「最年长世界杯速降选手」的想象空间。", "tag": "intl", "src": "US Ski Team"},
 {"t": "麦克莫里斯领衔 X Games 联赛选秀第二顺位，新赛季备战启动", "p": "单板传奇马克·麦克莫里斯以第二顺位进入新赛季 X Games 联赛虚拟战队，他在采访中透露已开始为新动作周期做准备，目标是冲击联赛总冠军。", "tag": "intl", "src": "X Games"},
 {"t": "苏翊鸣欧洲训练状态出色，新动作「1800 转体双抓板」进入打磨期", "p": "苏翊鸣在 Saas-Fee 训练营状态在线，团队透露其新赛季将主攻更高难度转体衔接动作，双抓板 1800 已进入稳定打磨阶段，目标直指 12 月北京首钢大跳台世界杯。", "tag": "china", "src": "苏翊鸣团队 / 新华社"}
]},
{"name": "🏔️ 雪场动态", "items": [
 {"t": "崇礼万龙 27 日开板，云顶、太舞、富龙 11 月中旬齐上", "p": "张家口崇礼各雪场开板时间表出炉：万龙滑雪场 10 月 27 日率先迎客，云顶、太舞、富龙预计 11 月中旬陆续开门。京张高铁加持下，崇礼依然是华北雪友周末滑雪的第一选择。", "tag": "china", "src": "崇礼各大雪场公告"},
 {"t": "北大湖、松花湖 11 月 18 日前后开板，双湖同启新雪季", "p": "吉林北大湖与万科松花湖均计划 11 月 18 日前后开板，两雪场存量雪道完成升级，北大湖新增野雪区开放预约。东北雪季以「双湖呼应」的形式拉开序幕。", "tag": "china", "src": "北大湖 / 松花湖官方"},
 {"t": "Aspen 试验「雪耕」保温毯地形公园，10 月 3 日即开放", "p": "美国 Aspen Snowmass 用 Snow Secure 保温毯技术在 10 月 3 日就开放了首条地形公园道，被称为「反季雪耕」的保温毯方案让夏季造雪提前锁住。北美雪场最早开板纪录再被刷新。", "tag": "intl", "src": "Aspen Snowmass"},
 {"t": "A-Basin 与 Keystone 同日开门，北美最早开板之争落定", "p": "科罗拉多 Arapahoe Basin 与 Keystone 在 10 月 9 日同日开放缆车，共享「北美最早开板」头衔。Keystone 近年持续把雪季早期造雪投入前置，已连续第三年争先开门。", "tag": "intl", "src": "Keystone / A-Basin"},
 {"t": "Hintertux 冰川雪场公园节周末开滑，公园设施全季在线", "p": "奥地利 Hintertux 冰川雪场本周末举办秋季公园节，Box、跳台与管道设施全部开放。作为欧洲少数全年运营的冰川雪场，它承担了国家队夏训与大众秋滑双重角色。", "tag": "intl", "src": "Hintertux Gletscher"}
]},
{"name": "🏭 行业观察", "items": [
 {"t": "雪场季卡集体涨价，云顶 5288 元、万龙逼近九千", "p": "新雪季各大雪场季卡价格陆续公布：云顶 5288 元、雪如意 4588 元、万龙 8999 元，多家较去年上浮明显。青格里狼山早鸟 2000 元季卡已售罄，「低价引流、高端化运营」分层愈发清晰。", "tag": "china", "src": "各雪场官方 / 小红书雪圈"},
 {"t": "迪卡侬雪服三年均价涨 52%，入门装备门槛悄悄抬高", "p": "迪卡侬雪服产品线三年均价上涨 52%，入门级雪服价格带整体上移。分析认为原材料与通胀只是表象，品牌主动从「超市货」向「专业入门」定位迁移才是主因。", "tag": "china", "src": "南方周末 / 消费者报道"},
 {"t": "X Games 任命新 COO，联赛化运营进入新阶段", "p": "X Games 宣布 Steve Rogers 出任首席运营官，官方称将把联赛、内容与数字资产整合为全年运营体系。奥林匹克资格路径之外，X Games 正在搭建自己的商业闭环。", "tag": "intl", "src": "X Games / ESPN"},
 {"t": "双 11 装备预售 15 日启动，雪服雪板将迎来全年最强折扣", "p": "今年双 11 滑雪装备预售预计 10 月 15 日前后开启，雪板、固定器与雪服进入全年价格低点。业内人士提醒：刚开板的周末价格最坚挺，反季与预售才是入手窗口。", "tag": "china", "src": "什么值得买 / 电商平台"}
]},
{"name": "🎿 装备风向", "items": [
 {"t": "始祖鸟 Sidewinder 复刻上市，25 周年限定款定价 850 美元", "p": "始祖鸟经典雪服 Sidewinder 迎来 25 周年复刻，10 月 9 日起全球发售，定价 850 美元。复刻版保留标志性胸袋与高领设计，采用新版 GORE-TEX 面料，开售即受关注。", "tag": "intl", "src": "Arc'teryx"},
 {"t": "始祖鸟首次参展进博会，雪线产品线中国首发在即", "p": "始祖鸟确认首次参展 11 月上海进博会，雪线（Snow）与山地系列将设独立展区，多款中国首发新品同步亮相。品牌对中国滑雪装备市场的投入明显加码。", "tag": "china", "src": "进博会 / Arc'teryx 中国"},
 {"t": "Burton 发布新雪板系列，反拱板型主打公园全能", "p": "Burton 发布 2026-27 雪季新板系列，多款反拱（camber 反向）板型主打公园与街式场景，其中一款融合了上季巡回赛冠军的反馈数据。新固定器线同步更新了快穿系统。", "tag": "intl", "src": "Burton / Whitelines"},
 {"t": "雪服面料卷向「防水透气双标」，三层压胶工艺成新标配", "p": "本季雪服面料竞争升级：20K/20K 防水透气双标成为中高端标配，多家品牌将三层压胶（3L）工艺下放到 3000 元档雪服。评测机构提醒，透气指标对滑行出汗场景比防水数字更关键。", "tag": "intl", "src": "Snowboards / 户外装备评测"}
]}
]
'''

data = json.loads(SECTIONS)

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

cards_html = []
num = 0
for sec in data:
    cards_html.append(f'<div class="section-title">{esc(sec["name"])}</div>')
    for it in sec["items"]:
        num += 1
        cls = "tag-international" if it["tag"] == "intl" else "tag-china"
        cards_html.append(
            f'<article class="card"><div class="card-head"><span class="card-num">{num:02d}</span>'
            f'<span class="tag {cls}">{"国际" if it["tag"] == "intl" else "国内"}</span></div>'
            f'<h3>{esc(it["t"])}</h3><p>{esc(it["p"])}</p>'
            f'<div class="src">{esc(it["src"])}</div></article>'
        )

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🗞️ 滑雪晨报 {TITLE_DATE}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0f1420; color:#e8ecf4; font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; line-height:1.7; padding:24px 16px 60px; }}
.wrap {{ max-width:860px; margin:0 auto; }}
.header {{ text-align:center; padding:28px 0 20px; border-bottom:1px solid #232b3d; }}
.header h1 {{ font-size:26px; letter-spacing:2px; }}
.header .sub {{ color:#8fa0b8; margin-top:8px; font-size:14px; }}
.stats-bar {{ display:flex; flex-wrap:wrap; gap:10px; justify-content:center; margin:18px 0 8px; }}
.stat {{ background:#1a2234; border:1px solid #2a3550; border-radius:8px; padding:6px 14px; font-size:12px; color:#aebdda; }}
.stat b {{ color:#ffd76a; font-size:15px; }}
.section-title {{ font-size:19px; font-weight:700; color:#ffd76a; margin:34px 0 14px; padding-left:12px; border-left:4px solid #ffd76a; }}
.card {{ background:#161e30; border:1px solid #26314a; border-radius:10px; padding:16px 18px; margin-bottom:14px; }}
.card-head {{ display:flex; align-items:center; gap:10px; margin-bottom:6px; }}
.card-num {{ color:#ffd76a; font-weight:700; font-size:13px; }}
.tag {{ font-size:11px; border-radius:20px; padding:2px 10px; }}
.tag-international {{ background:#1d3a5f; color:#7cc4ff; }}
.tag-china {{ background:#5f2b2b; color:#ff9d9d; }}
.card h3 {{ font-size:16px; margin:4px 0 8px; color:#fff; }}
.card p {{ font-size:13.5px; color:#c3cde0; }}
.card .src {{ margin-top:10px; font-size:11.5px; color:#7c88a0; text-align:right; }}
footer {{ margin-top:40px; padding-top:16px; border-top:1px solid #232b3d; text-align:center; color:#7c88a0; font-size:12px; }}
</style>
</head>
<body>
<div class="wrap">
  <header class="header">
    <h1>🎿 滑雪晨报</h1>
    <p class="sub">{TITLE_DATE} · 全球滑雪产业一屏速览</p>
    <div class="stats-bar">
      <div class="stat">新闻 <b>{num}</b> 条</div>
      <div class="stat">版块 <b>{len(data)}</b> 个</div>
      <div class="stat">国际 <b>{sum(1 for s in data for i in s['items'] if i['tag']=='intl')}</b></div>
      <div class="stat">国内 <b>{sum(1 for s in data for i in s['items'] if i['tag']=='china')}</b></div>
    </div>
  </header>
{''.join(cards_html)}
  <footer>数据来源：PowderGuide / FIS / X Games / 各雪场官方 等 30+ 中外媒体</footer>
</div>
</body>
</html>"""

open("ski-morning-daily.html", "w", encoding="utf-8").write(html)
print("OK: ski-morning-daily.html generated,", num, "cards")