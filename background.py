# -*- coding: utf-8 -*-
"""
背景渲染模块
"""
import os
import logging
from PIL import Image, ImageDraw
import requests
from io import BytesIO
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class BackgroundRenderer:
    """背景渲染类"""
    
    def __init__(self, config):
        """初始化背景渲染器
        
        Args:
            config: 配置管理器实例
        """
        self.config = config
    
    def create_background(self, width: int, height: int) -> Tuple[Image.Image, ImageDraw.ImageDraw]:
        """创建背景
        
        Args:
            width: 图片宽度
            height: 图片高度
            
        Returns:
            背景图片和绘图对象
        """
        background_type = self.config.get("background.type", "gradient")
        
        # 创建基础图片
        img = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        if background_type == "image":
            self._draw_image_background(img, draw, width, height)
        elif background_type == "solid":
            self._draw_solid_background(img, draw, width, height)
        else:  # gradient
            self._draw_gradient_background(img, draw, width, height)
        
        return img, draw
    
    def _draw_gradient_background(self, img: Image.Image, draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
        """绘制渐变背景
        
        Args:
            img: 图片对象
            draw: 绘图对象
            width: 图片宽度
            height: 图片高度
        """
        logger.info("开始绘制渐变背景")
        
        gradient_start = tuple(self.config.get("background.gradient_start", (26, 26, 46)))
        gradient_end = tuple(self.config.get("background.gradient_end", (52, 73, 94)))
        
        # 绘制垂直渐变
        for i in range(height):
            r = int(gradient_start[0] + (gradient_end[0] - gradient_start[0]) * i / height)
            g = int(gradient_start[1] + (gradient_end[1] - gradient_start[1]) * i / height)
            b = int(gradient_start[2] + (gradient_end[2] - gradient_start[2]) * i / height)
            color = (r, g, b)
            draw.line([(0, i), (width, i)], fill=color)
        
        logger.info("渐变背景绘制完成")
    
    def _draw_solid_background(self, img: Image.Image, draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
        """绘制纯色背景
        
        Args:
            img: 图片对象
            draw: 绘图对象
            width: 图片宽度
            height: 图片高度
        """
        logger.info("开始绘制纯色背景")
        
        # 使用渐变的起始颜色作为纯色背景
        solid_color = tuple(self.config.get("background.gradient_start", (26, 26, 46)))
        draw.rectangle([(0, 0), (width, height)], fill=solid_color)
        
        logger.info("纯色背景绘制完成")
    
    def _draw_image_background(self, img: Image.Image, draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
        """绘制图片背景
        
        Args:
            img: 图片对象
            draw: 绘图对象
            width: 图片宽度
            height: 图片高度
        """
        logger.info("开始绘制图片背景")
        
        # 获取背景图片
        background_image = self._load_background_image()
        if background_image is None:
            # 加载失败，使用渐变背景作为 fallback
            logger.warning("背景图片加载失败，使用渐变背景")
            self._draw_gradient_background(img, draw, width, height)
            return
        
        # 调整图片大小
        scaled_image = self._scale_image(background_image, width, height)
        
        # 计算图片位置
        if self.config.get("background.scale_mode") == "center":
            x = (width - scaled_image.width) // 2
            y = (height - scaled_image.height) // 2
        else:
            x, y = 0, 0
        
        # 应用透明度
        opacity = self.config.get("background.opacity", 0.8)
        if opacity < 1.0:
            scaled_image = scaled_image.copy()
            alpha = scaled_image.split()[3] if scaled_image.mode == 'RGBA' else scaled_image.convert('RGBA').split()[3]
            alpha = alpha.point(lambda p: int(p * opacity))
            scaled_image.putalpha(alpha)
        
        # 绘制背景图片
        img.paste(scaled_image, (x, y), scaled_image if scaled_image.mode == 'RGBA' else None)
        
        logger.info("图片背景绘制完成")
    
    def _load_background_image(self) -> Optional[Image.Image]:
        """加载背景图片
        
        Returns:
            加载的图片对象，失败则返回None
        """
        image_path = self.config.get("background.image_path", "")
        image_url = self.config.get("background.image_url", "")
        
        # 优先使用本地图片
        if image_path and os.path.exists(image_path):
            try:
                logger.info(f"加载本地背景图片: {image_path}")
                return Image.open(image_path).convert('RGBA')
            except Exception as e:
                logger.error(f"加载本地背景图片失败: {e}")
        
        # 尝试加载远程图片
        if image_url:
            try:
                logger.info(f"加载远程背景图片: {image_url}")
                response = requests.get(image_url, timeout=10)
                response.raise_for_status()
                return Image.open(BytesIO(response.content)).convert('RGBA')
            except Exception as e:
                logger.error(f"加载远程背景图片失败: {e}")
        
        logger.warning("未找到有效的背景图片")
        return None
    
    def _scale_image(self, image: Image.Image, width: int, height: int) -> Image.Image:
        """调整图片大小
        
        Args:
            image: 原始图片
            width: 目标宽度
            height: 目标高度
            
        Returns:
            调整后的图片
        """
        scale_mode = self.config.get("background.scale_mode", "fill")
        
        if scale_mode == "stretch":
            # 拉伸填充
            return image.resize((width, height), Image.LANCZOS)
        elif scale_mode == "center":
            # 保持比例，居中显示
            img_ratio = image.width / image.height
            target_ratio = width / height
            
            if img_ratio > target_ratio:
                # 图片更宽，按高度缩放
                new_height = height
                new_width = int(new_height * img_ratio)
            else:
                # 图片更高，按宽度缩放
                new_width = width
                new_height = int(new_width / img_ratio)
            
            return image.resize((new_width, new_height), Image.LANCZOS)
        else:  # fill
            # 填充，保持比例，裁剪多余部分
            img_ratio = image.width / image.height
            target_ratio = width / height
            
            if img_ratio > target_ratio:
                # 图片更宽，裁剪宽度
                new_width = int(height * img_ratio)
                new_height = height
                left = (new_width - width) // 2
                top = 0
                right = left + width
                bottom = new_height
            else:
                # 图片更高，裁剪高度
                new_width = width
                new_height = int(width / img_ratio)
                left = 0
                top = (new_height - height) // 2
                right = new_width
                bottom = top + height
            
            scaled = image.resize((new_width, new_height), Image.LANCZOS)
            return scaled.crop((left, top, right, bottom))
