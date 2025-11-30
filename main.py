# -*- coding: utf-8 -*-
import sys
import locale
import psutil
import platform
import datetime
import io
import math
import time
import os

from PIL import Image, ImageDraw, ImageFont

# 尝试导入AstrBot相关模块，如果失败则使用模拟对象
ASTRBOT_AVAILABLE = False
try:
    from astrbot.api.event import filter, AstrMessageEvent
    from astrbot.api.star import Context, Star, register
    from astrbot.api import logger
    from astrbot.api.message_components import Image as AstrImage, Plain
    ASTRBOT_AVAILABLE = True
except ImportError:
    # 模拟AstrBot相关对象，用于测试
    class MockLogger:
        def info(self, msg):
            print(f"[INFO] {msg}")
        def warning(self, msg):
            print(f"[WARNING] {msg}")
        def error(self, msg):
            print(f"[ERROR] {msg}")
    
    logger = MockLogger()
    
    # 其他模拟类（仅用于语法通过）
    class Context:
        pass
    
    class Star:
        def __init__(self, context):
            self.context = context
    
    def register(*args, **kwargs):
        def decorator(cls):
            return cls
        return decorator
    
    class MockFilter:
        def command(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    
    filter = MockFilter()
    
    class AstrMessageEvent:
        pass
    
    class AstrImage:
        @staticmethod
        def fromFileSystem(path):
            pass
    
    class Plain:
        def __init__(self, text):
            self.text = text

# 移除可能导致日志冲突的编码设置
# 让AstrBot自己处理编码问题

class ImageGenerator:
    """系统信息图片生成器，采用模块化设计"""
    
    def __init__(self):
        # 图片尺寸配置
        self.width = 900
        self.base_height = 800  # 基础高度，会根据内容动态调整
        
        # 颜色配置
        self.colors = {
            'background': (26, 26, 46),
            'background_gradient_end': (52, 73, 94),
            'section_bg': (38, 38, 68),  # 使用RGB格式，移除透明度
            'border': '#667eea',
            'text_title': '#ffffff',
            'text_content': '#e2e8f0',
            'text_subtitle': '#a0aec0',
            'cpu_color': '#4299e1',
            'cpu_warning_color': '#f56565',
            'mem_color': '#48bb78',
            'mem_warning_color': '#ed8936',
            'disk_color': '#9f7aea',
            'disk_warning_color': '#e53e3e',
            'system_disk_mark': '⭐ '
        }
        
        # 字体配置
        self.fonts = {
            'title': None,
            'large': None,
            'medium': None,
            'small': None
        }
        
        # 布局配置
        self.padding = 40
        self.section_spacing = 25  # 增加各部分之间的间距
        self.line_spacing = 25
        
        # 插件载入时默认安装&更新字体
        if platform.system() != 'Windows':
            logger.info("插件载入，开始安装&更新中文字体...")
            self._install_chinese_fonts()
        
        # 加载字体
        self._load_fonts()
    
    def _load_fonts(self):
        """加载字体"""
        logger.info("开始加载字体")
        
        # 字体配置
        if platform.system() == 'Windows':
            font_configs = [
                ("C:/Windows/Fonts/msyh.ttc", 0),  # 微软雅黑，索引0
                ("C:/Windows/Fonts/simhei.ttf", None),  # 黑体
                ("C:/Windows/Fonts/simsun.ttc", 0),  # 宋体，索引0
                ("C:/Windows/Fonts/msyhbd.ttc", 0),  # 微软雅黑粗体，索引0
                ("C:/Windows/Fonts/arial.ttf", None)  # 备用英文字体
            ]
        else:
            font_configs = [
                # 文泉驿字体 (最常见的Linux中文字体)
                ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", None),
                ("/usr/share/fonts/wqy-microhei/wqy-microhei.ttc", None),
                ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", None),
                ("/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc", None),
                ("/usr/share/fonts/cjkfonts/wqy-microhei.ttc", None),
                ("/usr/share/fonts/cjkfonts/wqy-zenhei.ttc", None),
                # Noto字体 (Google开源字体)
                ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 0),
                ("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc", 0),
                ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
                ("/usr/share/fonts/noto/NotoSansCJK-Regular.ttc", 0),
                ("/usr/share/fonts/noto-cjk-vf/NotoSansCJK-Regular.ttc", 0),
                # 思源字体
                ("/usr/share/fonts/truetype/source-han-sans/SourceHanSansCN-Regular.otf", None),
                ("/usr/share/fonts/opentype/source-han-sans/SourceHanSansCN-Regular.otf", None),
                # 其他常见中文字体路径
                ("/usr/share/fonts/chinese/TrueType/wqy-microhei.ttc", None),
                ("/usr/local/share/fonts/wqy-microhei.ttc", None),
            ]
        
        loaded_font_path = None
        
        # 尝试加载字体
        for font_path, font_index in font_configs:
            if os.path.exists(font_path):
                try:
                    if font_index is not None:
                        # 对于TTC字体文件，指定字体索引
                        self.fonts['title'] = ImageFont.truetype(font_path, 32, index=font_index)
                        self.fonts['large'] = ImageFont.truetype(font_path, 20, index=font_index)
                        self.fonts['medium'] = ImageFont.truetype(font_path, 16, index=font_index)
                        self.fonts['small'] = ImageFont.truetype(font_path, 14, index=font_index)
                    else:
                        self.fonts['title'] = ImageFont.truetype(font_path, 32)
                        self.fonts['large'] = ImageFont.truetype(font_path, 20)
                        self.fonts['medium'] = ImageFont.truetype(font_path, 16)
                        self.fonts['small'] = ImageFont.truetype(font_path, 14)
                    loaded_font_path = font_path
                    logger.info(f"成功加载字体: {font_path} (索引: {font_index})")
                    break
                except Exception as e:
                    logger.warning(f"字体加载失败: {font_path}, {e}")
                    continue  # 静默处理字体加载失败
        
        # 检查是否所有字体都加载成功
        fonts_loaded = all(self.fonts.values())
        
        # 如果预定义路径都失败，尝试动态搜索字体
        if not fonts_loaded and platform.system() != 'Windows':
            logger.info("预定义字体路径均失败，开始动态搜索中文字体...")
            # 重置字体字典，确保_search_fonts方法能正确检测到失败
            self.fonts = {
                'title': None,
                'large': None,
                'medium': None,
                'small': None
            }
            self._search_fonts()
            
            # 重新检查字体是否加载成功
            fonts_loaded = all(self.fonts.values())
            
            # 即使加载了英文字体，也要检查是否支持中文
            if fonts_loaded and platform.system() != 'Windows':
                logger.info("检查加载的字体是否支持中文...")
                try:
                    # 更可靠的中文支持检测方法：直接测试绘制效果
                    # 创建一个测试图像
                    test_img = Image.new('RGB', (200, 50), color=(255, 255, 255))
                    draw = ImageDraw.Draw(test_img)
                    
                    # 绘制中文测试文本
                    test_text = "系统信息"
                    draw.text((10, 10), test_text, font=self.fonts['title'], fill=(0, 0, 0))
                    
                    # 检查绘制结果
                    # 1. 分析像素数据，检查是否有实际的中文绘制
                    pixels = list(test_img.getdata())
                    # 计算非白色像素数量
                    non_white_pixels = sum(1 for pixel in pixels if pixel != (255, 255, 255))
                    logger.info(f"中文测试结果: 非白色像素数={non_white_pixels}")
                    
                    # 2. 检查字体名称，DejaVu等字体肯定不支持中文
                    font_name = self.fonts['title'].getname()[0].lower()
                    logger.info(f"字体名称: {font_name}")
                    
                    # 3. 明确排除已知不支持中文的字体
                    known_non_chinese_fonts = ['dejavu', 'ubuntu', 'roboto', 'arial', 'helvetica', 'times', 'courier', 'verdana', 'georgia', 'palatino', 'trebuchet', 'impact', 'comic', 'sans', 'serif', 'mono']
                    is_known_non_chinese = any(font in font_name for font in known_non_chinese_fonts)
                    
                    # 4. 检查是否为中文字体
                    is_chinese_font = any(keyword in font_name for keyword in ['wqy', 'microhei', 'zenhei', 'noto', 'cjk', 'han', 'chinese', 'simhei', 'simsun', 'yahei', 'pingfang', 'hiragino', 'arphic', 'ukai', 'uming', 'droid', 'source', 'song', 'hei', 'kai', 'fangsong'])
                    
                    # 5. 测试单个中文字符的宽度，方框字符通常宽度一致
                    char_widths = []
                    for char in test_text:
                        bbox = draw.textbbox((0, 0), char, font=self.fonts['title'])
                        char_width = bbox[2] - bbox[0]
                        char_widths.append(char_width)
                    logger.info(f"单个字符宽度: {char_widths}")
                    
                    # 综合判断：
                    # 1. 如果是已知不支持中文的字体
                    # 2. 或者不是已知的中文字体
                    # 3. 或者单个字符宽度差异很小（方框字符）
                    # 则认为字体不支持中文
                    width_variance = max(char_widths) - min(char_widths) if char_widths else 0
                    logger.info(f"字体名称检测: {is_chinese_font}, 已知非中文字体: {is_known_non_chinese}, 字符宽度差异: {width_variance}")
                    
                    # 严格判断：已知非中文字体直接判定为不支持中文
                    if is_known_non_chinese or not is_chinese_font or width_variance < 5:
                        logger.info("加载的字体不支持中文，准备自动安装中文字体...")
                        fonts_loaded = False
                    else:
                        logger.info("加载的字体支持中文")
                except Exception as e:
                    logger.warning(f"测试字体是否支持中文时出错: {e}")
                    # 如果测试失败，假设字体不支持中文
                    fonts_loaded = False
        
        # 如果动态搜索也失败，尝试自动安装中文字体
        if not fonts_loaded and platform.system() != 'Windows':
            logger.info("动态搜索字体失败或加载的字体不支持中文，尝试自动安装中文字体...")
            self._install_chinese_fonts()
            # 重置字体字典，安装后重新尝试动态搜索
            self.fonts = {
                'title': None,
                'large': None,
                'medium': None,
                'small': None
            }
            self._search_fonts()
            # 重新检查字体是否加载成功
            fonts_loaded = all(self.fonts.values())
        
        # 确保字体对象不为None（跨平台兜底）
        if not all(self.fonts.values()):
            logger.warning("部分字体加载失败，使用默认字体")
            self.fonts['title'] = ImageFont.load_default()
            self.fonts['large'] = ImageFont.load_default()
            self.fonts['medium'] = ImageFont.load_default()
            self.fonts['small'] = ImageFont.load_default()
        
        logger.info(f"字体加载完成，路径: {loaded_font_path if loaded_font_path else 'default'}")
    
    def _install_chinese_fonts(self):
        """自动安装中文字体"""
        try:
            import subprocess
            import platform
            
            logger.info("开始自动安装中文字体")
            
            # 检测Linux发行版
            distro = self._detect_linux_distro()
            logger.info(f"检测到Linux发行版: {distro}")
            
            # 根据发行版选择安装命令
            install_commands = {
                'ubuntu': ['apt-get', 'update', '-y'],
                'debian': ['apt-get', 'update', '-y'],
                'linuxmint': ['apt-get', 'update', '-y'],
                'fedora': ['dnf', 'update', '-y'],
                'centos': ['yum', 'update', '-y'],
                'redhat': ['yum', 'update', '-y'],
                'opensuse': ['zypper', 'refresh'],
                'arch': ['pacman', '-Syu', '--noconfirm']
            }
            
            font_packages = {
                'ubuntu': ['fonts-wqy-microhei', 'fonts-wqy-zenhei', 'fonts-noto-cjk'],
                'debian': ['fonts-wqy-microhei', 'fonts-wqy-zenhei', 'fonts-noto-cjk'],
                'linuxmint': ['fonts-wqy-microhei', 'fonts-wqy-zenhei', 'fonts-noto-cjk'],
                'fedora': ['wqy-microhei-fonts', 'wqy-zenhei-fonts', 'google-noto-cjk-fonts-common'],
                'centos': ['wqy-microhei-fonts', 'wqy-zenhei-fonts', 'google-noto-cjk-fonts-common'],
                'redhat': ['wqy-microhei-fonts', 'wqy-zenhei-fonts', 'google-noto-cjk-fonts-common'],
                'opensuse': ['wqy-microhei-fonts', 'wqy-zenhei-fonts', 'google-noto-cjk-fonts'],
                'arch': ['ttf-wqy-microhei', 'ttf-wqy-zenhei', 'noto-fonts-cjk']
            }
            
            # 执行安装命令
            if distro in install_commands and distro in font_packages:
                # 更新包列表
                update_cmd = install_commands[distro]
                logger.info(f"执行命令: {' '.join(update_cmd)}")
                try:
                    subprocess.run(update_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    logger.info("包列表更新成功")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"包列表更新失败: {e.stderr}")
                    # 继续尝试安装字体，不中断
                
                # 安装字体包
                packages = font_packages[distro]
                install_cmd = []
                
                if distro in ['ubuntu', 'debian', 'linuxmint']:
                    install_cmd = ['apt-get', 'install', '-y'] + packages
                elif distro in ['fedora']:
                    install_cmd = ['dnf', 'install', '-y'] + packages
                elif distro in ['centos', 'redhat']:
                    install_cmd = ['yum', 'install', '-y'] + packages
                elif distro in ['opensuse']:
                    install_cmd = ['zypper', 'install', '-y'] + packages
                elif distro in ['arch']:
                    install_cmd = ['pacman', '-S', '--noconfirm'] + packages
                
                logger.info(f"执行命令: {' '.join(install_cmd)}")
                try:
                    subprocess.run(install_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    logger.info("字体安装成功")
                    
                    # 刷新字体缓存
                    logger.info("刷新字体缓存")
                    cache_cmd = ['fc-cache', '-fv']
                    subprocess.run(cache_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    logger.info("字体缓存刷新成功")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"字体安装失败: {e.stderr}")
                except Exception as e:
                    logger.warning(f"字体安装过程中发生错误: {e}")
            else:
                logger.warning(f"不支持的Linux发行版: {distro}")
                
        except Exception as e:
            logger.warning(f"自动安装字体失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _detect_linux_distro(self):
        """检测Linux发行版"""
        try:
            import subprocess
            
            # 1. 优先读取/etc/os-release文件（现代Linux发行版的标准）
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('ID='):
                            distro = line.split('=')[1].strip().strip('"')
                            return distro.lower()
            
            # 2. 尝试使用lsb_release命令
            try:
                result = subprocess.run(['lsb_release', '-i'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                distro = result.stdout.split(':')[1].strip().lower()
                return distro
            except:
                pass
            
            # 3. 尝试检测常见的包管理器（最可靠的方法）
            if os.path.exists('/usr/bin/apt-get'):
                return 'ubuntu'  # Debian系
            elif os.path.exists('/usr/bin/dnf'):
                return 'fedora'
            elif os.path.exists('/usr/bin/yum'):
                return 'centos'
            elif os.path.exists('/usr/bin/zypper'):
                return 'opensuse'
            elif os.path.exists('/usr/bin/pacman'):
                return 'arch'
            
            return 'unknown'
        except Exception as e:
            logger.warning(f"检测Linux发行版失败: {e}")
            return 'unknown'
    
    def _search_fonts(self):
        """动态搜索字体"""
        try:
            import glob
            # 重置字体字典，确保每次搜索都从干净的状态开始
            self.fonts = {
                'title': None,
                'large': None,
                'medium': None,
                'small': None
            }
            
            # 搜索常见的字体目录
            search_paths = [
                "/usr/share/fonts/**/*.ttf",
                "/usr/share/fonts/**/*.ttc",
                "/usr/share/fonts/**/*.otf",
                "/usr/local/share/fonts/**/*.ttf",
                "/usr/local/share/fonts/**/*.ttc",
                "/usr/local/share/fonts/**/*.otf",
                "~/.fonts/**/*.ttf",
                "~/.fonts/**/*.ttc",
                "~/.fonts/**/*.otf",
                "/opt/fonts/**/*.ttf",
                "/opt/fonts/**/*.ttc",
                "/opt/fonts/**/*.otf",
                "/usr/share/fonts/chinese/**/*.ttf",
                "/usr/share/fonts/chinese/**/*.ttc",
                "/usr/share/fonts/cjk/**/*.ttf",
                "/usr/share/fonts/cjk/**/*.ttc"
            ]
            
            # 中文字体关键词
            chinese_font_keywords = [
                'wqy', 'microhei', 'zenhei', 'noto', 'cjk', 'han', 'chinese',
                'simhei', 'simsun', 'yahei', 'pingfang', 'hiragino', 'arphic',
                'ukai', 'uming', 'droid', 'source', 'song', 'hei', 'kai', 'fangsong'
            ]
            
            found_fonts = []
            all_fonts = []
            
            # 先收集所有字体文件，用于调试
            for search_path in search_paths:
                try:
                    expanded_path = os.path.expanduser(search_path)
                    for font_file in glob.glob(expanded_path, recursive=True):
                        all_fonts.append(font_file)
                        font_name_lower = os.path.basename(font_file).lower()
                        if any(keyword in font_name_lower for keyword in chinese_font_keywords):
                            found_fonts.append(font_file)
                except Exception as e:
                    logger.warning(f"动态搜索字体失败: {search_path}, {e}")
                    continue
            
            logger.info(f"动态搜索发现 {len(all_fonts)} 个字体文件，其中 {len(found_fonts)} 个可能是中文字体")
            
            # 尝试加载找到的中文字体
            for font_path in found_fonts[:15]:  # 增加尝试数量
                try:
                    logger.info(f"尝试加载中文字体: {font_path}")
                    self.fonts['title'] = ImageFont.truetype(font_path, 32)
                    self.fonts['large'] = ImageFont.truetype(font_path, 20)
                    self.fonts['medium'] = ImageFont.truetype(font_path, 16)
                    self.fonts['small'] = ImageFont.truetype(font_path, 14)
                    logger.info(f"动态搜索成功加载中文字体: {font_path}")
                    return
                except Exception as e:
                    logger.warning(f"尝试加载中文字体失败: {font_path}, {e}")
                    continue  # 继续尝试下一个字体
            
            # 如果没有找到中文字体，尝试加载任何可用的字体
            if not self.fonts['title']:
                logger.info("没有找到可用的中文字体，尝试加载任何可用字体")
                for font_path in all_fonts[:15]:  # 尝试前15个字体
                    try:
                        logger.info(f"尝试加载通用字体: {font_path}")
                        self.fonts['title'] = ImageFont.truetype(font_path, 32)
                        self.fonts['large'] = ImageFont.truetype(font_path, 20)
                        self.fonts['medium'] = ImageFont.truetype(font_path, 16)
                        self.fonts['small'] = ImageFont.truetype(font_path, 14)
                        logger.info(f"动态搜索成功加载通用字体: {font_path}")
                        return
                    except Exception as e:
                        logger.warning(f"尝试加载通用字体失败: {font_path}, {e}")
                        continue  # 继续尝试下一个字体
                    
        except Exception as e:
            logger.warning(f"动态搜索字体过程异常: {e}")
            import traceback
            traceback.print_exc()
            pass  # 静默处理动态搜索失败
    
    def create_background(self, height):
        """创建背景，高度根据内容动态调整"""
        logger.info(f"开始绘制背景，高度: {height}")
        # 创建图片
        img = Image.new('RGBA', (self.width, height), color=self.colors['background'])
        draw = ImageDraw.Draw(img)
        
        # 绘制渐变背景
        for i in range(height):
            r = int(self.colors['background'][0] + (self.colors['background_gradient_end'][0] - self.colors['background'][0]) * i / height)
            g = int(self.colors['background'][1] + (self.colors['background_gradient_end'][1] - self.colors['background'][1]) * i / height)
            b = int(self.colors['background'][2] + (self.colors['background_gradient_end'][2] - self.colors['background'][2]) * i / height)
            color = (r, g, b)
            draw.line([(0, i), (self.width, i)], fill=color)
        
        logger.info("背景绘制完成")
        return img, draw
    
    def draw_header(self, draw, title="系统状态监控"):
        """绘制标题"""
        logger.info("开始绘制标题")
        # 绘制标题
        title_bbox = draw.textbbox((0, 0), title, font=self.fonts['title'])
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (self.width - title_width) // 2
        title_y = 30
        draw.text((title_x, title_y), title, fill=self.colors['text_title'], font=self.fonts['title'])
        logger.info("标题绘制完成")
        return title_y + title_bbox[3] + 20  # 增加标题下方的间距
    
    def draw_system_info(self, draw, system_info, y_pos):
        """绘制系统信息区域"""
        logger.info("开始绘制系统信息")
        
        # 区域配置
        section_y = y_pos
        
        # 生成系统信息列表
        try:
            # 获取网络流量信息
            net_io = psutil.net_io_counters()
            network_traffic = self._format_network_traffic(net_io.bytes_sent, net_io.bytes_recv)
            
            # 格式化运行时间
            uptime_formatted = self._format_uptime(system_info['uptime'])
            
            info_lines = [
                f"系统信息: {system_info['system']} {system_info['release']}",
                f"运行时间: {uptime_formatted}",
                f"系统负载: {system_info['cpu_percent']:.2f}%, {system_info['memory_percent']:.1f}%, {system_info['disk_percent']:.1f}%",
                f"网络流量: {network_traffic}",
                f"当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ]
        except Exception as e:
            logger.warning(f"生成系统信息列表时出错: {e}")
            info_lines = ["系统信息获取失败"]
        
        # 动态计算区域高度，增加行高，确保内容完整显示
        line_height = 30  # 增加行高
        section_height = 90 + len(info_lines) * line_height
        
        # 绘制背景框
        # 转换十六进制颜色字符串为RGB元组
        border_color = self.colors['border']
        if isinstance(border_color, str) and border_color.startswith('#'):
            border_color = tuple(int(border_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        draw.rounded_rectangle(
            [self.padding, section_y, self.width - self.padding, section_y + section_height],
            radius=15, 
            fill=self.colors['section_bg'], 
            outline=border_color, 
            width=2
        )
        
        # 绘制标题
        draw.text((self.padding + 20, section_y + 20), "系统信息", fill=self.colors['text_title'], font=self.fonts['large'])
        
        # 绘制系统信息
        line_y = section_y + 55
        for line in info_lines:
            draw.text((self.padding + 20, line_y), line, fill=self.colors['text_content'], font=self.fonts['medium'])
            line_y += line_height
        
        logger.info("系统信息绘制完成")
        return section_y + section_height + self.section_spacing
    
    def draw_performance(self, draw, system_info, y_pos):
        """绘制性能监控区域"""
        logger.info("开始绘制性能监控")
        
        # 区域配置
        section_y = y_pos
        section_height = 250  # 增加高度，确保性能监控区域足够容纳所有内容
        
        # 绘制背景框
        # 转换十六进制颜色字符串为RGB元组
        border_color = self.colors['border']
        if isinstance(border_color, str) and border_color.startswith('#'):
            border_color = tuple(int(border_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        draw.rounded_rectangle(
            [self.padding, section_y, self.width - self.padding, section_y + section_height],
            radius=15, 
            fill=self.colors['section_bg'], 
            outline=border_color, 
            width=2
        )
        
        # 绘制标题
        draw.text((self.padding + 20, section_y + 20), "性能监控", fill=self.colors['text_title'], font=self.fonts['large'])
        
        # 绘制圆形进度指示器
        def draw_circular_progress(center_x, center_y, radius, percentage, color, label, value_text):
            # 绘制背景圆环
            draw.ellipse(
                [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                outline='#4a5568', 
                width=8
            )
            
            # 计算进度弧度
            start_angle = -90  # 从顶部开始
            end_angle = start_angle + (percentage / 100) * 360
            
            # 使用arc方法绘制进度弧
            if percentage > 0:
                draw.arc(
                    [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                    start=start_angle, 
                    end=end_angle, 
                    fill=color, 
                    width=8
                )
            
            # 绘制中心文字
            percentage_text = f"{percentage:.1f}%"
            text_bbox = draw.textbbox((0, 0), percentage_text, font=self.fonts['medium'])
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            draw.text(
                (center_x - text_width // 2, center_y - text_height // 2), 
                percentage_text, 
                fill=self.colors['text_title'], 
                font=self.fonts['medium']
            )
            
            # 绘制标签
            label_bbox = draw.textbbox((0, 0), label, font=self.fonts['small'])
            label_width = label_bbox[2] - label_bbox[0]
            draw.text(
                (center_x - label_width // 2, center_y + radius + 10), 
                label, 
                fill=self.colors['text_content'], 
                font=self.fonts['small']
            )
            
            # 绘制数值
            value_bbox = draw.textbbox((0, 0), value_text, font=self.fonts['small'])
            value_width = value_bbox[2] - value_bbox[0]
            draw.text(
                (center_x - value_width // 2, center_y + radius + 30), 
                value_text, 
                fill=self.colors['text_content'], 
                font=self.fonts['small']
            )
        
        # 计算圆形进度指示器的位置
        center_y = section_y + 120
        radius = 60
        spacing = 150
        start_x = (self.width - (2 * spacing)) // 2
        
        # CPU使用率圆形指示器
        cpu_color = self.colors['cpu_color'] if system_info['cpu_percent'] < 70 else self.colors['cpu_warning_color']
        draw_circular_progress(
            start_x, 
            center_y, 
            radius, 
            system_info['cpu_percent'], 
            cpu_color, 
            'CPU', 
            f"{system_info['cpu_count']}核心"
        )
        
        # 内存使用率圆形指示器  
        mem_color = self.colors['mem_color'] if system_info['memory_percent'] < 80 else self.colors['mem_warning_color']
        draw_circular_progress(
            start_x + spacing, 
            center_y, 
            radius, 
            system_info['memory_percent'], 
            mem_color, 
            'MEM', 
            f"{system_info['memory_used']:.1f}G/{system_info['memory_total']:.1f}G"
        )
        
        # 主磁盘使用率圆形指示器（系统盘）
        if system_info['main_disk']:
            main_disk = system_info['main_disk']
            disk_color = self.colors['disk_color'] if main_disk['percent'] < 90 else self.colors['disk_warning_color']
            disk_label = '系统盘' if main_disk['is_system_disk'] else '主磁盘'
            draw_circular_progress(
                start_x + 2 * spacing, 
                center_y, 
                radius, 
                main_disk['percent'], 
                disk_color, 
                disk_label, 
                f"{main_disk['used']:.0f}G/{main_disk['total']:.0f}G"
            )
        
        logger.info("性能监控绘制完成")
        return section_y + section_height + self.section_spacing
    
    def draw_disk_info(self, draw, system_info, y_pos):
        """绘制磁盘信息区域"""
        logger.info("开始绘制磁盘信息")
        
        # 区域配置
        section_y = y_pos
        
        # 获取磁盘分区信息
        disk_partitions = system_info.get('disk_partitions', [])
        
        # 显示所有磁盘分区，包括系统盘
        disks_to_show = disk_partitions
        title = "磁盘分区"
        
        # 最多显示10个磁盘，避免内容过多
        disks_to_show = disks_to_show[:10]
        
        if disks_to_show:
            # 计算区域高度，增加每个磁盘的高度，提高可读性
            disk_height = 55  # 增加磁盘信息行高，确保进度条和文字有足够空间
            section_height = 90 + len(disks_to_show) * disk_height
            
            # 绘制背景框
            # 转换十六进制颜色字符串为RGB元组
            border_color = self.colors['border']
            if isinstance(border_color, str) and border_color.startswith('#'):
                border_color = tuple(int(border_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            
            draw.rounded_rectangle(
                [self.padding, section_y, self.width - self.padding, section_y + section_height],
                radius=15, 
                fill=self.colors['section_bg'], 
                outline=border_color, 
                width=2
            )
            
            # 绘制标题
            draw.text((self.padding + 20, section_y + 20), title, fill=self.colors['text_title'], font=self.fonts['large'])
            
            # 绘制磁盘列表
            disk_start_y = section_y + 55
            for i, disk in enumerate(disks_to_show):
                current_y = disk_start_y + i * disk_height
                
                # 磁盘基本信息
                # 为系统盘添加特殊标识
                system_disk_mark = self.colors['system_disk_mark'] if disk['is_system_disk'] else "   "
                # 构建磁盘名称，包含设备、挂载点和文件系统类型
                disk_name = f"{system_disk_mark}{disk['device']} ({disk['mountpoint']}) [{disk['fstype']}]"
                disk_info = f"{disk['used']:.1f}G / {disk['total']:.1f}G ({disk['percent']:.1f}%)"
                
                # 绘制磁盘名称
                draw.text((self.padding + 20, current_y), disk_name, fill=self.colors['text_content'], font=self.fonts['small'])
                
                # 绘制使用率条
                bar_width = 300  # 增加进度条宽度
                bar_height = 8  # 增加进度条高度
                bar_x = self.padding + 20  # 进度条从左侧开始
                bar_y = current_y + 20  # 进度条在磁盘名称下方
                
                # 背景条
                draw.rectangle(
                    [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
                    fill='#4a5568', 
                    outline=self.colors['border'], 
                    width=1
                )
                
                # 进度条
                progress_width = int(bar_width * (disk['percent'] / 100))
                if disk['percent'] < 60:
                    disk_bar_color = self.colors['mem_color']  # 绿色 - 使用率较低
                elif disk['percent'] < 80:
                    disk_bar_color = self.colors['mem_warning_color']  # 橙色 - 使用率中等
                elif disk['percent'] < 95:
                    disk_bar_color = self.colors['disk_warning_color']  # 红色 - 使用率较高
                else:
                    disk_bar_color = self.colors['cpu_warning_color']  # 深红色 - 使用率极高
                if progress_width > 0:
                    draw.rectangle(
                        [bar_x, bar_y, bar_x + progress_width, bar_y + bar_height],
                        fill=disk_bar_color
                    )
                
                # 绘制磁盘信息，右对齐
                info_bbox = draw.textbbox((0, 0), disk_info, font=self.fonts['small'])
                info_width = info_bbox[2] - info_bbox[0]
                draw.text((self.width - self.padding - 20, current_y), disk_info, fill=self.colors['text_content'], font=self.fonts['small'], anchor="rt")
                
                logger.info(f"绘制磁盘: {disk['device']} ({disk['percent']:.1f}%)")
        else:
            # 没有可显示的磁盘分区
            section_height = 100
            # 绘制背景框
            # 转换十六进制颜色字符串为RGB元组
            border_color = self.colors['border']
            if isinstance(border_color, str) and border_color.startswith('#'):
                border_color = tuple(int(border_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            
            draw.rounded_rectangle(
                [self.padding, section_y, self.width - self.padding, section_y + section_height],
                radius=15, 
                fill=self.colors['section_bg'], 
                outline=border_color, 
                width=2
            )
            # 绘制标题
            draw.text((self.padding + 20, section_y + 20), title, fill=self.colors['text_title'], font=self.fonts['large'])
            # 绘制提示信息
            draw.text((self.padding + 20, section_y + 55), "没有可显示的磁盘分区", fill=self.colors['text_content'], font=self.fonts['medium'])
            logger.warning("没有可显示的磁盘分区")
        
        logger.info("磁盘信息绘制完成")
        return section_y + section_height + self.section_spacing
    
    def draw_footer(self, draw, height):
        """绘制页脚，适应动态高度"""
        logger.info("开始绘制页脚")
        # 添加数据来源标识
        source_text = "数据来源: 系统监控 (psutil)"
        source_bbox = draw.textbbox((0, 0), source_text, font=self.fonts['small'])
        source_width = source_bbox[2] - source_bbox[0]
        draw.text(
            (self.width - source_width - 20, height - 30), 
            source_text, 
            fill='#718096', 
            font=self.fonts['small']
        )
        logger.info("页脚绘制完成")
    
    def generate_image(self, system_info):
        """生成完整的系统信息图片，固定高度"""
        logger.info("开始生成系统信息图片")
        
        # 使用固定高度，确保所有用户生成的图片大小一致
        final_height = 900  # 固定高度，适合各种系统信息展示
        logger.info(f"使用固定图片高度: {final_height}")
        
        # 创建背景
        img, draw = self.create_background(final_height)
        
        # 绘制标题
        y_pos = self.draw_header(draw)
        
        # 绘制系统信息
        y_pos = self.draw_system_info(draw, system_info, y_pos)
        
        # 绘制性能监控
        y_pos = self.draw_performance(draw, system_info, y_pos)
        
        # 绘制磁盘信息
        y_pos = self.draw_disk_info(draw, system_info, y_pos)
        
        # 绘制页脚
        self.draw_footer(draw, final_height)
        
        # 保存图片到内存
        logger.info("进入PNG保存阶段")
        img_data = None
        try:
            # 直接将原图转换为RGB后保存，使用最高质量设置
            rgb_img = img.convert('RGB')
            img_buffer = io.BytesIO()
            # 使用最高质量设置保存PNG
            rgb_img.save(img_buffer, format='PNG', optimize=True, compress_level=9)
            img_data = img_buffer.getvalue()
            logger.info(f"图片生成成功，字节长度: {len(img_data)}")
            if not img_data:
                raise ValueError("生成的图片字节为空")
        except Exception as e:
            logger.error(f"图片生成失败，使用备用图片: {e}")
            img_data = self._create_fallback_image("系统信息图片生成失败")
            logger.info(f"备用图片字节长度: {len(img_data) if isinstance(img_data, (bytes, bytearray)) else '非字节'}")
        
        # 最终返回保护
        if not isinstance(img_data, (bytes, bytearray)) or len(img_data) == 0:
            logger.error("最终返回保护触发：返回备用图片")
            img_data = self._create_fallback_image("系统信息图片生成失败(最终保护)")
        
        logger.info(f"图片生成完成，类型: {type(img_data)}, 长度: {len(img_data) if isinstance(img_data, (bytes, bytearray)) else 'N/A'}")
        return img_data
    
    def _format_uptime(self, seconds):
        """格式化运行时间"""
        try:
            if hasattr(seconds, 'total_seconds'):
                seconds = int(seconds.total_seconds())
            else:
                seconds = int(seconds)
            
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            minutes = (seconds % 3600) // 60
            
            if days > 0:
                return f"{days}天{hours}小时{minutes}分钟"
            elif hours > 0:
                return f"{hours}小时{minutes}分钟"
            else:
                return f"{minutes}分钟"
        except:
            return "未知"
    
    def _format_network_traffic(self, bytes_sent, bytes_recv):
        """格式化网络流量"""
        try:
            sent_mb = bytes_sent / (1024 * 1024)
            recv_mb = bytes_recv / (1024 * 1024)
            
            if sent_mb >= 1024:
                sent_str = f"{sent_mb/1024:.1f}GB"
            else:
                sent_str = f"{sent_mb:.1f}MB"
                
            if recv_mb >= 1024:
                recv_str = f"{recv_mb/1024:.1f}GB"
            else:
                recv_str = f"{recv_mb:.1f}MB"
                
            return f"↑{sent_str} ↓{recv_str}"
        except:
            return "↑0.0MB ↓0.0MB"
    
    def _create_fallback_image(self, text="系统信息图片生成失败"):
        """创建备用图片"""
        try:
            fb_img = Image.new('RGB', (600, 300), color=self.colors['background'])
            fb_draw = ImageDraw.Draw(fb_img)
            fb_draw.text((20, 20), str(text), fill=self.colors['text_title'], font=self.fonts['medium'])
            buf = io.BytesIO()
            fb_img.save(buf, format='PNG')
            buf.seek(0)
            return buf.getvalue()
        except Exception as e:
            logger.error(f"生成备用图片失败: {e}")
            return b""

@register("sysinfoimg", "Binbim", "专注于系统硬件监控的插件，生成美观的系统状态图片", "v1.1.1")
class SysInfoImgPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 创建图片生成器实例
        self.image_generator = ImageGenerator()

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        logger.info("系统信息图片插件已初始化")
    
    def get_disk_partitions_info(self):
        """获取所有磁盘分区信息"""
        import os
        partitions = []
        
        try:
            # 获取所有磁盘分区
            all_partitions = psutil.disk_partitions()
            logger.info(f"检测到 {len(all_partitions)} 个磁盘分区")
            
            # 需要跳过的伪/系统文件系统类型
            skip_fstypes = {
                'proc','sysfs','cgroup','overlay','squashfs','aufs','ramfs','tmpfs',
                'devtmpfs','devpts','mqueue','hugetlbfs','fuse','fuseblk','fuse.lxcfs',
                'pstore','securityfs','configfs','efivarfs','selinuxfs','bpf','autofs',
                'tracefs','nsfs','binfmt_misc','iso9660','nfs','cifs','smbfs'
            }
            
            # Windows系统盘识别（更稳健）
            system_drive = None
            if platform.system() == 'Windows':
                system_drive = os.environ.get('SystemDrive', 'C:') + '\\'
            
            for partition in all_partitions:
                try:
                    # 跳过伪文件系统类型
                    if partition.fstype and partition.fstype.lower() in skip_fstypes:
                        continue
                    # 跳过特殊设备名
                    if any(skip in partition.device.lower() for skip in ['loop', 'ram']):
                        continue
                    
                    # 获取分区使用情况
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    # 过滤掉小容量分区
                    total_gb = round(usage.total / (1024**3), 2)
                    if total_gb < 1:
                        continue
                    
                    # 判断是否为系统盘
                    is_system_disk = False
                    if platform.system() == 'Windows':
                        # 使用挂载点匹配系统盘盘符
                        is_system_disk = (partition.mountpoint.rstrip('\\').upper() + '\\') == (system_drive.upper())
                    else:
                        is_system_disk = partition.mountpoint == '/'
                    
                    partition_info = {
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': total_gb,
                        'used': round(usage.used / (1024**3), 2),
                        'free': round(usage.free / (1024**3), 2),
                        'percent': round(usage.percent, 2),
                        'is_system_disk': is_system_disk
                    }
                    
                    partitions.append(partition_info)
                    logger.info(f"添加磁盘分区: {partition.device} -> {partition.mountpoint} "
                              f"({total_gb}GB, 系统盘: {is_system_disk})")
                    
                except (PermissionError, OSError) as e:
                    logger.warning(f"跳过无法访问的分区 {partition.device}: {e}")
                    continue
                
        except Exception as e:
            logger.warning(f"获取磁盘分区信息时出错: {e}")
            # 回退到单磁盘模式
            try:
                if platform.system() == 'Windows':
                    disk_path = system_drive or 'C:\\'
                else:
                    disk_path = '/'
                disk = psutil.disk_usage(disk_path)
                total_gb = round(disk.total / (1024**3), 2)
                used_gb = round(disk.used / (1024**3), 2)
                partitions = [{
                    'device': disk_path,
                    'mountpoint': disk_path,
                    'fstype': 'unknown',
                    'total': total_gb,
                    'used': used_gb,
                    'free': round(disk.free / (1024**3), 2),
                    'percent': round(disk.percent if hasattr(disk, 'percent') else (disk.used / disk.total) * 100, 2),
                    'is_system_disk': True
                }]
                logger.info(f"回退到单磁盘模式: {disk_path}")
            except Exception as fallback_error:
                logger.error(f"回退磁盘信息获取失败: {fallback_error}")
                partitions = []
        
        # 排序：系统盘优先，其次按使用率降序
        partitions.sort(key=lambda d: (not d['is_system_disk'], -d['percent']))
        
        # 记录最终结果
        system_disks = [d for d in partitions if d['is_system_disk']]
        data_disks = [d for d in partitions if not d['is_system_disk']]
        logger.info(f"磁盘分区统计: 系统盘 {len(system_disks)} 个, 数据盘 {len(data_disks)} 个")
        
        return partitions
    
    def get_system_info(self):
        """获取系统信息"""
        # 获取CPU信息
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # 获取内存信息
        memory = psutil.virtual_memory()
        memory_total = round(memory.total / (1024**3), 2)  # GB
        memory_used = round(memory.used / (1024**3), 2)   # GB
        memory_percent = memory.percent
        
        # 获取磁盘信息（多硬盘）
        disk_partitions = self.get_disk_partitions_info()
        
        # 获取主磁盘信息（用于兼容性）
        main_disk = None
        if disk_partitions:
            # 优先使用系统盘，否则使用第一个磁盘
            main_disk = next((d for d in disk_partitions if d['is_system_disk']), disk_partitions[0])
        
        # 获取系统信息
        system_info = {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'hostname': platform.node(),
            'uptime': datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time()),
            'cpu_percent': cpu_percent,
            'cpu_count': cpu_count,
            'cpu_freq': cpu_freq.current if cpu_freq else 0,
            'memory_total': memory_total,
            'memory_used': memory_used,
            'memory_percent': memory_percent,
            'disk_partitions': disk_partitions,  # 多硬盘信息
            'main_disk': main_disk,  # 主磁盘信息
            # 以下字段保持兼容性
            'disk_total': main_disk['total'] if main_disk else 0,
            'disk_used': main_disk['used'] if main_disk else 0,
            'disk_percent': main_disk['percent'] if main_disk else 0
        }
        
        return system_info
    
    @filter.command("sysinfo")
    async def sysinfo(self, event: AstrMessageEvent):
        """获取系统状态并生成图片"""
        try:
            logger.info("开始获取系统信息")
            # 获取系统信息
            system_info = self.get_system_info()
            # 生成图片
            img_data = self.image_generator.generate_image(system_info)
            logger.info(f"图片生成器返回类型: {type(img_data)}, 长度: {len(img_data) if isinstance(img_data, (bytes, bytearray)) else 'N/A'}")
            # 保护：确保字节数据有效
            if not isinstance(img_data, (bytes, bytearray)) or len(img_data) == 0:
                logger.warning("图片数据无效或为空，生成备用图片")
                img_data = self.image_generator._create_fallback_image()
            # 保存图片到临时文件
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                tmp_file.write(img_data)
                tmp_file_path = tmp_file.name
            try:
                try:
                    # 尝试发送图片（适用于支持文件系统图片的平台）
                    yield event.chain_result([
                        Plain("📊 系统状态监控报告："),
                        AstrImage.fromFileSystem(tmp_file_path)
                    ])
                    logger.info("系统信息图片发送成功")
                except Exception as send_err:
                    # 在不支持文件系统图片的平台（如钉钉）回退为文本摘要
                    logger.warning(f"图片发送失败，回退为文本摘要: {send_err}")
                    summary_text = self.format_system_info_text(system_info)
                    yield event.plain_result(summary_text)
            finally:
                # 清理临时文件
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
        except Exception as e:
            logger.error(f"获取系统信息时发生错误: {e}")
            yield event.plain_result(f"❌ 获取系统信息时发生错误: {str(e)}")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        logger.info("系统信息图片插件已卸载")

    def format_system_info_text(self, system_info):
        """格式化系统信息为文本"""
        try:
            lines = []
            lines.append("📊 系统状态监控报告")
            lines.append(f"CPU: {system_info.get('cpu_usage', 0)}%")
            mem = system_info.get('memory', {})
            lines.append(f"内存: 已用 {mem.get('used_percent', 0)}% ({mem.get('used_human','')}/{mem.get('total_human','')})")
            net = system_info.get('network', {})
            lines.append(f"网络: 上行 {net.get('bytes_sent_human','')}, 下行 {net.get('bytes_recv_human','')}")
            disks = system_info.get('disks', [])
            if isinstance(disks, list) and disks:
                used_avg = round(sum(d.get('usage_percent', 0) for d in disks) / len(disks), 1)
                lines.append(f"磁盘: 平均使用 {used_avg}%")
            uptime = system_info.get('uptime_human', '')
            if uptime:
                lines.append(f"运行时间: {uptime}")
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"生成文本摘要失败: {e}")
            return