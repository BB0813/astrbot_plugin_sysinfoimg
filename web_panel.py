# -*- coding: utf-8 -*-
"""
AstrBot-Web面板数据获取模块
"""
import time
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class WebPanelDataFetcher:
    """AstrBot-Web面板数据获取类"""
    
    def __init__(self, config):
        """初始化Web面板数据获取器
        
        Args:
            config: 配置管理器实例
        """
        self.config = config
        self.enabled = config.get("web_panel.enabled", False)
        self.base_url = config.get("web_panel.url", "http://localhost:8080")
        self.api_key = config.get("web_panel.api_key", "")
        self.refresh_interval = config.get("web_panel.refresh_interval", 300)
        
        # 数据缓存
        self._cache = {}
        self._last_refresh = 0
    
    def get_panel_data(self) -> Optional[Dict[str, Any]]:
        """获取Web面板数据
        
        Returns:
            Web面板数据字典，失败则返回None
        """
        if not self.enabled:
            return None
        
        # 检查缓存是否有效
        current_time = time.time()
        if current_time - self._last_refresh < self.refresh_interval and self._cache:
            logger.info("使用缓存的Web面板数据")
            return self._cache
        
        # 刷新数据
        try:
            logger.info("开始刷新Web面板数据")
            data = self._fetch_data()
            if data:
                self._cache = data
                self._last_refresh = current_time
                logger.info("Web面板数据刷新成功")
                return data
        except Exception as e:
            logger.error(f"刷新Web面板数据失败: {e}")
        
        # 如果刷新失败，返回旧缓存（如果有）
        if self._cache:
            logger.warning("使用过期的Web面板缓存数据")
            return self._cache
        
        return None
    
    def _fetch_data(self) -> Optional[Dict[str, Any]]:
        """从Web面板API获取数据
        
        Returns:
            API返回的数据，失败则返回None
        """
        endpoints = {
            "stats": "/api/v1/stats",
            "status": "/api/v1/status",
            "plugins": "/api/v1/plugins",
            "users": "/api/v1/users"
        }
        
        all_data = {}
        
        for name, endpoint in endpoints.items():
            try:
                url = f"{self.base_url}{endpoint}"
                headers = {}
                
                # 添加API认证
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                all_data[name] = response.json()
                logger.info(f"成功获取{name}数据")
            except Exception as e:
                logger.error(f"获取{name}数据失败: {e}")
                continue
        
        return all_data if all_data else None
    
    def get_stats_summary(self) -> Optional[Dict[str, Any]]:
        """获取统计数据摘要
        
        Returns:
            统计数据摘要字典，失败则返回None
        """
        panel_data = self.get_panel_data()
        if not panel_data or "stats" not in panel_data:
            return None
        
        stats = panel_data["stats"]
        stats_items = self.config.get("web_panel.stats_items", ["message_count", "user_count", "plugin_count"])
        
        summary = {}
        for item in stats_items:
            if item in stats:
                summary[item] = stats[item]
        
        return summary
    
    def get_status_info(self) -> Optional[Dict[str, Any]]:
        """获取状态信息
        
        Returns:
            状态信息字典，失败则返回None
        """
        panel_data = self.get_panel_data()
        if not panel_data or "status" not in panel_data:
            return None
        
        return panel_data["status"]
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache = {}
        self._last_refresh = 0
        logger.info("Web面板数据缓存已清除")
    
    def refresh_data(self) -> Optional[Dict[str, Any]]:
        """强制刷新数据
        
        Returns:
            刷新后的数据，失败则返回None
        """
        self.clear_cache()
        return self.get_panel_data()
