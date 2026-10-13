#!/usr/bin/env python3
"""
gov-report-writing（公文写作）环境与文件完整性自检脚本

在开始写公文之前跑一次，确认 Skill 包完整、环境可用；出问题时会直接告诉你
缺哪个文件、该装什么，而不是等到生成到一半才报错。

用法:
    python scripts/preflight_check.py                 # 完整自检
    python scripts/preflight_check.py --json          # JSON 输出（便于程序化调用）
    python scripts/preflight_check.py --quiet         # 仅输出问题项
    python scripts/preflight_check.py --root <路径>   # 指定 Skill 根目录

检查项:
    1. Python 版本（要求 3.9+）
    2. SKILL.md 存在性与版本号
    3. README.md 存在性
    4. references/ 参考资料完整性（必需 13 个）
    5. scripts/ 脚本完整性（必需 4 个）
    6. 各文件非空且可读
    7. Python 脚本语法可编译
    8. 报告类型识别表条目数（防止模板挂接丢失）
    9. 国标字体四个槽位检测（标题/正文/楷体/黑体，缺失仅告警，E1 有降级路径）

兼容性:
    - 平台: Windows / macOS / Linux
    - Python: 3.7+（本脚本自身）
    - 路径: 支持中文路径、路径含空格、~ 展开
    - 依赖: 纯标准库，不依赖 python-docx

输出:
    自检报告；退出码 0=全部通过, 1=存在警告, 2=存在错误
"""
import os
import re
import sys
import json
import platform
import argparse
import py_compile
import tempfile

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
            pass


_setup_console()

PLATFORM = platform.system()
PY_VERSION = platform.python_version()

# ============================================================
# 期望的文件清单
# ============================================================
REQUIRED_REFERENCES = [
    'gb-t9704-format.md',
    'report-templates.md',
    'vocabulary-guide.md',
    'ai-traces.md',
    'policy-database.md',
    'policy-citation-guide.md',
    'polishing-guide.md',
    'case-examples.md',
    'expression-library.md',
    'capability-matrix.md',
    'quality-scoring.md',
    'troubleshooting.md',
    'redhead-workflow.md',
]

REQUIRED_SCRIPTS = [
    'format_check.py',
    'quality_score.py',
    'policy_cite.py',
    'pdf_export.py',
]

REQUIRED_ROOT = [
    'SKILL.md',
    'README.md',
]

MIN_PYTHON = (3, 9)
MIN_TEMPLATE_ROWS = 38  # 报告类型识别表最少条目数（v1.9.0：模板 34→38 后为 38）

# 状态标记
OK = '[OK]'
WARN = '[WARN]'
FAIL = '[FAIL]'


# ============================================================
# 检查项
# ============================================================
class CheckResult(object):
    """单项检查结果。"""

    def __init__(self, name, status, detail, fix=''):
        self.name = name
        self.status = status      # OK / WARN / FAIL
        self.detail = detail
        self.fix = fix            # 修复建议，可为空

    def to_dict(self):
        return {
            'name': self.name,
            'status': self.status,
            'detail': self.detail,
            'fix': self.fix,
        }

    @property
    def is_problem(self):
        return self.status in (WARN, FAIL)


def check_python_version():
    """检查 Python 版本是否满足要求。"""
    actual = sys.version_info[:2]
    if actual >= MIN_PYTHON:
        return CheckResult(
            'Python 版本', OK,
            '当前 %s（要求 %d.%d+）' % (PY_VERSION, MIN_PYTHON[0], MIN_PYTHON[1])
        )
    return CheckResult(
        'Python 版本', FAIL,
        '当前 %s，低于要求的 %d.%d' % (PY_VERSION, MIN_PYTHON[0], MIN_PYTHON[1]),
        '请升级 Python 到 %d.%d 或更高版本' % (MIN_PYTHON[0], MIN_PYTHON[1])
    )


def check_root_files(root):
    """检查根目录必需文件。"""
    results = []
    for filename in REQUIRED_ROOT:
        path = os.path.join(root, filename)
        if not os.path.isfile(path):
            results.append(CheckResult(
                filename, FAIL, '文件缺失：%s' % path,
                '请重新安装 Skill 或从备份恢复该文件'
            ))
            continue
        size = os.path.getsize(path)
        if size == 0:
            results.append(CheckResult(
                filename, FAIL, '文件为空：%s' % path,
                '请重新安装 Skill 或从备份恢复该文件'
            ))
            continue
        results.append(CheckResult(
            filename, OK, '存在，%d 字节' % size
        ))
    return results


def _readable(path):
    """判断文件是否存在、非空且可读。"""
    if not os.path.isfile(path):
        return False, '文件缺失'
    if os.path.getsize(path) == 0:
        return False, '文件为空'
    if not os.access(path, os.R_OK):
        return False, '无读取权限'
    return True, ''


def check_references(root):
    """检查 references 目录完整性。"""
    results = []
    ref_dir = os.path.join(root, 'references')

    if not os.path.isdir(ref_dir):
        results.append(CheckResult(
            'references/', FAIL, '目录缺失：%s' % ref_dir,
            '请重新安装 Skill 或从备份恢复 references 目录'
        ))
        return results

    for filename in REQUIRED_REFERENCES:
        path = os.path.join(ref_dir, filename)
        ok, reason = _readable(path)
        if not ok:
            results.append(CheckResult(
                'references/%s' % filename, FAIL, reason,
                '缺失时 Skill 会降级为内置规则继续生成（E2），但格式/措辞准确度下降，建议恢复'
            ))
            continue
        size = os.path.getsize(path)
        results.append(CheckResult(
            'references/%s' % filename, OK, '%d 字节' % size
        ))

    return results


def check_scripts(root):
    """检查 scripts 目录完整性，并验证 Python 脚本语法可编译。"""
    results = []
    scripts_dir = os.path.join(root, 'scripts')

    if not os.path.isdir(scripts_dir):
        results.append(CheckResult(
            'scripts/', FAIL, '目录缺失：%s' % scripts_dir,
            '请重新安装 Skill 或从备份恢复 scripts 目录'
        ))
        return results

    for filename in REQUIRED_SCRIPTS:
        path = os.path.join(scripts_dir, filename)
        ok, reason = _readable(path)
        if not ok:
            results.append(CheckResult(
                'scripts/%s' % filename, FAIL, reason,
                '脚本缺失时对应自动检查不可用，Skill 会降级为人工核查（E9）'
            ))
            continue

        # 语法可编译性检查（用临时目录存放 pyc，避免污染 scripts 目录）
        compiled_ok = True
        compile_err = ''
        try:
            tmp_dir = tempfile.mkdtemp(prefix='gw_preflight_')
            try:
                py_compile.compile(path, cfile=os.path.join(tmp_dir, 'x.pyc'),
                                   doraise=True)
            finally:
                try:
                    import shutil
                    shutil.rmtree(tmp_dir)
                except Exception:
                    pass
        except py_compile.PyCompileError as exc:
            compiled_ok = False
            compile_err = str(exc).strip().splitlines()[-1] if str(exc) else '语法错误'
        except Exception as exc:
            compiled_ok = False
            compile_err = str(exc)

        if not compiled_ok:
            results.append(CheckResult(
                'scripts/%s' % filename, FAIL,
                '语法错误：%s' % compile_err,
                '脚本损坏，请重新安装 Skill 或从备份恢复'
            ))
            continue

        size = os.path.getsize(path)
        results.append(CheckResult(
            'scripts/%s' % filename, OK, '%d 字节，语法正常' % size
        ))

    return results


def check_version_field(root):
    """从 SKILL.md 的 frontmatter 读取 version 字段。"""
    path = os.path.join(root, 'SKILL.md')
    ok, reason = _readable(path)
    if not ok:
        return CheckResult('SKILL.md version', FAIL, reason,
                           '无法读取版本号，请恢复 SKILL.md')

    try:
        with open(path, 'r', encoding='utf-8') as fh:
            head = fh.read(4096)  # frontmatter 一定在开头
    except Exception as exc:
        return CheckResult('SKILL.md version', FAIL,
                           '读取失败：%s' % exc,
                           '请确认文件为 UTF-8 编码')

    match = re.search(r'^version:\s*([0-9][0-9A-Za-z.\-+]*)', head, re.M)
    if not match:
        return CheckResult('SKILL.md version', WARN,
                           'frontmatter 未找到 version 字段',
                           '不影响使用，但建议补上版本号便于排查问题')
    return CheckResult('SKILL.md version', OK, 'version = %s' % match.group(1))


def check_template_table(root):
    """检查报告类型识别表的条目数，防止模板挂接丢失。"""
    path = os.path.join(root, 'SKILL.md')
    ok, reason = _readable(path)
    if not ok:
        return CheckResult('报告类型识别表', FAIL, reason,
                           '无法读取 SKILL.md')

    try:
        with open(path, 'r', encoding='utf-8') as fh:
            content = fh.read()
    except Exception as exc:
        return CheckResult('报告类型识别表', FAIL, '读取失败：%s' % exc,
                           '请确认文件为 UTF-8 编码')

    # 统计表格中形如 templates#N 的挂接数
    anchors = re.findall(r'templates#(\d+)', content)
    unique_anchors = sorted(set(int(a) for a in anchors))

    if len(unique_anchors) < MIN_TEMPLATE_ROWS:
        return CheckResult(
            '报告类型识别表', WARN,
            '识别到 %d 个模板挂接（templates#N），少于预期的 %d 个'
            % (len(unique_anchors), MIN_TEMPLATE_ROWS),
            '部分模板可能未挂接，生成时会降级为最接近类型处理'
        )
    return CheckResult(
        '报告类型识别表', OK,
        '识别到 %d 个模板挂接（#%d ~ #%d）'
        % (len(unique_anchors), unique_anchors[0], unique_anchors[-1])
    )


# ============================================================
# 字体检测
# ============================================================
# 字体槽位与可接受的名称片段（与 format_check.py 的宽容设计一致：
# 任一片段命中已安装字体名即视为该槽位可用；官方国标字体缺失时
# 允许变体替代，与 E1 降级路径衔接）
FONT_SLOTS = [
    ('标题字体（方正小标宋 / 华文中宋）', '方正小标宋简体',
     ['方正小标宋', 'fzxb', 'stzhongsong', '华文中宋']),
    ('正文字体（仿宋）', '仿宋_GB2312',
     ['仿宋', 'fangsong', 'simfang']),
    ('二级标题（楷体）', '楷体_GB2312',
     ['楷体', 'kaiti', 'simkai', 'stkaiti']),
    ('一级标题（黑体）', '黑体',
     ['黑体', 'simhei']),
]

# 目录遍历保护上限（字体目录通常数百文件，超限视为异常环境）
_FONT_SCAN_LIMIT = 5000


def _collect_installed_fonts():
    """收集系统已安装字体名称集合（注册表显示名 + 字体文件名，统一小写）。

    Windows: 优先读注册表 Fonts 键（winreg 为标准库，值名即字体显示名，
             比文件名匹配更准确），失败时退化为纯目录扫描。
    macOS:   /System/Library/Fonts、/Library/Fonts、~/Library/Fonts
    Linux:   /usr/share/fonts、/usr/local/share/fonts、~/.fonts、~/.local/share/fonts
    """
    names = set()
    home = os.path.expanduser('~')

    if PLATFORM == 'Windows':
        try:
            import winreg
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    key = winreg.OpenKey(
                        hive, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts')
                except OSError:
                    continue
                try:
                    idx = 0
                    while True:
                        try:
                            value_name, _, _ = winreg.EnumValue(key, idx)
                        except OSError:
                            break
                        idx += 1
                        if value_name:
                            names.add(value_name.lower())
                finally:
                    winreg.CloseKey(key)
        except ImportError:
            pass  # 非 Windows 或精简环境无 winreg，走目录扫描

    # 目录扫描（全平台兜底；Linux 字体在子目录中，需递归）
    scan_dirs = []
    if PLATFORM == 'Windows':
        windir = os.environ.get('WINDIR', r'C:\Windows')
        scan_dirs.append(os.path.join(windir, 'Fonts'))
        local = os.environ.get(
            'LOCALAPPDATA', os.path.join(home, 'AppData', 'Local'))
        scan_dirs.append(os.path.join(local, 'Microsoft', 'Windows', 'Fonts'))
    elif PLATFORM == 'Darwin':
        scan_dirs.extend([
            '/System/Library/Fonts',
            '/Library/Fonts',
            os.path.join(home, 'Library', 'Fonts'),
        ])
    else:
        scan_dirs.extend([
            '/usr/share/fonts',
            '/usr/local/share/fonts',
            os.path.join(home, '.fonts'),
            os.path.join(home, '.local', 'share', 'fonts'),
        ])

    scanned = 0
    for d in scan_dirs:
        if not os.path.isdir(d):
            continue
        for dirpath, _dirnames, filenames in os.walk(d):
            for fn in filenames:
                names.add(fn.lower())
                scanned += 1
                if scanned >= _FONT_SCAN_LIMIT:
                    break
            if scanned >= _FONT_SCAN_LIMIT:
                break
        if scanned >= _FONT_SCAN_LIMIT:
            break

    return names


def check_fonts():
    """检测四个国标字体槽位。缺失仅告警不阻断（E1 降级：正文宋体/标题黑体加粗）。"""
    installed = _collect_installed_fonts()

    if not installed:
        return CheckResult(
            '国标字体（4 槽位）', WARN,
            '未能读取系统字体列表（权限受限或目录异常），跳过字体检测',
            '如文档字体显示异常，请手动确认四个国标字体是否已安装'
        )

    missing = []
    for _slot_name, font_label, fragments in FONT_SLOTS:
        hit = any(any(frag in n for frag in fragments) for n in installed)
        if not hit:
            missing.append(font_label)

    if not missing:
        return CheckResult(
            '国标字体（4 槽位）', OK,
            '标题 / 正文 / 楷体 / 黑体 四槽位全部可用'
        )

    return CheckResult(
        '国标字体（4 槽位）', WARN,
        '缺失 %d 项：%s' % (len(missing), '、'.join(missing)),
        '获取与安装方法见 SKILL.md「字体获取与安装指引」；'
        '缺失期间文档仍可正常生成（E1 降级），但排版非国标观感'
    )


def check_optional_docx():
    """检查可选的 python-docx 依赖（缺失不影响核心功能）。"""
    try:
        import docx  # noqa: F401
        return CheckResult('python-docx（可选）', OK, '已安装，Word 生成可用')
    except ImportError:
        return CheckResult(
            'python-docx（可选）', WARN, '未安装',
            '不影响本脚本；生成 Word 时会降级为 Markdown 输出（见 SKILL.md E1/E2）'
        )


def run_all_checks(root):
    """执行全部检查，返回结果列表。"""
    results = []
    results.append(check_python_version())
    results.extend(check_root_files(root))
    results.append(check_version_field(root))
    results.extend(check_references(root))
    results.extend(check_scripts(root))
    results.append(check_template_table(root))
    results.append(check_fonts())
    results.append(check_optional_docx())
    return results


# ============================================================
# 输出
# ============================================================
def print_report(results, root, quiet=False):
    """打印自检报告。"""
    if not quiet:
        print('=' * 62)
        print('gov-report-writing 环境与文件完整性自检')
        print('=' * 62)
        print('Skill 根目录: %s' % root)
        print('运行平台:     %s / Python %s' % (PLATFORM, PY_VERSION))
        print('-' * 62)

    n_ok = n_warn = n_fail = 0
    for item in results:
        if item.status == OK:
            n_ok += 1
            if quiet:
                continue
            print('%s %-28s %s' % (OK, item.name, item.detail))
        elif item.status == WARN:
            n_warn += 1
            print('%s %-28s %s' % (WARN, item.name, item.detail))
            if item.fix and not quiet:
                print('     └─ 建议: %s' % item.fix)
        else:
            n_fail += 1
            print('%s %-28s %s' % (FAIL, item.name, item.detail))
            if item.fix:
                print('     └─ 修复: %s' % item.fix)

    if not quiet:
        print('-' * 62)
        print('汇总: %d 项通过 / %d 项警告 / %d 项错误' % (n_ok, n_warn, n_fail))

    if n_fail:
        print()
        print('存在错误项，Skill 可降级运行，但建议先修复后使用。')
        print('参考: SKILL.md「错误处理与降级机制」')
    elif n_warn:
        print()
        print('存在警告项，核心功能可用，部分能力受限。')
    elif not quiet:
        print()
        print('全部检查通过，可以直接开始写公文。')

    return n_ok, n_warn, n_fail


def main():
    parser = argparse.ArgumentParser(
        description='gov-report-writing 环境与文件完整性自检脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='退出码: 0=全部通过, 1=存在警告, 2=存在错误'
    )
    parser.add_argument('--json', action='store_true',
                        help='以 JSON 格式输出结果（便于程序化调用）')
    parser.add_argument('--quiet', action='store_true',
                        help='仅输出问题项（警告和错误）')
    parser.add_argument('--root', default=None,
                        help='指定 Skill 根目录（默认自动推断为脚本所在目录的上级目录）')
    args = parser.parse_args()

    # 推断 Skill 根目录：脚本位于 <root>/scripts/ 下
    if args.root:
        root = os.path.abspath(os.path.expanduser(args.root.strip('"').strip("'")))
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(script_dir)

    if not os.path.isdir(root):
        print('%s 指定的 Skill 根目录不存在: %s' % (FAIL, root))
        return 2

    results = run_all_checks(root)

    if args.json:
        n_ok = sum(1 for r in results if r.status == OK)
        n_warn = sum(1 for r in results if r.status == WARN)
        n_fail = sum(1 for r in results if r.status == FAIL)
        payload = {
            'root': root,
            'platform': PLATFORM,
            'python_version': PY_VERSION,
            'summary': {'ok': n_ok, 'warn': n_warn, 'fail': n_fail},
            'checks': [r.to_dict() for r in results],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        n_ok, n_warn, n_fail = print_report(results, root, quiet=args.quiet)

    if n_fail:
        return 2
    if n_warn:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
