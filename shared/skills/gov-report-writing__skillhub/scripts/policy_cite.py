#!/usr/bin/env python3
"""
gov-report-writing（公文写作）政策引用溯源校验脚本

把公文里所有政策引用（《XX》 + 发文字号 + 发布/生效日期）抽出来，逐条校验
要素是否齐全、格式是否规范，输出一份可以直接附在稿子后面的**政策引用溯源表**。

⚠️ 边界（必须如实告知用户）:
    本脚本做的是**规范与要素完整性校验**，不是事实核验。
    它不会联网比对文件是否存在、是否已废止——那一步必须由用户拿官方原文核对。
    脚本的作用是把"哪些引用缺文号、缺日期、带待补标记"一次性列清楚，
    让核对这件事从"凭着感觉翻"变成"照着清单查"。

用法:
    python scripts/policy_cite.py 报告.docx
    python scripts/policy_cite.py 报告.docx --save 溯源清单.md
    python scripts/policy_cite.py 报告.docx --json
    python scripts/policy_cite.py 报告.docx --quiet

退出码:
    0 = 未发现问题
    1 = 存在建议项（P2/P3）
    2 = 存在必须处理项（P1，如政策依据无文号、疑似编造风险）

兼容性:
    - 平台: Windows / macOS / Linux
    - Python: 3.7+
    - 依赖: 纯标准库（DOCX 解析用 zipfile + ElementTree）
"""
import io
import os
import re
import sys
import json
import zipfile
import argparse
import datetime

import xml.etree.ElementTree as ET

# ============================================================
# 跨平台控制台编码兼容
# ============================================================
def _setup_console():
    """将 stdout/stderr 重配置为 UTF-8，Windows 控制台也可稳定输出。"""
    for stream_name in ('stdout', 'stderr'):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            reconfigure = getattr(stream, 'reconfigure', None)
            if reconfigure is not None:
                reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass


_setup_console()

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

# ============================================================
# 识别规则
# ============================================================
# 书名号内的政策/文件名（不含换行，2-60 字）
RE_BOOK = re.compile(r'《([^》\n]{2,60})》')

# 规范发文字号：机关代字 + 六角括号年份 + 序号 + 号
RE_DOC_NO_OK = re.compile(
    r'[\u4e00-\u9fa5A-Za-z]{0,12}〔\s*\d{4}\s*〕\s*第?\s*\d{1,4}\s*号')

# 不规范的括号形式（半角方括号 / 全角圆括号 / 六角括号缺"号"字）
RE_DOC_NO_BAD = re.compile(
    r'[\u4e00-\u9fa5A-Za-z]{0,12}(?:[\[【（(]\s*\d{4}\s*[\]】）)])'
    r'\s*第?\s*\d{1,4}\s*号?')

# 「令」式文号（主席令 / 国务院令 / 部令等）——不是〔〕格式，但同样合法，不按格式问题处理
RE_DOC_NO_ORDER = re.compile(
    r'(?:主席令|国务院令|部令|政府令|委员会令|总局令|局令|'
    r'银保监会令|证监会令|国家发展改革委令|中国人民银行令)'
    r'\s*第?\s*[0-9〇一二三四五六七八九十百]{1,6}\s*号')

# 国家/行业/地方标准编号（GB/T 9704-2012、DB11/T 等）——同样是有据可查的标识，不算缺文号
RE_STD_NO = re.compile(
    r'(?:GB|GB/T|GB/Z|GBJ|JGJ|CJJ|GA|DB\d{2}|Q/|ISO|IEC)\s*/?\s*'
    r'[A-Z]{0,3}\s*\d+(?:\.\d+)*(?:\s*[-—]\s*\d{2,4})?')

# 发布日期 / 生效日期
RE_DATE = re.compile(r'\d{4}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?')

# 待补/待核实标记（与 E11、E12 的占位约定一致）
RE_PENDING = re.compile(r'待核实|待补|待确认|需核实|XXXXX|XX单位|XX文件')

# 常见"引据动词"——用于判断该引用是不是"政策依据型"
RE_CITE_LEAD = re.compile(r'根据|依据|按照|遵照|贯彻|落实|对照|结合.{0,6}要求|为.{0,12}(?:深入)?贯彻')

# 文种词（书名号里出现这些，多半是用户把自家文件也写进书名号，需要区分对待）
GENRE_WORDS = ('通知', '通报', '报告', '请示', '批复', '函', '纪要', '决定',
               '意见', '公告', '通告', '方案', '办法', '规定', '标准', '细则')


# ============================================================
# 文本提取
# ============================================================
def resolve_path(raw_path):
    """路径规范化：去引号、展开 ~、转绝对路径（支持中文路径）。"""
    if not raw_path:
        return None
    p = raw_path.strip()
    if len(p) >= 2 and p[0] in ('"', "'") and p[-1] == p[0]:
        p = p[1:-1]
    p = os.path.expanduser(p)
    return os.path.abspath(p)


def extract_text(path):
    """提取文本：支持 .docx / .md / .txt，返回 (文本, 错误信息)。"""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.docx':
        try:
            with zipfile.ZipFile(path) as z:
                try:
                    raw_xml = z.read('word/document.xml')
                except KeyError:
                    return None, '无效 DOCX：缺少 word/document.xml'
                doc_xml = raw_xml.decode('utf-8-sig', errors='replace')
            root = ET.fromstring(doc_xml)
            paragraphs = []
            for p in root.findall('.//' + W + 'p'):
                texts = [t.text or '' for t in p.findall('.//' + W + 't')]
                line = ''.join(texts).strip()
                if line:
                    paragraphs.append(line)
            return '\n'.join(paragraphs), None
        except zipfile.BadZipFile:
            return None, '无法打开文件（不是有效的 zip/DOCX）'
        except ET.ParseError:
            return None, 'XML 解析失败（文档可能损坏）'
        except Exception as exc:
            return None, '读取 DOCX 失败: %s' % exc
    for enc in ('utf-8-sig', 'utf-8', 'gbk'):
        try:
            with io.open(path, 'r', encoding=enc) as fh:
                return fh.read(), None
        except UnicodeDecodeError:
            continue
        except Exception as exc:
            return None, '读取文件失败: %s' % exc
    return None, '无法解码文件（尝试过 UTF-8 / GBK）'


def _sentence_of(text, pos):
    """返回包含 pos 的句子区间 (start, end)。"""
    starts = [text.rfind(ch, 0, pos) for ch in ('。', '；', '\n', '：')]
    start = max(starts) + 1
    ends = [text.find(ch, pos) for ch in ('。', '；', '\n')]
    ends = [e for e in ends if e != -1]
    end = min(ends) + 1 if ends else len(text)
    return start, end


def _line_of(text, pos):
    """返回 pos 所在行号（1-based）。"""
    return text.count('\n', 0, pos) + 1


# ============================================================
# 核心分析
# ============================================================
def analyze(text, now_year=None):
    """抽取并校验全部政策引用，返回 (引用清单, 问题清单, 统计)。"""
    now_year = now_year or datetime.date.today().year
    citations = []
    issues = []

    seen_positions = set()
    for m in RE_BOOK.finditer(text):
        name = m.group(1).strip()
        pos = m.start()
        if name in ('.', '略') or not name:
            continue
        # 同一位置只处理一次
        if pos in seen_positions:
            continue
        seen_positions.add(pos)

        s_start, s_end = _sentence_of(text, pos)
        sentence = text[s_start:s_end]

        # 同句 + 紧随 60 字内的引用上下文（文号常跟在书名号之后）
        ctx = text[max(0, pos - 40): min(len(text), m.end() + 60)]

        doc_no_ok = RE_DOC_NO_OK.search(ctx)
        order_no = RE_DOC_NO_ORDER.search(ctx)
        std_no = RE_STD_NO.search(ctx)
        doc_no_bad = RE_DOC_NO_BAD.search(ctx)
        date_match = RE_DATE.search(ctx)
        pending = RE_PENDING.search(sentence)
        # 「引据动词」只在**本句内**找 —— 跨句/跨段的动词不算该引用的引导词
        lead_window = text[s_start:pos]
        if len(lead_window) > 60:
            lead_window = lead_window[-60:]
        lead = RE_CITE_LEAD.search(lead_window)
        is_cite = lead is not None
        is_own_document = any(g in name for g in GENRE_WORDS) and not is_cite

        doc_no = (doc_no_ok or order_no or std_no)
        entry = {
            'name': name,
            'line': _line_of(text, pos),
            'doc_no': doc_no.group(0).strip() if doc_no else None,
            'date': date_match.group(0).replace(' ', '') if date_match else None,
            'cite_lead': lead.group(0) if lead else None,
            'is_citation': is_cite,
            'is_own_document': is_own_document,
            'pending_mark': pending.group(0) if pending else None,
            'sentence': sentence.strip()[:120],
            'status': 'ok',
            'advice': None,
            'priority': None,
        }

        # ---- 逐条判定 ----
        if pending:
            entry['status'] = 'pending'
            entry['priority'] = 'P1'
            entry['advice'] = ('含「%s」占位，定稿前必须替换为真实文号与日期；'
                               '若确实查不到原文，保留缓冲表述「根据 XX 关于 XX 的要求」'
                               '并列入待补清单' % entry['pending_mark'])
        elif doc_no_bad and not doc_no:
            entry['status'] = 'format'
            entry['priority'] = 'P2'
            entry['advice'] = ('发文字号括号不规范（当前「%s」）。'
                               '国标要求用六角括号〔〕、且以「号」结尾，'
                               '例：国办发〔2026〕12号' % doc_no_bad.group(0).strip())
        elif is_cite and not doc_no:
            entry['status'] = 'no_doc_no'
            entry['priority'] = 'P1'
            entry['advice'] = ('该处为政策依据型引用，但未给出发文字号。'
                               '补上文号；查不到的不要凭印象补，改为缓冲表述并列入待补清单')
        elif is_cite and not date_match:
            entry['status'] = 'no_date'
            entry['priority'] = 'P3'
            entry['advice'] = '建议补发布日期或生效日期，便于核验时效'
        elif is_own_document:
            entry['status'] = 'own'
            entry['advice'] = '疑似本单位/国内文种名称而非外部政策，不计入溯源要求'

        # 文号年份合理性（仅在有〔〕式文号时）
        if doc_no_ok:
            ym = re.search(r'(\d{4})', doc_no_ok.group(0))
            if ym:
                y = int(ym.group(1))
                if y > now_year + 1 or y < 2000:
                    issues.append({
                        'priority': 'P1',
                        'line': entry['line'],
                        'found': '发文字号年份异常：%s' % doc_no_ok.group(0).strip(),
                        'suggestion': '核对年份是否写错（当前年份 %d）' % now_year,
                    })

        citations.append(entry)

    # ---- 书名号配对 ----
    n_open, n_close = text.count('《'), text.count('》')
    if n_open != n_close:
        issues.append({
            'priority': 'P1', 'line': None,
            'found': '书名号不成对：《 %d 个 / 》 %d 个' % (n_open, n_close),
            'suggestion': '补齐缺失的书名号，避免引用范围错误',
        })

    # ---- 同文异称（含非依据型引用，同一份文件不该有两种写法）----
    # 归一化：去掉「关于」「的」等虚词后比较，能抓住
    # 「关于完善科技激励机制的若干意见」vs「完善科技激励机制若干意见」这类差异
    def _norm_name(s):
        return re.sub(r'^关于|的', '', s)

    names = sorted(set(c['name'] for c in citations))
    norm_map = {}
    for nm in names:
        norm_map.setdefault(_norm_name(nm), []).append(nm)
    for _key, group in norm_map.items():
        if len(group) > 1:
            issues.append({
                'priority': 'P2', 'line': None,
                'found': '同一文件出现 %d 种写法：%s'
                         % (len(group), '、'.join('《%s》' % g for g in group)),
                'suggestion': '首次引用用全称，后续统一用简称，避免被理解为两份文件',
            })

    # 把条目级问题送进总问题清单
    for c in citations:
        if c['priority'] in ('P1', 'P2'):
            issues.append({
                'priority': c['priority'],
                'line': c['line'],
                'found': '《%s》%s' % (c['name'], {
                    'pending': ' 带待补占位',
                    'format': ' 发文字号格式不规范',
                    'no_doc_no': ' 缺发文字号',
                }.get(c['status'], '')),
                'suggestion': c['advice'],
            })

    real_cites = [c for c in citations if c['is_citation']]
    stats = {
        'total': len(citations),
        'citations': len(real_cites),
        'with_doc_no': sum(1 for c in real_cites if c['doc_no']),
        'with_date': sum(1 for c in real_cites if c['date']),
        'pending': sum(1 for c in citations if c['status'] == 'pending'),
        'problems': len([i for i in issues if i['priority'] == 'P1']),
        'advices': len([i for i in issues if i['priority'] == 'P2']),
    }
    return citations, issues, stats


# ============================================================
# 输出
# ============================================================
def render(citations, issues, stats, path):
    print('=' * 62)
    print('政策引用溯源校验')
    print('=' * 62)
    print('文件:     %s' % path)
    print('引用条目: %d 条（其中「根据/依据」型政策依据 %d 条）' % (stats['total'], stats['citations']))
    print('要素齐全: 带发文字号 %d 条 / 带日期 %d 条' % (stats['with_doc_no'], stats['with_date']))
    print('-' * 62)

    if not citations:
        print('未检出任何《》引用。')
        print('如果稿子里本应有政策依据，请检查书名号是否被省略——')
        print('国标要求政策文件名称必须加书名号，缺书名号会导致引用范围不清。')
        return

    print('引用清单:')
    for i, c in enumerate(citations, 1):
        flag = {'ok': '[OK]', 'pending': '[!!]', 'format': '[!!]',
                'no_doc_no': '[!!]', 'no_date': '[--]', 'own': '[--]'}[c['status']]
        print('  %s %-2d 第%3d 行  《%s》' % (flag, i, c['line'], c['name']))
        print('        文号: %s    日期: %s' % (c['doc_no'] or '—', c['date'] or '—'))
        if c['advice']:
            print('        %s' % c['advice'])

    print('-' * 62)
    print('汇总: 必须处理 %d 项 / 建议处理 %d 项' % (stats['problems'], stats['advices']))

    if issues:
        print()
        print('问题清单:')
        for it in issues:
            loc = '第 %d 行' % it['line'] if it['line'] else '全文'
            print('  [%s] %s  %s' % (it['priority'], loc, it['found']))
            print('         → %s' % it['suggestion'])

    print()
    print('接下来要做的事（本脚本不做事实核验）:')
    print('  1. 按下面的来源优先级，逐条找到政策原文，核对文件全称、发文字号、发布日期：')
    print('     ① 中国政府网 / 国务院政策文件库（.gov.cn）')
    print('     ② 部委官网 → ③ 省级政府官网 / 地方政策法规库 → ④ 人民日报 / 新华社')
    print('  2. 顺带确认该文件是否已被修订或废止（看有没有更新版本或废止通知）。')
    print('  3. 查不到的，改成缓冲表述「根据 XX 关于 XX 的要求」，不要凭印象补。')
    print('  4. 核完把文号与日期填回稿子，再跑一次本脚本，应显示「必须处理 0 项」。')


def _md_table(rows, headers):
    out = ['| ' + ' | '.join(headers) + ' |',
           '|' + '|'.join(['---'] * len(headers)) + '|']
    for r in rows:
        out.append('| ' + ' | '.join('' if v is None else str(v).replace('\n', ' ').replace('|', '\\|')
                                     for v in r) + ' |')
    return '\n'.join(out)


def build_markdown(citations, issues, stats, path):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = []
    lines.append('# 政策引用溯源表')
    lines.append('')
    lines.append('> 生成时间：%s' % now)
    lines.append('> 源文件：`%s`' % path)
    lines.append('> 说明：本表由 `scripts/policy_cite.py` 自动生成，')
    lines.append('> 作用是列出**需要逐条核对**的引用及其要素缺口。')
    lines.append('> **本表不构成事实核验**——文件是否存在、是否已废止，须比对官方原文。')
    lines.append('')
    lines.append('## 汇总')
    lines.append('')
    lines.append('- 引用条目：%d 条' % stats['total'])
    lines.append('- 政策依据型（根据/依据）：%d 条' % stats['citations'])
    lines.append('- 已带发文字号：%d 条' % stats['with_doc_no'])
    lines.append('- 已带日期：%d 条' % stats['with_date'])
    lines.append('- 必须处理：%d 项' % stats['problems'])
    lines.append('- 建议处理：%d 项' % stats['advices'])
    lines.append('')
    lines.append('## 引用清单')
    lines.append('')
    if citations:
        rows = []
        for i, c in enumerate(citations, 1):
            rows.append([
                i,
                '第 %d 行' % c['line'],
                '《%s》' % c['name'],
                c['doc_no'] or '—',
                c['date'] or '—',
                {'ok': '要素齐全', 'pending': '待补占位', 'format': '文号格式',
                 'no_doc_no': '缺文号', 'no_date': '缺日期', 'own': '本单位文件'}.get(c['status'], ''),
                '☐ 已核对',
            ])
        lines.append(_md_table(rows, ['#', '位置', '文件名称', '发文字号', '日期', '状态', '核对']))
    else:
        lines.append('_未检出《》引用。_')
    lines.append('')
    lines.append('## 问题清单')
    lines.append('')
    if issues:
        for it in issues:
            loc = '第 %d 行' % it['line'] if it['line'] else '全文'
            lines.append('- **[%s] %s** %s' % (it['priority'], loc, it['found']))
            lines.append('  - → %s' % it['suggestion'])
    else:
        lines.append('_未发现问题。_')
    lines.append('')
    lines.append('## 核对来源优先级')
    lines.append('')
    lines.append('1. 中国政府网 / 国务院政策文件库（.gov.cn）')
    lines.append('2. 部委官网')
    lines.append('3. 省级政府官网 / 地方政策法规库')
    lines.append('4. 人民日报 / 新华社')
    lines.append('')
    lines.append('核对时一并确认：是否已被修订、是否有更新版本、是否已废止。')
    lines.append('')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='gov-report-writing 政策引用溯源校验（要素完整性 + 格式规范）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='退出码: 0=无问题, 1=有建议项, 2=有必须处理项'
    )
    parser.add_argument('source', help='待检查的 .docx / .md / .txt 文件')
    parser.add_argument('--save', default=None,
                        help='把溯源表另存为 Markdown 文件（可直接附在稿子后面）')
    parser.add_argument('--json', dest='as_json', action='store_true',
                        help='以 JSON 格式输出结果')
    parser.add_argument('--quiet', action='store_true', help='仅输出问题项')
    args = parser.parse_args(argv)

    path = resolve_path(args.source)
    if not path or not os.path.isfile(path):
        print('[FAIL] 文件不存在：%s' % (path or args.source))
        print('       请检查路径；路径含空格时用引号包起来。')
        return 2

    text, err = extract_text(path)
    if err:
        print('[FAIL] %s' % err)
        return 2
    if not text.strip():
        print('[FAIL] 文件内容为空，无可校验的引用。')
        return 2

    citations, issues, stats = analyze(text)

    if args.save:
        save_path = resolve_path(args.save)
        try:
            with io.open(save_path, 'w', encoding='utf-8') as fh:
                fh.write(build_markdown(citations, issues, stats, path))
            print('[OK] 溯源表已保存：%s' % save_path)
        except Exception as exc:
            print('[WARN] 溯源表保存失败：%s' % exc)

    if args.as_json:
        print(json.dumps({
            'file': path,
            'stats': stats,
            'citations': citations,
            'issues': issues,
        }, ensure_ascii=False, indent=2))
    elif args.quiet:
        for it in issues:
            loc = '第 %d 行' % it['line'] if it['line'] else '全文'
            print('[%s] %s %s' % (it['priority'], loc, it['found']))
        print('必须处理 %d 项 / 建议处理 %d 项' % (stats['problems'], stats['advices']))
    else:
        render(citations, issues, stats, path)

    if stats['problems']:
        return 2
    if stats['advices']:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
