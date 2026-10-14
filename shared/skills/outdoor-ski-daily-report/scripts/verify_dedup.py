# -*- coding: utf-8 -*-
"""
日报查重 + 结构校验工具（滑雪晨报 / 户外日报通用）

用法:
    python3 verify_dedup.py ski        # 校验 ski-morning-daily.html + 查重
    python3 verify_dedup.py outdoor    # 校验 outdoor-adventure-daily.html + 查重
    python3 verify_dedup.py ski --n 5  # 指定基线期数（默认5）

设计要点（踩过的坑）:
1) 补丁文件的 NEW_SECTIONS 有两种历史写法：'''[  与  '''SECTIONS = [
   直接 s.index("SECTIONS") 会命中 re.sub(r'^SECTIONS = \\[...') 的正则字符串内部，
   导致 ast.literal_eval 报 unterminated string literal。
   稳法 = 先切三引号块 → 对块内第一个 "[" 做括号配平（跳过字符串内部与转义）→ 再 literal_eval。
2) 不能拿 ski_latest_titles.json 当"上一期"基线 —— 它被生成脚本每次覆盖。
   基线必须取自 patch_MMDD.py / gen_*.py.bakMMDD。
3) 6 字 shingle 检测必须过品牌/年份/通用赛事名白名单，否则噪音压倒信号。
   命中后仍需人工复核句式模板。
"""
import re, ast, sys, pathlib, itertools, argparse

WD = pathlib.Path(__file__).resolve().parent
# 技能目录下的副本(scripts/)会被直接调用,此时 __file__ 指向 skills/.../scripts/,
# 里面没有生成器与补丁。若当前工作目录看起来才是真正的项目根,就切过去。
if not (WD / "gen_ski.py").exists() and not (WD / "gen_outdoor.py").exists():
    _cand = pathlib.Path.cwd()
    if (_cand / "gen_ski.py").exists() or (_cand / "gen_outdoor.py").exists():
        WD = _cand

# ---------------------------------------------------------------- 解析工具

def bracket_span(s, start):
    """从 start（指向 '[' 或 '{'）开始做括号配平，跳过字符串内部与转义。返回 (start, end)。"""
    pairs = {"[": "]", "{": "}"}
    d = 0; in_str = None; p = start
    while p < len(s):
        c = s[p]
        if in_str:
            if c == "\\":
                p += 2; continue
            if c == in_str:
                in_str = None
        else:
            if c in "\"'":
                in_str = c
            elif c in "([{":
                d += 1
            elif c in ")]}":
                d -= 1
                if d == 0:
                    return start, p + 1
        p += 1
    raise ValueError("bracket not balanced")


def _strip_triple(s, marker):
    """若存在 marker='''，返回三引号之间的内容，否则原样返回。"""
    if marker in s:
        st = s.index(marker) + len(marker)
        en = s.index("'''", st)
        return s[st:en]
    return s


def _literal_from(s, order="[{"):
    """从字符串里抓出数据块并 literal_eval。
    order 决定优先尝试哪个起始符——因为 CARDS 字典内部也有列表，先试 '[' 会抓错。"""
    body = _strip_triple(s, "NEW_SECTIONS = '''")
    for ch in order:
        pos = 0
        while True:
            if ch not in body[pos:]:
                break
            j = body.index(ch, pos)
            try:
                a, b = bracket_span(body, j)
                return ast.literal_eval(body[a:b])
            except Exception:
                pos = j + 1
    raise ValueError("找不到可解析的数据块")


def titles_ski(path):
    data = _literal_from(pathlib.Path(path).read_text(encoding="utf-8"), order="[")
    return [it["t"] for sec in data for it in sec["items"]]


def titles_outdoor(path):
    data = _literal_from(pathlib.Path(path).read_text(encoding="utf-8"), order="{")
    out = []
    for k, lst in data.items():
        for it in lst:
            out.append(it[1])
    return out


# ---------------------------------------------------------------- 查重

WHITELIST = [
    "2026", "2027", "2627", "202627", "XGames", "FIS", "BOA", "Vail", "POWDER",
    "SKI", "BEAMS", "Amer", "Sports", "Capital", "Summer", "Atomic", "Salomon",
    "始祖鸟", "世界杯", "高山滑雪世界杯", "冬奥会", "北欧两项", "国际奥委会",
    "UCI", "ITT", "TTT", "MSR", "AI", "U23",
]


def _norm(t):
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", t)


def _shingles(t, n=6):
    t = _norm(t)
    return {t[i:i + n] for i in range(max(0, len(t) - n + 1))}


def _is_white(frag):
    return any(w.lower() in frag.lower() for w in WHITELIST)


def compare(new, old, tag):
    hits = 0
    for nt, ot in itertools.product(new, old):
        inter = {f for f in (_shingles(nt) & _shingles(ot)) if not _is_white(f)}
        if inter:
            hits += 1
            print(f"  [跨期] {tag}\n         本期: {nt}\n         旧期: {ot}\n         片段: {sorted(inter)}")
    return hits


# ---------------------------------------------------------------- 基线发现

def current_mmdd(kind):
    """从当前生成器里读出"今天"，用来把今天的补丁从基线里剔除。
    否则会出现'拿今天当昨天'的假重复（历史上踩过两次）。"""
    f = "gen_ski.py" if kind == "ski" else "gen_outdoor.py"
    s = (WD / f).read_text(encoding="utf-8")
    if kind == "outdoor":
        # 户外：日期写在 CARDS 上方那行注释里（# ... （YYYY-MM-DD））。历史上这行注释
        # 被重复写过多次，用 [:4000] 截断会读到旧注释行，于是 current_mmdd 返回上一期，
        # 当天的 cards_MMDD_data.py 被当成基线（= 拿今天当昨天，2026-09-30 踩到）。
        # 取 CARDS = { 之前最后一个日期即为当期。
        head = s[: s.index("CARDS = {")] if "CARDS = {" in s else s
        ms = re.findall(r"(\d{4})-(\d{1,2})-(\d{1,2})", head)
        if ms:
            _, mo, dy = ms[-1]
            return f"{int(mo):02d}{int(dy):02d}"
    m = re.search(r"DATE\s*=\s*['\"](\d{4})年(\d{1,2})月(\d{1,2})日", s)
    if m:
        return f"{int(m.group(2)):02d}{int(m.group(3)):02d}"
    m = re.search(r"[（(](\d{4})-(\d{1,2})-(\d{1,2})[)）]", s)
    if m:
        return f"{int(m.group(2)):02d}{int(m.group(3)):02d}"
    return None


def find_baselines(kind, n):
    """kind: 'ski' | 'outdoor'。按日期倒序取最近 n 份历史数据源（剔除当天）。"""
    today = current_mmdd(kind)
    patch_map, bak_map = {}, {}
    # 注意：patch_MMDD.py 是"滑雪"的补丁格式（NEW_SECTIONS）。户外日报历史上把卡片
    # 数据写到 /tmp/cards_sepN.py，项目内没有 outdoor 补丁，所以 outdoor 只能用
    # gen_outdoor.py.bakMMDD 做基线。
    if kind == "ski":
        # 注意 [a-z]* 而非 [a-z]?：历史上出现过 patch_0928ski.py / patch_0929ski.py
        # 这类多字母后缀命名，用 ? 会漏掉整期基线（2026-09-30 修）。
        pat = re.compile(r"patch_(\d{4})[a-z]*\.py$")
        for p in WD.glob("patch_*.py"):
            m = pat.search(p.name)
            if m and m.group(1).isdigit():
                d = m.group(1)
                # 同一天多份补丁，取文件名最大的那份（即当天最终定稿）
                if d not in patch_map or p.name > patch_map[d].name:
                    patch_map[d] = p
    else:
        # 户外日报的卡片数据存在 cards_MMDD_data.py（CARDS 字典），
        # 单独靠 gen_outdoor.py.bakMMDD 会缺期（如 9/29 没留 bak）。2026-09-30 补。
        cpat = re.compile(r"cards_(\d{4})_data\.py$")
        for p in WD.glob("cards_*_data.py"):
            m = cpat.search(p.name)
            if m and m.group(1).isdigit():
                d = m.group(1)
                if d not in patch_map or p.name > patch_map[d].name:
                    patch_map[d] = p
    for p in WD.glob(f"gen_{kind}.py.bak*"):
        d = re.findall(r"(\d{4})", p.name)
        if d:
            bak_map[d[-1]] = p
    merged = dict(bak_map)
    merged.update(patch_map)  # 同一天优先用 patch（当日定稿），bak 仅作补充
    cands = sorted(merged.items(), key=lambda x: x[0], reverse=True)
    # 剔除当天与未来
    cands = [(d, p) for d, p in cands if d != today]
    out = cands[:n]
    if today:
        print(f"[基线] 已剔除当天({today})的补丁；采用: " + ", ".join(f"{d}({p.name})" for d, p in out))
    return out


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["ski", "outdoor"])
    ap.add_argument("--n", type=int, default=5, help="基线期数，默认5")
    args = ap.parse_args()
    kind = args.kind

    cur = "gen_ski.py" if kind == "ski" else "gen_outdoor.py"
    html = "ski-morning-daily.html" if kind == "ski" else "outdoor-adventure-daily.html"
    extractor = titles_ski if kind == "ski" else titles_outdoor

    new = extractor(WD / cur)
    print(f"当前 {cur} 标题数: {len(new)}")

    print(f"\n--- 跨期查重（基线 {args.n} 期）---")
    total = 0
    for d, p in find_baselines(kind, args.n):
        try:
            old = extractor(p)
        except Exception as e:
            print(f"  [跳过] {p.name}: {e}")
            continue
        total += compare(new, old, p.name)
    print(f"跨期人工复核候选数（已过白名单）: {total}")

    print("\n--- 同期内部查重 ---")
    inner = 0
    for a, b in itertools.combinations(new, 2):
        inter = {f for f in (_shingles(a) & _shingles(b)) if not _is_white(f)}
        if inter:
            inner += 1
            print(f"  {a}  <<>>  {b}   片段={sorted(inter)}")
    print(f"同期内部命中: {inner}")

    print("\n--- HTML 结构 ---")
    h = (WD / html).read_text(encoding="utf-8")
    n_h3 = len(re.findall(r"<h3[^>]*>", h))
    n_sec = h.count('class="section-title"')
    print(f"h3 = {n_h3}")
    print(f"section-title = {n_sec}")
    if kind == "ski":
        nums = re.findall(r'class="card-num">(\d+)<', h)
        print("intl =", h.count('class="tag tag-international"'))
        print("cn =", h.count('class="tag tag-china"'))
        print(f"card-num 数量 = {len(nums)} 连续 = {nums == [f'{i:02d}' for i in range(1, len(nums) + 1)]}")
    else:
        tags = re.findall(r'class="tag tag-([a-z]+)"', h)
        from collections import Counter
        print("标签分布:", dict(Counter(tags)))
    print("日期 =", re.findall(r"2026年\d{1,2}月\d{1,2}日", h)[:3])


if __name__ == "__main__":
    main()
