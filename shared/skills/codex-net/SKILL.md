---
name: codex-net
description: 测试本机到各地区（新加坡/韩国/日本/美西/中国台湾，默认排除香港）网络线路的直连延迟，挑选最快线路。当用户说"测线路""哪个节点快""挑最快的网络线路""测试网络线路"时使用。
agent_created: true
---

# codex net.skill — 网络线路测速与选线

目标：从本机实测到各地区的直连延迟，输出排名表格，给出最快线路结论。**默认排除香港**（用户明确要求过，除非用户主动说包含香港）。

## 测速原理

- 用 TCP 握手时间（`curl %{time_connect}`）测延迟，不受目标主机禁 ping 影响。
- **必须绕过系统代理**（用户常开代理，`time_connect` 会变成连 127.0.0.1 的 ~1ms 假数据）：`--noproxy "*"`。
- 每条线路测 3 次，取稳定值/中位数（首个样本常有冷启动抖动，忽略明显离群值）。

## 测速目标（非香港线路）

| 线路 | 目标主机 | 备注 |
|---|---|---|
| 🇸🇬 新加坡 | www.nus.edu.sg:443 | 通常最快 |
| 🇰🇷 韩国 | www.naver.com:443 | 禁 ping，只能 TCP |
| 🇯🇵 日本 | www.yahoo.co.jp:443 | ping/TCP 都可用 |
| 🇺🇸 美西 | www.ucla.edu:443 | |
| 中国台湾 | www.ntu.edu.tw:443 | 禁 ping |

如用户要求包含香港，加 `www.hkex.com.hk:443`。

## 执行命令（bash，一次跑完所有线路）

```bash
for h in www.nus.edu.sg www.naver.com www.yahoo.co.jp www.ucla.edu www.ntu.edu.tw; do for i in 1 2 3; do curl -o /dev/null -s --noproxy "*" -w "$h %{time_connect}\n" --max-time 8 "https://$h:443"; done; done
```

## 已知环境坑（本机 Windows + PortableGit）

1. **bash 缺 coreutils**：`awk`、`mkdir`、`bc`、`dirname` 全都没有。不要在循环里做算术聚合——直接打印原始秒数，自己心算/口算平均值再汇报。
2. **PowerShell 工具输出可能不回显**（exit 0 但 stdout 为空），优先用 bash + curl 方案，别用 PowerShell TcpClient 测速。
3. `ping -n 4` 可用（输出有编码乱码但数字可读），可作为日本线路的交叉验证；韩国/台湾目标禁 ping，超时是正常的，不是线路问题。
4. DNS 可能被污染（如 pchome.com.tw 解析到错误 IP），若结果异常换目标主机复测。

## 输出格式

Markdown 表格：线路 | 平均延迟 | 排名（emoji 国旗 + 排名序号）。结论一句话点明最快线路；补充提醒"延迟低≠带宽高，选节点前在客户端实测下载速度"。

## 历史参考基准（2026-09 实测）

- 新加坡 ~65-106ms（常年第一）、韩国 ~70-110ms、日本 ~112-149ms、美西 ~156-188ms、中国台湾 ~290-316ms。
- 数值明显高于历史基准时，可能是路由拥堵或绕路，可复测一次再下结论。
