# -*- coding: utf-8 -*-
"""
图片渲染器模块
"""
import logging
import datetime
from PIL import ImageDraw, ImageFont
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class BaseRenderer:
    """渲染器基类"""
    
    def __init__(self, config):
        """初始化渲染器
        
        Args:
            config: 配置管理器实例
        """
        self.config = config
        self.colors = config.get("image_style.colors", {})
        self.font_sizes = config.get("image_style.fonts", {})
        self.layout = config.get("image_style.layout", {})
        self.fonts = {}
    
    def set_fonts(self, fonts: Dict[str, ImageFont.FreeTypeFont]) -> None:
        """设置字体
        
        Args:
            fonts: 字体字典
        """
        self.fonts = fonts

class SystemInfoRenderer(BaseRenderer):
    """系统信息渲染器"""
    
    def draw(self, draw: ImageDraw.ImageDraw, system_info: Dict[str, Any], y_pos: int, width: int) -> int:
        """绘制系统信息区域
        
        Args:
            draw: 绘图对象
            system_info: 系统信息字典
            y_pos: 起始y坐标
            width: 图片宽度
            
        Returns:
            结束y坐标
        """
        logger.info("开始绘制系统信息")
        
        padding = self.layout.get("padding", 40)
        section_spacing = self.layout.get("section_spacing", 25)
        
        # 区域配置
        section_y = y_pos
        
        # 生成系统信息列表
        try:
            # 获取网络流量信息
            import psutil
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
        fill_color = self.colors.get("section_bg", (38, 38, 68))
        border_color = self.colors.get("border", "#667eea")
        
        # 确保fill_color是元组
        if isinstance(fill_color, list):
            fill_color = tuple(fill_color)
        
        # 转换十六进制颜色字符串为RGB元组
        if isinstance(border_color, str) and border_color.startswith("#"):
            border_color = tuple(int(border_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        # 确保border_color是元组
        elif isinstance(border_color, list):
            border_color = tuple(border_color)
        
        draw.rounded_rectangle(
            [padding, section_y, width - padding, section_y + section_height],
            radius=15, 
            fill=fill_color, 
            outline=border_color, 
            width=2
        )
        
        # 绘制标题
        draw.text((padding + 20, section_y + 20), "系统信息", fill=self.colors.get("text_title", "#ffffff"), font=self.fonts['large'])
        
        # 绘制系统信息
        line_y = section_y + 55
        for line in info_lines:
            draw.text((padding + 20, line_y), line, fill=self.colors.get("text_content", "#e2e8f0"), font=self.fonts['medium'])
            line_y += line_height
        
        logger.info("系统信息绘制完成")
        return section_y + section_height + section_spacing
    
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

class PerformanceRenderer(BaseRenderer):
    """性能监控渲染器"""
    
    def draw(self, draw: ImageDraw.ImageDraw, system_info: Dict[str, Any], y_pos: int, width: int) -> int:
        """绘制性能监控区域
        
        Args:
            draw: 绘图对象
            system_info: 系统信息字典
            y_pos: 起始y坐标
            width: 图片宽度
            
        Returns:
            结束y坐标
        """
        logger.info("开始绘制性能监控")
        
        padding = self.layout.get("padding", 40)
        section_spacing = self.layout.get("section_spacing", 25)
        
        # 区域配置
        section_y = y_pos
        section_height = 250  # 增加高度，确保性能监控区域足够容纳所有内容
        
        # 绘制背景框
        fill_color = self.colors.get("section_bg", (38, 38, 68))
        border_color = self.colors.get("border", "#667eea")
        
        # 确保fill_color是元组
        if isinstance(fill_color, list):
            fill_color = tuple(fill_color)
        
        # 转换十六进制颜色字符串为RGB元组
        if isinstance(border_color, str) and border_color.startswith("#"):
            border_color = tuple(int(border_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        # 确保border_color是元组
        elif isinstance(border_color, list):
            border_color = tuple(border_color)
        
        draw.rounded_rectangle(
            [padding, section_y, width - padding, section_y + section_height],
            radius=15, 
            fill=fill_color, 
            outline=border_color, 
            width=2
        )
        
        # 绘制标题
        draw.text((padding + 20, section_y + 20), "性能监控", fill=self.colors.get("text_title", "#ffffff"), font=self.fonts['large'])
        
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
                fill=self.colors.get("text_title", "#ffffff"), 
                font=self.fonts['medium']
            )
            
            # 绘制标签
            label_bbox = draw.textbbox((0, 0), label, font=self.fonts['small'])
            label_width = label_bbox[2] - label_bbox[0]
            draw.text(
                (center_x - label_width // 2, center_y + radius + 10), 
                label, 
                fill=self.colors.get("text_content", "#e2e8f0"), 
                font=self.fonts['small']
            )
            
            # 绘制数值
            value_bbox = draw.textbbox((0, 0), value_text, font=self.fonts['small'])
            value_width = value_bbox[2] - value_bbox[0]
            draw.text(
                (center_x - value_width // 2, center_y + radius + 30), 
                value_text, 
                fill=self.colors.get("text_content", "#e2e8f0"), 
                font=self.fonts['small']
            )
        
        # 计算圆形进度指示器的位置
        center_y = section_y + 120
        radius = 60
        spacing = 150
        start_x = (width - (2 * spacing)) // 2
        
        # CPU使用率圆形指示器
        cpu_color = self.colors.get("cpu_color", "#4299e1") if system_info['cpu_percent'] < 70 else self.colors.get("cpu_warning_color", "#f56565")
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
        mem_color = self.colors.get("mem_color", "#48bb78") if system_info['memory_percent'] < 80 else self.colors.get("mem_warning_color", "#ed8936")
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
            disk_color = self.colors.get("disk_color", "#9f7aea") if main_disk['percent'] < 90 else self.colors.get("disk_warning_color", "#e53e3e")
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
        return section_y + section_height + section_spacing

class DiskInfoRenderer(BaseRenderer):
    """磁盘信息渲染器"""
    
    def draw(self, draw: ImageDraw.ImageDraw, system_info: Dict[str, Any], y_pos: int, width: int) -> int:
        """绘制磁盘信息区域
        
        Args:
            draw: 绘图对象
            system_info: 系统信息字典
            y_pos: 起始y坐标
            width: 图片宽度
            
        Returns:
            结束y坐标
        """
        logger.info("开始绘制磁盘信息")
        
        padding = self.layout.get("padding", 40)
        section_spacing = self.layout.get("section_spacing", 25)
        
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
            fill_color = self.colors.get("section_bg", (38, 38, 68))
            border_color = self.colors.get("border", "#667eea")
            
            # 确保fill_color是元组
            if isinstance(fill_color, list):
                fill_color = tuple(fill_color)
            
            # 转换十六进制颜色字符串为RGB元组
            if isinstance(border_color, str) and border_color.startswith("#"):
                border_color = tuple(int(border_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            # 确保border_color是元组
            elif isinstance(border_color, list):
                border_color = tuple(border_color)
            
            draw.rounded_rectangle(
                [padding, section_y, width - padding, section_y + section_height],
                radius=15, 
                fill=fill_color, 
                outline=border_color, 
                width=2
            )
            
            # 绘制标题
            draw.text((padding + 20, section_y + 20), title, fill=self.colors.get("text_title", "#ffffff"), font=self.fonts['large'])
            
            # 绘制磁盘列表
            disk_start_y = section_y + 55
            for i, disk in enumerate(disks_to_show):
                current_y = disk_start_y + i * disk_height
                
                # 磁盘基本信息
                # 为系统盘添加特殊标识
                system_disk_mark = self.colors.get("system_disk_mark", "⭐ ") if disk['is_system_disk'] else "   "
                # 构建磁盘名称，包含设备、挂载点和文件系统类型
                disk_name = f"{system_disk_mark}{disk['device']} ({disk['mountpoint']}) [{disk['fstype']}]"
                disk_info = f"{disk['used']:.1f}G / {disk['total']:.1f}G ({disk['percent']:.1f}%)"
                
                # 绘制磁盘名称
                draw.text((padding + 20, current_y), disk_name, fill=self.colors.get("text_content", "#e2e8f0"), font=self.fonts['small'])
                
                # 绘制使用率条
                bar_width = 300  # 增加进度条宽度
                bar_height = 8  # 增加进度条高度
                bar_x = padding + 20  # 进度条从左侧开始
                bar_y = current_y + 20  # 进度条在磁盘名称下方
                
                # 背景条
                draw.rectangle(
                    [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
                    fill='#4a5568', 
                    outline=self.colors.get("border", "#667eea"), 
                    width=1
                )
                
                # 进度条
                progress_width = int(bar_width * (disk['percent'] / 100))
                if disk['percent'] < 60:
                    disk_bar_color = self.colors.get("mem_color", "#48bb78")  # 绿色 - 使用率较低
                elif disk['percent'] < 80:
                    disk_bar_color = self.colors.get("mem_warning_color", "#ed8936")  # 橙色 - 使用率中等
                elif disk['percent'] < 95:
                    disk_bar_color = self.colors.get("disk_warning_color", "#e53e3e")  # 红色 - 使用率较高
                else:
                    disk_bar_color = self.colors.get("cpu_warning_color", "#f56565")  # 深红色 - 使用率极高
                if progress_width > 0:
                    draw.rectangle(
                        [bar_x, bar_y, bar_x + progress_width, bar_y + bar_height],
                        fill=disk_bar_color
                    )
                
                # 绘制磁盘信息，右对齐
                info_bbox = draw.textbbox((0, 0), disk_info, font=self.fonts['small'])
                info_width = info_bbox[2] - info_bbox[0]
                draw.text((width - padding - 20, current_y), disk_info, fill=self.colors.get("text_content", "#e2e8f0"), font=self.fonts['small'], anchor="rt")
                
                logger.info(f"绘制磁盘: {disk['device']} ({disk['percent']:.1f}%)")
        else:
            # 没有可显示的磁盘分区
            section_height = 100
            # 绘制背景框
            fill_color = self.colors.get("section_bg", (38, 38, 68))
            border_color = self.colors.get("border", "#667eea")
            
            # 确保fill_color是元组
            if isinstance(fill_color, list):
                fill_color = tuple(fill_color)
            
            # 转换十六进制颜色字符串为RGB元组
            if isinstance(border_color, str) and border_color.startswith("#"):
                border_color = tuple(int(border_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            # 确保border_color是元组
            elif isinstance(border_color, list):
                border_color = tuple(border_color)
            
            draw.rounded_rectangle(
                [padding, section_y, width - padding, section_y + section_height],
                radius=15, 
                fill=fill_color, 
                outline=border_color, 
                width=2
            )
            # 绘制标题
            draw.text((padding + 20, section_y + 20), title, fill=self.colors.get("text_title", "#ffffff"), font=self.fonts['large'])
            # 绘制提示信息
            draw.text((padding + 20, section_y + 55), "没有可显示的磁盘分区", fill=self.colors.get("text_content", "#e2e8f0"), font=self.fonts['medium'])
            logger.warning("没有可显示的磁盘分区")
        
        logger.info("磁盘信息绘制完成")
        return section_y + section_height + section_spacing

class WebPanelStatsRenderer(BaseRenderer):
    """Web面板统计信息渲染器"""
    
    def draw(self, draw: ImageDraw.ImageDraw, panel_data: Dict[str, Any], y_pos: int, width: int) -> int:
        """绘制Web面板统计信息
        
        Args:
            draw: 绘图对象
            panel_data: Web面板数据字典
            y_pos: 起始y坐标
            width: 图片宽度
            
        Returns:
            结束y坐标
        """
        logger.info("开始绘制Web面板统计信息")
        
        padding = self.layout.get("padding", 40)
        section_spacing = self.layout.get("section_spacing", 25)
        
        # 区域配置
        section_y = y_pos
        
        # 生成统计信息列表
        stats = panel_data.get("stats", {})
        status = panel_data.get("status", {})
        
        info_lines = []
        
        # 添加状态信息
        if status:
            bot_status = "在线" if status.get("online", False) else "离线"
            info_lines.append(f"机器人状态: {bot_status}")
            if "uptime" in status:
                info_lines.append(f"机器人运行时间: {self._format_uptime(status['uptime'])}")
        
        # 添加统计信息
        if stats:
            if "message_count" in stats:
                info_lines.append(f"消息总数: {stats['message_count']}")
            if "user_count" in stats:
                info_lines.append(f"用户数量: {stats['user_count']}")
            if "plugin_count" in stats:
                info_lines.append(f"插件数量: {stats['plugin_count']}")
        
        if not info_lines:
            info_lines = ["Web面板数据获取失败"]
        
        # 动态计算区域高度
        line_height = 30
        section_height = 90 + len(info_lines) * line_height
        
        # 绘制背景框
        fill_color = self.colors.get("section_bg", (38, 38, 68))
        border_color = self.colors.get("border", "#667eea")
        
        # 确保fill_color是元组
        if isinstance(fill_color, list):
            fill_color = tuple(fill_color)
        
        # 转换十六进制颜色字符串为RGB元组
        if isinstance(border_color, str) and border_color.startswith("#"):
            border_color = tuple(int(border_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        # 确保border_color是元组
        elif isinstance(border_color, list):
            border_color = tuple(border_color)
        
        draw.rounded_rectangle(
            [padding, section_y, width - padding, section_y + section_height],
            radius=15, 
            fill=fill_color, 
            outline=border_color, 
            width=2
        )
        
        # 绘制标题
        draw.text((padding + 20, section_y + 20), "机器人统计", fill=self.colors.get("text_title", "#ffffff"), font=self.fonts['large'])
        
        # 绘制统计信息
        line_y = section_y + 55
        for line in info_lines:
            draw.text((padding + 20, line_y), line, fill=self.colors.get("text_content", "#e2e8f0"), font=self.fonts['medium'])
            line_y += line_height
        
        logger.info("Web面板统计信息绘制完成")
        return section_y + section_height + section_spacing
    
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

class HeaderRenderer(BaseRenderer):
    """标题渲染器"""
    
    def draw(self, draw: ImageDraw.ImageDraw, title: str = "系统状态监控") -> int:
        """绘制标题
        
        Args:
            draw: 绘图对象
            title: 标题文本
            
        Returns:
            结束y坐标
        """
        logger.info("开始绘制标题")
        
        # 绘制标题
        title_bbox = draw.textbbox((0, 0), title, font=self.fonts['title'])
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (self.config.get("image_style.width", 900) - title_width) // 2
        title_y = 30
        draw.text((title_x, title_y), title, fill=self.colors.get("text_title", "#ffffff"), font=self.fonts['title'])
        
        logger.info("标题绘制完成")
        return title_y + (title_bbox[3] - title_bbox[1]) + 40  # 增加标题下方的间距，使用正确的文本高度计算

class FooterRenderer(BaseRenderer):
    """页脚渲染器"""
    
    def draw(self, draw: ImageDraw.ImageDraw, height: int, width: int) -> None:
        """绘制页脚
        
        Args:
            draw: 绘图对象
            height: 图片高度
            width: 图片宽度
        """
        logger.info("开始绘制页脚")
        
        # 添加数据来源标识
        source_text = "数据来源: 系统监控 (psutil)"
        source_bbox = draw.textbbox((0, 0), source_text, font=self.fonts['small'])
        source_width = source_bbox[2] - source_bbox[0]
        draw.text(
            (width - source_width - 20, height - 30), 
            source_text, 
            fill='#718096', 
            font=self.fonts['small']
        )
        
        logger.info("页脚绘制完成")
