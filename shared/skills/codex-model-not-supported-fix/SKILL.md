---
name: codex-model-not-supported-fix
description: ChatGPT/Codex 桌面版报「The 'xxx' model is not supported when using Codex with a ChatGPT account」、新会话秒报错、或一直「正在重新连接」时，排查本地记录的模型与账号实际可用模型不一致的问题并修复。触发词：model is not supported、模型不支持、Codex 报错、gpt-6-astra、gpt-6、正在重新连接 5/5。
agent_created: true
---

# Codex「模型不被支持」报错：排查与修复

## 适用场景

ChatGPT 桌面版（内置 Codex）发消息立即返回：

```json
{"detail":"The 'gpt-6-astra' model is not supported when using Codex with a ChatGPT account."}
```

可能伴随顶部「正在重新连接 5/5」。**这不是网络问题**，也不需要动代理 ——
是本地记录的「最近使用的模型」是一个账号不支持的灰度/实验模型。

## 排查步骤

### 1. 看报错里点名了哪个模型

错误 JSON 里的 `The 'xxx' model` 就是当前会话在用的模型 slug。

### 2. 对照账号实际可用的模型

```bash
# 账号可见/可用的模型列表（看 slug 和 visibility）
grep -o '"slug" *: *"[^"]*"' ~/.codex/models_cache.json | sort -u
# visibility 为 "hide" 的不可选；报错的模型大概率根本不在这个列表里
```

### 3. 找到本地哪里记了这个模型

```bash
grep -rl "报错的模型名" ~/.codex --include="*.json" --include="*.jsonl" --include="*.toml"
```

- `config.toml`：先排除（教程配中转站时会写死 model/provider，正常官方登录时不会有 model 字段）
- `.codex-global-state.json`：**最常见的窝点**，字段路径
  `electron-persisted-atom-state.composer-recent-model-configurations-v1[n].model`

### 4. 确认登录方式（排除中转站干扰）

```bash
python3 -c "import json; d=json.load(open('$HOME/.codex/auth.json')); print(list(d.keys()))"
# 有 tokens(id_token/access_token/refresh_token) = ChatGPT 账号 OAuth，正常
# 有 OPENAI_API_KEY 且是中转站的 key = 走了中转，另案处理
```

## 修复流程

1. **备份**：`cp ~/.codex/.codex-global-state.json ~/.codex/.codex-global-state.json.bak-<日期>`
2. **退出应用**（否则退出时会用内存状态覆盖你的修改）：
   `osascript quit` 在沙箱下会报「权限违例 (-10004)」，直接 `pkill -x ChatGPT`
3. **文本替换**（比 JSON 反序列化保真，改完务必 `json.load` 校验）：
   ```python
   raw = open(p).read().replace('坏模型名', '替代模型名')
   json.loads(raw)  # 校验
   open(p, 'w').write(raw)
   ```
4. 替代模型从 `models_cache.json` 里选 `visibility: "list"` 的（如 gpt-5.6-terra）
5. `open -a ChatGPT` 重启，验证新会话

## 注意事项

- 历史会话文件（`sessions/**/rollout-*.jsonl`）里也会有坏模型名，**不用改**，那是已死会话的记录。
- 修好后如果用户在模型选择器里又手动选了那个灰度模型，会复发 —— 提醒用户别选。
- 若 `models_cache.json` 本身过期（全是隐藏模型/为空），删除该缓存后重启 app 会重新拉取。
