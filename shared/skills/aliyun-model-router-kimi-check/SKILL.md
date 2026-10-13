---
name: aliyun-model-router-kimi-check
description: 测试阿里云 Model Router（model-router.edu-aliyun.com）的 Kimi / DeepSeek 自定义模型 API Key 是否有效、额度是否还有余额，并把正确的模型名与端点写回 WorkBuddy 配置。触发词：kimi 还有余额吗、测试 kimi 模型、api key 有用吗、model router、额度包、余额不足、Insufficient balance、自定义模型报错。
agent_created: true
---

# 阿里云 Model Router：Kimi 模型可用性与余额检测

## 适用场景

涛哥给一个 API Key（或一张「会员详情／额度包」截图），问：
「这个 kimi 模型还有余额吗」「这个 api-key 有用吗」。

## 端点与配置事实（已验证 2026-09-11）

| 项 | 值 |
|---|---|
| Base URL | `https://model-router.edu-aliyun.com/v1/chat/completions` |
| 有效模型名 | `qwen/kimi-k2.6`、`qwen/kimi-k2.7-code`、`qwen/glm-5.1`、`qwen/glm-5.2`（GLM 两个模型均实测返回 `reasoning_content`，`supportsReasoning` 应设 `true`；2026-09-14 验证） |
| DeepSeek 系 | `qwen/deepseek-v4-flash`、`qwen/deepseek-v4-pro`（2026-09-24 实测可用，两者均返回 `reasoning_content`，`supportsReasoning` 设 `true`） |
| 模型列表接口 | **不存在**（`/v1/models` 返回 404 page not found） |
| Key 前缀 | `sk-`（40~48 位十六进制）；`ol-` 等其它前缀不是这里用的 key |

**最大的坑：厂商前缀必须是 `qwen/`，不是 `kimi/`。**
写 `kimi/kimi-k2.6` 会返回 ModelNotFoundException（看着像没权限，其实只是名字错），
写 `qwen/kimi-k2.6` 才会走到真正的额度校验。

## 检测步骤

### 1. 最小请求测余额

```bash
KEY="sk-xxxx"
curl -sS -m 60 https://model-router.edu-aliyun.com/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"qwen/kimi-k2.6","messages":[{"role":"user","content":"回复ok"}],"max_tokens":16}'
```

两个候选模型都跑一遍：`qwen/kimi-k2.6`、`qwen/kimi-k2.7-code`。

### 2. 读错误码（唯一可靠的判据）

| error_code | 含义 | 结论 |
|---|---|---|
| `B.Auth.InvalidApiKeyException` | key 无效/已失效 | key 本身不对，重新复制 |
| `B.Balance.InsufficientException`（message: `Insufficient balance`） | **key 有效，余额不足** | 额度用光或额度包未兑换，需充值/兑换 |
| `B.Request.InvalidModelFormatException` | 模型名没带 `厂商/` 前缀 | 加 `qwen/` 前缀重试 |
| `B.Permission.ModelNotFoundException` | 模型名错 **或** 无权限 | **不可当权限判据**（见下） |
| 正常返回 `choices` | key 有效且有余额 | 可用 |

**注意：key 与额度包是绑定的**（2026-09-15 实测）：一把 key 只覆盖它购买/兑换的模型额度包。
同一把 key 调 GLM 报 `Balance.Insufficient`、调 Kimi 报 `ModelNotFoundException` 时，
结论是「这把 key 只绑了 GLM 包且 GLM 已耗尽」，而不是「Kimi 名字写错」。多模型需多把 key 或确认 key 的覆盖范围。

### 3. 必做的对照实验

`B.Permission.ModelNotFoundException` 是**通用报错**：瞎编的模型名
（如 `zzz/zzz-nonsense`）返回的是同一句。所以：

- 看到 ModelNotFoundException **不要**下「没有权限」的结论；
- 必须先换成 `qwen/` 前缀重试；
- 再用一个假 key（如 `sk-000...`）做对照，确认假 key 才报 `InvalidApiKeyException`，
  以此证明手上的 key 认证是通的。

### 4. 找当前有效的 key / 配置

`~/.workbuddy/models.json` 可能被清空（内容变成 `[]`）。历史配置在：

```
~/.workbuddy/workspace/sessions/*/modify_backup/*.models.json
```

用 `grep -o "sk-[a-zA-Z0-9]\{20,\}"` 提取旧 key —— 注意旧 key 往往**已失效**
（本次实测两个 `sk-28aa/bb18cbd` 开头的老 key 均报 401），别把旧 key 当结论。

## 结论话术

- 只有余额不足时：明确说「key 是有效的，但余额不足，现在调不通」，
  并指向额度包兑换/充值动作，而不是含糊说「没权限」。
- 提醒用户：额度包使用规则通常是「仅限当前账号使用，不支持转移」。

## 顺带可做

若确认可用，把配置写回 `~/.workbuddy/models.json`，格式：

```json
{
  "id": "qwen/kimi-k2.6",
  "name": "Kimi k2.6",
  "vendor": "Aliyun Model Router",
  "url": "https://model-router.edu-aliyun.com/v1/chat/completions",
  "apiKey": "sk-...",
  "maxInputTokens": 128000,
  "maxOutputTokens": 8192,
  "supportsToolCall": true,
  "supportsImages": false,
  "supportsReasoning": false
}
```

（`kimi-k2.7-code` 的 `supportsReasoning` 为 `true`。）
