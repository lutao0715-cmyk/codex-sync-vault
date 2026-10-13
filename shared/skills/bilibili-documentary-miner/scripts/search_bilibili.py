#!/usr/bin/env python3
"""B站搜索 + 验证 + 字幕检测 核心工具。

用法:
  python3 search_bilibili.py search <keyword> [--page N]
  python3 search_bilibili.py verify <bvid> [bvid2 ...]
  python3 search_bilibili.py related <bvid> [--depth N]
  python3 search_bilibili.py cc-check <bvid> [bvid2 ...]
  python3 search_bilibili.py multip-check <bvid> [bvid2 ...]
"""

import json, sys, os, re, urllib.request, time, random

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://www.bilibili.com/',
    'Cookie': 'buvid3=' + ''.join(random.choices('0123456789abcdef', k=32)),
}

def _api(url, retries=2):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode('utf-8'))
            if data.get('code') == 0:
                return data
            print(f"  API返回code={data.get('code')}: {data.get('message','')}", file=sys.stderr)
        except Exception as e:
            print(f"  请求失败: {e}", file=sys.stderr)
            if i < retries - 1:
                time.sleep(1)
    return None

def search(keyword, page=1):
    """搜索B站视频，返回视频列表。"""
    url = (f'https://api.bilibili.com/x/web-interface/search/all/v2'
           f'?keyword={urllib.parse.quote(keyword)}&page={page}')
    # 注意：每条请求需重新生成Cookie
    data = _api(url)
    if not data:
        return []
    for block in data.get('data', {}).get('result', []):
        if block.get('result_type') == 'video':
            return block.get('data', [])
    return []

def verify(bvid):
    """验证单条视频，返回 {bvid, title, duration(秒), play, pages(列表), desc}"""
    data = _api(f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}')
    if not data or not data.get('data'):
        return None
    d = data['data']
    return {
        'bvid': bvid,
        'title': d.get('title', ''),
        'duration': d.get('duration', 0),
        'play': d.get('stat', {}).get('view', 0),
        'pages': len(d.get('pages', [])),
        'desc': (d.get('desc', '') or '')[:300],
    }

def related(bvid):
    """获取相关推荐视频列表。"""
    data = _api(f'https://api.bilibili.com/x/web-interface/archive/related?bvid={bvid}')
    if not data:
        return []
    return data.get('data', [])

def cc_check(bvid, cid=None):
    """检查视频是否有中文CC字幕。返回字幕列表或空列表。"""
    if not cid:
        data = _api(f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}')
        if not data or not data.get('data'):
            return []
        cid = data['data'].get('cid')
    if not cid:
        return []
    data = _api(f'https://api.bilibili.com/x/web-interface/player/v2?bvid={bvid}&cid={cid}')
    if not data:
        return []
    subs = data.get('data', {}).get('subtitle', {}).get('subtitles', [])
    return [s for s in subs if s.get('lan', '').startswith('zh')]

def multip_check(bvid):
    """检查视频是否多P，返回pages数量及每P标题。"""
    data = _api(f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}')
    if not data or not data.get('data'):
        return None
    d = data['data']
    pages = d.get('pages', [])
    return {
        'bvid': bvid,
        'title': d.get('title', ''),
        'page_count': len(pages),
        'pages': [{'title': p.get('part', ''), 'duration': p.get('duration', 0)} for p in pages],
        'duration': d.get('duration', 0),
    }

# ========== 过滤/分类辅助 ==========

SUB_POS = ['中字', '中英', '双语', '国语', '国配', '中文', '熟肉', '简中', '繁中', '中文CC']
SUB_NEG = ['无字', '英字', '生肉', '无中字', '英文字幕', '日语', '韩语', '法语', '德语', '西班牙语', '俄语']
SERIES_PAT = re.compile(
    r'第[一二三四五六七八九十\d]+[季集]|'
    r'S\d{1,2}E\d{1,2}|EP\d{1,3}|'
    r'[Pp]\d{1,2}\s*(?:/|$)|'
    r'全\d{1,3}[集话]|合集|'
    r'[上中下]部|'
    r'\d{1,2}/\d{1,2}\s*(?:[集话]|$)'
)
FOREIGN_PAT = re.compile(r'[A-Za-z]{3,}')

def has_subtitle(title):
    """根据标题判断是否有中文字幕标记。"""
    title_lower = title.lower()
    for kw in SUB_NEG:
        if kw in title_lower or kw in title:
            return False
    for kw in SUB_POS:
        if kw in title_lower or kw in title:
            return True
    return False

def is_foreign(title):
    """判断是否为外国影片。"""
    return bool(FOREIGN_PAT.search(title))

def is_series(title):
    """判断是否为系列剧集。"""
    return bool(SERIES_PAT.search(title))

def classify(title, duration=0):
    """按标题关键词分类。"""
    t = title.lower()
    # 优先匹配
    categories = {
        '骑行': ['骑行', 'bike', 'cycle', 'bicycle', '单车', '摩托', 'motorcycle', 'skateboard',
                  '滑板', 'minding the gap', '直击弯心', 'unbound', 'tt3d', 'icarus', 'fastest',
                  'faster', 'why we ride', 'code yellow', '横跨', 'hitting the apex', 'life cycles',
                  'gravel', 'motorbike', '机车', '重机', '飞车', 'harley', 'ducati', 'moto'],
        '攀岩': ['攀岩', 'climb', 'rock', 'free solo', 'boulder', '抱石', 'dawn wall', '优胜美地',
                  'yosemite', '酋长岩', 'trapped 13', '洞穴救援', 'the rescue', 'reel rock',
                  '弗拉萨西', 'frasassi', '走钢丝', 'man on wire', 'the alpinist', 'el cap',
                  'honnold', 'ondra', 'sharma', 'caldwell', '黎明墙', 'meru', 'allez',
                  'spider', '蜘蛛侠', 'alain robert'],
        '冬季': ['冬季', '雪', '滑雪', 'ski', 'snowboard', '单板', '双板', 'powder', '粉雪',
                  'k2不可能滑降', 'torn', '雪崩', 'avalanche', '冰', 'ice', '冰川', 'glacier',
                  '南极', 'arctic', '北极', '冰原', 'antartic', '南极洲', 'frozen', 'winter'],
        '水上': ['水上', 'water', '冲浪', 'surf', '漂流', 'raft', 'kayak', '皮划艇', 'canoe',
                  '独木舟', '帆船', 'sail', 'kon-tiki', '孤筏', '轻舟', '渡', 'ocean', '大洋',
                  '划艇', 'rowing', 'suicide', 'pacific', 'rowing', 'row'],
        '钓鱼': ['钓鱼', 'fish', 'fishing', 'angler', '钩', '垂钓', '渔', '飞钓', 'fly fish'],
        '水下': ['水下', 'underwater', '潜水', 'dive', 'scuba', 'freedive', '浮潜', '深潜',
                  'shark', '鲨鱼', 'whale', '鲸', 'dolphin', '海豚', 'coral', '珊瑚', 'reef',
                  '深海', 'deep sea', '马里亚纳', 'mariana', 'trench', '海沟', '座头鲸',
                  'humpback', 'orca', '虎鲸', 'blackfish', '黑鲸', 'seaspiracy', '海洋',
                  '子非鱼', 'aquarium', 'aquatic', 'marine', 'ocean', 'sea', '水下漫步',
                  '深海绿洲', 'losing sight of shore', '与鲨', '鲨鱼新发现', '鲨鱼伊甸园',
                  '狂暴鲨鱼', '鲨鱼进食秀', '人鲨', '海洋守护者', 'sea shepherd', 'manta',
                  '蝠鲼', '海龟', 'turtle', 'octopus', '章鱼', 'squid', 'whale', 'manatee',
                  '儒艮', 'seal', '海豹', 'sea lion', '海狮', 'walrus', '海象', 'otter', '海獭',
                  'antarctic', 'polar', 'orca', 'killer', 'humpback', 'gray', 'grey', 'blue',
                  'great', 'white', 'hammerhead', 'bull', 'tiger', 'lemon', 'nurse', 'reef',
                  'blacktip', 'whitetip', 'mako', 'thresher', 'whale', 'basking', 'megamouth',
                  'goblin', 'frilled', 'cow', 'sixgill', 'sevengill', 'saw', 'guitar', 'torpedo',
                  'manta', 'devil', 'eagle', 'cownose', 'stingray', 'skate', 'ray', 'jellyfish',
                  '水母', 'anemone', '海葵', 'starfish', '海星', 'urchin', '海胆', 'cucumber',
                  '海参', 'crab', '蟹', 'lobster', '龙虾', 'shrimp', '虾', 'prawn', 'krill',
                  '磷虾', 'barnacle', '藤壶', 'mussel', '贻贝', 'clam', '蛤', 'oyster', '牡蛎',
                  'scallop', '扇贝', 'cockle', '鸟蛤', 'whelk', '峨螺', 'conch', '海螺',
                  'abalone', '鲍鱼', 'limpet', '帽贝', 'periwinkle', '玉黍螺', 'snail', '蜗牛',
                  'nautilus', '鹦鹉螺', 'ammonite', '菊石', 'giant', 'squid', '大王乌贼',
                  'colossal', 'squid', '巨鱿', 'cuttlefish', '墨鱼', 'sepia', 'octopus', '章鱼',
                  'coconut', 'octopus', 'mimic', 'octopus', 'blue-ringed', 'octopus',
                  'blanket', 'octopus', 'dumbo', 'octopus', 'pelagic', 'emperor', 'nudibranch',
                  '海蛞蝓', 'sea slug', 'flatworm', '扁虫', 'ribbon', 'worm', 'nemertean',
                  'bristle', 'worm', 'polychaete', 'feather', 'duster', 'christmas', 'tree',
                  'spaghetti', 'worm', 'scale', 'worm', 'clam', 'worm', 'peanut', 'worm',
                  'sipunculan', 'echiuran', 'spoon', 'worm', 'priapulid', 'penis', 'worm',
                  'lace', 'worm', 'nemertean', 'ribbon', 'worm', 'bootlace', 'worm', 'lineus',
                  'longissimus', 'horsehair', 'worm', 'nematomorph', 'gordian', 'worm',
                  'roundworm', 'nematode', 'hookworm', 'pinworm', 'whipworm', 'threadworm',
                  'ascaris', 'trichinella', 'guinea', 'worm', 'dracunculus', 'loa', 'loa',
                  'onchocerca', 'wuchereria', 'brugia', 'mansonella', 'dirofilaria', 'heartworm',
                  'lungworm', 'liver', 'fluke', 'blood', 'fluke', 'intestinal', 'fluke',
                  'schistosome', 'tapeworm', 'cestode', 'diphyllobothrium', 'taenia', 'echinococcus',
                  'hymenolepis', 'dipylidium', 'spirometra', 'sparganum', 'mesocestoides',
                  'tetrathyridium', 'platyhelminthes', 'flatworm', 'turbellarian', 'planarian',
                  'triclad', 'polyclad', 'monogenean', 'trematode', 'fluke', 'cestode', 'tapeworm'],
        '空中': ['空中', '天空', 'sky', '飞行', 'fly', 'flying', 'flight', '跳伞', 'skydive',
                  'base jump', 'wingsuit', '翼装', '滑翔', 'paraglide', '滑翔伞', 'hang glide',
                  '热气球', 'balloon', '降落伞', 'parachute', '高空', 'high altitude', 'flowstate',
                  'flow state', 'highline', 'slackline', 'skywalk', 'aerial', 'aviation',
                  'pilot', 'aircraft', 'airplane', 'plane', 'jet', 'glider', 'sailplane',
                  'ultralight', 'microlight', 'trike', 'paramotor', 'ppgl', 'canopy',
                  'freefall', 'track', 'dive', 'arch', 'sit', 'tracking', 'swoop', 'swooping',
                  'hook', 'turn', 'flare', 'landing', 'accuracy', 'target', 'formation',
                  'skydiving', 'belly', 'back', 'head', 'down', 'vertical', 'angle', 'freestyle',
                  'freeflying', 'freefly', 'head-up', 'head-down', 'sit-fly', 'stand-fly',
                  'side-slide', 'carve', 'turn', 'loop', 'roll', 'barrel', 'helix', 'spiral',
                  'dive', 'zoom', 'boost', 'swoop', 'hook', 'turn', 'downsize', 'cross-brace',
                  'rear-riser', 'front-riser', 'deep', 'brake', 'stall', 'parachut', 'parachute',
                  'para', 'chute', 'drop', 'jump', 'jumping', 'leap', 'fall', 'falling', 'dropzone',
                  'dz', 'landing', 'area', 'lz', 'safety', 'gear', 'rig', 'container', 'harness',
                  'reserve', 'aad', 'cypres', 'vigil', 'mars', 'argus', 'sigma', 'visio', 'altimeter',
                  'vario', 'audible', 'dytter', 'sonic', 'flysight', 'fly', 'sight', 'gps',
                  'protrack', 'atmos', 'optima', 'optima', 'neo', 'optima', 'xtreme', 'optima',
                  'xtreme', 'neo', 'optima', 'xtreme', 'neo', 'iar', 'naked', 'outlaw', 'jede',
                  'jede', 'neo', 'jede', 'xtreme', 'jede', 'xtreme', 'neo', 'surge', 'pillar',
                  'pulse', 'pulse', 'neo', 'mirage', 'spectre', 'phantom', 'ghost', 'shadow',
                  'shade', 'storm', 'tempest', 'cyclone', 'hurricane', 'typhoon', 'tornado',
                  'twister', 'whirlwind', 'dust', 'devil', 'wind', 'gust', 'blast', 'breeze',
                  'draft', 'current', 'updraft', 'downdraft', 'thermal', 'lift', 'sink', 'ridge',
                  'wave', 'rotor', 'shear', 'gradient', 'venturi', 'turbulence', 'clear', 'air',
                  'turbulence', 'CAT', 'mountain', 'wave', 'lee', 'wave', 'rotor', 'cloud',
                  'street', 'dust', 'devil', 'landspout', 'waterspout', 'funnel', 'wall', 'cloud',
                  'shelf', 'cloud', 'roll', 'cloud', 'arcus', 'cloud', 'cumulonimbus', 'cumulus',
                  'stratus', 'cirrus', 'altocumulus', 'altostratus', 'nimbostratus', 'stratocumulus',
                  'cirrocumulus', 'cirrostratus', 'lenticular', 'altocumulus', 'standing', 'lenticular',
                  'mammatus', 'anvil', 'overshooting', 'top', 'pileus', 'cap', 'scud', 'fractus',
                  'pannus', 'virga', 'rain', 'shaft', 'curtain', 'streak', 'fallstreak', 'hole',
                  'punch', 'hole', 'cavum', 'distrail', 'contrail', 'vapor', 'trail', 'aviation',
                  'paraglid', 'hangglid', 'speedflying', 'speed', 'fly', 'speed', 'riding', 'speed',
                  'gliding', 'speed', 'sailing', 'dynamic', 'soaring', 'ridge', 'soaring', 'thermal',
                  'soaring', 'wave', 'soaring', 'cross-country', 'XC', 'triangle', 'out-and-return',
                  'open', 'distance', 'goal', 'turnpoint', 'waypoint', 'track', 'log', 'igc',
                  'flight', 'instrument', 'fly', 'sky', 'heaven', 'cloud', 'cloud', 'nine', 'cloud'],
    }
    for cat, kws in categories.items():
        for kw in kws:
            if kw in t:
                return cat
    return '综合'

def filter_videos(videos, min_dur=30, require_sub=True, standalone_only=True):
    """过滤视频列表。"""
    out = []
    for v in videos:
        title = v.get('title', '') or ''
        duration = v.get('duration', v.get('length', 0))
        if isinstance(duration, str):
            parts = duration.split(':')
            if len(parts) == 2:
                duration = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                duration = 0
        if min_dur and duration < min_dur * 60:
            continue
        if not is_foreign(title):
            continue
        if require_sub and not has_subtitle(title):
            continue
        if standalone_only and is_series(title):
            continue
        v = dict(v)
        v['_duration_sec'] = duration
        v['_category'] = classify(title, duration)
        v['_has_sub_title'] = has_subtitle(title)
        v['_is_foreign'] = is_foreign(title)
        v['_is_series'] = is_series(title)
        out.append(v)
    return out


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='B站搜索工具')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('search', help='搜索视频')
    p.add_argument('keyword', help='搜索关键词')
    p.add_argument('--page', type=int, default=1)

    p = sub.add_parser('verify', help='验证视频信息')
    p.add_argument('bvid', nargs='+', help='BV号')

    p = sub.add_parser('related', help='获取相关推荐')
    p.add_argument('bvid', help='BV号')
    p.add_argument('--depth', type=int, default=1, help='扩展深度')

    p = sub.add_parser('cc-check', help='检查CC字幕')
    p.add_argument('bvid', nargs='+', help='BV号')

    p = sub.add_parser('multip-check', help='检查多P')
    p.add_argument('bvid', nargs='+', help='BV号')

    p = sub.add_parser('filter', help='过滤JSON文件')
    p.add_argument('input', help='输入JSON文件')
    p.add_argument('--min-dur', type=int, default=30)
    p.add_argument('--require-sub', action='store_true')
    p.add_argument('--standalone-only', action='store_true')

    args = parser.parse_args()

    if args.cmd == 'search':
        results = search(args.keyword, args.page)
        print(json.dumps(results, ensure_ascii=False, indent=2))

    elif args.cmd == 'verify':
        for bv in args.bvid:
            info = verify(bv)
            print(json.dumps(info, ensure_ascii=False, indent=2))

    elif args.cmd == 'related':
        seen = set()
        def recurse(bvid, depth):
            if depth <= 0 or bvid in seen:
                return
            seen.add(bvid)
            results = related(bvid)
            for v in results:
                bv = v.get('bvid', '')
                print(f"  depth={depth} {bv} dur={v.get('duration',0)}s play={v.get('stat',{}).get('view',0)} | {v.get('title','')[:60]}")
                if bv:
                    recurse(bv, depth - 1)
        recurse(args.bvid, args.depth)

    elif args.cmd == 'cc-check':
        for bv in args.bvid:
            subs = cc_check(bv)
            if subs:
                print(f"{bv}: ✅ 有中文CC字幕")
                for s in subs:
                    print(f"  lan={s.get('lan')} url={s.get('subtitle_url','')[:60]}")
            else:
                print(f"{bv}: ❌ 无中文CC字幕")

    elif args.cmd == 'multip-check':
        for bv in args.bvid:
            info = multip_check(bv)
            if info:
                print(f"===== {bv} =====")
                print(f"  标题: {info['title']}")
                print(f"  P数: {info['page_count']}")
                print(f"  总时长: {info['duration']}s")
                for i, p in enumerate(info['pages']):
                    print(f"    P{i+1}: {p['title']} ({p['duration']}s)")

    elif args.cmd == 'filter':
        data = json.load(open(args.input))
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list):
                    data = v
                    break
        filtered = filter_videos(data, args.min_dur, args.require_sub, args.standalone_only)
        print(json.dumps(filtered, ensure_ascii=False, indent=2))
        print(f"\n--- 过滤统计: {len(data)} -> {len(filtered)}条 ---", file=sys.stderr)