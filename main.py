from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.api.message_components import Image

import asyncio
import datetime
import json
import os
import platform
import psutil
import re
import sys
from typing import Any, Dict, List, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from monitor import collect_system_info
from dashboard_runtime import build_dashboard_render_data
from utils import (
    fmt_duration,
    fmt_rate,
    get_labels,
    install_chinese_fonts,
    merge_config,
    resolve_background,
)

THEME_PRESETS = {
    "custom_dashboard": {
        "page_bg": "#0f172a",
        "surface_bg": "rgba(15, 23, 42, 0.78)",
        "surface_alt": "rgba(30, 41, 59, 0.86)",
        "border": "rgba(148, 163, 184, 0.22)",
        "muted_text": "rgba(226, 232, 240, 0.74)",
        "accent": "#6366f1",
        "text": "#f8fafc",
    },
    "dark_glass": {
        "page_bg": "#020617",
        "surface_bg": "rgba(2, 6, 23, 0.72)",
        "surface_alt": "rgba(15, 23, 42, 0.82)",
        "border": "rgba(148, 163, 184, 0.18)",
        "muted_text": "rgba(226, 232, 240, 0.72)",
        "accent": "#38bdf8",
        "text": "#f8fafc",
    },
    "light_card": {
        "page_bg": "#e2e8f0",
        "surface_bg": "rgba(255, 255, 255, 0.88)",
        "surface_alt": "rgba(248, 250, 252, 0.96)",
        "border": "rgba(148, 163, 184, 0.28)",
        "muted_text": "rgba(51, 65, 85, 0.78)",
        "accent": "#2563eb",
        "text": "#0f172a",
    },
    "neon": {
        "page_bg": "#09090b",
        "surface_bg": "rgba(24, 24, 27, 0.82)",
        "surface_alt": "rgba(39, 39, 42, 0.88)",
        "border": "rgba(168, 85, 247, 0.26)",
        "muted_text": "rgba(212, 212, 216, 0.76)",
        "accent": "#a855f7",
        "text": "#fafafa",
    },
}


def _normalize_hex(color: Any, fallback: str) -> str:
    value = str(color or "").strip()
    if not value:
        return fallback
    if not value.startswith("#"):
        value = f"#{value}"
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value.lower()
    return fallback



def _hex_to_rgba(color: str, alpha: float) -> str:
    normalized = _normalize_hex(color, "#6366f1")
    red = int(normalized[1:3], 16)
    green = int(normalized[3:5], 16)
    blue = int(normalized[5:7], 16)
    return f"rgba({red}, {green}, {blue}, {alpha})"



def _clamp_percent(value: Any) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0



def _build_theme_tokens(theme: str, accent_color: str, text_color: str) -> Dict[str, str]:
    preset = dict(THEME_PRESETS.get(theme, THEME_PRESETS["custom_dashboard"]))
    accent = _normalize_hex(accent_color, preset["accent"])
    text = _normalize_hex(text_color, preset["text"])
    return {
        "page_bg": preset["page_bg"],
        "surface_bg": preset["surface_bg"],
        "surface_alt": preset["surface_alt"],
        "border_color": preset["border"],
        "muted_text_color": preset["muted_text"],
        "accent_color": accent,
        "accent_soft": _hex_to_rgba(accent, 0.16),
        "accent_glow": _hex_to_rgba(accent, 0.26),
        "text_color": text,
        "shadow_color": _hex_to_rgba("#020617", 0.30),
        "overlay_color": _hex_to_rgba("#020617", 0.58),
    }



def _estimate_render_height(metric_count: int, disk_count: int, panel_variant: str, panel_count: int, show_network: bool) -> int:
    metric_rows = max(1, (metric_count + 2) // 3)
    height = 280 + metric_rows * 150 + 260
    if show_network:
        height += 36
    if disk_count >= 0:
        height += 150 + max(disk_count, 1) * 74
    if panel_variant:
        row_height = 52
        if panel_variant == "processes":
            row_height = 62
        elif panel_variant == "summary":
            row_height = 48
        height += 150 + max(panel_count, 1) * row_height
    else:
        height += 50
    return min(max(height, 920), 2600)


def _collect_astrbot_runtime(context: Context) -> Dict[str, Any]:
    runtime = {
        "dashboard_username": "",
        "current_provider": "",
        "current_model": "",
        "plugin_count": 0,
        "platform_count": 0,
        "provider_count": 0,
    }
    acm = getattr(context, "astrbot_config_mgr", None)
    default_conf = getattr(acm, "default_conf", None)
    if default_conf is not None:
        try:
            dashboard = default_conf.get("dashboard", {}) or {}
            runtime["dashboard_username"] = str(dashboard.get("username") or "astrbot")
        except Exception:
            pass
        try:
            providers = default_conf.get("provider", []) or []
            if isinstance(providers, list):
                runtime["provider_count"] = len(providers)
        except Exception:
            pass
        try:
            platforms = default_conf.get("platform", []) or []
            if isinstance(platforms, list):
                runtime["platform_count"] = len(platforms)
        except Exception:
            pass
    try:
        runtime["plugin_count"] = len(list(context.get_all_stars()))
    except Exception:
        pass
    platform_manager = getattr(context, "platform_manager", None)
    if platform_manager is not None:
        for attr in ("platform_insts", "platforms"):
            items = getattr(platform_manager, attr, None)
            if isinstance(items, dict):
                runtime["platform_count"] = max(runtime["platform_count"], len(items))
                break
    provider_manager = getattr(context, "provider_manager", None)
    current_provider = getattr(provider_manager, "curr_provider_inst", None)
    if current_provider is not None:
        try:
            meta = current_provider.meta()
            runtime["current_provider"] = str(getattr(meta, "id", "") or getattr(meta, "type", "") or "")
            runtime["current_model"] = str(getattr(meta, "model", "") or "")
        except Exception:
            pass
    return runtime


@register("sysinfoimg", "Binbim", "ç³»ç»ç¶æå¾çæä»¶", "V2.5.0")
class ImgSysInfoPlugin(Star):
    CONFIG_NAMESPACE = "astrbot_plugin_sysinfoimg"

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.auto_tasks: Dict[str, Dict[str, Any]] = {}
        self.last_run: Dict[str, float] = {}
        self._load_tasks()
        install_chinese_fonts()
        asyncio.create_task(self._scheduler_loop())

    def _load_tasks(self):
        try:
            path = os.path.join(os.path.dirname(__file__), "auto_tasks.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    self.auto_tasks = data.get("tasks", {})
                    self.last_run = data.get("last_run", {})
        except Exception as exc:
            logger.error(f"Failed to load auto tasks: {exc}")

    def _save_tasks(self):
        try:
            path = os.path.join(os.path.dirname(__file__), "auto_tasks.json")
            with open(path, "w", encoding="utf-8") as file:
                json.dump({"tasks": self.auto_tasks, "last_run": self.last_run}, file, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error(f"Failed to save auto tasks: {exc}")

    def _reload_settings(self):
        self._load_tasks()

    def _get_cfg(self, event_or_umo: Any, command_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        plugin_config = dict(self.config)
        session_config = None
        if bool(plugin_config.get("enable_session_config", False)):
            try:
                umo = event_or_umo.unified_msg_origin if hasattr(event_or_umo, "unified_msg_origin") else event_or_umo
                session_cfg = self.context.get_config(umo=umo)
                if isinstance(session_cfg, dict):
                    session_config = session_cfg
            except Exception:
                session_config = None
        return merge_config(plugin_config, session_config, command_params)

    async def get_sysinfo_url(self, event_or_umo, title: str = ""):
        cfg = self._get_cfg(event_or_umo)
        bg_image, background_fit_css = resolve_background(
            str(cfg.get("background_mode", "none")),
            str(cfg.get("background_url", "")),
            str(cfg.get("background_file", "")),
            bool(cfg.get("auto_background", True)),
            str(cfg.get("background_fit", "cover")),
        )

        render_data = await build_dashboard_render_data(
            self.context,
            cfg,
            title=title,
            bg_image=bg_image,
            background_fit_css=background_fit_css,
        )

        template_path = os.path.join(os.path.dirname(__file__), "templates", "apple_class.html")
        try:
            with open(template_path, "r", encoding="utf-8") as file:
                template = file.read()
        except Exception as exc:
            logger.error(f"Failed to load template: {exc}")
            return ""

        return await self.html_render(
            template,
            render_data,
            options={"width": render_data["canvas_width"], "height": render_data["canvas_height"]},
        )

    async def _handle_sysinfo(self, event: AstrMessageEvent, title: str = ""):
        url = await self.get_sysinfo_url(event, title)
        if url:
            yield event.image_result(url)
        else:
            yield event.plain_result("生成图片失败，请检查日志。")

    @filter.command("sysinfo")
    async def sysinfo(self, event: AstrMessageEvent, title: str = ""):
        async for result in self._handle_sysinfo(event, title):
            yield result

    @filter.regex(r"^[\/!！\.]?(系统状态|系统状态面板)(?:\s+(.*))?$")
    async def sysinfo_regex(self, event: AstrMessageEvent):
        msg = event.message_str.strip()
        match = re.match(r"^[\/!！\.]?(?:系统状态|系统状态面板)(?:\s+(.*))?$", msg)
        title = match.group(1) if match and match.group(1) else ""
        async for result in self._handle_sysinfo(event, title):
            yield result

    @filter.command("sysinfo_auto")
    async def sysinfo_auto(self, event: AstrMessageEvent, interval: str = ""):
        async for result in self._handle_sysinfo_auto(event, interval):
            yield result

    @filter.regex(r"^[\/!！\.]?自动系统状态(?:\s+(.*))?$")
    async def sysinfo_auto_regex(self, event: AstrMessageEvent):
        msg = event.message_str.strip()
        match = re.match(r"^[\/!！\.]?自动系统状态(?:\s+(.*))?$", msg)
        interval = match.group(1) if match and match.group(1) else ""
        async for result in self._handle_sysinfo_auto(event, interval):
            yield result

    async def _handle_sysinfo_auto(self, event: AstrMessageEvent, interval: str = ""):
        if not interval:
            yield event.plain_result("请提供间隔分钟数，例如：sysinfo_auto 60。输入 off 关闭。")
            return

        self._reload_settings()
        umo = event.unified_msg_origin
        try:
            if hasattr(umo, "to_dict"):
                umo_dict = umo.to_dict()
            else:
                umo_dict = {key: value for key, value in umo.__dict__.items() if not key.startswith("_")}
            umo_key = str(umo_dict.get("session_id", "unknown")) + str(umo_dict.get("group_id", ""))
        except Exception as exc:
            yield event.plain_result(f"无法获取会话信息：{exc}")
            return

        if interval.lower() == "off":
            keys_to_remove = [key for key, value in self.auto_tasks.items() if value.get("umo_key") == umo_key]
            for key in keys_to_remove:
                del self.auto_tasks[key]
                self.last_run.pop(key, None)
            self._save_tasks()
            yield event.plain_result("已关闭当前会话的自动发送。")
            return

        try:
            minutes = int(interval)
            if minutes < 1:
                yield event.plain_result("间隔必须大于等于 1 分钟。")
                return

            task_id = f"{umo_key}_{datetime.datetime.now().timestamp()}"
            self.auto_tasks[task_id] = {
                "interval": minutes,
                "umo_dict": umo_dict,
                "umo_key": umo_key,
                "created_at": datetime.datetime.now().timestamp(),
                "enabled": True,
            }
            self.last_run[task_id] = datetime.datetime.now().timestamp()
            self._save_tasks()

            url = await self.get_sysinfo_url(event, "Test Report")
            if url:
                yield event.image_result(url)
                yield event.plain_result(f"✅ 已开启自动发送，每 {minutes} 分钟发送一次。")
            else:
                yield event.plain_result("❌ 测试发送失败，请检查日志。")
        except ValueError:
            yield event.plain_result("请输入有效的分钟数。")

    async def _scheduler_loop(self):
        logger.info("Sysinfo scheduler started")
        await asyncio.sleep(10)
        while True:
            try:
                self._load_tasks()
                now = datetime.datetime.now().timestamp()
                if not self.auto_tasks:
                    await asyncio.sleep(60)
                    continue

                for key, task in list(self.auto_tasks.items()):
                    interval_sec = int(task["interval"]) * 60
                    last_run = self.last_run.get(key, 0)
                    if now - last_run < interval_sec:
                        continue
                    try:
                        from astrbot.core.platform.sources.unified_message_origin import UnifiedMessageOrigin

                        umo = UnifiedMessageOrigin(**task["umo_dict"])
                        url = await self.get_sysinfo_url(umo, "Scheduled Report")
                        if url:
                            await self.context.send_message(umo, [Image.fromURL(url)])
                            self.last_run[key] = now
                            self._save_tasks()
                    except Exception as exc:
                        logger.error(f"Scheduler failed for task {key}: {exc}")
            except Exception as exc:
                logger.error(f"Scheduler loop error: {exc}")
            await asyncio.sleep(60)

    @filter.command("sysinfo_conf")
    async def sysinfo_conf(self, event: AstrMessageEvent):
        async for result in self._handle_sysinfo_conf(event):
            yield result

    @filter.regex(r"^[\/!！\.]?系统状态配置$")
    async def sysinfo_conf_regex(self, event: AstrMessageEvent):
        async for result in self._handle_sysinfo_conf(event):
            yield result

    async def _handle_sysinfo_conf(self, event: AstrMessageEvent):
        cfg = self._get_cfg(event)
        interesting_keys = [
            "theme",
            "width",
            "height",
            "auto_background",
            "background_mode",
            "bottom_right_panel",
            "show_network_per_iface",
            "process_sort_key",
        ]
        info = {key: cfg.get(key) for key in interesting_keys}
        yield event.plain_result(json.dumps(info, ensure_ascii=False, indent=2))

    @filter.command("sysinfo_disks")
    async def sysinfo_disks(self, event: AstrMessageEvent):
        async for result in self._handle_sysinfo_disks(event):
            yield result

    @filter.regex(r"^[\/!！\.]?系统磁盘列表$")
    async def sysinfo_disks_regex(self, event: AstrMessageEvent):
        async for result in self._handle_sysinfo_disks(event):
            yield result

    async def _handle_sysinfo_disks(self, event: AstrMessageEvent):
        from monitor import list_disks, norm_mounts

        cfg = self._get_cfg(event)
        partitions = norm_mounts(cfg.get("disk_partitions", []))
        disks, _, _ = list_disks(partitions)
        yield event.plain_result(json.dumps(disks, ensure_ascii=False, indent=2))
