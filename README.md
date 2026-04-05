# AstrBot 图片系统状态插件 / AstrBot Image Sysinfo

> 面向 AstrBot 的高分辨率系统状态与稳定统计图片插件。  
> A high-resolution system status and stable statistics image plugin for AstrBot.

![Version](https://img.shields.io/badge/version-V2.5.0-7c6cff)
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

## 指令 / Commands

- `/sysinfo` - 生成当前系统状态图片 / generate the current dashboard image
- `/sysinfo_auto <分钟>` - 开启定时发送 / enable scheduled sending
- `/sysinfo_auto off` - 关闭定时发送 / disable scheduled sending

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

## 安装 / Install

```bash
pip install -r requirements.txt
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

本插件使用浏览器截图渲染，不是直接用 PIL 画字，因此运行截图进程的环境必须安装中文字体。  
This plugin uses browser screenshot rendering rather than direct PIL text drawing, so the rendering environment must have Chinese fonts installed.

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
