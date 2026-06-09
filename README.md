# AstrBot 图片系统状态插件 / AstrBot Image Sysinfo

> 面向 AstrBot 的高分辨率系统状态与稳定统计图片插件。  
> A high-resolution system status and stable statistics image plugin for AstrBot.

![Version](https://img.shields.io/badge/version-V2.8.1-7c6cff)
![License](https://img.shields.io/badge/license-AGPL--3.0-blue)
![AstrBot](https://img.shields.io/badge/AstrBot-plugin-6ea8ff)

## 概述 / Overview

本插件会生成适合聊天场景分享的竖版看板图片，重点展示两类稳定数据：  
This plugin renders a portrait dashboard image for chat sharing and focuses on two stable data groups:

- 系统状态：CPU、内存、Swap、磁盘、网络速率、进程列表、主机信息  
  System status: CPU, memory, swap, disk, network rate, processes, and host information
- AstrBot 稳定统计：平台数量、消息总数、24 小时消息趋势、平台排名、24 小时 Token 趋势、Token Top  
  AstrBot stable stats: platform count, message total, 24h message trend, platform ranking, 24h token trend, and token top list

## 功能特性 / Features

- 基于 HTML 的图片渲染，支持高分辨率超采样  
  HTML-based image rendering with high-resolution supersampling
- 默认深蓝紫配色，适合聊天预览  
  Dark blue-violet default palette optimized for chat previews
- 支持会话级配置覆盖  
  Supports session-level config overrides
- 支持基于 Git 历史自动更新贡献者名单  
  Supports automatic contributor list updates from git history
- 内置 GitHub Actions 周期性更新贡献者文档  
  Includes a GitHub Actions workflow for scheduled contributor doc updates
- 支持按能力自动降级的深度主机指标采集（GPU、温度、电池、容器）  
  Supports capability-aware deep host metrics such as GPU, temperature, battery, and containers

## 指令 / Commands

- `/sysinfo` - 生成当前系统状态图片 / generate the current dashboard image
- `/sysinfo_auto <分钟>` - 开启定时发送 / enable scheduled sending
- `/sysinfo_auto off` - 关闭定时发送 / disable scheduled sending
- `/sysinfo_history [小时]` - 输出系统历史趋势看板 / render the system history dashboard
- `/sysinfo_alert <分钟>` - 开启阈值告警巡检 / enable threshold-based alert checks
- `/sysinfo_alert status` - 查看当前会话告警状态 / show current alert status
- `/sysinfo_alert off` - 关闭阈值告警 / disable threshold alerts
- `/sysinfo_stats_diag` - 输出 AstrBot 统计数据来源诊断 / show AstrBot stats source diagnostics
- `/sysinfo_host_diag` - 输出深度主机探测诊断 / show deep host probe diagnostics

## 主要配置 / Main Config

| Key | Default | 中文说明 | English Description |
| --- | --- | --- | --- |
| `title` | `系统状态` | 图片标题 | Dashboard title |
| `theme` | `custom_dashboard` | 主题预设 | Theme preset |
| `width` | `960` | 逻辑布局宽度 | Logical layout width |
| `height` | `1760` | 逻辑布局高度 | Logical layout height |
| `render_scale` | `3` | 高清渲染倍数 | High-resolution render scale |
| `locale` | `zh` | 界面语言 | Interface language |
| `background_mode` | `none` | 背景模式：`none` / `url` / `file` | Background mode: `none` / `url` / `file` |
| `show_cpu` | `true` | 显示 CPU 卡片 | Show CPU card |
| `show_memory` | `true` | 显示内存卡片 | Show memory card |
| `show_swap` | `true` | 显示 Swap 卡片 | Show swap card |
| `show_disk` | `true` | 显示磁盘数据 | Show disk data |
| `show_network` | `true` | 显示网络数据 | Show network data |
| `show_top_processes` | `true` | 显示进程列表 | Show process list |
| `enable_system_history` | `true` | 开启本地系统历史采样 | Enable local system history sampling |
| `show_system_history_panel` | `true` | 在主看板中显示历史趋势面板 | Show the history trend panel on the main dashboard |
| `history_sample_minutes` | `5` | 历史采样间隔（分钟） | History sampling interval in minutes |
| `history_retention_hours` | `72` | 历史采样保留时长（小时） | History retention window in hours |
| `history_chart_hours` | `24` | 历史趋势默认展示窗口（小时） | Default history chart window in hours |
| `history_chart_points` | `36` | 历史趋势最大采样点数 | Maximum plotted history points |
| `history_alert_context_hours` | `1` | 告警附带趋势回看窗口（小时） | Alert trend lookback window in hours |
| `enable_deep_host_metrics` | `true` | 开启深度主机指标采集 | Enable deep host metric collection |
| `show_battery_card` | `true` | 显示电池卡片 | Show the battery card |
| `show_temperature_card` | `true` | 显示温度卡片 | Show the temperature card |
| `show_gpu_card` | `true` | 显示 GPU 卡片 | Show the GPU card |
| `show_container_card` | `true` | 显示容器卡片 | Show the container card |
| `alert_battery_percent` | `0` | 电池放电阈值，`0` 为关闭 | Battery threshold while discharging; `0` disables the alert |
| `alert_container_stopped` | `0` | 停止容器数量阈值，`0` 为关闭 | Stopped container count threshold; `0` disables the alert |

## 告警 / Alerts

- `alert_cpu_percent` / `alert_memory_percent` / `alert_disk_percent` / `alert_swap_percent`：百分比阈值，设置为 `0` 可关闭对应项。  
  Percentage thresholds; set to `0` to disable a metric.
- `alert_gpu_percent`：GPU 百分比阈值，设置为 `0` 可关闭 GPU 告警。  
  GPU percentage threshold; set to `0` to disable GPU alerts.
- `alert_temperature_c`：温度告警阈值（摄氏度），设置为 `0` 可关闭温度告警。  
  Temperature alert threshold in Celsius; set to `0` to disable temperature alerts.
- `alert_battery_percent`：电池放电阈值，仅在未接电源时生效，设置为 `0` 可关闭电池告警。  
  Battery threshold while discharging; only applies when unplugged, and `0` disables the alert.
- `alert_container_stopped`：停止容器数量阈值，达到或超过该值时触发告警，设置为 `0` 可关闭容器告警。  
  Stopped container count threshold; triggers when the stopped count reaches the value, and `0` disables the alert.
- `alert_cooldown_minutes`：同一告警的重复提醒冷却时间。  
  Cooldown minutes before repeating the same alert.
- `alert_send_recovery`：告警恢复后补发一条恢复通知。  
  Send a recovery message when metrics return to normal.
- `alert_with_image`：触发告警时附带一张最新系统状态图。  
  Attach a fresh dashboard image when an alert fires.

## 历史趋势 / History Trends

- `/sysinfo_history [小时]`：输出带历史趋势面板的系统看板；未填写时使用 `history_chart_hours` 默认窗口。  
  Render a dashboard with the history trend panel; if omitted, it uses the default `history_chart_hours` window.
- 历史数据保存到本地 `system_history.json`，按 `history_sample_minutes` 周期采样，并根据 `history_retention_hours` 自动裁剪。  
  History is stored in local `system_history.json`, sampled every `history_sample_minutes`, and trimmed by `history_retention_hours`.
- 启用 `show_system_history_panel` 后，主看板会追加 CPU、内存、磁盘、网络四类趋势卡片。  
  When `show_system_history_panel` is enabled, the main dashboard adds trend cards for CPU, memory, disk, and network.
- 告警消息会结合 `history_alert_context_hours` 附加最近峰值/波动摘要，便于区分瞬时抖动与持续升高。  
  Alert messages append recent peak and fluctuation context based on `history_alert_context_hours`.

## 深度主机指标 / Deep Host Metrics

- 主看板会在能力可用时自动展示 GPU、温度、电池、容器等扩展指标；不可用时自动降级，不影响基础系统卡片。  
  The main dashboard automatically shows GPU, temperature, battery, and container metrics when available, and degrades gracefully when they are not.
- 当前版本优先通过 `psutil`、`nvidia-smi` 与 `docker` CLI 进行可选探测，因此不同主机环境显示内容可能不同。  
  This version primarily relies on optional probing through `psutil`, `nvidia-smi`, and the `docker` CLI, so visible metrics may differ by host.
- `/sysinfo_alert` 已扩展到 `alert_gpu_percent`、`alert_temperature_c`、`alert_battery_percent` 与 `alert_container_stopped` 四类阈值。  
  `/sysinfo_alert` now covers `alert_gpu_percent`, `alert_temperature_c`, `alert_battery_percent`, and `alert_container_stopped`.
- `/sysinfo_host_diag` 可直接输出宿主机探测结果、指标来源与当前配置，便于定位为什么某些深度指标没有显示。  
  `/sysinfo_host_diag` prints probe results, data sources, and the active config so you can diagnose why a deep host metric is missing.
- 深度主机指标的采集已与卡片显隐解耦；即使隐藏单个卡片，相关告警、能力摘要和诊断链路仍可继续工作。  
  Deep host probing is now decoupled from card visibility, so alerts, capability summaries, and diagnostics still work even when individual cards are hidden.
- 将 `bottom_right_panel` 设为 `deep_host` 后，底部细节区会显示多 GPU、温度、电池与容器明细，并对停止容器进行额外标记。  
  Set `bottom_right_panel` to `deep_host` to show detailed rows for multi-GPU, temperature, battery, and containers, with extra stopped-container markers.
- 历史趋势面板现在可在指标可用时追加 GPU 利用率与温度趋势。  
  The history trend panel can now append GPU utilization and temperature trends when those metrics are available.

## 贡献者自动更新 / Contributor Auto Update

仓库已经内置贡献者自动维护链路：  
This repository already includes automatic contributor maintenance:

- 本地更新：`python scripts/update_contributors.py`  
  Local update: `python scripts/update_contributors.py`
- 工作流文件：`.github/workflows/update-contributors.yml`  
  Workflow file: `.github/workflows/update-contributors.yml`
- 数据来源：`git shortlog -sne --all`  
  Data source: `git shortlog -sne --all`
- 更新时机：支持手动触发、推送到 `main` / `master`、以及每周定时任务  
  Update timing: manual trigger, push to `main` / `master`, and weekly schedule

<!-- CONTRIBUTORS:START -->
- Binbim_ProMax - 10 commits
<!-- CONTRIBUTORS:END -->

完整贡献者表见 `CONTRIBUTORS.md`。  
See `CONTRIBUTORS.md` for the full contributor table.

## Star 趋势 / Star Trend

[![Star History Chart](https://api.star-history.com/svg?repos=BB0813/astrbot_plugin_sysinfoimg&type=Date)](https://www.star-history.com/#BB0813/astrbot_plugin_sysinfoimg&Date)

## 项目结构 / Project Structure

- `main.py` - AstrBot 插件入口 / AstrBot plugin entry
- `dashboard_runtime.py` - 稳定统计采集与渲染数据组装 / stable stats collection and render data assembly
- `monitor.py` - 系统指标采集 / system metric collection
- `utils.py` - 字体、文案、背景等辅助逻辑 / helper logic for fonts, labels, and backgrounds
- `templates/apple_class.html` - HTML 看板模板 / HTML dashboard template
- `_conf_schema.json` - AstrBot 配置 schema / AstrBot config schema
- `scripts/update_contributors.py` - 贡献者名单生成脚本 / contributor generator script
- `metadata.yaml` 与 `main.py`（仓库根目录）- 当前发布入口 / active plugin entry for release
- `archive/README.md` - 归档内容说明 / archive guide
- `archive/astrbot_plugin_sysinfoimg/` - 历史实现参考归档，不参与当前发布 / archived legacy implementation, not part of the current release
- `archive/Apple-Class 设计风格指南.md` 与 `archive/样图.png` - 设计说明与样图归档 / archived design notes and sample image

## 安装 / Install

```bash
pip install -r requirements.txt
```

如需本地跑测试或做开发校验，可额外安装：  
For local tests or development checks, install additionally:

```bash
pip install -r requirements-dev.txt
```

将插件放入 AstrBot 插件目录后，在 AstrBot WebUI 中重载即可。  
After placing the plugin in your AstrBot plugin directory, reload it in AstrBot WebUI.

## 常见问题 / FAQ

### 图片仍然不够清晰？ / Why is the image still blurry?

请优先检查：  
Check these first:

- `render_scale` 通常建议为 `2` 或 `3`  
  `render_scale` should usually be `2` or `3`
- `width` 不宜过小  
  `width` should not be too small
- 某些聊天平台会再次压缩图片  
  Some chat platforms recompress uploaded images

### 中文字符不显示？ / Why are Chinese characters missing?

本插件使用浏览器截图渲染，不是直接用 PIL 画字，因此运行截图进程的环境必须安装中文字体；插件现在只会检测并提示，不会自动安装系统字体包。  
This plugin uses browser screenshot rendering rather than direct PIL text drawing, so the rendering environment must have Chinese fonts installed; the plugin now only checks and warns instead of auto-installing system font packages.
如需排查 AstrBot 统计图表为什么为空，可先执行 `/sysinfo_stats_diag` 查看运行时、平台统计、数据库历史统计与会话 Token 数据源是否可用。  
Use `/sysinfo_stats_diag` to inspect runtime, platform stats, database history stats, and conversation token sources when AstrBot charts appear empty.

Linux 示例：  
Linux example:

```bash
apt-get update && apt-get install -y fonts-wqy-microhei fonts-wqy-zenhei fonts-noto-cjk
fc-cache -fv
```

安装字体后请重启 AstrBot。  
Restart AstrBot after installing fonts.

## 许可证 / License

本项目使用 `GNU AGPL-3.0`，详见 `LICENSE`。  
This project uses `GNU AGPL-3.0`. See `LICENSE` for details.
