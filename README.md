# AstrBot 系统信息图片插件

一个用于获取当前系统状态并生成图片发送的 AstrBot 插件。

## 功能特性

- 🖥️ **系统信息监控**: 显示CPU、内存、磁盘使用情况
- 🤖 **AstrBot状态**: 显示消息总数、平台数、运行时间、内存占用
- 📊 **可视化图表**: 美观的圆形进度条和彩色信息卡片
- 🌐 **跨平台支持**: 支持Windows、Linux、macOS
- 🎨 **中文字体优化**: 智能字体加载，完美支持中文显示
- ⚡ **实时数据**: 获取当前系统和AstrBot实时状态信息
- 🛡️ **错误处理**: 完善的异常处理和日志记录

## 安装要求

- Python 3.7+
- AstrBot 框架
- 依赖库：
  - `psutil>=5.9.0` - 系统信息获取
  - `Pillow>=9.0.0` - 图片生成和处理

## 安装方法

1. 将插件文件放置到 AstrBot 的插件目录：`AstrBot/data/plugins/astrbot_plugin_sysinfoimg/`

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 在 AstrBot WebUI 中重载插件或重启 AstrBot

## 使用方法

安装插件后，在聊天中发送以下命令：

```
/sysinfo
```

插件将生成一张包含以下信息的图片：

### 系统信息区域
- 系统基本信息（操作系统、运行时间等）
- CPU使用率（圆形进度条显示）
- 内存使用情况（已用/总计）
- 磁盘使用情况（已用/总计）
- 网络流量统计
- 当前时间

### AstrBot状态区域
- 🟣 **消息总数**: 显示AstrBot处理的消息数量
- 🔵 **消息平台**: 显示已连接的平台数量
- 🟢 **运行时间**: 显示AstrBot的运行时长
- 🟠 **内存占用**: 显示AstrBot进程的内存使用情况

## 显示信息

生成的图片包含以下系统信息：

- **系统信息**：操作系统类型和版本
- **主机名**：当前设备的主机名
- **处理器**：CPU 型号信息
- **CPU 使用率**：当前 CPU 使用百分比和核心数
- **CPU 频率**：当前 CPU 运行频率
- **内存使用情况**：已用内存/总内存及使用百分比
- **磁盘使用情况**：已用磁盘空间/总磁盘空间及使用百分比
- **系统运行时间**：自上次启动以来的运行时间

## 图片特性

- 🎨 深色主题设计，美观易读
- 📊 彩色进度条显示资源使用率
- 🔤 自适应字体，支持多种系统字体
- 📐 固定尺寸 800x600 像素，适合各种聊天场景

## 技术实现

- 使用 `psutil` 库获取系统硬件和性能信息
- 使用 `PIL (Pillow)` 库生成和绘制图片
- 支持 base64 编码图片传输
- 异常处理确保插件稳定运行

## 兼容性

- ✅ Windows 10/11
- ✅ Linux (Ubuntu, CentOS, Debian 等)
- ✅ macOS

### Linux 环境特别说明

在 Linux 环境下，如果图片中的中文字符显示为方块或不显示，需要安装中文字体：

**快速安装（推荐）：**
```bash
# 使用提供的安装脚本
chmod +x install_fonts_linux.sh
./install_fonts_linux.sh
```

**手动安装：**
```bash
# Ubuntu/Debian
sudo apt-get install fonts-wqy-microhei fonts-wqy-zenhei fonts-noto-cjk

# CentOS/RHEL/Fedora
sudo yum install wqy-microhei-fonts wqy-zenhei-fonts google-noto-cjk-fonts
# 或者使用 dnf
sudo dnf install wqy-microhei-fonts wqy-zenhei-fonts google-noto-cjk-fonts

# Arch Linux
sudo pacman -S wqy-microhei wqy-zenhei noto-fonts-cjk
```

## 故障排除

### 中文字符显示问题

**问题现象：** 生成的图片中中文字符显示为方块或空白

**解决方案：**

1. **检查字体安装：**
   ```bash
   # 检查系统中的中文字体
   fc-list :lang=zh
   ```

2. **查看插件日志：**
   - 在 AstrBot 日志中查找字体加载相关信息
   - 关键词："成功加载字体"、"字体加载失败"、"动态搜索"

3. **手动测试字体：**
   ```python
   from PIL import Image, ImageDraw, ImageFont
   import os
   
   # 测试字体是否支持中文
   font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
   if os.path.exists(font_path):
       font = ImageFont.truetype(font_path, 20)
       img = Image.new('RGB', (200, 100), 'white')
       draw = ImageDraw.Draw(img)
       draw.text((10, 10), "测试中文", fill='black', font=font)
       img.save('test_chinese.png')
   ```

4. **重启服务：**
   - 安装字体后重启 AstrBot 服务
   - 清除字体缓存：`fc-cache -fv`

### 性能问题

如果图片生成较慢，可以：
- 减少字体搜索范围
- 使用更轻量的字体文件
- 检查系统资源使用情况

## 更新日志

### v1.0.4
- 🔧 **修复比例圆环错误**: 纠正可见比例错误

### v1.0.3
- 🔧 **优化日志输出**: 减少不必要的debug和info级别日志
- 🔇 **静默处理**: 静默处理字体加载失败等非关键错误
- 🐛 **修复问题**: 解决部分用户反馈的logging error问题
- 🛡️ **提升稳定性**: 提升插件运行稳定性

### v1.0.2
- 🤖 **新增AstrBot状态监控**: 显示消息总数、平台数、运行时间、内存占用
- 🎨 **全新UI设计**: 添加彩色信息卡片，提升视觉效果
- 📊 **增强数据展示**: 系统信息 + AstrBot数据双重监控
- 🔧 **智能数据获取**: 自动检测AstrBot运行状态和统计信息
- 📏 **优化布局**: 调整图片尺寸和元素排列，容纳更多信息

### v1.0.1
- 🔧 大幅改进 Linux 环境下的中文字体支持
- ➕ 添加动态字体搜索功能
- 📝 增强字体加载日志和错误处理
- 🛠️ 提供 Linux 字体安装脚本
- 📚 完善文档和故障排除指南

### v1.0.0
- 初始版本发布
- 支持基本系统信息获取和图片生成
- 跨平台兼容性支持
- 美观的图片界面设计

## 支持

如有问题或建议，请访问：
- [AstrBot 官方文档](https://astrbot.app)
- [插件开发文档](https://astrbot.app/dev/star/plugin.html)
- [开发者联系方式](https://qm.qq.com/q/nDHgJBm5Mc)
- [插件反馈群](https://qm.qq.com/q/d4lwUp9ap4)

## 许可证

本插件基于 GNU Affero General Public License v3.0 许可证开源。
