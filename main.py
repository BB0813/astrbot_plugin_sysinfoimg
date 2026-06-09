from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.api.message_components import Image, Plain

import asyncio
import datetime
import json
import os
import platform
import psutil
import re
import sys
import urllib.parse
from typing import Any, Dict, List, Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    from .monitor import collect_system_info
    from . import dashboard_runtime as dashboard_runtime_module
    from .utils import (
        fmt_duration,
        fmt_rate,
        get_labels,
        check_chinese_fonts,
        merge_config,
        resolve_background,
    )
    from .history_store import (
        append_history_sample,
        build_alert_history_context,
        build_history_record,
        estimate_history_max_entries,
    )
except ImportError:
    from monitor import collect_system_info
    import dashboard_runtime as dashboard_runtime_module
    from utils import (
        fmt_duration,
        fmt_rate,
        get_labels,
        check_chinese_fonts,
        merge_config,
        resolve_background,
    )
    from history_store import (
        append_history_sample,
        build_alert_history_context,
        build_history_record,
        estimate_history_max_entries,
    )

build_dashboard_render_data = dashboard_runtime_module.build_dashboard_render_data
collect_astrbot_dashboard_stats = dashboard_runtime_module.collect_astrbot_dashboard_stats
build_stats_diagnostics_payload = getattr(
    dashboard_runtime_module,
    "build_stats_diagnostics_payload",
    None,
)

if not callable(build_stats_diagnostics_payload):
    logger.warning(
        "dashboard_runtime.build_stats_diagnostics_payload not found; "
        "using fallback diagnostics payload."
    )

    def build_stats_diagnostics_payload(stats: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(stats, dict):
            return {
                "ok": False,
                "data_sources": {},
                "warning": "dashboard_runtime.py version mismatch",
            }

        return {
            "ok": bool(stats),
            "data_sources": stats.get("data_sources") or {},
            "warning": "dashboard_runtime.py version mismatch",
        }

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



TASK_MODE_REPORT = "report"
TASK_MODE_ALERT = "alert"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default



def _normalize_umo_dict(umo: Any) -> Dict[str, Any]:
    if hasattr(umo, "to_dict"):
        try:
            data = umo.to_dict()
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    raw = getattr(umo, "__dict__", None)
    if isinstance(raw, dict):
        return {key: value for key, value in raw.items() if not key.startswith("_")}
    return {}



def _build_umo_key(umo_dict: Dict[str, Any]) -> str:
    return str(umo_dict.get("session_id", "unknown")) + str(umo_dict.get("group_id", ""))



def _format_timestamp(timestamp: Any) -> Optional[str]:
    try:
        if not timestamp:
            return None
        return datetime.datetime.fromtimestamp(float(timestamp)).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError):
        return None



def _image_component_from_render_url(url: str) -> Optional[Image]:
    value = str(url or "").strip()
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return Image.fromURL(value)
    if value.startswith("file:///"):
        return Image.fromFileSystem(urllib.parse.unquote(value.removeprefix("file:///")))
    if value.startswith("file://"):
        return Image.fromFileSystem(urllib.parse.unquote(value[7:]))
    if os.path.exists(value):
        return Image.fromFileSystem(value)
    return None



def _alert_metric_labels(locale: str) -> Dict[str, str]:
    if locale == "zh":
        return {
            "cpu": "CPU",
            "memory": '内存',
            "disk": '磁盘',
            "swap": "Swap",
            "gpu": "GPU",
            "temperature": '温度',
            "battery": '电池',
            "containers": '停止容器',
        }
    return {
        "cpu": "CPU",
        "memory": "Memory",
        "disk": "Disk",
        "swap": "Swap",
        "gpu": "GPU",
        "temperature": "Temperature",
        "battery": "Battery",
        "containers": "Stopped Containers",
    }


def _build_alert_thresholds(cfg: Dict[str, Any]) -> Dict[str, int]:
    return {
        "cpu": max(0, _safe_int(cfg.get("alert_cpu_percent"), 85)),
        "memory": max(0, _safe_int(cfg.get("alert_memory_percent"), 90)),
        "disk": max(0, _safe_int(cfg.get("alert_disk_percent"), 90)),
        "swap": max(0, _safe_int(cfg.get("alert_swap_percent"), 80)),
        "gpu": max(0, _safe_int(cfg.get("alert_gpu_percent"), 95)),
        "temperature": max(0, _safe_int(cfg.get("alert_temperature_c"), 85)),
        "battery": max(0, _safe_int(cfg.get("alert_battery_percent"), 0)),
        "containers": max(0, _safe_int(cfg.get("alert_container_stopped"), 0)),
    }



def _evaluate_alert_metrics(sysinfo: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    locale = str(cfg.get("locale", "zh"))
    labels = _alert_metric_labels(locale)
    thresholds = _build_alert_thresholds(cfg)

    disk_peak = {"value": 0.0, "name": ""}
    disk_total = sysinfo.get("disk_total") or {}
    try:
        disk_total_percent = float(disk_total.get("percent") or 0)
        if disk_total_percent >= disk_peak["value"]:
            disk_peak = {"value": disk_total_percent, "name": ""}
    except (TypeError, ValueError):
        pass

    for row in sysinfo.get("disk_info") or []:
        try:
            percent = float(row.get("percent") or 0)
        except (TypeError, ValueError):
            continue
        if percent >= disk_peak["value"]:
            disk_peak = {"value": percent, "name": str(row.get("mount") or "").strip()}

    battery_info = sysinfo.get("battery") or {}
    container_info = sysinfo.get("containers") or {}
    container_total = max(0, _safe_int(container_info.get("total"), 0))
    container_running = max(0, _safe_int(container_info.get("running"), 0))
    container_stopped = max(0, _safe_int(container_info.get("stopped"), max(0, container_total - container_running)))

    candidates = {
        "cpu": float(sysinfo.get("cpu_percent") or 0),
        "memory": float(((sysinfo.get("mem") or {}).get("percent")) or 0),
        "disk": float(disk_peak["value"] or 0),
        "swap": float(((sysinfo.get("swap") or {}).get("percent")) or 0),
        "gpu": float(((sysinfo.get("gpu") or {}).get("util_percent")) or 0),
        "temperature": float(((sysinfo.get("temperature") or {}).get("current_c")) or 0),
        "battery": float(battery_info.get("percent") or 0),
        "containers": float(container_stopped),
    }
    rules = {
        "cpu": {"comparison": "ge", "unit": "%", "available": True},
        "memory": {"comparison": "ge", "unit": "%", "available": True},
        "disk": {"comparison": "ge", "unit": "%", "available": True},
        "swap": {"comparison": "ge", "unit": "%", "available": True},
        "gpu": {"comparison": "ge", "unit": "%", "available": bool(sysinfo.get("gpu"))},
        "temperature": {"comparison": "ge", "unit": "?C", "available": bool(sysinfo.get("temperature"))},
        "battery": {"comparison": "le", "unit": "%", "available": bool(battery_info) and not bool(battery_info.get("plugged"))},
        "containers": {"comparison": "ge", "unit": "", "available": bool(container_info)},
    }

    triggered: List[Dict[str, Any]] = []
    for key in ("cpu", "memory", "disk", "swap", "gpu", "temperature", "battery", "containers"):
        threshold = thresholds.get(key, 0)
        if threshold <= 0:
            continue
        rule = rules.get(key, {"comparison": "ge", "unit": "%", "available": True})
        if not bool(rule.get("available", True)):
            continue

        value = float(candidates.get(key, 0) or 0)
        comparison = str(rule.get("comparison") or "ge")
        if comparison == "le":
            if value > threshold:
                continue
            comparison_symbol = chr(0x2264) if locale == "zh" else "<="
        else:
            if value < threshold:
                continue
            comparison_symbol = chr(0x2265) if locale == "zh" else ">="

        label = labels[key]
        if key == "disk" and disk_peak["name"]:
            label = f"{label}({disk_peak['name']})" if locale == "zh" else f"{label} ({disk_peak['name']})"

        unit = str(rule.get("unit") or "")
        if key == "containers":
            value_display = str(int(round(value)))
            threshold_display = str(int(threshold))
        else:
            value_display = f"{round(value, 1):g}{unit}"
            threshold_display = f"{threshold}{unit}"

        triggered.append(
            {
                "key": key,
                "label": label,
                "value": round(value, 1),
                "threshold": threshold,
                "value_display": value_display,
                "threshold_display": threshold_display,
                "comparison_symbol": comparison_symbol,
            }
        )
    return triggered



def _format_alert_metric_line(item: Dict[str, Any]) -> str:
    symbol = str(item.get("comparison_symbol") or chr(0x2265))
    return f"{item['label']} {item['value_display']} {symbol} {item['threshold_display']}"



def _format_alert_message(triggered: List[Dict[str, Any]], locale: str) -> str:
    if locale == "zh":
        return "?? ???????" + "?".join(_format_alert_metric_line(item) for item in triggered)
    return "?? System alert: " + "; ".join(_format_alert_metric_line(item) for item in triggered)



def _format_recovery_message(locale: str) -> str:
    if locale == "zh":
        return "? ???????????????"
    return "? System metrics are back within the configured alert thresholds."



def _build_deep_host_probe_flags(cfg: Dict[str, Any]) -> Dict[str, bool]:
    deep_host_enabled = bool(cfg.get("enable_deep_host_metrics", True))
    battery_alert_enabled = _safe_int(cfg.get("alert_battery_percent"), 0) > 0
    temperature_alert_enabled = _safe_int(cfg.get("alert_temperature_c"), 85) > 0
    gpu_alert_enabled = _safe_int(cfg.get("alert_gpu_percent"), 95) > 0
    container_alert_enabled = _safe_int(cfg.get("alert_container_stopped"), 0) > 0
    any_host_alert_enabled = (
        battery_alert_enabled
        or temperature_alert_enabled
        or gpu_alert_enabled
        or container_alert_enabled
    )
    if deep_host_enabled:
        return {
            "enable_deep_host_metrics": True,
            "show_battery": True,
            "show_temperature": True,
            "show_gpu": True,
            "show_containers": True,
        }
    return {
        "enable_deep_host_metrics": any_host_alert_enabled,
        "show_battery": battery_alert_enabled,
        "show_temperature": temperature_alert_enabled,
        "show_gpu": gpu_alert_enabled,
        "show_containers": container_alert_enabled,
    }



def _build_host_diagnostics_payload(sysinfo: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    battery_info = sysinfo.get("battery") or {}
    temperature_info = sysinfo.get("temperature") or {}
    gpu_info = sysinfo.get("gpu") or {}
    container_info = sysinfo.get("containers") or {}
    host_capabilities = sysinfo.get("host_capabilities") or {}

    def make_entry(status: str, source: str, detail: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        entry = {
            "status": status,
            "source": source,
            "detail": detail,
        }
        if extra:
            entry.update(extra)
        return entry

    battery_detail = "no battery detected or battery sensor unavailable"
    if battery_info:
        battery_detail = f"{battery_info.get('percent', 0)}% / {'charging' if battery_info.get('plugged') else 'on battery'}"
        if battery_info.get("time_left"):
            battery_detail += f" / {battery_info.get('time_left')}"
    temperature_detail = "no temperature sensor data detected"
    if temperature_info:
        temperature_detail = (
            f"{temperature_info.get('current_c', 0)}?C / sensors={temperature_info.get('sensor_count', 0)}"
        )
    gpu_detail = "nvidia-smi unavailable or no supported GPU detected"
    if gpu_info:
        gpu_detail = (
            f"{gpu_info.get('name', 'GPU')} / util={gpu_info.get('util_percent', 0)}% / count={gpu_info.get('count', 0)}"
        )
        if gpu_info.get("temp_c") not in (None, ""):
            gpu_detail += f" / temp={gpu_info.get('temp_c')}?C"
    container_detail = "docker CLI unavailable or container runtime not accessible"
    if container_info:
        container_detail = (
            f"running={container_info.get('running', 0)} / total={container_info.get('total', 0)} / stopped={container_info.get('stopped', 0)}"
        )

    return {
        "probe_mode": "forced_deep_host_diagnostics",
        "host": {
            "hostname": sysinfo.get("hostname", platform.node()),
            "system": sysinfo.get("distro", platform.system()),
            "kernel": sysinfo.get("kernel", platform.release()),
            "processor": sysinfo.get("processor", platform.processor() or "Unknown CPU"),
            "load_avg": sysinfo.get("load_avg", "N/A"),
        },
        "config": {
            "enable_deep_host_metrics": bool(cfg.get("enable_deep_host_metrics", True)),
            "show_battery_card": bool(cfg.get("show_battery_card", True)),
            "show_temperature_card": bool(cfg.get("show_temperature_card", True)),
            "show_gpu_card": bool(cfg.get("show_gpu_card", True)),
            "show_container_card": bool(cfg.get("show_container_card", True)),
            "alert_gpu_percent": max(0, _safe_int(cfg.get("alert_gpu_percent"), 95)),
            "alert_temperature_c": max(0, _safe_int(cfg.get("alert_temperature_c"), 85)),
            "alert_battery_percent": max(0, _safe_int(cfg.get("alert_battery_percent"), 0)),
            "alert_container_stopped": max(0, _safe_int(cfg.get("alert_container_stopped"), 0)),
        },
        "capabilities": host_capabilities,
        "sources": {
            "battery": make_entry(
                "ok" if battery_info else "missing",
                str(battery_info.get("source") or "psutil.sensors_battery"),
                battery_detail,
                {
                    "percent": battery_info.get("percent"),
                    "plugged": battery_info.get("plugged"),
                    "time_left": battery_info.get("time_left"),
                } if battery_info else None,
            ),
            "temperature": make_entry(
                "ok" if temperature_info else "missing",
                str(temperature_info.get("source") or "psutil.sensors_temperatures / linux_thermal"),
                temperature_detail,
                {
                    "current_c": temperature_info.get("current_c"),
                    "average_c": temperature_info.get("average_c"),
                    "sensor_count": temperature_info.get("sensor_count"),
                } if temperature_info else None,
            ),
            "gpu": make_entry(
                "ok" if gpu_info else "missing",
                str(gpu_info.get("source") or "nvidia-smi"),
                gpu_detail,
                {
                    "name": gpu_info.get("name"),
                    "util_percent": gpu_info.get("util_percent"),
                    "temp_c": gpu_info.get("temp_c"),
                    "count": gpu_info.get("count"),
                } if gpu_info else None,
            ),
            "containers": make_entry(
                "ok" if container_info else "missing",
                str(container_info.get("source") or "docker ps -a"),
                container_detail,
                {
                    "runtime": container_info.get("runtime"),
                    "running": container_info.get("running"),
                    "total": container_info.get("total"),
                    "stopped": container_info.get("stopped"),
                    "states": container_info.get("states"),
                } if container_info else None,
            ),
        },
    }


@register("sysinfoimg", "Binbim", "ç³»ç»ç¶æå¾çæä»¶", "V2.8.1")
class ImgSysInfoPlugin(Star):
    CONFIG_NAMESPACE = "astrbot_plugin_sysinfoimg"

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.auto_tasks: Dict[str, Dict[str, Any]] = {}
        self.last_run: Dict[str, float] = {}
        self._last_history_sample_at = 0.0
        self._load_tasks()
        check_chinese_fonts()
        asyncio.create_task(self._scheduler_loop())
        asyncio.create_task(self._history_loop())

    def _load_tasks(self):
        try:
            path = os.path.join(os.path.dirname(__file__), "auto_tasks.json")
            self.auto_tasks = {}
            self.last_run = {}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                raw_tasks = data.get("tasks", {}) or {}
                if isinstance(raw_tasks, dict):
                    for task_id, task in raw_tasks.items():
                        if not isinstance(task, dict):
                            continue
                        normalized = dict(task)
                        normalized["mode"] = str(normalized.get("mode") or TASK_MODE_REPORT)
                        normalized["enabled"] = bool(normalized.get("enabled", True))
                        normalized["alert_active"] = bool(normalized.get("alert_active", False))
                        normalized["last_alert_at"] = float(normalized.get("last_alert_at", 0) or 0)
                        if not isinstance(normalized.get("last_alert_metrics"), list):
                            normalized["last_alert_metrics"] = []
                        self.auto_tasks[str(task_id)] = normalized
                raw_last_run = data.get("last_run", {}) or {}
                if isinstance(raw_last_run, dict):
                    for task_id, value in raw_last_run.items():
                        try:
                            self.last_run[str(task_id)] = float(value)
                        except (TypeError, ValueError):
                            continue
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

    def _iter_session_tasks(self, umo_key: str, mode: Optional[str] = None):
        for task_id, task in list(self.auto_tasks.items()):
            task_mode = str(task.get("mode") or TASK_MODE_REPORT)
            if task.get("umo_key") != umo_key:
                continue
            if mode and task_mode != mode:
                continue
            yield task_id, task

    def _remove_session_tasks(self, umo_key: str, mode: Optional[str] = None) -> int:
        removed = 0
        for task_id, _task in list(self._iter_session_tasks(umo_key, mode)):
            self.auto_tasks.pop(task_id, None)
            self.last_run.pop(task_id, None)
            removed += 1
        return removed

    async def _collect_alert_snapshot(self, event_or_umo: Any) -> Dict[str, Any]:
        cfg = self._get_cfg(event_or_umo)
        deep_host_probe = _build_deep_host_probe_flags(cfg)
        return await collect_system_info(
            show_cpu=bool(cfg.get("show_cpu", True)),
            show_memory=bool(cfg.get("show_memory", True)),
            show_swap=bool(cfg.get("show_swap", True)),
            show_disk=bool(cfg.get("show_disk", True)),
            disk_partitions=cfg.get("disk_partitions", []),
            show_disk_total=bool(cfg.get("show_disk_total", True)),
            show_network=bool(cfg.get("show_network", True)),
            network_interfaces=cfg.get("network_interfaces", []),
            show_network_per_iface=bool(cfg.get("show_network_per_iface", False)),
            show_top_processes=bool(cfg.get("show_top_processes", True)),
            top_n=int(cfg.get("top_n", 10) or 10),
            process_sort_key=str(cfg.get("process_sort_key", "cpu")),
            enable_deep_host_metrics=bool(deep_host_probe.get("enable_deep_host_metrics")),
            show_battery=bool(deep_host_probe.get("show_battery")),
            show_temperature=bool(deep_host_probe.get("show_temperature")),
            show_gpu=bool(deep_host_probe.get("show_gpu")),
            show_containers=bool(deep_host_probe.get("show_containers")),
        )


    def _get_history_cfg(self) -> Dict[str, Any]:
        cfg = dict(self.config)
        sample_minutes = max(1, _safe_int(cfg.get("history_sample_minutes"), 5))
        retention_hours = max(1, _safe_int(cfg.get("history_retention_hours"), 72))
        context_hours = max(1, _safe_int(cfg.get("history_alert_context_hours"), 1))
        return {
            "enabled": bool(cfg.get("enable_system_history", True)),
            "sample_minutes": sample_minutes,
            "retention_hours": retention_hours,
            "context_hours": context_hours,
            "max_entries": estimate_history_max_entries(retention_hours, sample_minutes),
        }

    def _persist_history_snapshot(self, snapshot: Dict[str, Any], timestamp: Optional[float] = None) -> None:
        history_cfg = self._get_history_cfg()
        if not history_cfg.get("enabled"):
            return
        append_history_sample(
            build_history_record(snapshot, timestamp=timestamp),
            retention_hours=int(history_cfg["retention_hours"]),
            max_entries=int(history_cfg["max_entries"]),
        )

    async def _history_loop(self):
        logger.info("Sysinfo history sampler started")
        await asyncio.sleep(6)
        while True:
            try:
                history_cfg = self._get_history_cfg()
                if not history_cfg.get("enabled"):
                    await asyncio.sleep(60)
                    continue
                now = datetime.datetime.now().timestamp()
                if now - self._last_history_sample_at < int(history_cfg["sample_minutes"]) * 60:
                    await asyncio.sleep(30)
                    continue
                raw_cfg = dict(self.config)
                deep_host_probe = _build_deep_host_probe_flags(raw_cfg)
                snapshot = await collect_system_info(
                    show_cpu=True,
                    show_memory=True,
                    show_swap=True,
                    show_disk=True,
                    disk_partitions=raw_cfg.get("disk_partitions", []),
                    show_disk_total=True,
                    show_network=True,
                    network_interfaces=raw_cfg.get("network_interfaces", []),
                    show_network_per_iface=False,
                    show_top_processes=False,
                    top_n=1,
                    process_sort_key="cpu",
                    enable_deep_host_metrics=bool(deep_host_probe.get("enable_deep_host_metrics")),
                    show_battery=bool(deep_host_probe.get("show_battery")),
                    show_temperature=bool(deep_host_probe.get("show_temperature")),
                    show_gpu=bool(deep_host_probe.get("show_gpu")),
                    show_containers=bool(deep_host_probe.get("show_containers")),
                )
                self._persist_history_snapshot(snapshot, timestamp=now)
                self._last_history_sample_at = now
            except Exception as exc:
                logger.error(f"History loop error: {exc}")
            await asyncio.sleep(30)

    async def _send_scheduler_chain(self, umo: Any, text: str = "", image_url: str = ""):
        chain = []
        if text:
            chain.append(Plain(text=text))
        image_component = _image_component_from_render_url(image_url)
        if image_component is not None:
            chain.append(image_component)
        if not chain:
            return False
        await self.context.send_message(umo, chain)
        return True

    def _build_alert_status_payload(self, cfg: Dict[str, Any], task_id: Optional[str], task: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {
            "enabled": bool(task),
            "interval_minutes": task.get("interval") if task else None,
            "cooldown_minutes": max(0, _safe_int(cfg.get("alert_cooldown_minutes"), 120)),
            "with_image": bool(cfg.get("alert_with_image", True)),
            "send_recovery": bool(cfg.get("alert_send_recovery", True)),
            "thresholds": _build_alert_thresholds(cfg),
            "alert_active": bool(task.get("alert_active", False)) if task else False,
            "last_check_at": _format_timestamp(self.last_run.get(task_id)) if task_id else None,
            "last_alert_at": _format_timestamp(task.get("last_alert_at")) if task else None,
            "last_alert_metrics": task.get("last_alert_metrics", []) if task else [],
        }
        return payload

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

    async def get_sysinfo_url(self, event_or_umo, title: str = "", command_params: Optional[Dict[str, Any]] = None):
        cfg = self._get_cfg(event_or_umo, command_params=command_params)
        bg_image, background_fit_css = resolve_background(
            str(cfg.get("background_mode", "none")),
            str(cfg.get("background_url", "")),
            str(cfg.get("background_file", "")),
            bool(cfg.get("auto_background", True)),
            str(cfg.get("background_fit", "cover")),
        )

        umo = str(event_or_umo.unified_msg_origin) if hasattr(event_or_umo, "unified_msg_origin") else str(event_or_umo)
        render_data = await build_dashboard_render_data(
            self.context,
            cfg,
            title=title,
            bg_image=bg_image,
            background_fit_css=background_fit_css,
            umo=umo,
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

    async def _handle_sysinfo(self, event: AstrMessageEvent, title: str = "", command_params: Optional[Dict[str, Any]] = None):
        url = await self.get_sysinfo_url(event, title, command_params=command_params)
        if url:
            yield event.image_result(url)
        else:
            yield event.plain_result("生成图片失败，请检查日志。")

    @filter.command("sysinfo")
    async def sysinfo(self, event: AstrMessageEvent, title: str = ""):
        async for result in self._handle_sysinfo(event, title):
            yield result

    @filter.regex("^[\/!！\.]?(?:系统状态|系统状态面板)(?:\s+(.*))?$")
    async def sysinfo_regex(self, event: AstrMessageEvent):
        msg = event.message_str.strip()
        match = re.match(r"^[\/!！\.]?(?:系统状态|系统状态面板)(?:\s+(.*))?$", msg)
        title = match.group(1) if match and match.group(1) else ""
        async for result in self._handle_sysinfo(event, title):
            yield result


    @filter.command("sysinfo_history")
    async def sysinfo_history(self, event: AstrMessageEvent, hours: str = ""):
        async for result in self._handle_sysinfo_history(event, hours):
            yield result

    @filter.regex(r"^[\\/!！\\.]?(?:系统历史趋势|系统趋势)(?:\\s+(.*))?$")
    async def sysinfo_history_regex(self, event: AstrMessageEvent):
        msg = event.message_str.strip()
        match = re.match(r"^[\\/!！\\.]?(?:系统历史趋势|系统趋势)(?:\\s+(.*))?$", msg)
        hours = match.group(1) if match and match.group(1) else ""
        async for result in self._handle_sysinfo_history(event, hours):
            yield result

    async def _handle_sysinfo_history(self, event: AstrMessageEvent, hours: str = ""):
        locale = str(self._get_cfg(event).get("locale", "zh"))
        command_params: Dict[str, Any] = {"show_system_history_panel": True}
        if hours:
            try:
                command_params["history_chart_hours"] = max(1, min(72, int(hours)))
            except ValueError:
                yield event.plain_result("请输入有效的小时数，例如：/sysinfo_history 24。")
                return
        title = "系统历史趋势" if locale == "zh" else "System History"
        async for result in self._handle_sysinfo(event, title, command_params=command_params):
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
            help_text = str(self._get_cfg(event).get("sysinfo_auto_help", "")).strip()
            yield event.plain_result(help_text or "请提供间隔分钟数，例如：sysinfo_auto 60。输入 off 关闭。")
            return

        self._reload_settings()
        umo = event.unified_msg_origin
        try:
            umo_dict = _normalize_umo_dict(umo)
            umo_key = _build_umo_key(umo_dict)
        except Exception as exc:
            yield event.plain_result(f"无法获取会话信息：{exc}")
            return

        if interval.lower() == "off":
            removed = self._remove_session_tasks(umo_key, TASK_MODE_REPORT)
            self._save_tasks()
            if removed:
                yield event.plain_result("已关闭当前会话的自动发送。")
            else:
                yield event.plain_result("当前会话没有开启定时发送。")
            return

        try:
            minutes = int(interval)
            if minutes < 1:
                yield event.plain_result("间隔必须大于等于 1 分钟。")
                return

            self._remove_session_tasks(umo_key, TASK_MODE_REPORT)
            now = datetime.datetime.now().timestamp()
            task_id = f"report_{umo_key}_{now}"
            self.auto_tasks[task_id] = {
                "mode": TASK_MODE_REPORT,
                "interval": minutes,
                "umo_dict": umo_dict,
                "umo_key": umo_key,
                "created_at": now,
                "enabled": True,
            }
            self.last_run[task_id] = now
            self._save_tasks()

            url = await self.get_sysinfo_url(event, "Test Report")
            if url:
                yield event.image_result(url)
                yield event.plain_result(f"✅ 已开启自动发送，每 {minutes} 分钟发送一次。")
            else:
                yield event.plain_result("❌ 测试发送失败，请检查日志。")
        except ValueError:
            yield event.plain_result("请输入有效的分钟数。")

    @filter.command("sysinfo_alert")
    async def sysinfo_alert(self, event: AstrMessageEvent, interval: str = ""):
        async for result in self._handle_sysinfo_alert(event, interval):
            yield result

    @filter.regex(r"^[\\/!！\\.]?系统状态告警(?:\\s+(.*))?$")
    async def sysinfo_alert_regex(self, event: AstrMessageEvent):
        msg = event.message_str.strip()
        match = re.match(r"^[\\/!！\\.]?系统状态告警(?:\\s+(.*))?$", msg)
        interval = match.group(1) if match and match.group(1) else ""
        async for result in self._handle_sysinfo_alert(event, interval):
            yield result

    async def _handle_sysinfo_alert(self, event: AstrMessageEvent, interval: str = ""):
        cfg = self._get_cfg(event)
        locale = str(cfg.get("locale", "zh"))
        if not interval:
            help_text = str(cfg.get("sysinfo_alert_help", "")).strip()
            default_help = (
                "请使用 /sysinfo_alert <分钟> 开启阈值告警，"
                "输入 status 查看状态，输入 off 关闭。"
            )
            yield event.plain_result(help_text or default_help)
            return

        self._reload_settings()
        try:
            umo_dict = _normalize_umo_dict(event.unified_msg_origin)
            umo_key = _build_umo_key(umo_dict)
        except Exception as exc:
            yield event.plain_result(f"无法获取会话信息：{exc}")
            return

        action = interval.strip().lower()
        if action == "off":
            removed = self._remove_session_tasks(umo_key, TASK_MODE_ALERT)
            self._save_tasks()
            if removed:
                yield event.plain_result("已关闭当前会话的阈值告警。")
            else:
                yield event.plain_result("当前会话没有开启阈值告警。")
            return

        if action == "status":
            task_id = None
            task = None
            for found_task_id, found_task in self._iter_session_tasks(umo_key, TASK_MODE_ALERT):
                task_id = found_task_id
                task = found_task
                break
            payload = self._build_alert_status_payload(cfg, task_id, task)
            yield event.plain_result(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        try:
            minutes = int(action)
            if minutes < 1:
                yield event.plain_result("间隔必须大于等于 1 分钟。")
                return

            self._remove_session_tasks(umo_key, TASK_MODE_ALERT)
            now = datetime.datetime.now().timestamp()
            task_id = f"alert_{umo_key}_{now}"
            task = {
                "mode": TASK_MODE_ALERT,
                "interval": minutes,
                "umo_dict": umo_dict,
                "umo_key": umo_key,
                "created_at": now,
                "enabled": True,
                "alert_active": False,
                "last_alert_at": 0,
                "last_alert_metrics": [],
            }
            self.auto_tasks[task_id] = task

            snapshot = await self._collect_alert_snapshot(event)
            triggered = _evaluate_alert_metrics(snapshot, cfg)
            self.last_run[task_id] = now
            if triggered:
                task["alert_active"] = True
                task["last_alert_at"] = now
                task["last_alert_metrics"] = [
                    _format_alert_metric_line(item)
                    for item in triggered
                ]
            self.auto_tasks[task_id] = task
            self._save_tasks()

            status_text = "当前状态正常。"
            if triggered:
                status_text = _format_alert_message(triggered, locale)
            yield event.plain_result(
                f"✅ 已开启阈值告警，每 {minutes} 分钟检查一次。{status_text}"
            )
        except ValueError:
            yield event.plain_result("请输入有效的分钟数。")

    async def _run_report_task(self, task_id: str, task: Dict[str, Any], now: float):
        from astrbot.core.platform.sources.unified_message_origin import UnifiedMessageOrigin

        umo = UnifiedMessageOrigin(**task["umo_dict"])
        url = await self.get_sysinfo_url(umo, "Scheduled Report")
        if url:
            sent = await self._send_scheduler_chain(umo, image_url=url)
            if sent:
                self.last_run[task_id] = now
                self._save_tasks()

    async def _run_alert_task(self, task_id: str, task: Dict[str, Any], now: float):
        from astrbot.core.platform.sources.unified_message_origin import UnifiedMessageOrigin

        umo = UnifiedMessageOrigin(**task["umo_dict"])
        cfg = self._get_cfg(umo)
        locale = str(cfg.get("locale", "zh"))
        cooldown_sec = max(0, _safe_int(cfg.get("alert_cooldown_minutes"), 120)) * 60
        snapshot = await self._collect_alert_snapshot(umo)
        self._persist_history_snapshot(snapshot, timestamp=now)
        self._last_history_sample_at = now
        triggered = _evaluate_alert_metrics(snapshot, cfg)
        task["last_alert_metrics"] = [
            _format_alert_metric_line(item)
            for item in triggered
        ]

        if triggered:
            should_send = (not bool(task.get("alert_active"))) or cooldown_sec == 0 or (
                now - float(task.get("last_alert_at", 0) or 0) >= cooldown_sec
            )
            task["alert_active"] = True
            if should_send:
                image_url = ""
                if bool(cfg.get("alert_with_image", True)):
                    image_url = await self.get_sysinfo_url(
                        umo,
                        "告警快照" if locale == "zh" else "Alert Snapshot",
                    )
                alert_text = _format_alert_message(triggered, locale)
                history_cfg = self._get_history_cfg()
                context_text = build_alert_history_context(
                    locale=locale,
                    metric_keys=[item["key"] for item in triggered],
                    within_hours=int(history_cfg.get("context_hours", 1)),
                )
                if context_text:
                    alert_text = f"{alert_text}\n{context_text}"
                sent = await self._send_scheduler_chain(
                    umo,
                    text=alert_text,
                    image_url=image_url,
                )
                if sent:
                    task["last_alert_at"] = now
        else:
            if bool(task.get("alert_active")) and bool(cfg.get("alert_send_recovery", True)):
                await self._send_scheduler_chain(umo, text=_format_recovery_message(locale))
            task["alert_active"] = False
            task["last_alert_metrics"] = []

        self.auto_tasks[task_id] = task
        self.last_run[task_id] = now
        self._save_tasks()

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

                for task_id, task in list(self.auto_tasks.items()):
                    try:
                        interval_sec = max(60, int(task.get("interval", 1)) * 60)
                        last_run = float(self.last_run.get(task_id, 0) or 0)
                        if now - last_run < interval_sec:
                            continue
                        task_mode = str(task.get("mode") or TASK_MODE_REPORT)
                        if task_mode == TASK_MODE_ALERT:
                            await self._run_alert_task(task_id, task, now)
                        else:
                            await self._run_report_task(task_id, task, now)
                    except Exception as exc:
                        logger.error(f"Scheduler failed for task {task_id}: {exc}")
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
            "alert_cpu_percent",
            "alert_memory_percent",
            "alert_disk_percent",
            "alert_swap_percent",
            "alert_gpu_percent",
            "alert_temperature_c",
            "alert_battery_percent",
            "alert_container_stopped",
            "alert_cooldown_minutes",
            "alert_send_recovery",
            "alert_with_image",
            "enable_system_history",
            "show_system_history_panel",
            "history_sample_minutes",
            "history_retention_hours",
            "history_chart_hours",
            "history_chart_points",
            "history_alert_context_hours",
            "enable_deep_host_metrics",
            "show_battery_card",
            "show_temperature_card",
            "show_gpu_card",
            "show_container_card",
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

    @filter.command("sysinfo_stats_diag")
    async def sysinfo_stats_diag(self, event: AstrMessageEvent):
        async for result in self._handle_sysinfo_stats_diag(event):
            yield result

    @filter.regex(r"^[\/!！\.]?系统状态统计诊断$")
    async def sysinfo_stats_diag_regex(self, event: AstrMessageEvent):
        async for result in self._handle_sysinfo_stats_diag(event):
            yield result

    async def _handle_sysinfo_stats_diag(self, event: AstrMessageEvent):
        stats = await collect_astrbot_dashboard_stats(self.context, hours=24, umo=str(event.unified_msg_origin))
        payload = build_stats_diagnostics_payload(stats)
        yield event.plain_result(json.dumps(payload, ensure_ascii=False, indent=2))


    @filter.command("sysinfo_host_diag")
    async def sysinfo_host_diag(self, event: AstrMessageEvent):
        async for result in self._handle_sysinfo_host_diag(event):
            yield result

    @filter.regex(r"^[\/!?\.]?系统主机诊断$")
    async def sysinfo_host_diag_regex(self, event: AstrMessageEvent):
        async for result in self._handle_sysinfo_host_diag(event):
            yield result

    async def _handle_sysinfo_host_diag(self, event: AstrMessageEvent):
        cfg = self._get_cfg(event)
        sysinfo = await collect_system_info(
            show_cpu=False,
            show_memory=False,
            show_swap=False,
            show_disk=False,
            show_disk_total=False,
            show_network=False,
            show_network_per_iface=False,
            show_top_processes=False,
            top_n=1,
            process_sort_key="cpu",
            enable_deep_host_metrics=True,
            show_battery=True,
            show_temperature=True,
            show_gpu=True,
            show_containers=True,
        )
        payload = _build_host_diagnostics_payload(sysinfo, cfg)
        yield event.plain_result(json.dumps(payload, ensure_ascii=False, indent=2))

    async def _handle_sysinfo_disks(self, event: AstrMessageEvent):
        from monitor import list_disks, norm_mounts

        cfg = self._get_cfg(event)
        partitions = norm_mounts(cfg.get("disk_partitions", []))
        disks, _, _ = list_disks(partitions)
        yield event.plain_result(json.dumps(disks, ensure_ascii=False, indent=2))
