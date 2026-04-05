import datetime
import inspect
import platform
import psutil
import re
from monitor import collect_system_info
from typing import Any, Dict, Iterable, List, Optional

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
        "system": "\u7cfb\u7edf", "host": "\u4e3b\u673a", "processor": "\u5904\u7406\u5668", "system_status": "\u7cfb\u7edf\u72b6\u6001", "basic_info": "\u57fa\u7840\u4fe1\u606f", "network": "\u7f51\u7edc", "upload": "\u4e0a\u4f20", "download": "\u4e0b\u8f7d", "swap": "Swap", "disk": "\u78c1\u76d8", "disk_usage": "\u78c1\u76d8\u5360\u7528", "top_processes": "\u8fdb\u7a0b\u6392\u540d", "current_time": "\u5f53\u524d\u65f6\u95f4", "kernel": "Kernel", "no_partitions": "\u6682\u65e0\u78c1\u76d8\u6570\u636e"
    }
    en = {
        "default_title": "System Stats", "subtitle": "Overview of platforms, messages, and model usage.", "layout_hint": "DASHBOARD",
        "platform_count": "Platforms", "message_total": "Messages", "today_tokens": "Today Tokens", "cpu": "CPU", "memory": "Memory", "uptime": "Uptime",
        "message_overview": "Message Overview", "message_trend": "Message Trend", "platform_ranking": "Platform Ranking", "model_usage": "Model Usage", "token_trend": "Token Trend", "recent_tokens": "Recent 24h Token Top 10",
        "dashboard_user": "Dashboard User", "provider": "Current Provider", "model": "Current Model", "plugins": "Plugins", "platforms": "Platforms", "providers": "Providers",
        "messages_24h": "Messages in 24h", "tokens_24h": "Tokens in 24h", "generated": "Updated", "powered": "Powered by AstrBot", "no_data": "No data",
        "system": "System", "host": "Host", "processor": "Processor", "system_status": "System Status", "basic_info": "Basic Info", "network": "Network", "upload": "Upload", "download": "Download", "swap": "Swap", "disk": "Disk", "disk_usage": "Disk Usage", "top_processes": "Top Processes", "current_time": "Current Time", "kernel": "Kernel", "no_partitions": "No disk data"
    }
    return zh if locale == 'zh' else en


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


async def collect_astrbot_dashboard_stats(context: Any, hours: int = 24) -> Dict[str, Any]:
    now = datetime.datetime.now()
    start_time = now - datetime.timedelta(hours=hours)
    runtime = {'dashboard_username': 'astrbot', 'current_provider': '', 'current_model': '', 'plugin_count': 0, 'platform_count': 0, 'provider_count': 0}
    acm = getattr(context, 'astrbot_config_mgr', None)
    default_conf = getattr(acm, 'default_conf', None)
    if default_conf is not None:
        try:
            dashboard = default_conf.get('dashboard', {}) or {}
            runtime['dashboard_username'] = str(dashboard.get('username') or 'astrbot')
        except Exception:
            pass
        try:
            providers = default_conf.get('provider', []) or []
            runtime['provider_count'] = len(providers) if isinstance(providers, list) else 0
        except Exception:
            pass
        try:
            platforms = default_conf.get('platform', []) or []
            runtime['platform_count'] = len(platforms) if isinstance(platforms, list) else 0
        except Exception:
            pass
    try:
        runtime['plugin_count'] = len(list(context.get_all_stars()))
    except Exception:
        pass
    provider_manager = getattr(context, 'provider_manager', None)
    current_provider = getattr(provider_manager, 'curr_provider_inst', None)
    if current_provider is not None:
        try:
            meta = current_provider.meta()
            runtime['current_provider'] = str(getattr(meta, 'id', '') or getattr(meta, 'type', '') or '')
            runtime['current_model'] = str(getattr(meta, 'model', '') or '')
        except Exception:
            pass

    live_totals: Dict[str, int] = {}
    platform_manager = getattr(context, 'platform_manager', None)
    if platform_manager is not None and hasattr(platform_manager, 'get_all_stats'):
        try:
            live_totals = extract_live_platform_totals(await maybe_await(platform_manager.get_all_stats()))
            if live_totals:
                runtime['platform_count'] = max(runtime['platform_count'], len(live_totals))
        except Exception:
            live_totals = {}

    message_buckets = {bucket: 0 for bucket in build_hour_buckets(hours)}
    platform_ranking: Dict[str, int] = dict(live_totals)
    db = resolve_db(context)
    if db is not None and hasattr(db, 'get_platform_stats'):
        try:
            rows = await maybe_await(db.get_platform_stats(offset_sec=hours * 3600))
        except Exception:
            rows = []
        per_platform: Dict[str, List[Any]] = {}
        for row in rows or []:
            ts = extract_datetime(row, ['stat_time', 'timestamp', 'created_at', 'time', 'updated_at'])
            if ts is None or ts < start_time:
                continue
            name = str(extract_value(row, ['platform_id', 'platform_name', 'name', 'platform'], 'unknown'))
            count = max(0.0, extract_number(row, ['message_count', 'count', 'total_count', 'total_messages', 'messages', 'total'], 0))
            per_platform.setdefault(name, []).append((ts, count))
        if per_platform:
            platform_ranking = {}
            for name, series in per_platform.items():
                series.sort(key=lambda item: item[0])
                monotonic = sum(1 for i in range(1, len(series)) if series[i][1] >= series[i - 1][1]) >= max(1, len(series) - 2)
                previous, total = None, 0.0
                for ts, value in series:
                    delta = max(0.0, value - previous) if previous is not None and monotonic else value
                    previous = value
                    total += delta
                    bucket = round_hour(ts)
                    if bucket in message_buckets:
                        message_buckets[bucket] += int(round(delta))
                platform_ranking[name] = int(round(total if total > 0 else series[-1][1]))

    message_series = [{'label': bucket.strftime('%H:%M'), 'value': int(message_buckets[bucket])} for bucket in sorted(message_buckets.keys())]
    message_total = max(sum(live_totals.values()), sum(item['value'] for item in message_series), sum(platform_ranking.values()))
    ranking_items = [{'name': name, 'value': value} for name, value in sorted(platform_ranking.items(), key=lambda item: item[1], reverse=True)[:8] if value > 0]

    conversation_rows: List[Dict[str, Any]] = []
    conversation_manager = getattr(context, 'conversation_manager', None) or getattr(context, 'conversation_mgr', None)
    if conversation_manager is not None and hasattr(conversation_manager, 'get_filtered_conversations'):
        page, page_size = 1, 100
        while page <= 8:
            try:
                result = await maybe_await(conversation_manager.get_filtered_conversations(page=page, page_size=page_size, platform_ids=[], search_query='', message_types=[], exclude_ids=[], exclude_platforms=[]))
            except Exception:
                break
            if isinstance(result, dict):
                conversations, total = result.get('conversations', []), int(result.get('total', 0) or 0)
            elif isinstance(result, (list, tuple)) and len(result) >= 2:
                conversations, total = result[0], int(result[1] or 0)
            else:
                break
            if not conversations:
                break
            for conv in conversations:
                token_usage = int(extract_number(conv, ['token_usage', 'tokens', 'total_tokens'], 0))
                updated_at = extract_datetime(conv, ['updated_at', 'created_at', 'timestamp'])
                if token_usage <= 0 or updated_at is None or updated_at < start_time:
                    continue
                conversation_rows.append({'name': truncate(str(extract_value(conv, ['title', 'conversation_id', 'user_id'], 'conversation')), 54), 'value': token_usage, 'timestamp': updated_at})
            if page * page_size >= total:
                break
            page += 1

    token_buckets = {bucket: 0 for bucket in build_hour_buckets(hours)}
    for row in conversation_rows:
        bucket = round_hour(row['timestamp'])
        if bucket in token_buckets:
            token_buckets[bucket] += int(row['value'])
    token_series = [{'label': bucket.strftime('%H:%M'), 'value': int(token_buckets[bucket])} for bucket in sorted(token_buckets.keys())]
    today_tokens = sum(row['value'] for row in conversation_rows)
    token_top = [{'name': row['name'], 'value': format_full_number(row['value']), 'raw': row['value']} for row in sorted(conversation_rows, key=lambda item: item['value'], reverse=True)[:10]]
    return {**runtime, 'message_total': int(message_total), 'today_tokens': int(today_tokens), 'message_chart': build_line_chart(message_series), 'platform_ranking': [{'name': truncate(item['name'], 24), 'value': format_full_number(item['value']), 'raw': item['value']} for item in ranking_items], 'token_chart_bars': build_bar_chart(token_series), 'token_top': token_top}


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

    stats = await collect_astrbot_dashboard_stats(context, hours=24)
    sysinfo = await collect_system_info(
        show_cpu=bool(cfg.get('show_cpu', True)),
        show_memory=bool(cfg.get('show_memory', True)),
        show_swap=bool(cfg.get('show_swap', True)),
        show_disk=bool(cfg.get('show_disk', True)),
        disk_partitions=cfg.get('disk_partitions', []),
        show_disk_total=bool(cfg.get('show_disk_total', True)),
        show_network=bool(cfg.get('show_network', True)),
        network_interfaces=cfg.get('network_interfaces', []),
        show_network_per_iface=bool(cfg.get('show_network_per_iface', False)),
        show_top_processes=bool(cfg.get('show_top_processes', True)),
        top_n=max(1, int(cfg.get('top_n', 8))),
        process_sort_key=str(cfg.get('process_sort_key', 'cpu')),
    )
    system = collect_system_snapshot()
    now = datetime.datetime.now()
    uptime = format_duration(now.timestamp() - psutil.boot_time())

    mem = sysinfo.get('mem') or {}
    swap = sysinfo.get('swap') or {}
    disk_total = sysinfo.get('disk_total') or {}

    summary_cards = [
        {'label': texts['platform_count'], 'value': format_full_number(stats.get('platform_count', 0)), 'note': texts['message_overview']},
        {'label': texts['message_total'], 'value': format_full_number(stats.get('message_total', 0)), 'note': texts['messages_24h']},
        {'label': texts['today_tokens'], 'value': format_short_number(stats.get('today_tokens', 0)), 'note': texts['tokens_24h']},
        {'label': texts['uptime'], 'value': uptime, 'note': now.strftime('%Y-%m-%d %H:%M')},
    ]

    system_metric_cards: List[Dict[str, Any]] = [
        {'label': texts['cpu'], 'value': f"{clamp_percent(sysinfo.get('cpu_percent', 0))}%", 'note': sysinfo.get('processor', system['processor'])},
    ]
    if mem:
        system_metric_cards.append({'label': texts['memory'], 'value': f"{clamp_percent(mem.get('percent', 0))}%", 'note': f"{mem.get('used_h', '0 B')} / {mem.get('total_h', '0 B')}"})
    if swap:
        system_metric_cards.append({'label': texts['swap'], 'value': f"{clamp_percent(swap.get('percent', 0))}%", 'note': f"{swap.get('used_h', '0 B')} / {swap.get('total_h', '0 B')}"})
    if disk_total:
        system_metric_cards.append({'label': texts['disk'], 'value': f"{clamp_percent(disk_total.get('percent', 0))}%", 'note': f"{disk_total.get('used_h', '0 B')} / {disk_total.get('total_h', '0 B')}"})
    if bool(cfg.get('show_network', True)):
        system_metric_cards.append({'label': texts['upload'], 'value': sysinfo.get('net_sent_str', '0 B/s'), 'note': texts['network']})
        system_metric_cards.append({'label': texts['download'], 'value': sysinfo.get('net_recv_str', '0 B/s'), 'note': texts['network']})

    token_top = with_ratio(stats.get('token_top', []), 'raw')
    platform_ranking_rows = with_ratio(stats.get('platform_ranking', []), 'raw')
    info_rows = [
        {'label': texts['dashboard_user'], 'value': stats.get('dashboard_username') or 'astrbot'},
        {'label': texts['provider'], 'value': stats.get('current_provider') or texts['no_data']},
        {'label': texts['model'], 'value': stats.get('current_model') or texts['no_data']},
        {'label': texts['plugins'], 'value': format_full_number(stats.get('plugin_count', 0))},
        {'label': texts['system'], 'value': f"{sysinfo.get('distro', platform.system())} {sysinfo.get('kernel', platform.release())}".strip()},
        {'label': texts['host'], 'value': sysinfo.get('hostname', system['hostname'])},
        {'label': texts['processor'], 'value': sysinfo.get('processor', system['processor'])},
        {'label': texts['current_time'], 'value': now.strftime('%Y-%m-%d %H:%M:%S')},
    ]

    disk_rows = []
    for row in (sysinfo.get('disk_info') or [])[:4]:
        disk_rows.append({
            'name': row.get('mount', '-'),
            'note': row.get('fstype', 'N/A'),
            'value': f"{row.get('used_h', '0 B')} / {row.get('total_h', '0 B')}",
            'percent': clamp_percent(row.get('percent', 0)),
        })

    process_rows = []
    for row in (sysinfo.get('top_procs') or [])[:6]:
        process_rows.append({
            'name': truncate(str(row.get('name', 'process')), 42),
            'value': f"{float(row.get('cpu', 0)):.1f}%",
            'note': row.get('mem_h', '0 B'),
        })

    logical_height = max(
        requested_height,
        1540 + max(0, len(token_top) - 5) * 30 + max(0, len(disk_rows) - 2) * 30 + max(0, len(process_rows) - 4) * 24,
    )

    return {
        'locale': locale,
        'theme': theme,
        'title': title or str(cfg.get('title', texts['default_title'])),
        'subtitle': texts['subtitle'],
        'layout_hint': texts['layout_hint'],
        'timestamp_text': now.strftime('%H:%M:%S'),
        'generated_text': now.strftime('%Y-%m-%d %H:%M:%S'),
        'page_width': logical_width,
        'logical_height': logical_height,
        'render_scale': render_scale,
        'canvas_width': logical_width * render_scale + 48,
        'canvas_height': logical_height * render_scale + 48,
        'bg_image': bg_image,
        'background_fit_css': background_fit_css,
        'footer_text': texts['powered'],
        'summary_cards': summary_cards,
        'system_metric_cards': system_metric_cards,
        'message_chart': stats.get('message_chart', build_line_chart([])),
        'message_total': format_full_number(stats.get('message_total', 0)),
        'platform_ranking_rows': platform_ranking_rows,
        'token_total': format_full_number(stats.get('today_tokens', 0)),
        'token_chart_bars': stats.get('token_chart_bars', []),
        'token_top': token_top,
        'info_rows': info_rows,
        'disk_rows': disk_rows,
        'process_rows': process_rows,
        **texts,
        **theme_tokens,
    }
