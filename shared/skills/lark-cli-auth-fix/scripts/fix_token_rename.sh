#!/bin/bash
# 修复 lark-cli「授权成功但 user 身份仍 missing」的问题。
#
# 症状：扫码授权后 `lark-cli auth status` 仍显示 User identity: missing，
#       日志（~/.lark-cli/logs/auth-YYYY-MM-DD.log）里出现
#       keychain Set error: rename .../<name>.enc.<uuid>.tmp → <name>.enc: operation not permitted
#
# 原理：token 其实已经换到了（日志 path=/open-apis/authen/v2/oauth/token status=200），
#       只是 CLI 把凭证从临时文件 rename 成正式名时被系统拒绝（EPERM）。
#       CLI 随后会重试一次 → 必然返回 `device_code is invalid`，所以命令行报错具有误导性。
#       本脚本把遗留的 .enc.<uuid>.tmp 直接改名为 .enc，绕过 rename 失败。
#
# 用法：bash fix_token_rename.sh
# 之后用 `lark-cli auth status` 验证；若仍 missing，说明本次根本没换到 token，需重新扫码。

set -u
DIR="$HOME/Library/Application Support/lark-cli"

[ -d "$DIR" ] || { echo "❌ 目录不存在：$DIR"; exit 1; }
cd "$DIR" || exit 1

echo "== 现有 .tmp 文件 =="
ls -lt *.enc.*.tmp 2>/dev/null || { echo "（没有 .tmp 文件，说明没走到落盘这步，请重新扫码授权）"; exit 1; }
echo

# 排除 refresh-storage-probe 这类探测文件，只挑真正的凭证临时文件
SRC=$(ls -t *.enc.*.tmp 2>/dev/null | grep -v 'refresh-storage-probe' | head -1)
[ -n "$SRC" ] || { echo "❌ 没找到凭证 .tmp（只有 probe 文件），请重新扫码授权"; exit 1; }

# 目标名 = 去掉最后的 .<uuid>.tmp
DST="${SRC%.*}"      # 去掉 .tmp
DST="${DST%.*}"      # 去掉 <uuid>
DST="${DST}.enc"
echo "临时文件: $SRC"
echo "目标文件: $DST"

if [ -f "$DST" ]; then
  BAK="/tmp/lark_token_$(date +%Y%m%d_%H%M%S).bak"
  cp "$DST" "$BAK" && echo "旧凭证已备份: $BAK"
fi

mv -f "$SRC" "$DST" || { echo "❌ 改名失败"; exit 1; }
chmod 600 "$DST"
echo "✅ 已落位：$DST"
echo
echo "== 验证 =="
lark-cli auth status 2>&1 | python3 -c "
import sys, json
d = json.load(sys.stdin)
u = d['identities']['user']
print('identity:', d['identity'])
print('user status:', u['status'], '| token:', u.get('tokenStatus'))
print('user:', u.get('userName'))
print('scope 数:', len(u.get('scope', '').split()))
" 2>/dev/null || lark-cli auth status
