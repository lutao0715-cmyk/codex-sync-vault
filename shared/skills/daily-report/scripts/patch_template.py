# -*- coding: utf-8 -*-
"""通用补丁模板：把当天数据块写进 gen_ski.py（不破坏 HTML 模板）

用法一（推荐，数据外置）：
    # data_1013.py 里写一行： NEW_SECTIONS = '''[ ... ]'''
    python3 patch_template.py --date 2026年10月13日 --weekday 星期一 \
        --sections-file data_1013.py --footer "数据来源：PowderGuide / FIS 等 30+ 中外媒体"

用法二（直接改本文件顶部的 NEW_SECTIONS 与 DATE/WEEKDAY）：
    python3 patch_template.py --date 2026年10月13日 --weekday 星期一

安全约束（踩坑换来的，别改）：
  * 引号铁律：数据块里 "t"/"p" 的值只能用中文「」，出现 ASCII 双引号会与定界符冲突 → SyntaxError
  * 逗号铁律：每个字典项行末必须有逗号，否则报错行号会指向下一行，排查极费时
  * 本脚本写盘前会做 ast.literal_eval + compile 双重自检，任一失败不落盘
"""
import argparse, ast, importlib.util, pathlib, re, sys

# ---- 用法二：直接把当天数据写在这里 ----
NEW_SECTIONS = ""

ap = argparse.ArgumentParser()
ap.add_argument("--date", required=True, help="如 2026年10月13日")
ap.add_argument("--weekday", required=True, help="如 星期一")
ap.add_argument("--sections-file", default=None, help="含 NEW_SECTIONS 变量的 py 文件")
ap.add_argument("--footer", default=None, help="页脚「数据来源：…」整行文字")
ap.add_argument("--gen", default="gen_ski.py", help="目标生成器，默认 gen_ski.py")
a = ap.parse_args()

wd = pathlib.Path(__file__).resolve().parent

if a.sections_file:
    p = pathlib.Path(a.sections_file)
    if not p.is_absolute():
        p = wd / p
    spec = importlib.util.spec_from_file_location("seg", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    NEW_SECTIONS = mod.NEW_SECTIONS

if not NEW_SECTIONS.strip():
    sys.exit("[中止] NEW_SECTIONS 为空：请用 --sections-file 指定数据文件，或直接编辑本文件")

# ---- 自检：数据块必须能被解析，且条数/版块数对得上 ----
data = ast.literal_eval(NEW_SECTIONS)
n_items = sum(len(s["items"]) for s in data)
n_sec = len(data)
print(f"[自检] 版块 {n_sec} 个 / 条目 {n_items} 条")
if n_items != 27:
    print(f"[警告] 滑雪晨报标准为 27 条，当前 {n_items} 条 —— 确认是本期有意调整？")
china = sum(1 for s in data for i in s["items"] if i["tag"] == "china")
intl = n_items - china
print(f"[自检] 国际 {intl} / 国内 {china}（tag-china 数 = {china}）")
if (intl, china) != (25, 2):
    print("[提醒] 与标准配额（国际 25 / 国内 2）不一致 —— 若为用户授权放宽，请在当天日志中注明；"
          "否则请调整选题")

# ---- 日期常量 ----
TITLE_DATE = f"{a.date} · {a.weekday}"
src_path = wd / a.gen
src = src_path.read_text(encoding="utf-8")
for pat, val in [
    (r'DATE = "[^"]*"', f'DATE = "{a.date}"'),
    (r'WEEKDAY = "[^"]*"', f'WEEKDAY = "{a.weekday}"'),
    (r'TITLE_DATE = "[^"]*"', f'TITLE_DATE = "{TITLE_DATE}"'),
]:
    if not re.search(pat, src):
        sys.exit(f"[中止] 在 {a.gen} 里找不到 {pat}")
    src = re.sub(pat, val, src, count=1)

# ---- SECTIONS 整块替换（括号配平，跳过字符串内部与转义）----
def block_span(s, key):
    i = s.index(key)
    j = s.index("[", i)
    d = 0; in_str = None; p = j
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
            elif c == "[":
                d += 1
            elif c == "]":
                d -= 1
                if d == 0:
                    return j, p + 1
        p += 1
    raise ValueError("SECTIONS 括号未配平")

# 注意：必须先切出 SECTIONS 这个三引号块再找 "["。
# 否则 s.index("SECTIONS") 可能命中本文件/生成器里正则字符串内部的 "SECTIONS"。
m = re.search(r"SECTIONS\s*=\s*'''", src)
if m:
    head = src[:m.end()]
    tail = src[m.end():]
    end = tail.index("'''")
    body = tail[:end]
    a0, b0 = block_span(body, "[")
    new_body = NEW_SECTIONS.strip()
    src = head + "\n" + new_body + "\n" + tail[end:]
else:
    sys.exit("[中止] gen_ski.py 里没找到 SECTIONS = ''' 结构")

# ---- 页脚 ----
if a.footer:
    if not re.search(r"数据来源：[^<]*", src):
        print("[警告] 没找到页脚「数据来源：」行，已跳过")
    else:
        src = re.sub(r"数据来源：[^<]*", a.footer, src, count=1)

# ---- 落盘前双重自检 ----
compile(src, a.gen, "exec")
src_path.write_text(src, encoding="utf-8")
print(f"[完成] {a.gen} 已更新：{n_sec} 版块 / {n_items} 条 / {TITLE_DATE}")
print("       接着运行：python3 gen_ski.py")
