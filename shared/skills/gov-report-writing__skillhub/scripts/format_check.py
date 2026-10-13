#!/usr/bin/env python3
"""
gov-report-writing（公文写作）格式自动检查脚本（跨平台兼容版）

检查生成的 DOCX 文件是否符合 GB/T 9704-2012 以及企业级公文格式规范。

用法:
    python format_check.py <docx文件路径>
    python format_check.py <docx文件路径> --json     # JSON 输出（便于程序化调用）
    python format_check.py <docx文件路径> --quiet     # 仅输出问题项

兼容性:
    - 平台: Windows / macOS / Linux（自动适配路径分隔符、编码、字体名变体）
    - Python: 3.7+
    - 路径: 支持绝对/相对路径、~ 展开、路径含空格、Windows 拖拽带引号

输出:
    格式检查报告，标注所有不符合规范的问题；退出码 0=通过, 1=存在问题
"""
import sys
import os
import re
import io
import json
import platform
import zipfile
import argparse
import xml.etree.ElementTree as ET

# ============================================================
# 跨平台控制台编码兼容
# Windows 控制台默认 GBK，emoji/中文混排时 print 可能 UnicodeEncodeError
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
            pass  # 非标准流（如管道）下 reconfig 失败则忽略

_setup_console()

# ============================================================
# 平台检测
# ============================================================
PLATFORM = platform.system()  # Windows / Darwin / Linux
PY_VERSION = platform.python_version()

# ============================================================
# GB/T 9704-2012 + 企业标准 参数
# ============================================================
EXPECTED_PARAMS = {
    # 页边距 (cm)
    'margin_top_cm': 3.7,      # 上边距
    'margin_bottom_cm': 3.5,    # 下边距
    'margin_left_cm': 2.8,     # 左边距（订口）
    'margin_right_cm': 2.6,    # 右边距（翻口）

    # 标题：允许的字体名变体（跨平台字体名差异）
    'title_fonts': ['方正小标宋简体', '方正小标宋', '方正小标宋_GBK',
                    'FZXiaoBiaoSong-B05S', 'STZhongsong', '华文中宋'],
    'title_size_pt': [20, 22, 18],  # 党组20pt / 通用22pt / 部门18pt(小二号)

    # 正文
    'body_fonts': ['仿宋_GB2312', '仿宋', '仿宋_GBK', 'FangSong_GB2312',
                   'FangSong', '方正仿宋简体'],
    'body_size_pt': 16,  # 三号 = 16pt

    # 一级标题
    'h1_fonts': ['黑体', 'SimHei', '方正黑体简体'],

    # 二级标题
    'h2_fonts': ['楷体_GB2312', '楷体', 'KaiTi', '楷体_GBK'],

    # 行距（固定值，单位 twips：磅 * 20）
    'line_spacing_twips': 560,          # 正文：28 磅
    'title_line_spacing_twips': 600,    # 标题（含各级标题）：30 磅

    # 页码（GB/T 9704-2012 第 7.4 条：4 号半角宋体阿拉伯数字，
    #       单页码居右空一字、双页码居左空一字）
    'page_fonts': ['宋体', 'SimSun', 'NSimSun', '中易宋体'],
    'page_size_pt': 14,                 # 4 号 = 14pt
    'page_size_half_pt': 28,            # w:sz 为半磅值，14pt → 28

    # 首行缩进（DXA，2字符≈480-640，随字号浮动）
    'indent_range': (400, 700),

    # 数字字体
    'number_font': 'Times New Roman',
}

# Word 命名空间
W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W = '{' + W_NS + '}'


def cm_to_twips(cm):
    """cm → twips (1cm ≈ 567 twips, Word 用 1440/inch)"""
    return int(round(cm * 1440 / 2.54))


def resolve_path(raw_path):
    """
    路径规范化（跨平台）：
    - 去掉外层引号（Windows 拖拽/复制路径常带引号）
    - 展开 ~ 用户目录
    - 转换为绝对路径
    """
    if not raw_path:
        return None
    p = raw_path.strip()
    # 去掉成对引号（单引号/双引号）
    if len(p) >= 2 and p[0] in ('"', "'") and p[-1] == p[0]:
        p = p[1:-1]
    p = os.path.expanduser(p)
    p = os.path.abspath(p)
    return p


def normalize_font(font_name):
    """字体名归一化，忽略大小写、下划线、空格差异。"""
    if not font_name:
        return ''
    return re.sub(r'[\s_\-]+', '', font_name).lower()


def font_matches(actual, candidates):
    """判断实际字体名是否命中候选列表（含变体与包含匹配）。"""
    if not actual:
        return False
    a = normalize_font(actual)
    for cand in candidates:
        c = normalize_font(cand)
        if a == c:
            return True
        # 包含匹配：如 '方正小标宋_GBK' 命中 '方正小标宋'
        if len(c) >= 2 and (c in a or a in c):
            return True
    return False


_W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def _serialize_element(elem):
    """把 ElementTree 元素序列化回带 w: 前缀的 XML 字符串。

    不能直接用 ET.tostring() —— 它会把命名空间前缀重写为 ns0:，
    导致依赖 'w:rFonts'、'w:color' 等字面量的正则全部匹配失败
    （曾因此在版头字体检测中误报"未检出方正小标宋简体"）。
    """
    parts = []

    def _walk(el):
        tag = el.tag
        if tag.startswith('{'):
            uri, local = tag[1:].split('}', 1)
            name = ('w:' + local) if uri == _W_NS else local
        else:
            name = tag
        attrs = []
        for k, v in el.attrib.items():
            if k.startswith('{'):
                uri, local = k[1:].split('}', 1)
                aname = ('w:' + local) if uri == _W_NS else local
            else:
                aname = k
            attrs.append(f'{aname}="{v}"')
        attr_s = (' ' + ' '.join(attrs)) if attrs else ''
        children = list(el)
        if children:
            parts.append(f'<{name}{attr_s}>')
            for c in children:
                _walk(c)
            parts.append(f'</{name}>')
        else:
            text = el.text or ''
            parts.append(f'<{name}{attr_s}>{text}</{name}>')

    _walk(elem)
    return ''.join(parts)


def check_format(docx_path, quiet=False):
    """检查 DOCX 格式，返回 (issues, passed)"""
    issues = []
    passed = []
    notes = []  # 中性提示（不计入评分）

    if not os.path.exists(docx_path):
        msg = f"文件不存在: {docx_path}"
        issues.append(msg)
        return issues, passed, notes

    if not os.path.isfile(docx_path):
        issues.append(f"不是有效文件: {docx_path}")
        return issues, passed, notes

    # ---- 打开并解析 DOCX ----
    try:
        with zipfile.ZipFile(docx_path) as z:
            try:
                raw_xml = z.read('word/document.xml')
            except KeyError:
                issues.append("❌ 无效 DOCX：缺少 word/document.xml（可能不是 Word 文档）")
                return issues, passed, notes
            # BOM 容错：utf-8-sig 自动剥离 UTF-8 BOM
            doc_xml = raw_xml.decode('utf-8-sig', errors='replace')
    except zipfile.BadZipFile:
        issues.append(f"❌ 无法打开文件（不是有效的 zip/DOCX）: {os.path.basename(docx_path)}")
        return issues, passed, notes
    except Exception as e:
        issues.append(f"❌ 读取文件失败: {e}")
        return issues, passed, notes

    try:
        root = ET.fromstring(doc_xml)
    except ET.ParseError as e:
        issues.append(f"❌ XML 解析失败（文档可能损坏）: {e}")
        return issues, passed, notes

    # ---- 1. 页边距 ----
    margins = root.findall('.//' + W + 'sectPr/' + W + 'pgMar')
    if margins:
        mg = margins[0]
        margin_checked = 0
        for attr, expected_cm in [
            ('top', EXPECTED_PARAMS['margin_top_cm']),
            ('bottom', EXPECTED_PARAMS['margin_bottom_cm']),
            ('left', EXPECTED_PARAMS['margin_left_cm']),
            ('right', EXPECTED_PARAMS['margin_right_cm']),
        ]:
            raw = mg.get(W + attr)
            if raw is None:
                issues.append(f"⚠️ 页边距 {attr}: 未显式设置")
                continue
            try:
                val = int(raw)
            except (TypeError, ValueError):
                issues.append(f"⚠️ 页边距 {attr}: 无法解析值 '{raw}'")
                continue
            margin_checked += 1
            expected_twips = cm_to_twips(expected_cm)
            if val == 0:
                issues.append(f"⚠️ 页边距 {attr}: 设置为 0（可能未生效）")
            elif abs(val - expected_twips) > 114:  # 允许约2mm误差 (2mm≈114twips)
                issues.append(f"❌ 页边距 {attr}: 当前 {val/567:.1f}cm, 应为 {expected_cm}cm")
            else:
                passed.append(f"✅ 页边距 {attr}: {expected_cm}cm ✓")
        if margin_checked < 4:
            notes.append(f"ℹ️ 页边距: 仅 {margin_checked}/4 项可检查（其余未显式设置）")
    else:
        notes.append("ℹ️ 未找到页边距设置（sectPr/pgMar）")

    # ---- 2. 标题检查 ----
    title_para = None
    for p in root.findall('.//' + W + 'p'):
        ppr = p.find(W + 'pPr')
        if ppr is None:
            continue
        pstyle = ppr.find(W + 'pStyle')
        if pstyle is not None:
            style_val = pstyle.get(W + 'val', '')
            if style_val and style_val.lower() in ('title', '1', 'heading1', '标题'):
                title_para = p
                break
    if title_para is not None:
        title_font_elem = title_para.find('.//' + W + 'rFonts')
        if title_font_elem is not None:
            asc = title_font_elem.get(W + 'eastAsia', '') or title_font_elem.get(W + 'ascii', '')
            if font_matches(asc, EXPECTED_PARAMS['title_fonts']):
                passed.append(f"✅ 标题字体: {asc} ✓")
            else:
                issues.append(f"❌ 标题字体: {asc}, 应为方正小标宋简体或其变体")
        else:
            notes.append("ℹ️ 标题段落未设置字体")
    else:
        notes.append("ℹ️ 未检测到标题样式段落（非标题模板文档？）")

    # ---- 3. 首行缩进 ----
    indent_elements = root.findall('.//' + W + 'pPr/' + W + 'ind')
    correct_indent = 0
    wrong_indent = 0
    for indent in indent_elements:
        raw = indent.get(W + 'firstLine')
        if raw is None:
            continue
        try:
            first_line = int(raw)
        except ValueError:
            continue
        if first_line > 0:
            lo, hi = EXPECTED_PARAMS['indent_range']
            if lo <= first_line <= hi:
                correct_indent += 1
            else:
                wrong_indent += 1
    if correct_indent > 0:
        passed.append(f"✅ 首行缩进: {correct_indent} 段正确 ✓")
    if wrong_indent > 0:
        issues.append(f"❌ 首行缩进: {wrong_indent} 段缩进值异常")
    if correct_indent == 0 and wrong_indent == 0:
        notes.append("ℹ️ 未检测到首行缩进设置")

    # ---- 4. 行距（区分 auto/exact 规则；exact 内再按槽位分流） ----
    # GB/T 9704-2012：正文固定行距 28 磅；各级标题固定行距 30 磅。
    # 旧口径把所有 exact 段落一律按 28±1 磅判定，导致完全合规公文的
    # 标题（30 磅）被误报为问题，格式规范度被无端压低 —— 本版修复。
    spacing_elements = root.findall('.//' + W + 'pPr/' + W + 'spacing')
    body_expected = EXPECTED_PARAMS['line_spacing_twips']        # 560 = 28 磅
    title_expected = EXPECTED_PARAMS['title_line_spacing_twips']  # 600 = 30 磅
    exact_ok = 0      # 正文槽位命中（28 磅）
    exact_bad = 0     # 正文槽位偏离
    title_ok = 0      # 标题槽位命中（30 磅）
    title_bad = 0     # 标题槽位偏离
    auto_seen = 0
    tol = 20          # ±1 磅容差
    for spacing in spacing_elements:
        line_rule = spacing.get(W + 'lineRule', '')
        raw_line = spacing.get(W + 'line')
        if raw_line is None:
            continue
        try:
            line = int(raw_line)
        except ValueError:
            continue
        if line_rule == 'exact':
            # 以行距值就近归类槽位：28 磅与 30 磅相距 40 twips，取中值 580 为界
            if abs(line - title_expected) < abs(line - body_expected):
                if abs(line - title_expected) <= tol:
                    title_ok += 1
                else:
                    title_bad += 1
            else:
                if abs(line - body_expected) <= tol:
                    exact_ok += 1
                else:
                    exact_bad += 1
        else:
            # auto 或 atLeast 行距不强制固定值，记录但不算错
            auto_seen += 1

    if exact_ok > 0:
        passed.append(f"✅ 行距（正文）: {exact_ok} 段固定值28磅 ✓")
    if title_ok > 0:
        passed.append(f"✅ 行距（标题）: {title_ok} 段固定值30磅 ✓")
    if exact_bad > 0:
        issues.append(f"❌ 行距（正文）: {exact_bad} 段偏离28磅（fixed 值异常）")
    if title_bad > 0:
        issues.append(f"❌ 行距（标题）: {title_bad} 段偏离30磅（fixed 值异常）")
    if exact_ok == 0 and title_ok == 0 and exact_bad == 0 and title_bad == 0 and auto_seen > 0:
        notes.append(f"ℹ️ 行距: 使用自动行距（{auto_seen} 段），未强制固定值28/30磅")

    # ---- 5. 层级序号 ----
    document_text = ''.join(t.text or '' for t in root.findall('.//' + W + 't'))
    cn_numbering = re.findall(r'[一二三四五六七八九十]+、', document_text)
    if cn_numbering:
        passed.append(f"✅ 一级标题序号: \"一、\" 格式正确 ✓")
    # 检测用点号代替顿号的错误写法（如 "1. 标题" 或 "一. 标题"）
    wrong_dot = re.findall(r'[一二三四五六七八九十]+\.\s', document_text)
    if wrong_dot:
        issues.append(f"❌ 一级标题序号: 发现用点号代替顿号 ({wrong_dot[:3]})")

    # ---- 6. 年份括号 ----
    if re.search(r'\[\d{4}\]', document_text):
        issues.append("❌ 年份括号: 发现使用方括号[]，应使用六角括号〔〕")
    elif re.search(r'〔\d{4}〕', document_text):
        passed.append("✅ 年份括号: 〔〕六角括号正确 ✓")
    else:
        notes.append("ℹ️ 未检测到年份引用")

    # ---- 7. 数字字体（简化检查） ----
    if EXPECTED_PARAMS['number_font'] not in doc_xml and len(re.findall(r'\d{2,}', document_text)) > 5:
        issues.append("⚠️ 数字字体: 未设置 Times New Roman（建议设置）")

    # ---- 8. 页码检查（GB/T 9704-2012 第 7.4 条三项：字体 / 字号 / 对齐位） ----
    # 国标：页码用 4 号半角宋体阿拉伯数字，单页码居右空一字、双页码居左空一字。
    footer_xmls = []
    try:
        with zipfile.ZipFile(docx_path) as z:
            footer_files = sorted(f for f in z.namelist()
                                  if re.search(r'word/footer\d*\.xml$', f, re.I))
            for ff in footer_files:
                footer_xmls.append(z.read(ff).decode('utf-8-sig', errors='replace'))
    except Exception:
        pass

    if not footer_xmls:
        notes.append("ℹ️ 未检测到页脚（可能使用默认页码或未插入页码域）")
    else:
        has_page_field = any(re.search(r'\bPAGE\b', fx) or '页码' in fx for fx in footer_xmls)
        if not has_page_field:
            notes.append("ℹ️ 检测到页脚但未识别页码字段（PAGE 域）")
        else:
            page_ok = []
            page_bad = []

            # (1) 字体：4 号半角宋体
            font_hit = False
            for fx in footer_xmls:
                for m in re.finditer(r'<w:rFonts[^>]*>', fx):
                    tag = m.group(0)
                    for attr in ('w:eastAsia', 'w:ascii', 'w:hAnsi'):
                        mm = re.search(attr + r'="([^"]*)"', tag)
                        if mm and font_matches(mm.group(1), EXPECTED_PARAMS['page_fonts']):
                            font_hit = True
                            break
                    if font_hit:
                        break
                if font_hit:
                    break
            if font_hit:
                page_ok.append("宋体")
            else:
                page_bad.append("字体非宋体（国标要求 4 号半角宋体）")

            # (2) 字号：4 号 = 14pt，w:sz 为半磅值 → 28
            size_hit = False
            size_seen = False
            for fx in footer_xmls:
                for m in re.finditer(r'<w:sz w:val="(\d+)"\s*/>', fx):
                    size_seen = True
                    if int(m.group(1)) == EXPECTED_PARAMS['page_size_half_pt']:
                        size_hit = True
            if size_hit:
                page_ok.append("4号（14pt）")
            elif size_seen:
                page_bad.append("字号非 4 号（14pt）")
            else:
                page_bad.append("未显式设置字号（无法确认为 4 号）")

            # (3) 对齐位：单页码居右空一字、双页码居左空一字
            right_hit = any(re.search(r'<w:jc w:val="right"\s*/>', fx) for fx in footer_xmls)
            left_hit = any(re.search(r'<w:jc w:val="left"\s*/>', fx) for fx in footer_xmls)
            if right_hit or left_hit:
                page_ok.append("居右/居左对齐（单/双页码）")
            else:
                page_bad.append("对齐位未设置居右（单页码）或居左（双页码）")

            if page_ok:
                passed.append("✅ 页码: " + "、".join(page_ok) + " ✓")
            if page_bad:
                issues.append("❌ 页码: " + "；".join(page_bad))

    # ---- 9. 版头要素（红头文件专用，GB/T 9704-2012 第 7.2 条） ----
    # 仅在检测到红头特征时才逐项校验，普通报告不受影响。
    # 判据（**放宽以捕获"有错误的红头"**）：文首前 10 段内命中任一条即视为红头——
    #   a. 出现「XXX文件」发文机关标志
    #   b. 出现发文字号（含六角/方/圆括号任一形式，错误的也要抓）
    #   c. 出现「密级/份号/签发人/紧急程度」等版头专用词
    #   d. 文档前部存在红色要素
    head_zone_paras = root.findall('.//' + W + 'p')[:10]
    # 逐段取文本（保留段落边界，便于判断"某段是否为纯 6 位份号"）
    head_zone_lines = [
        ''.join(t.text or '' for t in p.findall('.//' + W + 't'))
        for p in head_zone_paras
    ]
    head_zone_text = '\n'.join(head_zone_lines)

    # 文档前部是否存在红色要素（发文机关标志 / 分隔线）
    head_zone_xml = ''.join(_serialize_element(p) for p in head_zone_paras)
    has_red = bool(re.search(r'w:color="FF0000"', head_zone_xml, re.I)
                   or re.search(r'w:fill="FF0000"', head_zone_xml, re.I))

    is_redhead = bool(
        re.search(r'[\u4e00-\u9fa5]{2,}\s*文件\s*$', head_zone_text, re.M)
        or re.search(r'[\u4e00-\u9fa5]{1,}\s*[\[\(（〔]\s*\d{4}\s*[\]\)）〕]\s*\d+\s*号', head_zone_text)
        or re.search(r'(签发人|密级|紧急程度|特急|加急|绝密|机密|秘密)', head_zone_text)
        or has_red
    )

    if is_redhead:
        head_ok = []
        head_bad = []

        # (1) 发文字号括号类型：「机关代字〔年份〕序号」——含错误括号也要能捕获
        num_match = re.search(
            r'[\u4e00-\u9fa5]{1,}\s*([\[\(（〔])\s*(\d{4})\s*([\]\)）〕])\s*\d+\s*号',
            head_zone_text)
        if num_match:
            open_b, close_b = num_match.group(1), num_match.group(3)
            if open_b != '〔' or close_b != '〕':
                head_bad.append(f"发文字号括号用了「{open_b}{close_b}」，国标要求六角括号「〔〕」")
            else:
                head_ok.append("发文字号括号〔〕")
        elif re.search(r'〔\d{4}〕', head_zone_text):
            head_ok.append("发文字号括号〔〕")
        else:
            head_bad.append("未识别到发文字号（格式应为「机关代字〔年份〕序号号」）")

        # (2) 密级与保密期限配套
        secret_m = re.search(r'(绝密|机密|秘密)\s*(★\s*\d+\s*年)?', head_zone_text)
        if secret_m:
            if secret_m.group(2):
                head_ok.append("密级与保密期限同行")
            else:
                head_ok.append("密级标注")
            # 涉密（真密级）公文应有份号：任一行为纯 3-6 位数字即认为标了份号
            has_fenhao = any(re.fullmatch(r'\s*\d{3,6}\s*', ln) for ln in head_zone_lines)
            if not has_fenhao:
                head_bad.append("标注了密级但未发现份号（涉密公文应标份号）")
        # 无论如何，密级写"公开"都是错的
        if re.search(r'密级\s*[:：]\s*公开', head_zone_text):
            head_bad.append("密级写成了「公开」，无密级应整行不出现")

        # (3) 签发人：仅上行文（请示/报告）应出现；下行文不应出现
        has_sign = bool(re.search(r'签发人', head_zone_text))
        if has_sign:
            # 抓标题：文首 30 段内的「关于……的X」结构
            title_zone = '\n'.join(
                ''.join(t.text or '' for t in p.findall('.//' + W + 't'))
                for p in root.findall('.//' + W + 'p')[:30]
            )
            downward_kw = r'(通知|通报|决定|意见|批复|命令|公告|通告|公示)'
            upward_kw = r'(请示|报告)'
            if re.search(downward_kw, title_zone) and not re.search(upward_kw, title_zone):
                head_bad.append("下行文出现「签发人」，国标规定仅上行文标注")
            else:
                head_ok.append("签发人（上行文）")

        # (4) 红色要素：发文机关标志与分隔线均应为红
        if has_red:
            head_ok.append("红色要素（分隔线/机关标志）")
        else:
            head_bad.append("未发现红色要素（发文机关标志与分隔线均应为红色）")

        # (5) 发文机关标志字体：方正小标宋简体（或可接受的替代）
        head_font_hit = False
        for p_xml in (_serialize_element(p) for p in head_zone_paras):
            for m in re.finditer(r'<w:rFonts[^>]*>', p_xml):
                tag = m.group(0)
                for attr in ('w:eastAsia', 'w:ascii', 'w:hAnsi'):
                    mm = re.search(attr + r'="([^"]*)"', tag)
                    if mm and font_matches(mm.group(1), EXPECTED_PARAMS['title_fonts']):
                        head_font_hit = True
                        break
                if head_font_hit:
                    break
            if head_font_hit:
                break
        if head_font_hit:
            head_ok.append("发文机关标志字体（小标宋体系）")
        else:
            head_bad.append("未检出方正小标宋简体（发文机关标志与标题应为小标宋体系）")

        if head_ok:
            passed.append("✅ 版头要素: " + "、".join(head_ok) + " ✓")
        for b in head_bad:
            issues.append(f"❌ 版头要素: {b}")
    else:
        notes.append("ℹ️ 未检测到红头特征（版头要素校验已跳过，普通报告无需版头）")

    return issues, passed, notes


def render_report(docx_path, issues, passed, notes):
    """文本报告输出"""
    print(f"\n{'=' * 60}")
    print(f"  公文格式检查报告: {os.path.basename(docx_path)}")
    print(f"{'=' * 60}\n")

    print(f"## 通过项 ({len(passed)})")
    for p in passed:
        print(f"  {p}")

    if notes:
        print(f"\n## 提示项 ({len(notes)})")
        for n in notes:
            print(f"  {n}")

    print(f"\n## 问题项 ({len(issues)})")
    if issues:
        for i in issues:
            print(f"  {i}")
    else:
        print("  🎉 未发现格式问题！")

    print(f"\n{'=' * 60}")
    total = len(passed) + len(issues)
    if total > 0:
        score = len(passed) / total * 100
        print(f"  格式规范度: {score:.0f}% ({len(passed)}/{total})")
        print(f"  提示项: {len(notes)}（不计分）")
        print("  判定口径: 正文固定行距 28 磅 / 标题固定行距 30 磅；")
        print("            页码为 4 号半角宋体，单页码居右空一字、双页码居左空一字。")
    print(f"{'=' * 60}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='gov-report-writing（公文写作）格式检查（GB/T 9704-2012）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='示例: python format_check.py 年度总结.docx\n'
               '      python format_check.py 年度总结.docx --json')
    parser.add_argument('docx', nargs='?', help='待检查的 DOCX 文件路径')
    parser.add_argument('--json', action='store_true', dest='json_out',
                        help='以 JSON 格式输出（便于程序化调用）')
    parser.add_argument('--quiet', action='store_true',
                        help='仅输出问题项（文本模式）')
    parser.add_argument('--version', action='version',
                        version=f'format_check.py 跨平台版 | Python {PY_VERSION} | {PLATFORM}')
    args = parser.parse_args(argv)

    if not args.docx:
        parser.print_help()
        return 2

    docx_path = resolve_path(args.docx)
    if docx_path is None:
        print("❌ 未提供文件路径")
        return 2

    issues, passed, notes = check_format(docx_path, quiet=args.quiet)

    if args.json_out:
        result = {
            'file': docx_path,
            'platform': PLATFORM,
            'python': PY_VERSION,
            'passed': passed,
            'notes': notes,
            'issues': issues,
            'score_percent': round(len(passed) / (len(passed) + len(issues)) * 100) if (len(passed) + len(issues)) > 0 else 0,
            'ok': len(issues) == 0,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.quiet:
        for i in issues:
            print(i)
        if not issues:
            print("✅ 未发现格式问题")
    else:
        render_report(docx_path, issues, passed, notes)

    return 0 if not issues else 1


if __name__ == '__main__':
    sys.exit(main())
