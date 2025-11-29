# -*- coding: utf-8 -*-
"""
配置管理模块
"""
import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理类"""
    
    def __init__(self, config_path: str = "config.json"):
        """初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        self._save_config()  # 确保配置文件存在
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件
        
        Returns:
            配置字典
        """
        default_config = {
            "background": {
                "type": "gradient",  # gradient, image, solid
                "image_path": "",
                "image_url": "",
                "opacity": 0.8,
                "scale_mode": "fill",  # fill, stretch, center
                "gradient_start": (26, 26, 46),
                "gradient_end": (52, 73, 94)
            },
            "web_panel": {
                "enabled": False,
                "url": "http://localhost:8080",
                "api_key": "",
                "refresh_interval": 300,  # 秒
                "show_stats": True,
                "stats_items": ["message_count", "user_count", "plugin_count"]
            },
            "image_style": {
                "width": 900,
                "base_height": 800,
                "colors": {
                    "section_bg": (38, 38, 68),
                    "border": "#667eea",
                    "text_title": "#ffffff",
                    "text_content": "#e2e8f0",
                    "text_subtitle": "#a0aec0",
                    "cpu_color": "#4299e1",
                    "cpu_warning_color": "#f56565",
                    "mem_color": "#48bb78",
                    "mem_warning_color": "#ed8936",
                    "disk_color": "#9f7aea",
                    "disk_warning_color": "#e53e3e",
                    "system_disk_mark": "⭐ "
                },
                "fonts": {
                    "title_size": 32,
                    "large_size": 20,
                    "medium_size": 16,
                    "small_size": 14
                },
                "layout": {
                    "padding": 40,
                    "section_spacing": 25,
                    "line_spacing": 25
                }
            }
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                # 合并配置，保留默认值
                return self._merge_configs(default_config, loaded_config)
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                return default_config
        else:
            logger.info(f"配置文件不存在，使用默认配置: {self.config_path}")
            return default_config
    
    def _merge_configs(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置字典
        
        Args:
            default: 默认配置
            loaded: 加载的配置
            
        Returns:
            合并后的配置
        """
        merged = default.copy()
        for key, value in loaded.items():
            if key in merged and isinstance(value, dict) and isinstance(merged[key], dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        return merged
    
    def _save_config(self) -> None:
        """保存配置到文件"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到: {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项
        
        Args:
            key: 配置项键名，支持点分隔路径（如 "background.image_path"）
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split(".")
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """设置配置项
        
        Args:
            key: 配置项键名，支持点分隔路径（如 "background.image_path"）
            value: 配置值
        """
        keys = key.split(".")
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self._save_config()
    
    def reload(self) -> None:
        """重新加载配置文件"""
        self.config = self._load_config()
        logger.info("配置已重新加载")
