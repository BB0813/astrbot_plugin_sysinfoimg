# -*- coding: utf-8 -*-
"""
图片合成器模块
"""
import logging
import platform
import os
import io
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, Optional

from config import ConfigManager
from background import BackgroundRenderer
from renderers import (
    SystemInfoRenderer,
    PerformanceRenderer,
    DiskInfoRenderer,
    WebPanelStatsRenderer,
    HeaderRenderer,
    FooterRenderer
)
from web_panel import WebPanelDataFetcher

logger = logging.getLogger(__name__)

class ImageComposer:
    """图片合成器，负责组合所有渲染器生成最终图片"""
    
    def __init__(self, config_path: str = "config.json"):
        """初始化图片合成器
        
        Args:
            config_path: 配置文件路径
        """
        # 初始化配置管理器
        self.config = ConfigManager(config_path)
        
        # 初始化各个组件
        self.background_renderer = BackgroundRenderer(self.config)
        self.web_panel_fetcher = WebPanelDataFetcher(self.config)
        
        # 初始化渲染器
        self.system_info_renderer = SystemInfoRenderer(self.config)
        self.performance_renderer = PerformanceRenderer(self.config)
        self.disk_info_renderer = DiskInfoRenderer(self.config)
        self.web_panel_stats_renderer = WebPanelStatsRenderer(self.config)
        self.header_renderer = HeaderRenderer(self.config)
        self.footer_renderer = FooterRenderer(self.config)
        
        # 加载字体
        self.fonts = self._load_fonts()
        
        # 设置渲染器字体
        for renderer in [
            self.system_info_renderer,
            self.performance_renderer,
            self.disk_info_renderer,
            self.web_panel_stats_renderer,
            self.header_renderer,
            self.footer_renderer
        ]:
            renderer.set_fonts(self.fonts)
    
    def _load_fonts(self) -> Dict[str, ImageFont.FreeTypeFont]:
        """加载字体
        
        Returns:
            字体字典
        """
        logger.info("开始加载字体")
        
        font_sizes = self.config.get("image_style.fonts", {})
        title_size = font_sizes.get("title_size", 32)
        large_size = font_sizes.get("large_size", 20)
        medium_size = font_sizes.get("medium_size", 16)
        small_size = font_sizes.get("small_size", 14)
        
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
                # Noto字体 (Google开源字体)
                ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 0),
                ("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc", 0),
                ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
                # 思源字体
                ("/usr/share/fonts/truetype/source-han-sans/SourceHanSansCN-Regular.otf", None),
            ]
        
        loaded_font_path = None
        fonts = {}
        
        # 尝试加载字体
        for font_path, font_index in font_configs:
            if os.path.exists(font_path):
                try:
                    if font_index is not None:
                        # 对于TTC字体文件，指定字体索引
                        fonts['title'] = ImageFont.truetype(font_path, title_size, index=font_index)
                        fonts['large'] = ImageFont.truetype(font_path, large_size, index=font_index)
                        fonts['medium'] = ImageFont.truetype(font_path, medium_size, index=font_index)
                        fonts['small'] = ImageFont.truetype(font_path, small_size, index=font_index)
                    else:
                        fonts['title'] = ImageFont.truetype(font_path, title_size)
                        fonts['large'] = ImageFont.truetype(font_path, large_size)
                        fonts['medium'] = ImageFont.truetype(font_path, medium_size)
                        fonts['small'] = ImageFont.truetype(font_path, small_size)
                    loaded_font_path = font_path
                    logger.info(f"成功加载字体: {font_path} (索引: {font_index})")
                    break
                except Exception as e:
                    logger.warning(f"字体加载失败: {font_path}, {e}")
                    continue  # 静默处理字体加载失败
        
        # 如果预定义路径都失败，尝试动态搜索字体
        if not fonts and platform.system() != 'Windows':
            logger.info("预定义字体路径均失败，开始动态搜索中文字体...")
            fonts = self._search_fonts(title_size, large_size, medium_size, small_size)
        
        # 确保字体对象不为None（跨平台兜底）
        if not all(fonts.values()):
            logger.warning("部分字体加载失败，使用默认字体")
            fonts['title'] = ImageFont.load_default()
            fonts['large'] = ImageFont.load_default()
            fonts['medium'] = ImageFont.load_default()
            fonts['small'] = ImageFont.load_default()
        
        logger.info(f"字体加载完成，路径: {loaded_font_path if loaded_font_path else 'default'}")
        return fonts
    
    def _search_fonts(self, title_size: int, large_size: int, medium_size: int, small_size: int) -> Dict[str, ImageFont.FreeTypeFont]:
        """动态搜索字体
        
        Args:
            title_size: 标题字体大小
            large_size: 大字体大小
            medium_size: 中字体大小
            small_size: 小字体大小
            
        Returns:
            字体字典
        """
        fonts = {}
        
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
                    fonts['title'] = ImageFont.truetype(font_path, title_size)
                    fonts['large'] = ImageFont.truetype(font_path, large_size)
                    fonts['medium'] = ImageFont.truetype(font_path, medium_size)
                    fonts['small'] = ImageFont.truetype(font_path, small_size)
                    logger.info(f"动态搜索成功加载字体: {font_path}")
                    return fonts
                except Exception as e:
                    logger.warning(f"尝试加载字体失败: {font_path}, {e}")
                    continue  # 静默处理失败的字体
                    
        except Exception as e:
            logger.warning(f"动态搜索字体过程异常: {e}")
            pass  # 静默处理动态搜索失败
        
        return fonts
    
    def generate_image(self, system_info: Dict[str, Any]) -> bytes:
        """生成完整的系统信息图片
        
        Args:
            system_info: 系统信息字典
            
        Returns:
            生成的图片字节数据
        """
        logger.info("开始生成系统信息图片")
        
        width = self.config.get("image_style.width", 900)
        base_height = self.config.get("image_style.base_height", 800)
        
        # 预计算各部分高度，确定最终图片高度
        logger.info("开始预计算图片高度")
        
        # 估算各部分高度
        header_height = 100  # 标题高度
        system_info_height = 240  # 系统信息高度
        performance_height = 245  # 性能监控高度
        disk_height = 135 + len(system_info.get('disk_partitions', [])) * 45  # 磁盘信息高度
        web_panel_height = 160 if self.config.get("web_panel.enabled") else 0  # Web面板统计高度
        footer_height = 40  # 页脚高度
        
        # 计算总高度
        total_height = header_height + system_info_height + performance_height + disk_height + web_panel_height + footer_height
        
        # 确保总高度不小于基础高度
        final_height = max(total_height, base_height)
        logger.info(f"预计算完成，总高度: {total_height}, 最终高度: {final_height}")
        
        # 创建背景
        img, draw = self.background_renderer.create_background(width, final_height)
        
        # 绘制标题
        y_pos = self.header_renderer.draw(draw)
        
        # 绘制系统信息
        y_pos = self.system_info_renderer.draw(draw, system_info, y_pos, width)
        
        # 绘制性能监控
        y_pos = self.performance_renderer.draw(draw, system_info, y_pos, width)
        
        # 绘制磁盘信息
        y_pos = self.disk_info_renderer.draw(draw, system_info, y_pos, width)
        
        # 绘制Web面板统计信息（如果启用）
        if self.config.get("web_panel.enabled"):
            panel_data = self.web_panel_fetcher.get_panel_data()
            if panel_data:
                y_pos = self.web_panel_stats_renderer.draw(draw, panel_data, y_pos, width)
        
        # 绘制页脚
        self.footer_renderer.draw(draw, final_height, width)
        
        # 保存图片到内存
        logger.info("进入PNG保存阶段")
        img_data = None
        try:
            # 直接将原图转换为RGB后保存
            rgb_img = img.convert('RGB')
            img_buffer = io.BytesIO()
            rgb_img.save(img_buffer, format='PNG')
            img_data = img_buffer.getvalue()
            logger.info(f"图片生成成功，字节长度: {len(img_data)}")
            if not img_data:
                raise ValueError("生成的图片字节为空")
        except Exception as e:
            logger.error(f"图片生成失败，使用备用图片: {e}")
            img_data = self._create_fallback_image("系统信息图片生成失败")
        
        # 最终返回保护
        if not isinstance(img_data, (bytes, bytearray)) or len(img_data) == 0:
            logger.error("最终返回保护触发：返回备用图片")
            img_data = self._create_fallback_image("系统信息图片生成失败(最终保护)")
        
        logger.info(f"图片生成完成，类型: {type(img_data)}, 长度: {len(img_data) if isinstance(img_data, (bytes, bytearray)) else 'N/A'}")
        return img_data
    
    def _create_fallback_image(self, text: str = "系统信息图片生成失败") -> bytes:
        """创建备用图片
        
        Args:
            text: 错误信息文本
            
        Returns:
            备用图片字节数据
        """
        import io
        
        try:
            width = self.config.get("image_style.width", 900)
            height = 300
            fb_img = Image.new('RGB', (width, height), color=self.config.get("background.gradient_start", (26, 26, 46)))
            fb_draw = ImageDraw.Draw(fb_img)
            fb_draw.text((20, 20), str(text), fill=self.config.get("image_style.colors.text_title", "#ffffff"), font=self.fonts['medium'])
            buf = io.BytesIO()
            fb_img.save(buf, format='PNG')
            buf.seek(0)
            return buf.getvalue()
        except Exception as e:
            logger.error(f"生成备用图片失败: {e}")
            return b""