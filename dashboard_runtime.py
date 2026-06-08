import datetime
import inspect
import os
import platform
import psutil
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    from .monitor import collect_system_info
    from .utils import fmt_rate
except ImportError:
    from monitor import collect_system_info
    from utils import fmt_rate

THEME_PRESETS = {
    "custom_dashboard": {"page_bg": "#171735", "page_bg_end": "#0c1026", "surface_bg": "rgba(18,24,52,0.84)", "surface_alt": "rgba(34,42,78,0.92)", "border": "rgba(120,133,196,0.18)", "muted_text": "rgba(204,214,255,0.72)", "accent": "#7c6cff", "text": "#f8fbff"},
    "dark_glass": {"page_bg": "#11182f", "page_bg_end": "#090d1f", "surface_bg": "rgba(16,23,47,0.82)", "surface_alt": "rgba(28,36,67,0.90)", "border": "rgba(118,136,214,0.18)", "muted_text": "rgba(210,220,255,0.74)", "accent": "#6ea8ff", "text": "#f8fbff"},
    "light_card": {"page_bg": "#f5f7fb", "surface_bg": "rgba(255,255,255,0.98)", "surface_alt": "#f8fafc", "border": "rgba(148,163,184,0.20)", "muted_text": "#6b7280", "accent": "#2563eb", "text": "#111827"},
    "neon": {"page_bg": "#09090b", "surface_bg": "rgba(24,24,27,0.84)", "surface_alt": "rgba(39,39,42,0.92)", "border": "rgba(168,85,247,0.25)", "muted_text": "rgba(212,212,216,0.76)", "accent": "#a855f7", "text": "#fafafa"},
}


def dashboard_texts(locale: str) -> Dict[str, str]:
    zh = {
        "default_title": "\u7cfb\u7edf\u7edf\u8ba1", "subtitle": "\u5e73\u53f0\u3001\u6d88\u606f\u4e0e\u6a21\u578b\u8c03\u7528\u7684\u4e00\u89c8\u3002", "layout_hint": "DASHBOARD",
        "platform_count": "\u5e73\u53f0\u6570\u91cf", "message_total": "\u6d88\u606f\u603b\u6570", "today_tokens": "\u4eca\u65e5 Tokens", "cpu": "CPU", "memory": "\u8fd0\u884c\u5185\u5b58", "uptime": "\u8fd0\u884c\u65f6\u957f",
        "message_overview": "\u6d88\u606f\u6982\u89c8", "message_trend": "\u6d88\u606f\u8d8b\u52bf", "platform_ranking": "\u5e73\u53f0\u6d88\u606f\u6392\u540d", "model_usage": "\u6a21\u578b\u8c03\u7528", "token_trend": "\u8c03\u7528 Token \u8d8b\u52bf", "recent_tokens": "\u6700\u8fd1 1 \u5929 Token Top 10",
        "dashboard_user": "Dashboard \u7528\u6237", "provider": "\u5f53\u524d\u63d0\u4f9b\u5546", "model": "\u5f53\u524d\u6a21\u578b", "plugins": "\u63d2\u4ef6\u6570", "platforms": "\u5e73\u53f0\u6570", "providers": "\u63d0\u4f9b\u5546\u6570",
        "messages_24h": "\u6700\u8fd1 24 \u5c0f\u65f6\u6d88\u606f", "tokens_24h": "\u6700\u8fd1 24 \u5c0f\u65f6 Tokens", "generated": "\u66f4\u65b0\u65f6\u95f4", "powered": "Powered by AstrBot", "no_data": "\u6682\u65e0\u6570\u636e",
        "system": "\u7cfb\u7edf", "host": "\u4e3b\u673a", "processor": "\u5904\u7406\u5668", "system_status": "\u7cfb\u7edf\u72b6\u6001", "basic_info": "\u57fa\u7840\u4fe1\u606f", "network": "\u7f51\u7edc", "upload": "\u4e0a\u4f20", "download": "\u4e0b\u8f7d", "swap": "Swap", "disk": "\u78c1\u76d8", "disk_usage": "\u78c1\u76d8\u5360\u7528", "top_processes": "\u8fdb\u7a0b\u6392\u540d", "current_time": "\u5f53\u524d\u65f6\u95f4", "kernel": "Kernel", "no_partitions": "\u6682\u65e0\u78c1\u76d8\u6570\u636e",
        "default_chat_provider": "\u9ed8\u8ba4\u5bf9\u8bdd\u6a21\u578b", "model_source": "\u5f53\u524d\u6a21\u578b\u6765\u6e90", "model_hint": "\u53e3\u5f84\u63d0\u793a", "not_set": "\u672a\u8bbe\u7f6e",
        "source_active_provider": "\u8fd0\u884c\u65f6\u5f53\u524d\u6a21\u578b", "source_default_provider": "\u5df2\u843d\u76d8\u9ed8\u8ba4\u6a21\u578b", "source_active_fallback": "\u8fd0\u884c\u65f6\u56de\u9000\uff08\u672a\u8bbe\u7f6e\u9ed8\u8ba4\u6a21\u578b\uff09",
        "hint_default_missing": "default_provider_id \u4e3a\u7a7a\uff1b\u5f53\u524d\u663e\u793a\u7684\u662f\u8fd0\u884c\u65f6\u56de\u9000\u6a21\u578b\uff0c\u4e0d\u662f\u843d\u76d8\u9ed8\u8ba4\u503c\u3002",
        "hint_default_active_mismatch": "\u843d\u76d8\u9ed8\u8ba4\u6a21\u578b\u4e0e\u5f53\u524d\u6fc0\u6d3b\u6a21\u578b\u4e0d\u4e00\u81f4\uff1b\u53ef\u80fd\u5b58\u5728\u4f1a\u8bdd\u7ea7\u8986\u76d6\u6216\u8fd0\u884c\u65f6\u5207\u6362\u3002"
    }
    en = {
        "default_title": "System Stats", "subtitle": "Overview of platforms, messages, and model usage.", "layout_hint": "DASHBOARD",
        "platform_count": "Platforms", "message_total": "Messages", "today_tokens": "Today Tokens", "cpu": "CPU", "memory": "Memory", "uptime": "Uptime",
        "message_overview": "Message Overview", "message_trend": "Message Trend", "platform_ranking": "Platform Ranking", "model_usage": "Model Usage", "token_trend": "Token Trend", "recent_tokens": "Recent 24h Token Top 10",
        "dashboard_user": "Dashboard User", "provider": "Current Provider", "model": "Current Model", "plugins": "Plugins", "platforms": "Platforms", "providers": "Providers",
        "messages_24h": "Messages in 24h", "tokens_24h": "Tokens in 24h", "generated": "Updated", "powered": "Powered by AstrBot", "no_data": "No data",
        "system": "System", "host": "Host", "processor": "Processor", "system_status": "System Status", "basic_info": "Basic Info", "network": "Network", "upload": "Upload", "download": "Download", "swap": "Swap", "disk": "Disk", "disk_usage": "Disk Usage", "top_processes": "Top Processes", "current_time": "Current Time", "kernel": "Kernel", "no_partitions": "No disk data",
        "default_chat_provider": "Default Chat Provider", "model_source": "Current Model Source", "model_hint": "Model Hint", "not_set": "Not set",
        "source_active_provider": "Runtime active provider", "source_default_provider": "Persisted default provider", "source_active_fallback": "Runtime fallback (default provider not set)",
        "hint_default_missing": "`default_provider_id` is empty, so the current model shown here is a runtime fallback instead of a persisted default value.",
        "hint_default_active_mismatch": "The persisted default provider differs from the current active provider. A session-level override or runtime switch may be in effect."
    }
    return zh if locale == 'zh' else en


def build_model_resolution(runtime: Dict[str, Any]) -> Dict[str, Any]:
    active_provider = str(runtime.get('active_provider') or '').strip()
    active_model = str(runtime.get('active_model') or '').strip()
    default_provider = str(runtime.get('default_provider') or '').strip()
    default_model = str(runtime.get('default_model') or '').strip()
    current_provider = str(runtime.get('current_provider') or '').strip()
    current_model = str(runtime.get('current_model') or '').strip()

    current_source = 'unknown'
    if current_provider and active_provider and current_provider == active_provider:
        current_source = 'active_provider'
    elif current_provider and default_provider and current_provider == default_provider:
        current_source = 'default_provider'

    default_missing_with_active_fallback = not default_provider and bool(active_provider)
    default_active_mismatch = bool(default_provider and active_provider and default_provider != active_provider)

    warnings: List[str] = []
    if default_missing_with_active_fallback:
        warnings.append(
            'provider_settings.default_provider_id is empty; current runtime provider comes from provider_manager.curr_provider_inst.'
        )
    if default_active_mismatch:
        warnings.append(
            'Persisted default provider differs from current active provider; a session-level override or runtime switch may be in effect.'
        )

    return {
        'current_provider_source': current_source,
        'current_model_source': current_source,
        'default_missing_with_active_fallback': default_missing_with_active_fallback,
        'default_active_mismatch': default_active_mismatch,
        'current_provider_value': current_provider,
        'current_model_value': current_model,
        'active_provider_value': active_provider,
        'active_model_value': active_model,
        'default_provider_value': default_provider,
        'default_model_value': default_model,
        'warnings': warnings,
        'webui_hint': 'If AstrBot WebUI shows a different chat model, verify whether it is a temporary page or session selection instead of persisted default config.',
    }


def normalize_hex(color: Any, fallback: str) -> str:
    value = str(color or '').strip()
    if not value:
        return fallback
    if not value.startswith('#'):
        value = f'#{value}'
    return value.lower() if re.fullmatch(r'#[0-9a-fA-F]{6}', value) else fallback


def hex_to_rgba(color: str, alpha: float) -> str:
    normalized = normalize_hex(color, '#6366f1')
    red = int(normalized[1:3], 16)
    green = int(normalized[3:5], 16)
    blue = int(normalized[5:7], 16)
    return f'rgba({red}, {green}, {blue}, {alpha})'


def build_theme_tokens(theme: str, accent_color: str, text_color: str) -> Dict[str, str]:
    preset = dict(THEME_PRESETS.get(theme, THEME_PRESETS['custom_dashboard']))
    accent = normalize_hex(accent_color, preset['accent'])
    text = normalize_hex(text_color, preset['text'])
    return {
        'page_bg': preset['page_bg'], 'page_bg_end': preset.get('page_bg_end', preset['page_bg']), 'surface_bg': preset['surface_bg'], 'surface_alt': preset['surface_alt'], 'border_color': preset['border'],
        'muted_text_color': preset['muted_text'], 'accent_color': accent, 'accent_soft': hex_to_rgba(accent, 0.12), 'accent_glow': hex_to_rgba(accent, 0.22),
        'text_color': text, 'shadow_color': hex_to_rgba('#020617', 0.10 if theme == 'light_card' else 0.30),
        'overlay_color': hex_to_rgba('#020617', 0.34 if theme == 'light_card' else 0.62), 'chart_grid': hex_to_rgba(accent, 0.10),
    }


def clamp_percent(value: Any) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def format_short_number(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return '0'
    if abs(number) >= 1000000:
        return f'{number / 1000000:.1f}M'
    if abs(number) >= 1000:
        return f'{number / 1000:.1f}K'
    return str(int(number))


def format_full_number(value: Any) -> str:
    try:
        return f'{int(round(float(value or 0))):,}'
    except (TypeError, ValueError):
        return '0'


def truncate(value: str, limit: int = 42) -> str:
    value = str(value or '').strip()
    return value if len(value) <= limit else value[: limit - 1] + '…'


def mapping(obj: Any) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    for attr in ('model_dump', 'dict'):
        fn = getattr(obj, attr, None)
        if callable(fn):
            try:
                data = fn()
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
    data = getattr(obj, '__dict__', None)
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if not k.startswith('_')}
    return {}


def extract_value(obj: Any, candidates: Iterable[str], default: Any = None) -> Any:
    data = mapping(obj)
    for name in candidates:
        if name in data and data[name] is not None:
            return data[name]
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value
    return default


def extract_number(obj: Any, candidates: Iterable[str], default: float = 0.0) -> float:
    try:
        return float(extract_value(obj, candidates, default))
    except (TypeError, ValueError):
        return float(default)


def extract_datetime(obj: Any, candidates: Iterable[str]) -> Optional[datetime.datetime]:
    value = extract_value(obj, candidates)
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.astimezone().replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, (int, float)):
        raw = float(value / 1000 if value > 1_000_000_000_000 else value)
        try:
            return datetime.datetime.fromtimestamp(raw)
        except Exception:
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.datetime.fromisoformat(text.replace('Z', '+00:00')).replace(tzinfo=None)
    except Exception:
        return None

def round_hour(value: datetime.datetime) -> datetime.datetime:
    return value.replace(minute=0, second=0, microsecond=0)


def build_hour_buckets(hours: int = 24) -> List[datetime.datetime]:
    now = datetime.datetime.now()
    start = round_hour(now - datetime.timedelta(hours=hours - 1))
    return [start + datetime.timedelta(hours=i) for i in range(hours)]


def build_line_chart(series: List[Dict[str, Any]]) -> Dict[str, Any]:
    width, height = 620, 220
    left, right, top, bottom = 18, 18, 16, 26
    max_value = max([item.get('value', 0) for item in series] + [1])
    plot_width, plot_height = width - left - right, height - top - bottom
    points, enriched = [], []
    for idx, item in enumerate(series):
        ratio = 0.0 if max_value <= 0 else float(item.get('value', 0)) / float(max_value)
        x = left if len(series) == 1 else left + plot_width * idx / max(1, len(series) - 1)
        y = top + plot_height * (1 - ratio)
        points.append(f'{x:.1f},{y:.1f}')
        enriched.append({'x': f'{x:.1f}', 'y': f'{y:.1f}', 'label': item.get('label', ''), 'value': format_full_number(item.get('value', 0))})
    area_points = []
    if enriched:
        area_points.append(f"{enriched[0]['x']},{height - bottom}")
        area_points.extend(points)
        area_points.append(f"{enriched[-1]['x']},{height - bottom}")
    interval = max(1, len(series) // 6)
    ticks = [item.get('label', '') if idx % interval == 0 or idx == len(series) - 1 else '' for idx, item in enumerate(series)]
    return {'width': width, 'height': height, 'points': ' '.join(points), 'area_points': ' '.join(area_points), 'points_data': enriched, 'ticks': ticks, 'max_value': format_full_number(max_value)}


def build_bar_chart(series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    max_value = max([item.get('value', 0) for item in series] + [1])
    rows = []
    for item in series:
        value = float(item.get('value', 0))
        height = max(6, int(round((value / max_value) * 100))) if value > 0 else 6
        rows.append({'label': item.get('label', ''), 'value': format_full_number(value), 'height': height})
    return rows


async def maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def extract_live_platform_totals(all_stats: Any) -> Dict[str, int]:
    totals: Dict[str, int] = {}
    items: List[Any] = []
    if isinstance(all_stats, dict):
        if all_stats and all(isinstance(v, dict) for v in all_stats.values()):
            for key, value in all_stats.items():
                item = dict(value)
                item.setdefault('platform_id', key)
                items.append(item)
        else:
            items.append(all_stats)
    elif isinstance(all_stats, (list, tuple, set)):
        items.extend(all_stats)
    for idx, item in enumerate(items):
        name = str(extract_value(item, ['platform_id', 'platform_name', 'name', 'id'], f'platform-{idx + 1}'))
        count = int(extract_number(item, ['message_count', 'count', 'total_count', 'total_messages', 'messages', 'total'], 0))
        if count > 0:
            totals[name] = totals.get(name, 0) + count
    return totals



async def collect_astrbot_dashboard_stats(context: Any, hours: int = 24, umo: Optional[str] = None) -> Dict[str, Any]:
    now = datetime.datetime.now()
    start_time = now - datetime.timedelta(hours=hours)
    runtime = {
        'dashboard_username': 'astrbot',
        'config_id': 'default',
        'config_name': 'default',
        'current_provider': '',
        'current_model': '',
        'active_provider': '',
        'active_model': '',
        'default_provider': '',
        'default_model': '',
        'default_image_caption_provider': '',
        'default_image_caption_model': '',
        'plugin_count': 0,
        'platform_count': 0,
        'provider_count': 0,
    }
    data_sources: Dict[str, Dict[str, Any]] = {
        'runtime': {'source': 'context', 'status': 'missing', 'detail': ''},
        'live_platform_stats': {'source': 'platform_manager', 'status': 'missing', 'detail': ''},
        'platform_history': {'source': 'database', 'status': 'missing', 'detail': ''},
        'conversation_tokens': {'source': 'conversation_manager', 'status': 'missing', 'detail': ''},
    }

    runtime_errors: List[str] = []
    acm = getattr(context, 'astrbot_config_mgr', None)
    config_obj = None
    config_getter = getattr(context, 'get_config', None)
    if callable(config_getter):
        try:
            config_obj = config_getter(umo)
        except Exception as exc:
            runtime_errors.append(f'get_config: {describe_exception(exc)}')
    if config_obj is None and acm is not None:
        try:
            config_obj = acm.get_conf(umo)
        except Exception as exc:
            runtime_errors.append(f'acm.get_conf: {describe_exception(exc)}')
    if config_obj is None and acm is not None:
        config_obj = getattr(acm, 'default_conf', None)

    if acm is not None and umo:
        conf_info_getter = getattr(acm, 'get_conf_info', None)
        if callable(conf_info_getter):
            try:
                conf_info = conf_info_getter(umo)
                if isinstance(conf_info, dict):
                    runtime['config_id'] = str(conf_info.get('id') or 'default')
                    runtime['config_name'] = str(conf_info.get('name') or runtime['config_id'])
            except Exception as exc:
                runtime_errors.append(f'conf_info: {describe_exception(exc)}')

    if config_obj is not None:
        try:
            dashboard = config_obj.get('dashboard', {}) or {}
            runtime['dashboard_username'] = str(dashboard.get('username') or 'astrbot')
        except Exception as exc:
            runtime_errors.append(f'dashboard: {describe_exception(exc)}')
        try:
            providers = config_obj.get('provider', []) or []
            runtime['provider_count'] = len(providers) if isinstance(providers, list) else 0
        except Exception as exc:
            runtime_errors.append(f'provider_count: {describe_exception(exc)}')
        try:
            platforms = config_obj.get('platform', []) or []
            runtime['platform_count'] = len(platforms) if isinstance(platforms, list) else 0
        except Exception as exc:
            runtime_errors.append(f'platform_count: {describe_exception(exc)}')
    try:
        runtime['plugin_count'] = len(list(context.get_all_stars()))
    except Exception as exc:
        runtime_errors.append(f'plugin_count: {describe_exception(exc)}')
    provider_manager = getattr(context, 'provider_manager', None)
    provider_settings = config_obj.get('provider_settings', {}) if config_obj is not None else {}
    default_provider_id = str(provider_settings.get('default_provider_id') or '').strip()
    default_image_caption_provider_id = str(provider_settings.get('default_image_caption_provider_id') or '').strip()

    if provider_manager is not None:
        active_provider = getattr(provider_manager, 'curr_provider_inst', None)
        if active_provider is not None:
            try:
                meta = active_provider.meta()
                runtime['active_provider'] = str(getattr(meta, 'id', '') or getattr(meta, 'type', '') or '')
                runtime['active_model'] = str(getattr(meta, 'model', '') or '')
            except Exception as exc:
                runtime_errors.append(f'active_provider: {describe_exception(exc)}')

        resolver = getattr(provider_manager, 'get_provider_config_by_id', None)
        if callable(resolver):
            try:
                if default_provider_id:
                    default_provider_cfg = resolver(default_provider_id, merged=True) or resolver(default_provider_id)
                    if isinstance(default_provider_cfg, dict):
                        runtime['default_provider'] = str(default_provider_cfg.get('id') or default_provider_id)
                        runtime['default_model'] = str(default_provider_cfg.get('model') or '')
                if default_image_caption_provider_id:
                    image_caption_cfg = resolver(default_image_caption_provider_id, merged=True) or resolver(default_image_caption_provider_id)
                    if isinstance(image_caption_cfg, dict):
                        runtime['default_image_caption_provider'] = str(image_caption_cfg.get('id') or default_image_caption_provider_id)
                        runtime['default_image_caption_model'] = str(image_caption_cfg.get('model') or '')
            except Exception as exc:
                runtime_errors.append(f'default_provider: {describe_exception(exc)}')

    runtime['current_provider'] = runtime['active_provider'] or runtime['default_provider']
    runtime['current_model'] = runtime['active_model'] or runtime['default_model']
    runtime['model_resolution'] = build_model_resolution(runtime)

    data_sources['runtime'] = {
        'source': 'astrbot_config_mgr/provider_manager/context',
        'status': 'ok',
        'detail': f"config={runtime['config_name']}, plugins={runtime['plugin_count']}, providers={runtime['provider_count']}, platforms={runtime['platform_count']}",
        'errors': runtime_errors[:3],
    }

    live_totals, live_probe = await collect_live_platform_totals(context)
    data_sources['live_platform_stats'] = live_probe
    if live_totals:
        runtime['platform_count'] = max(runtime['platform_count'], len(live_totals))

    message_buckets = {bucket: 0 for bucket in build_hour_buckets(hours)}
    platform_ranking: Dict[str, int] = dict(live_totals)
    history_ranking, history_probe = await collect_platform_history(context, hours, start_time, message_buckets)
    data_sources['platform_history'] = history_probe
    if history_ranking:
        platform_ranking = history_ranking
        runtime['platform_count'] = max(runtime['platform_count'], len(history_ranking))

    message_series = [
        {'label': bucket.strftime('%H:%M'), 'value': int(message_buckets[bucket])}
        for bucket in sorted(message_buckets.keys())
    ]
    message_total_hint = int(live_probe.get('message_total') or live_probe.get('messages') or 0)
    message_total = max(
        message_total_hint,
        sum(item['value'] for item in message_series),
        sum(platform_ranking.values()),
    )
    ranking_items = [
        {'name': name, 'value': value}
        for name, value in sorted(platform_ranking.items(), key=lambda item: item[1], reverse=True)[:8]
        if value > 0
    ]

    conversation_rows, conversation_probe = await collect_conversation_token_rows(context, hours, start_time)
    data_sources['conversation_tokens'] = conversation_probe
    token_buckets = {bucket: 0 for bucket in build_hour_buckets(hours)}
    for row in conversation_rows:
        bucket = round_hour(row['timestamp'])
        if bucket in token_buckets:
            token_buckets[bucket] += int(row['value'])
    token_series = [
        {'label': bucket.strftime('%H:%M'), 'value': int(token_buckets[bucket])}
        for bucket in sorted(token_buckets.keys())
    ]
    today_tokens = sum(row['value'] for row in conversation_rows)
    aggregated_token_rows = aggregate_named_rows(conversation_rows)
    token_top = [
        {'name': row['name'], 'value': format_full_number(row['value']), 'raw': row['value']}
        for row in sorted(aggregated_token_rows, key=lambda item: item['value'], reverse=True)[:10]
    ]
    return {
        **runtime,
        'message_total': int(message_total),
        'today_tokens': int(today_tokens),
        'message_chart': build_line_chart(message_series),
        'platform_ranking': [
            {'name': truncate(item['name'], 24), 'value': format_full_number(item['value']), 'raw': item['value']}
            for item in ranking_items
        ],
        'token_chart_bars': build_bar_chart(token_series),
        'token_top': token_top,
        'model_resolution': runtime.get('model_resolution', {}),
        'data_sources': data_sources,
    }



def describe_exception(exc: Exception) -> str:
    return f'{type(exc).__name__}: {exc}'



def normalize_row_collection(result: Any) -> List[Any]:
    if result is None:
        return []
    if isinstance(result, dict):
        for key in ('platform', 'rows', 'items', 'data', 'stats', 'conversations'):
            value = result.get(key)
            if isinstance(value, (list, tuple, set)):
                return list(value)
        return [result]
    nested_rows = extract_value(result, ['platform', 'rows', 'items', 'data', 'stats', 'conversations'])
    if isinstance(nested_rows, (list, tuple, set)):
        return list(nested_rows)
    if isinstance(result, (list, tuple, set)):
        return list(result)
    return [result]




def normalize_paged_conversations(result: Any) -> Tuple[List[Any], Optional[int]]:
    if result is None:
        return [], None
    if isinstance(result, dict):
        for key in ('conversations', 'items', 'rows', 'data'):
            value = result.get(key)
            if isinstance(value, (list, tuple, set)):
                total = result.get('total', result.get('count', len(value)))
                try:
                    return list(value), int(total)
                except Exception:
                    return list(value), len(value)
        total = result.get('total', result.get('count'))
        return [], int(total) if total is not None else None
    if isinstance(result, (list, tuple)):
        if len(result) >= 2 and isinstance(result[0], (list, tuple, set)):
            items = list(result[0])
            try:
                return items, int(result[1] or len(items))
            except Exception:
                return items, len(items)
        items = list(result)
        return items, len(items)
    return [], None



def extract_token_usage(obj: Any) -> int:
    direct = int(extract_number(obj, ['token_usage', 'tokens', 'total_tokens'], 0))
    if direct > 0:
        return direct
    usage = extract_value(obj, ['usage'])
    if usage is not None:
        nested_total = int(extract_number(usage, ['total_tokens', 'tokens'], 0))
        if nested_total > 0:
            return nested_total
        nested_prompt = int(extract_number(usage, ['prompt_tokens', 'input_tokens'], 0))
        nested_completion = int(extract_number(usage, ['completion_tokens', 'output_tokens'], 0))
        if nested_prompt > 0 or nested_completion > 0:
            return nested_prompt + nested_completion
    prompt = int(extract_number(obj, ['prompt_tokens', 'input_tokens'], 0))
    completion = int(extract_number(obj, ['completion_tokens', 'output_tokens'], 0))
    return prompt + completion



def aggregate_named_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    totals: Dict[str, int] = {}
    timestamps: Dict[str, datetime.datetime] = {}
    for row in rows:
        name = str(row.get('name') or 'unknown')
        value = int(row.get('value', 0) or 0)
        if value <= 0:
            continue
        totals[name] = totals.get(name, 0) + value
        timestamp = row.get('timestamp')
        if isinstance(timestamp, datetime.datetime):
            previous = timestamps.get(name)
            if previous is None or timestamp > previous:
                timestamps[name] = timestamp
    return [
        {'name': name, 'value': value, 'timestamp': timestamps.get(name)}
        for name, value in totals.items()
    ]



async def collect_live_platform_totals(context: Any) -> Tuple[Dict[str, int], Dict[str, Any]]:
    probe: Dict[str, Any] = {'source': 'platform_manager', 'status': 'missing', 'detail': ''}
    errors: List[str] = []
    platform_manager = getattr(context, 'platform_manager', None)

    if platform_manager is not None:
        for attr_name in ('get_all_stats', 'get_stats'):
            fn = getattr(platform_manager, attr_name, None)
            if not callable(fn):
                continue
            try:
                result = await maybe_await(fn())
            except TypeError:
                continue
            except Exception as exc:
                errors.append(f'{attr_name}: {describe_exception(exc)}')
                continue
            totals = extract_live_platform_totals(result)
            if totals:
                return totals, {
                    'source': f'platform_manager.{attr_name}',
                    'status': 'ok',
                    'detail': f"platforms={len(totals)}, messages={sum(totals.values())}",
                    'platforms': len(totals),
                    'messages': int(sum(totals.values())),
                    'message_total': int(sum(totals.values())),
                }
        for attr_name in ('all_stats', 'stats', 'platform_stats'):
            value = getattr(platform_manager, attr_name, None)
            if value is None:
                continue
            totals = extract_live_platform_totals(value)
            if totals:
                return totals, {
                    'source': f'platform_manager.{attr_name}',
                    'status': 'ok',
                    'detail': f"platforms={len(totals)}, messages={sum(totals.values())}",
                    'platforms': len(totals),
                    'messages': int(sum(totals.values())),
                    'message_total': int(sum(totals.values())),
                }
    else:
        errors.append('platform_manager missing')

    db = resolve_db(context)
    if db is not None:
        db_errors: List[str] = []
        total_messages: Optional[int] = None
        total_fn = getattr(db, 'get_total_message_count', None)
        if callable(total_fn):
            try:
                total_messages = int(await maybe_await(total_fn()) or 0)
            except Exception as exc:
                db_errors.append(f'get_total_message_count: {describe_exception(exc)}')
        for method_name, kwargs in (
            ('get_grouped_base_stats', {'offset_sec': 3650 * 24 * 3600}),
            ('get_platform_stats', {'offset_sec': 3650 * 24 * 3600}),
        ):
            fn = getattr(db, method_name, None)
            if not callable(fn):
                continue
            try:
                result = await maybe_await(fn(**kwargs))
            except TypeError:
                try:
                    result = await maybe_await(fn())
                except Exception as exc:
                    db_errors.append(f'{method_name}: {describe_exception(exc)}')
                    continue
            except Exception as exc:
                db_errors.append(f'{method_name}: {describe_exception(exc)}')
                continue
            rows = normalize_row_collection(result)
            totals: Dict[str, int] = {}
            for row in rows:
                name = str(extract_value(row, ['platform_id', 'platform_name', 'name', 'platform'], 'unknown'))
                count = int(max(0.0, extract_number(row, ['message_count', 'count', 'total_count', 'total_messages', 'messages', 'total'], 0)))
                if count <= 0:
                    continue
                totals[name] = totals.get(name, 0) + count
            if totals:
                if total_messages is None:
                    total_messages = int(sum(totals.values()))
                return totals, {
                    'source': f'db.{method_name}',
                    'status': 'ok',
                    'detail': f"platforms={len(totals)}, messages={total_messages}",
                    'platforms': len(totals),
                    'messages': int(total_messages),
                    'message_total': int(total_messages),
                }
        if total_messages is not None:
            return {}, {
                'source': 'db.get_total_message_count',
                'status': 'ok',
                'detail': f'messages={total_messages}',
                'platforms': 0,
                'messages': int(total_messages),
                'message_total': int(total_messages),
            }
        errors.extend(db_errors)

    probe['detail'] = '; '.join(errors[:3]) or 'no supported live stats entry found'
    if errors:
        probe['errors'] = errors[:3]
        probe['status'] = 'error'
    return {}, probe




async def collect_platform_history(
    context: Any,
    hours: int,
    start_time: datetime.datetime,
    message_buckets: Dict[datetime.datetime, int],
) -> Tuple[Dict[str, int], Dict[str, Any]]:
    probe: Dict[str, Any] = {'source': 'database', 'status': 'missing', 'detail': ''}
    db = resolve_db(context)
    if db is None:
        probe['detail'] = 'database handle missing'
        return {}, probe

    errors: List[str] = []
    attempts = (
        ('get_base_stats', ({'offset_sec': hours * 3600}, {})),
        ('get_platform_stats', ({'offset_sec': hours * 3600}, {})),
        ('get_grouped_base_stats', ({'offset_sec': hours * 3600}, {})),
        ('get_message_stats', ({'offset_sec': hours * 3600}, {})),
        ('get_stats', ({'offset_sec': hours * 3600}, {})),
    )
    for method_name, variants in attempts:
        fn = getattr(db, method_name, None)
        if not callable(fn):
            continue
        for kwargs in variants:
            try:
                result = await maybe_await(fn(**kwargs))
            except TypeError:
                continue
            except Exception as exc:
                errors.append(f'{method_name}: {describe_exception(exc)}')
                break
            rows = normalize_row_collection(result)
            per_platform: Dict[str, List[Any]] = {}
            for row in rows:
                ts = extract_datetime(row, ['stat_time', 'timestamp', 'created_at', 'time', 'updated_at'])
                if ts is None or ts < start_time:
                    continue
                name = str(extract_value(row, ['platform_id', 'platform_name', 'name', 'platform'], 'unknown'))
                count = max(0.0, extract_number(row, ['message_count', 'count', 'total_count', 'total_messages', 'messages', 'total'], 0))
                per_platform.setdefault(name, []).append((ts, count))
            if not per_platform:
                continue
            platform_ranking: Dict[str, int] = {}
            for name, series in per_platform.items():
                series.sort(key=lambda item: item[0])
                monotonic = sum(1 for index in range(1, len(series)) if series[index][1] >= series[index - 1][1]) >= max(1, len(series) - 2)
                previous, total = None, 0.0
                for ts, value in series:
                    delta = max(0.0, value - previous) if previous is not None and monotonic else value
                    previous = value
                    total += delta
                    bucket = round_hour(ts)
                    if bucket in message_buckets:
                        message_buckets[bucket] += int(round(delta))
                platform_ranking[name] = int(round(total if total > 0 else series[-1][1]))
            return platform_ranking, {
                'source': f'db.{method_name}',
                'status': 'ok',
                'detail': f"rows={len(rows)}, platforms={len(platform_ranking)}",
                'rows': len(rows),
                'platforms': len(platform_ranking),
            }
    probe['detail'] = '; '.join(errors[:3]) or 'no supported history stats method found'
    if errors:
        probe['errors'] = errors[:3]
        probe['status'] = 'error'
    return {}, probe




async def collect_conversation_token_rows(
    context: Any,
    hours: int,
    start_time: datetime.datetime,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    probe: Dict[str, Any] = {'source': 'conversation_manager', 'status': 'missing', 'detail': ''}
    errors: List[str] = []
    db = resolve_db(context)
    db_probe: Optional[Dict[str, Any]] = None
    db_rows: List[Dict[str, Any]] = []

    if db is not None and hasattr(db, 'get_db'):
        try:
            from astrbot.core.db.po import ProviderStat
            from sqlmodel import col, select

            query_start_utc = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
            async with db.get_db() as session:
                result = await session.execute(
                    select(ProviderStat)
                    .where(
                        ProviderStat.agent_type == 'internal',
                        ProviderStat.created_at >= query_start_utc,
                    )
                    .order_by(col(ProviderStat.created_at).asc())
                )
                records = result.scalars().all()

            for record in records:
                token_usage = (
                    int(getattr(record, 'token_input_other', 0) or 0)
                    + int(getattr(record, 'token_input_cached', 0) or 0)
                    + int(getattr(record, 'token_output', 0) or 0)
                )
                if token_usage <= 0:
                    continue
                created_at = extract_datetime(record, ['created_at', 'updated_at'])
                if created_at is None or created_at < start_time:
                    continue
                label = truncate(
                    str(
                        getattr(record, 'provider_model', None)
                        or getattr(record, 'provider_id', None)
                        or getattr(record, 'conversation_id', None)
                        or getattr(record, 'umo', None)
                        or 'provider'
                    ),
                    54,
                )
                db_rows.append({
                    'name': label,
                    'value': token_usage,
                    'timestamp': created_at,
                })

            db_probe = {
                'source': 'db.provider_stats',
                'status': 'ok' if db_rows else 'empty',
                'detail': f"records={len(records)}, rows={len(db_rows)}",
                'records': len(records),
                'rows': len(db_rows),
            }
            if db_rows:
                return db_rows, db_probe
        except Exception as exc:
            errors.append(f'provider_stats: {describe_exception(exc)}')
            db_probe = {
                'source': 'db.provider_stats',
                'status': 'error',
                'detail': describe_exception(exc),
                'errors': errors[:3],
            }

    conversation_manager = getattr(context, 'conversation_manager', None) or getattr(context, 'conversation_mgr', None)
    if conversation_manager is None:
        if db_probe is not None:
            return db_rows, db_probe
        probe['detail'] = 'conversation_manager missing'
        if errors:
            probe['errors'] = errors[:3]
            probe['status'] = 'error'
        return [], probe

    method_attempts = (
        ('get_filtered_conversations', [
            {'page': 1, 'page_size': 100, 'platform_ids': [], 'search_query': '', 'message_types': [], 'exclude_ids': [], 'exclude_platforms': []},
            {'page': 1, 'page_size': 100},
        ]),
        ('get_conversations', [
            {'page': 1, 'page_size': 100},
            {},
        ]),
        ('list_conversations', [
            {'page': 1, 'page_size': 100},
            {},
        ]),
    )
    fallback_probe: Optional[Dict[str, Any]] = None
    fallback_rows: List[Dict[str, Any]] = []

    for method_name, first_page_variants in method_attempts:
        fn = getattr(conversation_manager, method_name, None)
        if not callable(fn):
            continue
        selected_variant: Optional[Dict[str, Any]] = None
        first_items: List[Any] = []
        total_items: Optional[int] = None
        for kwargs in first_page_variants:
            try:
                result = await maybe_await(fn(**kwargs))
            except TypeError:
                continue
            except Exception as exc:
                errors.append(f'{method_name}: {describe_exception(exc)}')
                break
            first_items, total_items = normalize_paged_conversations(result)
            selected_variant = kwargs
            break
        if selected_variant is None:
            continue
        page_size = int(selected_variant.get('page_size', 100) or 100)
        rows: List[Dict[str, Any]] = []
        page = int(selected_variant.get('page', 1) or 1)
        pages_scanned = 0
        while True:
            pages_scanned += 1
            items = first_items if page == int(selected_variant.get('page', 1) or 1) else []
            if page != int(selected_variant.get('page', 1) or 1):
                if 'page' not in selected_variant:
                    break
                page_kwargs = dict(selected_variant)
                page_kwargs['page'] = page
                try:
                    result = await maybe_await(fn(**page_kwargs))
                except Exception as exc:
                    errors.append(f'{method_name} page {page}: {describe_exception(exc)}')
                    break
                items, total_items = normalize_paged_conversations(result)
            if not items:
                break
            for conv in items:
                token_usage = extract_token_usage(conv)
                updated_at = extract_datetime(conv, ['updated_at', 'created_at', 'timestamp'])
                if token_usage <= 0 or updated_at is None or updated_at < start_time:
                    continue
                rows.append({
                    'name': truncate(str(extract_value(conv, ['title', 'conversation_id', 'user_id', 'session_id'], 'conversation')), 54),
                    'value': token_usage,
                    'timestamp': updated_at,
                })
            if 'page' not in selected_variant:
                break
            if total_items is not None and page * page_size >= total_items:
                break
            if page >= 8:
                break
            page += 1
        fallback_rows = rows
        fallback_probe = {
            'source': f'conversation_manager.{method_name}',
            'status': 'ok' if rows else 'empty',
            'detail': f"conversations={len(rows)}, pages={pages_scanned}",
            'conversations': len(rows),
            'pages': pages_scanned,
        }
        if rows:
            if db_probe is not None:
                merged_probe = dict(db_probe)
                merged_probe['fallback_source'] = fallback_probe['source']
                merged_probe['fallback_status'] = fallback_probe['status']
                merged_probe['fallback_detail'] = fallback_probe['detail']
                return rows, merged_probe
            return rows, fallback_probe
        break

    if db_probe is not None:
        if fallback_probe is not None:
            merged_probe = dict(db_probe)
            merged_probe['fallback_source'] = fallback_probe['source']
            merged_probe['fallback_status'] = fallback_probe['status']
            merged_probe['fallback_detail'] = fallback_probe['detail']
            if errors and 'errors' not in merged_probe:
                merged_probe['errors'] = errors[:3]
            return db_rows, merged_probe
        if errors and 'errors' not in db_probe:
            db_probe = dict(db_probe)
            db_probe['errors'] = errors[:3]
        return db_rows, db_probe

    if fallback_probe is not None:
        if errors:
            fallback_probe = dict(fallback_probe)
            fallback_probe['errors'] = errors[:3]
        return fallback_rows, fallback_probe

    probe['detail'] = '; '.join(errors[:3]) or 'no supported conversation method found'
    if errors:
        probe['errors'] = errors[:3]
        probe['status'] = 'error'
    return [], probe




def build_stats_diagnostics_payload(stats: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'runtime': {
            'dashboard_username': stats.get('dashboard_username', ''),
            'config_id': stats.get('config_id', ''),
            'config_name': stats.get('config_name', ''),
            'current_provider': stats.get('current_provider', ''),
            'current_model': stats.get('current_model', ''),
            'active_provider': stats.get('active_provider', ''),
            'active_model': stats.get('active_model', ''),
            'default_provider': stats.get('default_provider', ''),
            'default_model': stats.get('default_model', ''),
            'default_image_caption_provider': stats.get('default_image_caption_provider', ''),
            'default_image_caption_model': stats.get('default_image_caption_model', ''),
            'plugin_count': stats.get('plugin_count', 0),
            'platform_count': stats.get('platform_count', 0),
            'provider_count': stats.get('provider_count', 0),
            'message_total': stats.get('message_total', 0),
            'today_tokens': stats.get('today_tokens', 0),
        },
        'model_resolution': stats.get('model_resolution', {}),
        'data_sources': stats.get('data_sources', {}),
    }




def resolve_db(context: Any) -> Any:
    for candidate in (
        getattr(context, 'db', None),
        getattr(context, 'database', None),
        getattr(getattr(context, 'conversation_manager', None), 'db', None),
    ):
        if candidate is not None:
            return candidate
    getter = getattr(context, 'get_db', None)
    if callable(getter):
        try:
            return getter()
        except Exception:
            return None
    return None


def collect_system_snapshot() -> Dict[str, Any]:
    processor = platform.processor() or 'Unknown CPU'
    if platform.system() == 'Linux':
        try:
            with open('/proc/cpuinfo', 'r', encoding='utf-8', errors='ignore') as file:
                for line in file:
                    if 'model name' in line:
                        processor = line.split(':', 1)[1].strip()
                        break
        except Exception:
            pass
    memory = psutil.virtual_memory()
    return {'cpu_percent': clamp_percent(psutil.cpu_percent(interval=0.1)), 'memory_percent': clamp_percent(memory.percent), 'memory_used_h': f'{memory.used / 1024 / 1024:.0f} MB', 'memory_total_h': f'{memory.total / 1024 / 1024 / 1024:.1f} GB', 'processor': processor, 'hostname': platform.node(), 'kernel': platform.release()}

def format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    days = total // 86400
    hours = (total % 86400) // 3600
    minutes = (total % 3600) // 60
    if days > 0:
        return f'{days}d {hours}h {minutes}m'
    if hours > 0:
        return f'{hours}h {minutes}m'
    return f'{minutes}m'


def with_ratio(rows: List[Dict[str, Any]], key: str = 'raw') -> List[Dict[str, Any]]:
    max_value = max([int(row.get(key, 0) or 0) for row in rows] + [1])
    enriched: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item['ratio'] = max(6, int(round((int(item.get(key, 0) or 0) / max_value) * 100))) if int(item.get(key, 0) or 0) > 0 else 0
        enriched.append(item)
    return enriched



async def build_dashboard_render_data(
    context: Any,
    cfg: Dict[str, Any],
    title: str = '',
    bg_image: str = '',
    background_fit_css: str = 'cover',
    umo: Optional[str] = None,
) -> Dict[str, Any]:
    locale = str(cfg.get('locale', 'zh'))
    theme = str(cfg.get('theme', 'custom_dashboard'))
    logical_width = max(960, int(cfg.get('width', 960)))
    render_scale = max(1, int(cfg.get('render_scale', 3)))
    requested_height = max(1560, int(cfg.get('height', 1760)))
    texts = dashboard_texts(locale)
    theme_tokens = build_theme_tokens(
        theme,
        str(cfg.get('accent_color', '#6366f1')),
        str(cfg.get('text_color', '#111827' if theme == 'light_card' else '#f8fafc')),
    )

    default_accent = theme_tokens['accent_color']
    bar_colors = {
        'cpu': normalize_hex(cfg.get('bar_color_cpu', default_accent), default_accent),
        'memory': normalize_hex(cfg.get('bar_color_mem', default_accent), default_accent),
        'swap': normalize_hex(cfg.get('bar_color_swap', default_accent), default_accent),
        'network': normalize_hex(cfg.get('bar_color_net', default_accent), default_accent),
        'disk': normalize_hex(cfg.get('bar_color_disk', default_accent), default_accent),
    }

    show_cpu = bool(cfg.get('show_cpu', True))
    show_memory = bool(cfg.get('show_memory', True))
    show_swap = bool(cfg.get('show_swap', True))
    show_disk = bool(cfg.get('show_disk', True))
    show_disk_total = bool(cfg.get('show_disk_total', True))
    show_network = bool(cfg.get('show_network', True))
    show_network_per_iface = bool(cfg.get('show_network_per_iface', False))
    show_top_processes = bool(cfg.get('show_top_processes', True))
    show_hostname = bool(cfg.get('show_hostname', True))
    show_os = bool(cfg.get('show_os', True))
    show_time = bool(cfg.get('show_time', True))
    show_uptime = bool(cfg.get('show_uptime', True))
    force_show_empty_disk = bool(cfg.get('force_show_empty_disk', True))
    process_show_user = bool(cfg.get('process_show_user', True))
    process_sort_key = str(cfg.get('process_sort_key', 'cpu'))
    bottom_right_panel = str(cfg.get('bottom_right_panel', 'processes'))

    stats = await collect_astrbot_dashboard_stats(context, hours=24, umo=umo)
    sysinfo = await collect_system_info(
        show_cpu=show_cpu,
        show_memory=show_memory,
        show_swap=show_swap,
        show_disk=show_disk,
        disk_partitions=cfg.get('disk_partitions', []),
        show_disk_total=show_disk_total,
        show_network=show_network,
        network_interfaces=cfg.get('network_interfaces', []),
        show_network_per_iface=show_network_per_iface or bottom_right_panel == 'net_ifaces',
        show_top_processes=show_top_processes or bottom_right_panel == 'processes',
        top_n=max(1, int(cfg.get('top_n', 10))),
        process_sort_key=process_sort_key,
    )
    system = collect_system_snapshot()
    now = datetime.datetime.now()
    uptime = format_duration(now.timestamp() - psutil.boot_time())

    mem = sysinfo.get('mem') or {}
    swap = sysinfo.get('swap') or {}
    disk_total = (sysinfo.get('disk_total') or {}) if show_disk_total else {}
    net_sent = int(sysinfo.get('net_sent', 0) or 0)
    net_recv = int(sysinfo.get('net_recv', 0) or 0)
    net_peak = max(net_sent, net_recv, 1)
    iface_names = [str(item.get('name', '')) for item in (sysinfo.get('net_per') or []) if item.get('name')]
    network_note = ' / '.join(iface_names[:2]) if show_network_per_iface and iface_names else texts['network']

    summary_cards = [
        {'label': texts['platform_count'], 'value': format_full_number(stats.get('platform_count', 0)), 'note': texts['message_overview']},
        {'label': texts['message_total'], 'value': format_full_number(stats.get('message_total', 0)), 'note': texts['messages_24h']},
        {'label': texts['today_tokens'], 'value': format_short_number(stats.get('today_tokens', 0)), 'note': texts['tokens_24h']},
    ]
    if show_uptime:
        summary_cards.append({'label': texts['uptime'], 'value': uptime, 'note': now.strftime('%Y-%m-%d %H:%M')})

    system_metric_cards: List[Dict[str, Any]] = []
    if show_cpu:
        system_metric_cards.append({
            'label': texts['cpu'],
            'value': f"{clamp_percent(sysinfo.get('cpu_percent', 0))}%",
            'note': sysinfo.get('processor', system['processor']),
            'progress': clamp_percent(sysinfo.get('cpu_percent', 0)),
            'progress_color': bar_colors['cpu'],
        })
    if mem:
        system_metric_cards.append({
            'label': texts['memory'],
            'value': f"{clamp_percent(mem.get('percent', 0))}%",
            'note': f"{mem.get('used_h', '0 B')} / {mem.get('total_h', '0 B')}",
            'progress': clamp_percent(mem.get('percent', 0)),
            'progress_color': bar_colors['memory'],
        })
    if swap:
        system_metric_cards.append({
            'label': texts['swap'],
            'value': f"{clamp_percent(swap.get('percent', 0))}%",
            'note': f"{swap.get('used_h', '0 B')} / {swap.get('total_h', '0 B')}",
            'progress': clamp_percent(swap.get('percent', 0)),
            'progress_color': bar_colors['swap'],
        })
    if disk_total:
        system_metric_cards.append({
            'label': texts['disk'],
            'value': f"{clamp_percent(disk_total.get('percent', 0))}%",
            'note': f"{disk_total.get('used_h', '0 B')} / {disk_total.get('total_h', '0 B')}",
            'progress': clamp_percent(disk_total.get('percent', 0)),
            'progress_color': bar_colors['disk'],
        })
    if show_network:
        system_metric_cards.append({
            'label': texts['upload'],
            'value': sysinfo.get('net_sent_str', '0 B/s'),
            'note': network_note,
            'progress': clamp_percent((net_sent / net_peak) * 100) if net_peak else 0,
            'progress_color': bar_colors['network'],
        })
        system_metric_cards.append({
            'label': texts['download'],
            'value': sysinfo.get('net_recv_str', '0 B/s'),
            'note': network_note,
            'progress': clamp_percent((net_recv / net_peak) * 100) if net_peak else 0,
            'progress_color': bar_colors['network'],
        })

    token_top = [dict(row, progress_color=default_accent) for row in with_ratio(stats.get('token_top', []), 'raw')]
    platform_ranking_rows = [dict(row, progress_color=default_accent) for row in with_ratio(stats.get('platform_ranking', []), 'raw')]
    token_chart_bars = [dict(bar, color=default_accent) for bar in stats.get('token_chart_bars', [])]
    model_resolution = stats.get('model_resolution') or {}

    info_rows = [
        {'label': texts['dashboard_user'], 'value': stats.get('dashboard_username') or 'astrbot'},
        {'label': texts['provider'], 'value': stats.get('current_provider') or texts['no_data']},
        {'label': texts['model'], 'value': stats.get('current_model') or texts['no_data']},
        {'label': texts['default_chat_provider'], 'value': stats.get('default_provider') or texts['not_set']},
        {'label': texts['plugins'], 'value': format_full_number(stats.get('plugin_count', 0))},
    ]
    if model_resolution.get('default_missing_with_active_fallback'):
        info_rows.append({'label': texts['model_source'], 'value': texts['source_active_fallback']})
        info_rows.append({'label': texts['model_hint'], 'value': texts['hint_default_missing']})
    elif model_resolution.get('default_active_mismatch'):
        info_rows.append({'label': texts['model_source'], 'value': texts['source_active_provider']})
        info_rows.append({'label': texts['model_hint'], 'value': texts['hint_default_active_mismatch']})
    elif stats.get('default_provider'):
        info_rows.append({'label': texts['model_source'], 'value': texts['source_default_provider']})
    elif stats.get('active_provider'):
        info_rows.append({'label': texts['model_source'], 'value': texts['source_active_provider']})
    if show_os:
        info_rows.append({'label': texts['system'], 'value': f"{sysinfo.get('distro', platform.system())} {sysinfo.get('kernel', platform.release())}".strip()})
    if show_hostname:
        info_rows.append({'label': texts['host'], 'value': sysinfo.get('hostname', system['hostname'])})
    info_rows.append({'label': texts['processor'], 'value': sysinfo.get('processor', system['processor'])})
    if show_time:
        info_rows.append({'label': texts['current_time'], 'value': now.strftime('%Y-%m-%d %H:%M:%S')})

    disk_rows: List[Dict[str, Any]] = []
    for row in (sysinfo.get('disk_info') or [])[:4]:
        disk_rows.append({
            'name': row.get('mount', '-'),
            'note': row.get('fstype', 'N/A'),
            'value': f"{row.get('used_h', '0 B')} / {row.get('total_h', '0 B')}",
            'percent': clamp_percent(row.get('percent', 0)),
            'progress_color': bar_colors['disk'],
        })
    show_disk_panel = show_disk and (bool(disk_rows) or force_show_empty_disk)
    if show_disk_panel and not disk_rows:
        disk_rows.append({
            'name': texts['no_partitions'],
            'note': texts['no_data'],
            'value': '',
            'percent': 0,
            'progress_color': bar_colors['disk'],
            'is_placeholder': True,
        })

    process_rows: List[Dict[str, Any]] = []
    if show_top_processes:
        for row in (sysinfo.get('top_procs') or [])[:6]:
            cpu_value = float(row.get('cpu', 0) or 0)
            username = str(row.get('username') or '').strip()
            detail_parts: List[str] = []
            if process_show_user and username:
                detail_parts.append(username)
            if process_sort_key == 'memory':
                detail_parts.append(f"CPU {cpu_value:.1f}%")
                display_value = row.get('mem_h', '0 B')
            else:
                detail_parts.append(row.get('mem_h', '0 B'))
                display_value = f"{cpu_value:.1f}%"
            process_rows.append({
                'name': truncate(str(row.get('name', 'process')), 42),
                'value': display_value,
                'note': ' / '.join(part for part in detail_parts if part),
            })

    bottom_panel: Optional[Dict[str, Any]] = None
    if bottom_right_panel == 'processes':
        if show_top_processes:
            bottom_panel = {
                'kicker': texts['top_processes'],
                'title': texts['system_status'],
                'rows': process_rows,
            }
    elif bottom_right_panel == 'net_ifaces':
        if show_network:
            raw_rows = []
            for item in (sysinfo.get('net_per') or [])[:6]:
                throughput = int(item.get('up', 0) or 0) + int(item.get('down', 0) or 0)
                raw_rows.append({
                    'name': truncate(str(item.get('name', 'iface')), 24),
                    'value': f"DL {fmt_rate(float(item.get('down', 0) or 0))}",
                    'note': f"UL {fmt_rate(float(item.get('up', 0) or 0))}",
                    'raw': throughput,
                })
            bottom_panel = {
                'kicker': texts['network'],
                'title': texts['interfaces'],
                'rows': [dict(row, progress_color=bar_colors['network']) for row in with_ratio(raw_rows, 'raw')],
            }
    elif bottom_right_panel == 'summary':
        bottom_panel = {
            'kicker': texts['summary'],
            'title': texts['message_overview'],
            'rows': [
                {'name': texts['platforms'], 'value': format_full_number(stats.get('platform_count', 0)), 'note': texts['platform_count']},
                {'name': texts['providers'], 'value': format_full_number(stats.get('provider_count', 0)), 'note': texts['providers']},
                {'name': texts['message_total'], 'value': format_full_number(stats.get('message_total', 0)), 'note': texts['messages_24h']},
                {'name': texts['today_tokens'], 'value': format_full_number(stats.get('today_tokens', 0)), 'note': texts['tokens_24h']},
            ],
        }

    visible_panels = 1 + int(show_disk_panel) + int(bottom_panel is not None)
    span_class = 'span-4'
    if visible_panels == 1:
        span_class = 'span-12'
    elif visible_panels == 2:
        span_class = 'span-6'

    bottom_row_count = len(bottom_panel.get('rows', [])) if bottom_panel else 0
    logical_height = max(
        requested_height,
        1460
        + max(0, len(summary_cards) - 4) * 32
        + max(0, len(system_metric_cards) - 6) * 48
        + (max(0, len(disk_rows) - 2) * 30 if show_disk_panel else 0)
        + (max(0, bottom_row_count - 4) * 26 if bottom_panel else 0)
        + max(0, len(token_top) - 5) * 30,
    )

    footer_position = str(cfg.get('footer_position', 'left_bottom'))
    footer_class = 'footer footer-right' if footer_position == 'right_bottom' else 'footer footer-left'

    return {
        'locale': locale,
        'theme': theme,
        'title': title or str(cfg.get('title', texts['default_title'])),
        'subtitle': texts['subtitle'],
        'layout_hint': texts['layout_hint'],
        'timestamp_text': now.strftime('%H:%M:%S'),
        'generated_text': now.strftime('%Y-%m-%d %H:%M:%S'),
        'show_time_badge': show_time,
        'page_width': logical_width,
        'logical_height': logical_height,
        'render_scale': render_scale,
        'canvas_width': logical_width * render_scale + 48,
        'canvas_height': logical_height * render_scale + 48,
        'bg_image': bg_image,
        'background_fit_css': background_fit_css,
        'footer_text': texts['powered'],
        'footer_class': footer_class,
        'summary_cards': summary_cards,
        'system_metric_cards': system_metric_cards,
        'message_chart': stats.get('message_chart', build_line_chart([])),
        'message_total': format_full_number(stats.get('message_total', 0)),
        'platform_ranking_rows': platform_ranking_rows,
        'token_total': format_full_number(stats.get('today_tokens', 0)),
        'token_chart_bars': token_chart_bars,
        'token_top': token_top,
        'info_rows': info_rows,
        'show_disk_panel': show_disk_panel,
        'disk_rows': disk_rows,
        'bottom_panel': bottom_panel,
        'info_panel_span': span_class,
        'disk_panel_span': span_class,
        'bottom_panel_span': span_class,
        **texts,
        **theme_tokens,
    }
