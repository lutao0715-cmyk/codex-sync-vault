何时读本文件：出现渲染地基、数据根迁移、cwd、模板路径或抽帧等环境故障时；先读对应报错，再按本文处置，不用旧项目和临时脚本绕过。

## 数据根整体迁移

换盘或换目录时不重装，程序层不动，只搬数据根：

1. 整目录搬迁 `projects/`、`brands/`、`templates/`，旧版遗留的 `.env.local` 若存在随目录带走。
2. 把程序根的 data-root 记录改成新绝对路径：macOS 为 `~/.svf/data-root`，Windows 为 `%USERPROFILE%\.svf\data-root`；Windows 必须是无 BOM 的 UTF-8。
3. 运行 `svf doctor` 验证数据根定位、网关连通和渲染地基。网关断网时 WARN 属正常，不影响安装。

重装解决不了迁移，数据根记录一次锁定，重装只沿用旧值。

## 常见定位

- `hyperframes: command not found`：项目不在共享根之下。把项目移进数据根 `projects/`，或在其祖先目录安装 hyperframes，再零参数重跑 build。
- `--brand`/`--project` 找不到：相对路径按当前工作目录解析，先核对 cwd，再用绝对路径重试。
- macOS 拷贝模板树使用 `ditto`；ffmpeg 抽帧先准备输出文件名清单，再循环执行。
