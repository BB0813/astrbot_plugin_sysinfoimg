# AstrBot 系统状态监控插件 (sysinfoimg)

> ⚠️ **注意：本项目已在 v2.0.0 版本进行完全重构，带来全新的 UI 设计与底层架构优化。**

一个专为 AstrBot 设计的高级系统状态监控插件，提供专业级、美观的服务器仪表盘图片。

![Dashboard Preview](https://raw.githubusercontent.com/Binbim/astrbot_plugin_img-sysinfo/main/preview.png)

## ✨ 核心特性

### 📊 现代化展示
- **📱 竖屏自适应**：默认 720x1280 分辨率，完美适配手机端查看。
- **🚀 实时采样**：采用 1秒 采样窗口，精准捕获 CPU 瞬时负载与网络上传/下载速率（告别 0KB/s）。
- **🎨 多样化主题**：
  - **Custom Dashboard (默认)**：基于 Tailwind CSS 的现代化大屏设计，大号字体与圆环图表。
  - **Dark Glass**：经典的深色毛玻璃风格。
  - **Neon**：赛博朋克霓虹风格。

### 🖥️ 全面监控
- **基础信息**: 操作系统、主机名、CPU型号、运行时间、系统负载。
- **性能图表**: CPU 核心使用率、内存/交换内存占比、网络实时流量。
- **进程榜单**: 实时显示资源占用最高的进程 Top 10。
- **磁盘监控**: 智能过滤 `overlay`, `tmpfs` 等虚拟文件系统，只展示真实磁盘分区。

## 🛠️ 安装与使用

### 安装方法
1. 在 AstrBot 插件市场搜索 `sysinfoimg` 并安装。
2. 或手动安装：
   ```bash
   # 将插件放置到 AstrBot/data/plugins/astrbot_plugin_sysinfoimg/
   pip install -r requirements.txt
   ```

### 指令
- `/sysinfo [标题]`：生成并发送系统状态图片。
  - 示例：`/sysinfo 我的服务器`
- `/sysinfo_disks`：查看详细的磁盘分区列表（用于调试分区挂载点）。

## ⚙️ 配置说明

插件默认配置已调优为最佳体验，您也可以在 AstrBot 管理面板中进行微调：

| 配置项 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `theme` | `custom_dashboard` | 主题模板：`custom_dashboard`, `dark_glass`, `neon` |
| `width` | `720` | 图片宽度，默认适配竖屏。 |
| `height` | `1280` | 图片高度。 |
| `top_n` | `10` | 进程榜单显示的进程数量。 |
| `process_sort_key` | `cpu` | 进程排序依据 (`cpu` 或 `memory`)。 |
| `background_mode` | `none` | 背景模式：`none` (默认渐变), `url` (网络图片), `file` (本地文件)。 |

## 🧩 依赖库
- `psutil`: 用于采集系统硬件信息。
- `jinja2`: 用于渲染 HTML 模板。
- `html2image`: 用于将 HTML 转换为图片。

## ❓ 故障排除

### 中文字符显示问题
如果生成的图片中中文字符显示为方块或空白，通常是因为系统缺少中文字体。

**Linux 安装字体方案：**
```bash
# Ubuntu/Debian
sudo apt-get install fonts-wqy-microhei fonts-wqy-zenhei fonts-noto-cjk

# CentOS/RHEL
sudo yum install wqy-microhei-fonts google-noto-cjk-fonts
```
安装后建议执行 `fc-cache -fv` 刷新缓存并重启 AstrBot。

### 磁盘分区显示异常
插件会自动过滤系统虚拟分区。如果正常分区未显示，请使用 `/sysinfo_disks` 查看插件识别到的原始分区列表，并检查分区挂载状态。

## 📝 版本历史

### v2.x (重构版)
- **v2.0.0**: 
  - 💥 **完全重构**：基于 HTML/CSS 的全新渲染引擎，彻底解决字体渲染与布局问题。
  - 🎨 **全新 UI**：引入 Custom Dashboard、Dark Glass 等现代化主题。
  - 📱 **竖屏适配**：默认 720x1280 分辨率，完美适配移动端查看。
  - ⚡ **性能优化**：引入 1秒 统一采样逻辑，修复网络速率为 0 的问题。
  - 🧹 **精简功能**：移除了不稳定的定时发送功能，专注于核心监控体验。
- **v0.2.1**: 修复图片尺寸与内容不匹配导致的留白问题；修复定时发送功能在部分环境下的兼容性问题；移除定时发送功能以精简插件。
- **v0.2.0**: 全新 HTML 渲染引擎，重构 UI 布局；引入 1秒 统一采样逻辑修复速率为 0 的问题；默认启用竖屏模式。

### v1.x (旧版本)
- **v1.1.1**: 固定图片高度为 900px，修复尺寸不一致问题。
- **v1.1.0**: 优化 Linux 字体加载逻辑，移除 composer 依赖。
- **v1.0.5**: 移除 AstrBot 内部数据展示，专注系统监控。
- **v1.0.2**: 新增 AstrBot 状态监控卡片。
- **v1.0.0**: 初始版本发布，基于 PIL 绘图。

## 🤝 支持与反馈
- [AstrBot 官方文档](https://astrbot.app)
- [插件反馈群](https://qm.qq.com/q/d4lwUp9ap4)

## 许可证
本插件基于 GNU Affero General Public License v3.0 许可证开源。
