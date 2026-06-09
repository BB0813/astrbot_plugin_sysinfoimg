import datetime
import json
import os
import threading
from typing import Any, Dict, List, Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(CURRENT_DIR, "system_history.json")
HISTORY_LOCK = threading.Lock()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_record(record: Dict[str, Any]) -> Optional[Dict[str, float]]:
    if not isinstance(record, dict):
        return None
    timestamp = _safe_float(record.get("timestamp"), 0.0)
    if timestamp <= 0:
        return None
    return {
        "timestamp": timestamp,
        "cpu_percent": max(0.0, _safe_float(record.get("cpu_percent"), 0.0)),
        "memory_percent": max(0.0, _safe_float(record.get("memory_percent"), 0.0)),
        "swap_percent": max(0.0, _safe_float(record.get("swap_percent"), 0.0)),
        "disk_percent": max(0.0, _safe_float(record.get("disk_percent"), 0.0)),
        "network_up_bps": max(0.0, _safe_float(record.get("network_up_bps"), 0.0)),
        "network_down_bps": max(0.0, _safe_float(record.get("network_down_bps"), 0.0)),
        "network_total_bps": max(0.0, _safe_float(record.get("network_total_bps"), 0.0)),
        "gpu_util_percent": max(0.0, _safe_float(record.get("gpu_util_percent"), 0.0)),
        "gpu_mem_percent": max(0.0, _safe_float(record.get("gpu_mem_percent"), 0.0)),
        "gpu_present": max(0.0, _safe_float(record.get("gpu_present"), 0.0)),
        "temperature_c": max(0.0, _safe_float(record.get("temperature_c"), 0.0)),
        "temperature_present": max(0.0, _safe_float(record.get("temperature_present"), 0.0)),
    }


def _read_records_unlocked() -> List[Dict[str, float]]:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except Exception:
        return []
    rows = payload.get("samples", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []
    normalized: List[Dict[str, float]] = []
    for row in rows:
        item = _normalize_record(row)
        if item is not None:
            normalized.append(item)
    normalized.sort(key=lambda item: item["timestamp"])
    return normalized


def _write_records_unlocked(records: List[Dict[str, float]]) -> None:
    tmp_path = HISTORY_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as file:
        json.dump({"samples": records}, file, ensure_ascii=False, indent=2)
    os.replace(tmp_path, HISTORY_FILE)


def estimate_history_max_entries(retention_hours: int, sample_minutes: int) -> int:
    safe_hours = max(1, int(retention_hours or 1))
    safe_minutes = max(1, int(sample_minutes or 1))
    return max(288, int((safe_hours * 60) / safe_minutes) + 128)


def build_history_record(sysinfo: Dict[str, Any], timestamp: Optional[float] = None) -> Dict[str, float]:
    disk_total = sysinfo.get("disk_total") or {}
    disk_percent = _safe_float(disk_total.get("percent"), 0.0)
    for row in sysinfo.get("disk_info") or []:
        disk_percent = max(disk_percent, _safe_float(row.get("percent"), 0.0))
    up = max(0.0, _safe_float(sysinfo.get("net_sent"), 0.0))
    down = max(0.0, _safe_float(sysinfo.get("net_recv"), 0.0))
    memory = sysinfo.get("mem") or {}
    swap = sysinfo.get("swap") or {}
    gpu = sysinfo.get("gpu") or {}
    temperature = sysinfo.get("temperature") or {}
    gpu_present = 1.0 if gpu else 0.0
    temperature_present = 1.0 if temperature else 0.0
    return {
        "timestamp": float(timestamp or datetime.datetime.now().timestamp()),
        "cpu_percent": max(0.0, _safe_float(sysinfo.get("cpu_percent"), 0.0)),
        "memory_percent": max(0.0, _safe_float(memory.get("percent"), 0.0)),
        "swap_percent": max(0.0, _safe_float(swap.get("percent"), 0.0)),
        "disk_percent": max(0.0, disk_percent),
        "network_up_bps": up,
        "network_down_bps": down,
        "network_total_bps": up + down,
        "gpu_util_percent": max(0.0, _safe_float(gpu.get("util_percent"), 0.0)),
        "gpu_mem_percent": max(0.0, _safe_float(gpu.get("mem_percent"), 0.0)),
        "gpu_present": gpu_present,
        "temperature_c": max(0.0, _safe_float(temperature.get("current_c"), 0.0)),
        "temperature_present": temperature_present,
    }


def append_history_sample(
    sample: Dict[str, Any],
    retention_hours: int = 72,
    max_entries: int = 1024,
    dedupe_window_seconds: int = 45,
) -> int:
    record = _normalize_record(sample)
    if record is None:
        return 0
    retention_seconds = max(3600, int(retention_hours or 72) * 3600)
    with HISTORY_LOCK:
        records = _read_records_unlocked()
        cutoff = record["timestamp"] - retention_seconds
        records = [row for row in records if row["timestamp"] >= cutoff]
        if records and abs(records[-1]["timestamp"] - record["timestamp"]) <= max(0, int(dedupe_window_seconds or 0)):
            records[-1] = record
        else:
            records.append(record)
        if max_entries and len(records) > int(max_entries):
            records = records[-int(max_entries):]
        _write_records_unlocked(records)
        return len(records)


def load_history_samples(hours: Optional[int] = 24, limit: Optional[int] = None) -> List[Dict[str, float]]:
    with HISTORY_LOCK:
        records = _read_records_unlocked()
    if hours is not None and int(hours or 0) > 0:
        cutoff = datetime.datetime.now().timestamp() - int(hours) * 3600
        records = [row for row in records if row["timestamp"] >= cutoff]
    if limit is not None and int(limit or 0) > 0:
        records = records[-int(limit):]
    return records


def build_alert_history_context(locale: str, metric_keys: List[str], within_hours: int = 1) -> str:
    samples = load_history_samples(hours=max(1, int(within_hours or 1)))
    if not samples:
        return ""
    mapping = {
        "cpu": ("cpu_percent", "CPU", "CPU", "%"),
        "memory": ("memory_percent", "\u5185\u5b58", "Memory", "%"),
        "disk": ("disk_percent", "\u78c1\u76d8", "Disk", "%"),
        "swap": ("swap_percent", "Swap", "Swap", "%"),
        "gpu": ("gpu_util_percent", "GPU", "GPU", "%"),
        "temperature": ("temperature_c", "\u6e29\u5ea6", "Temperature", "\u00b0C"),
    }
    rows = []
    for key in metric_keys:
        if key not in mapping:
            continue
        field, zh_label, en_label, unit = mapping[key]
        values = [max(0.0, _safe_float(item.get(field), 0.0)) for item in samples]
        if not values:
            continue
        label = zh_label if locale == "zh" else en_label
        rows.append(f"{label} {max(values):.0f}{unit}")
    if not rows:
        return ""
    hours = max(1, int(within_hours or 1))
    if locale == "zh":
        return f"\u8fd1 {hours} \u5c0f\u65f6\u5cf0\u503c\uff1a" + " / ".join(rows)
    return f"Last {hours}h peaks: " + " / ".join(rows)
