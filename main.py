# -*- coding: utf-8 -*-
import sys
import locale
import psutil
import platform
import datetime
import io
import base64
import math
import time

from PIL import Image, ImageDraw, ImageFont
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Image as AstrImage, Plain

# 移除可能导致日志冲突的编码设置
# 让AstrBot自己处理编码问题

@register("sysinfoimg", "Binbim", "专注于系统硬件监控的插件，生成美观的系统状态图片", "1.0.5")
class SysInfoImgPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

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
    


    def create_system_info_image(self, system_info):
        """创建系统信息图片"""
        logger.info("开始生成系统信息图片")
        # 参数摘要日志
        try:
            sys_summary = {
                'system': system_info.get('system'),
                'release': system_info.get('release'),
                'cpu_percent': system_info.get('cpu_percent'),
                'memory_percent': system_info.get('memory_percent'),
                'disk_percent': system_info.get('disk_percent'),
                'cpu_count': system_info.get('cpu_count'),
                'main_disk': system_info.get('main_disk')
            }
            logger.info(f"系统信息摘要: {sys_summary}")
        except Exception as e:
            logger.warning(f"记录参数摘要失败: {e}")
        # 创建图片
        width, height = 900, 650
        img = Image.new('RGBA', (width, height), color=(26, 26, 46, 255))
        draw = ImageDraw.Draw(img)
        
        # 绘制渐变背景
        for i in range(height):
            r = int(26 + (52 - 26) * i / height)  # 从深蓝到稍浅的蓝
            g = int(26 + (73 - 26) * i / height)
            b = int(46 + (94 - 46) * i / height)
            color = (r, g, b)
            draw.line([(0, i), (width, i)], fill=color)
        logger.info("背景绘制完成")
        try:
            # 尝试使用中文字体
            import os
            if platform.system() == 'Windows':
                # Windows系统尝试使用微软雅黑，指定字体索引
                font_configs = [
                    ("C:/Windows/Fonts/msyh.ttc", 0),  # 微软雅黑，索引0
                    ("C:/Windows/Fonts/simhei.ttf", None),  # 黑体
                    ("C:/Windows/Fonts/simsun.ttc", 0),  # 宋体，索引0
                    ("C:/Windows/Fonts/msyhbd.ttc", 0),  # 微软雅黑粗体，索引0
                    ("C:/Windows/Fonts/arial.ttf", None)  # 备用英文字体
                ]
            else:
                # Linux/Unix系统字体配置 - 扩展更多中文字体路径
                font_configs = [
                    # 文泉驿字体 (最常见的Linux中文字体)
                    ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", None),
                    ("/usr/share/fonts/wqy-microhei/wqy-microhei.ttc", None),
                    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", None),
                    ("/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc", None),
                    # Noto字体 (Google开源字体)
                    ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 0),
                    ("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc", 0),
                    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
                    # 思源字体
                    ("/usr/share/fonts/truetype/source-han-sans/SourceHanSansCN-Regular.otf", None),
                    ("/usr/share/fonts/opentype/source-han-sans/SourceHanSansCN-Regular.otf", None),
                    # Ubuntu/Debian常见字体
                    ("/usr/share/fonts/truetype/arphic/ukai.ttc", None),
                    ("/usr/share/fonts/truetype/arphic/uming.ttc", None),
                    # CentOS/RHEL常见字体
                    ("/usr/share/fonts/chinese/TrueType/ukai.ttf", None),
                    ("/usr/share/fonts/chinese/TrueType/uming.ttf", None),
                    # 其他可能的中文字体路径
                    ("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", None),
                    ("/usr/share/fonts/TTF/DejaVuSans.ttf", None),
                    # macOS字体
                    ("/System/Library/Fonts/PingFang.ttc", None),
                    ("/System/Library/Fonts/Hiragino Sans GB.ttc", None),
                    # 备用英文字体
                    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", None),
                    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", None),
                    ("/usr/share/fonts/TTF/arial.ttf", None)
                ]
            
            font_large = None
            font_medium = None
            font_small = None
            font_title = None
            loaded_font_path = None
            
            # 首先尝试预定义的字体路径
            for font_path, font_index in font_configs:
                if os.path.exists(font_path):
                    try:
                        if font_index is not None:
                            # 对于TTC字体文件，指定字体索引
                            font_title = ImageFont.truetype(font_path, 32, index=font_index)
                            font_large = ImageFont.truetype(font_path, 20, index=font_index)
                            font_medium = ImageFont.truetype(font_path, 16, index=font_index)
                            font_small = ImageFont.truetype(font_path, 14, index=font_index)
                        else:
                            font_title = ImageFont.truetype(font_path, 32)
                            font_large = ImageFont.truetype(font_path, 20)
                            font_medium = ImageFont.truetype(font_path, 16)
                            font_small = ImageFont.truetype(font_path, 14)
                        loaded_font_path = font_path
                        logger.info(f"成功加载字体: {font_path} (索引: {font_index})")
                        break
                    except Exception as e:
                        logger.warning(f"字体加载失败: {font_path}, {e}")
                        continue  # 静默处理字体加载失败
            
            # 如果预定义路径都失败，尝试动态搜索字体
            if not font_large and platform.system() != 'Windows':
                logger.info("预定义字体路径均失败，开始动态搜索中文字体...")
                try:
                    import glob
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
                        "~/.fonts/**/*.otf"
                    ]
                    
                    # 中文字体关键词
                    chinese_font_keywords = [
                        'wqy', 'microhei', 'zenhei', 'noto', 'cjk', 'han', 'chinese',
                        'simhei', 'simsun', 'yahei', 'pingfang', 'hiragino', 'arphic',
                        'ukai', 'uming', 'droid', 'source'
                    ]
                    
                    found_fonts = []
                    for search_path in search_paths:
                        try:
                            expanded_path = os.path.expanduser(search_path)
                            for font_file in glob.glob(expanded_path, recursive=True):
                                font_name_lower = os.path.basename(font_file).lower()
                                if any(keyword in font_name_lower for keyword in chinese_font_keywords):
                                    found_fonts.append(font_file)
                        except Exception as e:
                            logger.warning(f"动态搜索字体失败: {search_path}, {e}")
                            continue
                    
                    # 尝试加载找到的字体
                    for font_path in found_fonts[:10]:  # 限制尝试数量
                        try:
                            font_title = ImageFont.truetype(font_path, 32)
                            font_large = ImageFont.truetype(font_path, 20)
                            font_medium = ImageFont.truetype(font_path, 16)
                            font_small = ImageFont.truetype(font_path, 14)
                            loaded_font_path = font_path
                            logger.info(f"动态搜索成功加载字体: {font_path}")
                            break
                        except Exception as e:
                            logger.warning(f"尝试加载字体失败: {font_path}, {e}")
                            continue  # 静默处理失败的字体
                            
                except Exception as e:
                    logger.warning(f"动态搜索字体过程异常: {e}")
                    pass  # 静默处理动态搜索失败
                
                # 如果仍然没有加载成功，使用默认字体
                if not font_large:
                    pass  # 静默使用默认字体，避免日志过多
                # 使用PIL的默认字体
                font_title = ImageFont.load_default()
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
        except Exception as e:
            logger.error(f"字体初始化错误: {e}")
            font_title = ImageFont.load_default()
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # 确保字体对象不为None（跨平台兜底）
        if not all([font_title, font_large, font_medium, font_small]):
            font_title = ImageFont.load_default()
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        logger.info(f"字体就绪，路径: {loaded_font_path if 'loaded_font_path' in locals() else 'default'}")
        
        # 绘制主标题
        def safe_draw_text(draw_obj, position, text, fill, font, fallback_text=None):
            """安全绘制文本，如果失败则使用备用文本"""
            try:
                # 确保文本是字符串格式
                text_str = str(text)
                # 尝试编码测试
                text_str.encode('utf-8')
                
                # 测试字体是否支持该文本
                try:
                    draw_obj.textbbox((0, 0), text_str, font=font)
                    # 如果textbbox成功，尝试绘制
                    draw_obj.text(position, text_str, fill=fill, font=font)
                    return True
                except Exception as font_error:
                    # 字体不支持该文本，使用备用文本
                    if fallback_text and fallback_text != text:
                        try:
                            draw_obj.text(position, fallback_text, fill=fill, font=font)
                            return True
                        except Exception as e2:
                            pass  # 静默处理，避免日志过多
                    
                    # 如果没有备用文本或备用文本也失败，尝试只绘制ASCII字符
                    try:
                        ascii_text = ''.join(c if ord(c) < 128 else '?' for c in text_str)
                        if ascii_text != text_str:
                            draw_obj.text(position, ascii_text, fill=fill, font=font)
                            return True
                    except Exception as e3:
                        pass  # 静默处理，避免日志过多
                    
                    raise font_error
                    
            except Exception as e:
                # 最后的备用方案：绘制简单的占位符
                try:
                    placeholder = "[TEXT]" if not fallback_text else fallback_text
                    draw_obj.text(position, placeholder, fill=fill, font=font)
                    return True
                except:
                    return False  # 静默失败，避免日志过多
        
        title = "系统状态监控"
        title_bbox = draw.textbbox((0, 0), title, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        safe_draw_text(draw, ((width - title_width) // 2, 30), title, '#ffffff', font_title, "System Monitor")
        
        # 调用绘制系统信息区域
        self.draw_system_info_section(draw, system_info, font_large, font_medium, safe_draw_text)
        
        # 调用绘制性能监控区域
        self.draw_performance_section(draw, system_info, font_medium, font_small)
        
        # 调用绘制数据磁盘区域
        self.draw_data_disks_section(draw, system_info, font_large, font_small, safe_draw_text, width)
        
        # 添加数据来源标识
        source_text = "数据来源: 系统监控 (psutil)"
        source_text_en = "Data Source: System Monitor (psutil)"
        source_bbox = draw.textbbox((0, 0), source_text, font=font_small)
        source_width = source_bbox[2] - source_bbox[0]
        safe_draw_text(draw, (width - source_width - 20, height - 30), source_text, 
                      '#718096', font_small, source_text_en)
        
        # 保存图片到内存 - 稳健的RGBA合成后保存PNG
        logger.info("进入PNG保存阶段")
        img_data = None
        try:
            base_rgba = Image.new('RGBA', (width, height), color=(26, 26, 46, 255))
            composed = Image.alpha_composite(base_rgba, img)
            rgb_img = composed.convert('RGB')
            img_buffer = io.BytesIO()
            rgb_img.save(img_buffer, format='PNG')
            img_data = img_buffer.getvalue()
            logger.info(f"图片生成成功（alpha合成），字节长度: {len(img_data)}")
            if not img_data:
                raise ValueError("生成的图片字节为空")
        except Exception as e:
            logger.warning(f"alpha合成保存失败，尝试直接保存RGB：{e}")
            try:
                # 备用方案：直接将原图转换为RGB后保存
                direct_rgb = img.convert('RGB')
                buf2 = io.BytesIO()
                direct_rgb.save(buf2, format='PNG')
                img_data = buf2.getvalue()
                logger.info(f"图片生成成功（直接RGB），字节长度: {len(img_data)}")
                if not img_data:
                    raise ValueError("生成的图片字节为空(直接RGB)")
            except Exception as e2:
                logger.error(f"图片生成完全失败，使用备用图片: {e2}")
                img_data = self.create_fallback_image("系统信息图片生成失败")
                logger.info(f"备用图片字节长度: {len(img_data) if isinstance(img_data, (bytes, bytearray)) else '非字节'}")
        # 最终返回保护
        if not isinstance(img_data, (bytes, bytearray)) or len(img_data) == 0:
            logger.error("最终返回保护触发：返回备用图片")
            img_data = self.create_fallback_image("系统信息图片生成失败(最终保护)")
        logger.info(f"create_system_info_image 即将返回，类型: {type(img_data)}, 长度: {len(img_data) if isinstance(img_data, (bytes, bytearray)) else 'N/A'}")
        return img_data

    def format_uptime(self, seconds):
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
    
    def format_network_traffic(self, bytes_sent, bytes_recv):
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

    def draw_system_info_section(self, draw, system_info, font_large, font_medium, safe_draw_text):
        """绘制系统基本信息区域"""
        info_y = 100
        width = 900
        
        # 绘制系统信息背景框
        info_box_height = 180
        draw.rounded_rectangle([40, info_y, width-40, info_y + info_box_height], 
                             radius=15, fill=(255, 255, 255, 25), outline='#4a5568', width=2)
        
        # 系统信息标题
        safe_draw_text(draw, (60, info_y + 15), "系统信息", '#e2e8f0', font_large, "System Info")
        
        # 处理器信息
        processor_info = system_info['processor'] or '未知'
        if len(processor_info) > 40:
            processor_info = processor_info[:40] + "..."
        
        # 生成系统信息列表
        try:
            # 获取网络流量信息
            net_io = psutil.net_io_counters()
            network_traffic = self.format_network_traffic(net_io.bytes_sent, net_io.bytes_recv)
            
            # 格式化运行时间
            uptime_formatted = self.format_uptime(system_info['uptime'])
            
            info_lines_cn = [
                f"系统信息: {system_info['system']} {system_info['release']}",
                f"运行时间: {uptime_formatted}",
                f"系统负载: {system_info['cpu_percent']:.2f}%, {system_info['memory_percent']:.1f}%, {system_info['disk_percent']:.1f}%",
                f"网络流量: {network_traffic}",
                f"当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ]
            info_lines_en = [
                f"System: {system_info['system']} {system_info['release']}",
                f"Uptime: {uptime_formatted}",
                f"Load: {system_info['cpu_percent']:.2f}%, {system_info['memory_percent']:.1f}%, {system_info['disk_percent']:.1f}%",
                f"Network: {network_traffic}",
                f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ]
        except Exception as e:
            logger.warning(f"生成信息列表时出错: {e}")
            # 使用简化的英文备用
            info_lines_cn = ["System information unavailable"]
            info_lines_en = ["System information unavailable"]
        
        y_pos = info_y + 50
        for i, (line_cn, line_en) in enumerate(zip(info_lines_cn, info_lines_en)):
            safe_draw_text(draw, (60, y_pos), line_cn, '#cbd5e0', font_medium, line_en)
            y_pos += 25
        logger.info("系统基本信息区域绘制完成")
        
    def draw_performance_section(self, draw, system_info, font_medium, font_small):
        """绘制性能监控区域"""
        monitor_y = 320
        
        # 绘制圆形进度指示器
        def draw_circular_progress(center_x, center_y, radius, percentage, color, label, value_text):
            # 绘制背景圆环
            draw.ellipse([center_x - radius, center_y - radius, center_x + radius, center_y + radius], 
                        outline='#4a5568', width=8)
            
            # 计算进度弧度
            start_angle = -90  # 从顶部开始
            arc_length = int((percentage / 100) * 360)
            
            # 绘制进度弧（使用多个小弧段来模拟）
            if percentage > 0:
                for i in range(arc_length):  # 每度一个点
                    angle = math.radians(start_angle + i)
                    x1 = center_x + (radius - 4) * math.cos(angle)
                    y1 = center_y + (radius - 4) * math.sin(angle)
                    x2 = center_x + (radius + 4) * math.cos(angle)
                    y2 = center_y + (radius + 4) * math.sin(angle)
                    draw.line([x1, y1, x2, y2], fill=color, width=8)
            
            # 绘制中心文字
            percentage_text = f"{percentage:.1f}%"
            text_bbox = draw.textbbox((0, 0), percentage_text, font=font_medium)
            text_width = text_bbox[2] - text_bbox[0]
            draw.text((center_x - text_width // 2, center_y - 10), percentage_text, 
                     fill='#ffffff', font=font_medium)
            
            # 绘制标签
            label_bbox = draw.textbbox((0, 0), label, font=font_small)
            label_width = label_bbox[2] - label_bbox[0]
            draw.text((center_x - label_width // 2, center_y + radius + 15), label, 
                     fill='#e2e8f0', font=font_small)
            
            # 绘制数值
            value_bbox = draw.textbbox((0, 0), value_text, font=font_small)
            value_width = value_bbox[2] - value_bbox[0]
            draw.text((center_x - value_width // 2, center_y + radius + 35), value_text, 
                     fill='#a0aec0', font=font_small)
        
        # CPU使用率圆形指示器
        cpu_color = '#4299e1' if system_info['cpu_percent'] < 70 else '#f56565'
        draw_circular_progress(200, monitor_y + 80, 60, system_info['cpu_percent'], 
                             cpu_color, 'CPU', f"{system_info['cpu_count']}核心")
        
        # 内存使用率圆形指示器  
        mem_color = '#48bb78' if system_info['memory_percent'] < 80 else '#ed8936'
        draw_circular_progress(450, monitor_y + 80, 60, system_info['memory_percent'], 
                             mem_color, 'MEM', 
                             f"{system_info['memory_used']:.1f}G/{system_info['memory_total']:.1f}G")
        
        # 主磁盘使用率圆形指示器（系统盘）
        if system_info['main_disk']:
            main_disk = system_info['main_disk']
            disk_color = '#9f7aea' if main_disk['percent'] < 90 else '#e53e3e'
            disk_label = '系统盘' if main_disk['is_system_disk'] else '主磁盘'
            disk_label_en = 'System Disk' if main_disk['is_system_disk'] else 'Main Disk'
            draw_circular_progress(700, monitor_y + 80, 60, main_disk['percent'], 
                                 disk_color, disk_label, 
                                 f"{main_disk['used']:.0f}G/{main_disk['total']:.0f}G")
        logger.info("性能监控区域绘制完成")
    def draw_data_disks_section(self, draw, system_info, font_large, font_small, safe_draw_text, width):
        """绘制数据磁盘区域"""
        monitor_y = 320
        
        # 绘制多硬盘信息区域
        disk_partitions = system_info.get('disk_partitions', [])
        data_disks = [d for d in disk_partitions if not d['is_system_disk']]
        
        # 如果没有数据磁盘，显示所有磁盘（除了第一个系统磁盘）
        disks_to_show = data_disks
        title = "数据磁盘"
        
        if not data_disks:
            # 如果没有数据磁盘，显示所有磁盘
            disks_to_show = disk_partitions[1:] if len(disk_partitions) > 1 else disk_partitions
            title = "磁盘分区"
            logger.info("没有检测到数据磁盘，显示所有磁盘分区")
        
        if disks_to_show:
            disks_y = monitor_y + 180
            
            # 绘制磁盘标题
            safe_draw_text(draw, (60, disks_y), title, '#e2e8f0', font_large, "Disk Partitions")
            
            # 绘制磁盘列表
            disk_start_y = disks_y + 40
            for i, disk in enumerate(disks_to_show[:4]):  # 最多显示4个磁盘
                y_pos = disk_start_y + i * 25
                
                # 磁盘基本信息
                disk_name = f"{disk['device']} ({disk['mountpoint']})"
                disk_info = f"{disk['used']:.1f}G / {disk['total']:.1f}G ({disk['percent']:.1f}%)"
                
                # 绘制磁盘名称
                safe_draw_text(draw, (60, y_pos), disk_name, '#cbd5e0', font_small, disk['device'])
                
                # 绘制磁盘信息
                info_bbox = draw.textbbox((0, 0), disk_info, font=font_small)
                info_width = info_bbox[2] - info_bbox[0]
                safe_draw_text(draw, (width - info_width - 60, y_pos), disk_info, '#cbd5e0', font_small, disk_info)
                
                # 绘制使用率条
                bar_width = 200
                bar_height = 6
                bar_x = width - info_width - 80 - bar_width
                bar_y = y_pos + 8
                
                # 背景条
                draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], 
                             fill='#2d3748', outline='#4a5568', width=1)
                
                # 进度条
                progress_width = int(bar_width * (disk['percent'] / 100))
                disk_bar_color = '#48bb78' if disk['percent'] < 80 else '#ed8936' if disk['percent'] < 90 else '#e53e3e'
                if progress_width > 0:
                    draw.rectangle([bar_x, bar_y, bar_x + progress_width, bar_y + bar_height], 
                                 fill=disk_bar_color)
                
                logger.info(f"绘制磁盘: {disk['device']} ({disk['percent']:.1f}%)")
        else:
            logger.warning("没有可显示的磁盘分区")
        
        logger.info("数据磁盘区域绘制完成")

    
    def create_fallback_image(self, text="系统信息图片生成失败"):
        try:
            fb_img = Image.new('RGB', (600, 300), color=(26, 26, 46))
            fb_draw = ImageDraw.Draw(fb_img)
            fb_font = ImageFont.load_default()
            fb_draw.text((20, 20), str(text), fill='#ffffff', font=fb_font)
            buf = io.BytesIO()
            fb_img.save(buf, format='PNG')
            buf.seek(0)
            return buf.getvalue()
        except Exception as e:
            logger.error(f"生成备用图片失败: {e}")
            return b""
    
    @filter.command("sysinfo")
    async def sysinfo(self, event: AstrMessageEvent):
        """获取系统状态并生成图片""" 
        try:
            logger.info("开始获取系统信息")
            # 获取系统信息
            system_info = self.get_system_info()
            # 生成图片
            img_data = self.create_system_info_image(system_info)
            logger.info(f"create_system_info_image返回类型: {type(img_data)}, 长度: {len(img_data) if isinstance(img_data, (bytes, bytearray)) else 'N/A'}")
            # 保护：确保字节数据有效
            if not isinstance(img_data, (bytes, bytearray)) or len(img_data) == 0:
                logger.warning("图片数据无效或为空，生成备用图片")
                img_data = self.create_fallback_image()
            # 保存图片到临时文件
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                tmp_file.write(img_data)
                tmp_file_path = tmp_file.name
            try:
                # 发送图片消息
                yield event.chain_result([
                    Plain("📊 系统状态监控报告："),
                    AstrImage.fromFileSystem(tmp_file_path)
                ])
            finally:
                # 清理临时文件
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
            logger.info("系统信息图片发送成功")
        except Exception as e:
            logger.error(f"获取系统信息时发生错误: {e}")
            yield event.plain_result(f"❌ 获取系统信息时发生错误: {str(e)}")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        logger.info("系统信息图片插件已卸载")
