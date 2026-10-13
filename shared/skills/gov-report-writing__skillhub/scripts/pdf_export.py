#!/usr/bin/env python3
"""
gov-report-writing（公文写作）PDF 一键直出脚本

把已经排好国标版式的 .docx 转为 PDF，并在转完后**实测校验**字体嵌入状态与页数——
这两项是"PDF 换台电脑打开就跑版"的直接原因。

设计原则（与 Skill 整体一致）：
    1. **纯标准库**：本脚本只用 Python 标准库，不 pip 装任何东西。
       转换本身调用用户**本机已有**的 Word 或 LibreOffice，不联网、不上传。
    2. **不静默失败**：任何一步失败都给出「哪里出问题 → 为什么会这样 → 怎么做」三段说明。
    3. **不做降级糊弄**：不用 HTML 打印、不手搓 PDF，版式不对宁可不生成。

用法:
    python scripts/pdf_export.py 报告.docx
    python scripts/pdf_export.py 报告.docx --out 报告.pdf
    python scripts/pdf_export.py 报告.docx --method libreoffice   # 指定通道
    python scripts/pdf_export.py 报告.docx --json
    python scripts/pdf_export.py --check                       # 只探测可用通道

退出码:
    0 = 转换成功且未发现风险项
    1 = 转换成功但存在提示项（如字体未嵌入）
    2 = 转换失败（含通道不可用）

兼容性:
    - 平台: Windows / macOS / Linux
    - Python: 3.7+
    - 路径: 支持中文路径、路径含空格、~ 展开
"""
import os
import re
import sys
import json
import shutil
import hashlib
import platform
import argparse
import subprocess

# ============================================================
# 跨平台控制台编码兼容（与其他脚本一致）
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

PLATFORM = platform.system()

# 国标四字体在 PDF 中的常见字面名（用于字体嵌入风险提示）
GUOBIAO_FONT_HINTS = [
    ('方正小标宋 / 华文中宋', ['FZXiaoBiaoSong', '方正小标宋', 'STZhongsong', 'STZhongsong-Bold']),
    ('仿宋_GB2312', ['FangSong', 'FangSong_GB2312', '仿宋', 'SimFang']),
    ('楷体_GB2312', ['KaiTi', 'KaiTi_GB2312', '楷体', 'STKaiti']),
    ('黑体', ['SimHei', '黑体', 'STHeiti']),
]

# 已知禁止嵌入（OS/2 fsType=2）的字体特征 —— X-5 告警依据
NO_EMBED_HINTS = ['FZXiaoBiaoSong', '方正小标宋', 'STZhongsong']

CONVERT_TIMEOUT = 180  # 秒


# ============================================================
# 路径与工具
# ============================================================
def resolve_path(raw_path):
    """路径规范化：去引号、展开 ~、转绝对路径（支持中文路径）"""
    if not raw_path:
        return None
    p = raw_path.strip()
    if len(p) >= 2 and p[0] in ('"', "'") and p[-1] == p[0]:
        p = p[1:-1]
    p = os.path.expanduser(p)
    return os.path.abspath(p)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ============================================================
# 通道探测
# ============================================================
def detect_word():
    """Windows 上是否装有 Microsoft Word（查注册表 ProgID，不启动 Word）。"""
    if PLATFORM != 'Windows':
        return None
    try:
        import winreg
        for root in (winreg.HKEY_CLASSES_ROOT,):
            try:
                key = winreg.OpenKey(root, r'Word.Application\CLSID')
                winreg.CloseKey(key)
                return 'word'
            except OSError:
                continue
    except ImportError:
        return None
    return None


def detect_libreoffice():
    """查找 LibreOffice 可执行文件（跨平台）。"""
    for name in ('soffice', 'soffice.exe', 'libreoffice'):
        found = shutil.which(name)
        if found:
            return found
    candidates = []
    if PLATFORM == 'Windows':
        candidates = [
            r'C:\Program Files\LibreOffice\program\soffice.exe',
            r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
        ]
    elif PLATFORM == 'Darwin':
        candidates = ['/Applications/LibreOffice.app/Contents/MacOS/soffice']
    else:
        candidates = ['/usr/bin/soffice', '/usr/local/bin/soffice',
                      '/snap/bin/libreoffice']
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def detect_wps():
    """WPS 仅作提示，不自动驱动（其命令行接口不稳定）。"""
    if PLATFORM != 'Windows':
        return None
    for p in (r'C:\Program Files\WPS Office\ksolaunch.exe',
              r'C:\Program Files (x86)\WPS Office\ksolaunch.exe'):
        if os.path.isfile(p):
            return p
    return None


def detect_channels():
    """返回可用通道清单，按优先级排序。"""
    channels = []
    w = detect_word()
    if w:
        channels.append(('word', 'Microsoft Word（COM 调用）'))
    lo = detect_libreoffice()
    if lo:
        channels.append(('libreoffice', 'LibreOffice：%s' % lo))
    return channels


# ============================================================
# 转换通道实现
# ============================================================
# Word COM：路径通过环境变量传入，避免引号/中文在命令串中被破坏
_PS_WORD_SCRIPT = (
    "$ErrorActionPreference='Stop';"
    "$w=New-Object -ComObject Word.Application;"
    "$w.Visible=$false;$w.DisplayAlerts=0;"
    "try{"
    "$d=$w.Documents.Open($env:GW_DOCX,$false,$true);"
    "try{$d.ExportAsFixedFormat($env:GW_PDF,17)}"
    "catch{$d.SaveAs([ref]$env:GW_PDF,[ref]17)};"
    "$d.Close([ref]0)"
    "}finally{"
    "$w.Quit();"
    "try{[System.Runtime.InteropServices.Marshal]::ReleaseComObject($w)|Out-Null}catch{}"
    "}"
)


def convert_with_word(docx, pdf_out):
    """用 Microsoft Word 转 PDF。返回 (成功, 日志)。"""
    env = dict(os.environ)
    env['GW_DOCX'] = docx
    env['GW_PDF'] = pdf_out
    cmd = ['powershell', '-NoProfile', '-NonInteractive',
           '-ExecutionPolicy', 'Bypass', '-Command', _PS_WORD_SCRIPT]
    try:
        proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              timeout=CONVERT_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, '调用 Word 超时（>%d 秒）' % CONVERT_TIMEOUT
    except OSError as exc:
        return False, '无法启动 powershell：%s' % exc
    log = (proc.stdout or b'').decode('utf-8', 'replace').strip()
    if os.path.isfile(pdf_out) and os.path.getsize(pdf_out) > 0:
        return True, log
    return False, log or ('Word 进程返回码 %d，未产出 PDF' % proc.returncode)


def convert_with_libreoffice(soffice, docx, pdf_out):
    """用 LibreOffice 无头模式转 PDF。返回 (成功, 日志)。"""
    out_dir = os.path.dirname(pdf_out) or '.'
    base = os.path.splitext(os.path.basename(docx))[0]
    produced = os.path.join(out_dir, base + '.pdf')
    if os.path.abspath(produced) != os.path.abspath(pdf_out):
        # 目标名与源同名时不冲突；不同名时先转出再改名
        pass
    cmd = [soffice, '--headless', '--norestore', '--convert-to', 'pdf',
           '--outdir', out_dir, docx]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              timeout=CONVERT_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, '调用 LibreOffice 超时（>%d 秒）' % CONVERT_TIMEOUT
    except OSError as exc:
        return False, '无法启动 LibreOffice：%s' % exc
    log = (proc.stdout or b'').decode('utf-8', 'replace').strip()

    if not os.path.isfile(produced):
        return False, log or 'LibreOffice 未产出文件'

    if os.path.abspath(produced) != os.path.abspath(pdf_out):
        try:
            if os.path.exists(pdf_out):
                os.remove(pdf_out)
            shutil.move(produced, pdf_out)
        except Exception as exc:
            return False, '重命名输出文件失败：%s' % exc
    return True, log


# ============================================================
# PDF 实测校验（纯标准库，解析 PDF 内部对象）
# ============================================================
def _strip_subset_prefix(name_bytes):
    """去掉 PDF 子集前缀（形如 ABCDEE+），返回可读字体名。"""
    raw = re.sub(rb'^[A-Z]{6}\+', b'', name_bytes)
    return raw.decode('latin-1', 'replace')


def _font_name_in(body, key):
    """从对象体中取 /BaseFont 或 /FontName 的值（去子集前缀）。"""
    m = re.search(key + rb'\s*/([^\s/\[\]<>()]+)', body)
    return _strip_subset_prefix(m.group(1)) if m else None


def inspect_pdf(path):
    """读取 PDF，返回页数估计、字体清单与嵌入状态。

    关键结构（实测 Microsoft Word / LibreOffice 产物）：
        字体字典对象：<</Type/Font/Subtype/TrueType/BaseFont/BCDFEE+TimesNewRomanPSMT
                        ... /FontDescriptor 16 0 R >>
        描述符对象：  <</Type/FontDescriptor/FontName/BCDFEE+Calibri ... /FontFile2 70 0 R >>
    即 **/FontFile* 只出现在描述符里**，字体字典只持有对描述符的间接引用。
    因此必须按对象号把两者关联，不能只看字体字典。
    """
    with open(path, 'rb') as fh:
        data = fh.read()

    info = {
        'bytes': len(data),
        'pages': None,
        'pages_estimated': False,
        'fonts': [],          # [{'name':..., 'embedded': True/False/None}]
        'embedded_any': None,
    }

    # --- 页数：优先读页树 /Count，退化为数 /Type /Page 出现次数 ---
    m = re.search(rb'/Type\s*/Pages\b[^>]*?/Count\s+(\d+)', data, re.S)
    if not m:
        m = re.search(rb'/Count\s+(\d+)', data)
    if m:
        try:
            info['pages'] = int(m.group(1))
        except ValueError:
            pass
    if info['pages'] is None:
        n = len(re.findall(rb'/Type\s*/Page\b(?!s)', data))
        if n:
            info['pages'] = n
            info['pages_estimated'] = True

    # --- 收集全部 PDF 对象（未压缩的明文对象）---
    objs = {}
    for m in re.finditer(rb'(\d+)\s+\d+\s+obj(.*?)endobj', data, re.S):
        objs[int(m.group(1))] = m.group(2)

    # --- 第一遍：描述符对象 → 该字体是否嵌入 ---
    desc_embedded = {}      # 对象号 -> bool
    desc_name = {}          # 对象号 -> 字体名
    for num, body in objs.items():
        if b'/FontName' not in body:
            continue
        nm = _font_name_in(body, rb'/FontName')
        if nm is None:
            continue
        has_file = re.search(rb'/FontFile[23]?\s+\d+\s+\d+\s+R', body) is not None
        desc_embedded[num] = has_file
        desc_name[num] = nm

    # --- 第二遍：字体字典 → 按 /FontDescriptor 引用关联嵌入状态 ---
    fonts = {}
    for num, body in objs.items():
        if b'/BaseFont' not in body:
            continue
        nm = _font_name_in(body, rb'/BaseFont')
        if nm is None:
            continue
        ref = re.search(rb'/FontDescriptor\s+(\d+)\s+\d+\s+R', body)
        if ref:
            embedded = desc_embedded.get(int(ref.group(1)))  # 可能为 None（未知）
        else:
            # 无描述符：Type3 字体或 PDF 基础 14 字体，不需要嵌入
            embedded = True
        if nm in fonts:
            # 同名多字形：任一嵌入即视为已嵌入
            if embedded is True or fonts[nm] is True:
                fonts[nm] = True
            elif fonts[nm] is None:
                fonts[nm] = embedded
        else:
            fonts[nm] = embedded

    # --- 兜底：对象被压缩进对象流（看不到明文对象）时，退回全局关键字探测 ---
    if not fonts:
        names = set()
        for m in re.finditer(rb'/BaseFont\s*/([^\s/\[\]<>()]+)', data):
            names.add(_strip_subset_prefix(m.group(1)))
        n_embed = len(re.findall(rb'/FontFile[23]?\b', data))
        for n in sorted(names):
            fonts[n] = None            # 无法逐字体判定，整体给结论
        info['embedded_any'] = bool(names) and n_embed > 0
        if names:
            info['estimate_only'] = True

    info['fonts'] = [{'name': k, 'embedded': v}
                     for k, v in sorted(fonts.items())]
    if info.get('embedded_any') is None and fonts:
        info['embedded_any'] = any(v is True for v in fonts.values())
    return info


def build_font_warnings(info):
    """根据字体嵌入情况生成风险提示。"""
    warnings = []
    for f in info['fonts']:
        name = f['name']
        is_gb = None
        for label, hints in GUOBIAO_FONT_HINTS:
            if any(h.lower() in name.lower() for h in hints):
                is_gb = label
                break
        if is_gb is None:
            continue
        if f['embedded'] is False:
            risky = any(h.lower() in name.lower() for h in NO_EMBED_HINTS)
            warnings.append({
                'font': name,
                'slot': is_gb,
                'level': 'high' if risky else 'medium',
                'reason': ('该字体厂商授权禁止嵌入（fsType=2），PDF 中只能以替代字形或位图保存'
                           if risky else '该字体未嵌入 PDF，换台电脑打开会被替换'),
            })
    return warnings


# ============================================================
# 报告输出
# ============================================================
def print_howto(channels, wps):
    """通道全部不可用时的三段式说明。"""
    print()
    print('为什么：docx 转 PDF 需要一个「渲染引擎」。本脚本不内置引擎'
          '（内置会把体积撑到几十 MB，且版式与 Word 不一致），')
    print('        所以它调用你电脑上已经装好的 Word 或 LibreOffice。'
          '当前这台机器上两者都没检测到。')
    print()
    print('怎么做（任选一种，装好后再跑一次本命令即可）：')
    print('  1. 装了 Word / WPS 的话——直接手动导出最省事：')
    print('     打开 docx → 「文件」→「另存为」→ 格式选 PDF → 保存。')
    print('     注意：导出时点「选项」，勾选「PDF/A 兼容」可提高换机后的稳定性。')
    if wps:
        print('     本机已装 WPS（%s），走这条最快。' % wps)
    print('  2. 想要脚本自动化——装 LibreOffice（免费，约 300MB）：')
    print('     官网 https://www.libreoffice.org/download/ ，装完无需配置，重跑本命令。')
    print('     Linux: sudo apt install libreoffice   /   sudo dnf install libreoffice')
    print('     macOS: brew install --cask libreoffice')
    print('  3. 只要看版式效果、不要求正式交付——'
          '让 Skill 输出 HTML 预览即可。')


def render(path, pdf_path, info, method_label, warnings, elapsed):
    """打印人类可读报告。"""
    print('=' * 62)
    print('公文 PDF 直出结果')
    print('=' * 62)
    print('源文件:   %s' % path)
    print('PDF 输出: %s' % pdf_path)
    print('转换通道: %s' % method_label)
    print('耗时:     %.1f 秒' % elapsed)
    print('-' * 62)
    print('文件大小: %.1f KB' % (info['bytes'] / 1024.0))
    if info['pages'] is not None:
        tag = '（估算）' if info['pages_estimated'] else ''
        print('页数:     %d 页%s' % (info['pages'], tag))
    print('SHA256:   %s' % _sha256(pdf_path)[:32] + '...')

    print()
    print('字体嵌入检查:')
    if not info['fonts']:
        print('  [--] 未解析到字体对象（文档未使用自定义字体，或对象被压缩），无法逐字体判定')
        print('       建议：用阅读器打开 PDF →「文件属性 → 字体」人工确认')
    else:
        for f in info['fonts']:
            if f['embedded'] is True:
                mark, note = '[OK]', '已嵌入'
            elif f['embedded'] is False:
                mark, note = '[!!]', '未嵌入 ← 换机打开会被替换'
            else:
                mark, note = '[--]', '未能定位描述符，无法判定'
            print('  %s %-38s %s' % (mark, f['name'], note))
        if info.get('estimate_only'):
            print('  注：本 PDF 的对象流被压缩，逐字体判定不可靠，以上仅为清单。')

    if warnings:
        print()
        print('风险提示:')
        for w in warnings:
            lv = '高危' if w['level'] == 'high' else '注意'
            print('  [%s] %s（%s 槽位）' % (lv, w['font'], w['slot']))
            print('         %s' % w['reason'])
        print()
        print('  会影响什么：PDF 发到别的电脑 / 手机 / 微信里打开时，标题可能不是方正小标宋，')
        print('              看着不像正式公文；本机打开是正常的。')
        print('  怎么办：① 正式发文场景，直接用 Word/WPS「另存为 PDF」并在选项里勾选')
        print('            「符合 PDF/A」——部分阅读器会以位图方式保留字形外观；')
        print('          ② 若单位有内网 OA / 公文字体包，装齐四个国标字体后重新导出；')
        print('          ③ 只在本机 / 单位统一装有字体的环境内流转，风险可忽略。')

    print('-' * 62)
    if warnings:
        print('结果：转换成功，但有 %d 项字体提示（不影响本机查看）。' % len(warnings))
    else:
        print('结果：转换成功，未发现字体嵌入风险。')


# ============================================================
# 主流程
# ============================================================
def main(argv=None):
    parser = argparse.ArgumentParser(
        description='gov-report-writing PDF 一键直出（docx → PDF + 字体嵌入实测校验）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='退出码: 0=成功, 1=成功但有提示, 2=失败'
    )
    parser.add_argument('source', nargs='?', help='待转换的 .docx 文件路径')
    parser.add_argument('--out', default=None, help='PDF 输出路径（默认与源文件同目录同名）')
    parser.add_argument('--method', default='auto',
                        choices=['auto', 'word', 'libreoffice'],
                        help='指定转换通道，默认自动选择')
    parser.add_argument('--check', action='store_true',
                        help='只探测本机可用通道，不做转换')
    parser.add_argument('--json', dest='as_json', action='store_true',
                        help='以 JSON 格式输出结果')
    parser.add_argument('--quiet', action='store_true', help='仅输出结论')
    args = parser.parse_args(argv)

    channels = detect_channels()
    wps = detect_wps()

    if args.check:
        if args.as_json:
            print(json.dumps({
                'platform': PLATFORM,
                'channels': [{'key': k, 'label': v} for k, v in channels],
                'wps': wps,
                'available': bool(channels),
            }, ensure_ascii=False, indent=2))
        else:
            print('=' * 62)
            print('PDF 转换通道探测')
            print('=' * 62)
            print('平台: %s' % PLATFORM)
            if channels:
                for i, (k, v) in enumerate(channels, 1):
                    print('  [OK] %d. %s' % (i, v))
            else:
                print('  [!!] 未检测到可用的转换通道')
                if wps:
                    print('  [--] 检测到 WPS（%s），但不自动驱动——建议手动导出' % wps)
                print_howto(channels, wps)
            print('-' * 62)
        return 0 if channels else 2

    if not args.source:
        parser.error('缺少源文件参数（或使用 --check 仅探测通道）')

    src = resolve_path(args.source)
    if not src or not os.path.isfile(src):
        print('[FAIL] 源文件不存在：%s' % (src or args.source))
        print('       请检查路径是否正确；路径含空格时用引号包起来。')
        return 2
    if os.path.splitext(src)[1].lower() not in ('.docx', '.doc'):
        print('[FAIL] 源文件不是 Word 文档：%s' % os.path.basename(src))
        print('       本脚本只接受 .docx / .doc，先把内容存成 Word 再转。')
        return 2

    pdf_path = resolve_path(args.out) if args.out else \
        os.path.splitext(src)[0] + '.pdf'

    # 通道选择
    method = args.method
    if method == 'auto':
        if not channels:
            print('[FAIL] 本机没有可用的 PDF 转换通道（既没找到 Word，也没找到 LibreOffice）')
            print()
            print('哪里出问题：需要 Word 或 LibreOffice 把 docx 渲染成 PDF，两者都没检测到。')
            print_howto(channels, wps)
            return 2
        method = channels[0][0]
    else:
        avail = [k for k, _ in channels]
        if method not in avail:
            label = {'word': 'Microsoft Word', 'libreoffice': 'LibreOffice'}[method]
            print('[FAIL] 你指定的通道不可用：%s（未检测到）' % label)
            print('       可用的是：%s' % ('、'.join(avail) if avail else '无'))
            return 2

    method_label = {'word': 'Microsoft Word（COM）',
                    'libreoffice': 'LibreOffice（无头模式）'}[method]

    # 输出目录准备
    out_dir = os.path.dirname(pdf_path)
    if out_dir and not os.path.isdir(out_dir):
        try:
            os.makedirs(out_dir)
        except OSError as exc:
            print('[FAIL] 无法创建输出目录 %s：%s' % (out_dir, exc))
            return 2
    if os.path.isfile(pdf_path):
        try:
            os.remove(pdf_path)
        except OSError as exc:
            print('[FAIL] 目标 PDF 已存在且无法覆盖（可能被阅读器占用）：%s' % exc)
            print('       关掉正在打开的 PDF，或换 --out 指定别的文件名。')
            return 2

    import time
    t0 = time.time()
    if method == 'word':
        ok, log = convert_with_word(src, pdf_path)
    else:
        soffice = detect_libreoffice()
        ok, log = convert_with_libreoffice(soffice, src, pdf_path)
    elapsed = time.time() - t0

    if not ok or not os.path.isfile(pdf_path) or os.path.getsize(pdf_path) == 0:
        print('[FAIL] 转换失败')
        print()
        print('哪里出问题：%s 通道没能产出 PDF 文件。' % method_label)
        if log:
            print('底层信息：%s' % log[-600:])
        print()
        print('为什么会这样：常见三种原因——')
        print('  ① 源 docx 正被 Word/WPS 打开着（文件被占用，Word 会静默失败）；')
        print('  ② 源文件损坏或不是真正的 docx（比如把 .doc 改了扩展名）；')
        print('  ③ Word 首次运行未完成激活/初始化弹窗，COM 调用被挡住。')
        print()
        print('怎么做：')
        print('  1. 关掉 Word / WPS 里打开的这份文档，重跑本命令；')
        print('  2. 换通道再试一次：python scripts/pdf_export.py "%s" --method libreoffice' % args.source)
        print('  3. 还不行就手动导出：打开 docx →「文件」→「另存为」→ 选 PDF。')
        print('  4. 只是要看版式效果的话，让 Skill 输出 HTML 预览也能看。')
        return 2

    info = inspect_pdf(pdf_path)
    warnings = build_font_warnings(info)

    if args.as_json:
        print(json.dumps({
            'ok': True,
            'source': src,
            'pdf': pdf_path,
            'method': method,
            'elapsed_seconds': round(elapsed, 2),
            'inspect': info,
            'font_warnings': warnings,
        }, ensure_ascii=False, indent=2))
    elif args.quiet:
        print('%s | %d 页 | 字体提示 %d 项' % (
            pdf_path,
            info['pages'] if info['pages'] is not None else 0,
            len(warnings)))
        for w in warnings:
            print('  [%s] %s' % (w['level'], w['font']))
    else:
        render(src, pdf_path, info, method_label, warnings, elapsed)

    return 1 if warnings else 0


if __name__ == '__main__':
    sys.exit(main())
