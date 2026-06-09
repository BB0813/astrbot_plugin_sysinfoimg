import psutil
import os
import asyncio
import platform
import sys
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from astrbot.api import logger

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    from .utils import fmt_bytes, fmt_rate, fmt_duration, detect_linux_distro
except ImportError:
    from utils import fmt_bytes, fmt_rate, fmt_duration, detect_linux_distro

def norm_mounts(parts_cfg: List[str]) -> List[str]:
    """Normalize mount points for different OS."""
    res = []
    for p in parts_cfg or []:
        if os.name == "nt":
            if len(p) == 2 and p[1] == ":":
                res.append(p + "\\")
            else:
                res.append(p)
        else:
            res.append(p)
    return res

def list_disks(parts_cfg: List[str]) -> Tuple[List[Dict], int, int]:
    """List disk usage for specified mount points or auto-discover."""
    disks = []
    
    def add_disk(mp, fstype="N/A"):
        try:
            du = psutil.disk_usage(mp)
            # Check if already added
            for d in disks:
                if d["mount"] == mp: return
            
            disks.append({
                "mount": mp,
                "percent": int(du.percent),
                "used_h": fmt_bytes(du.used),
                "total_h": fmt_bytes(du.total),
                "used_raw": du.used,
                "total_raw": du.total,
                "fstype": fstype,
                "is_system": False
            })
        except Exception as e:
            logger.debug(f"Failed to get disk usage for {mp}: {e}")

    if parts_cfg:
        for mp in parts_cfg:
            add_disk(mp)
        t_used = sum(d["used_raw"] for d in disks)
        t_total = sum(d["total_raw"] for d in disks)
        return disks, t_used, t_total

    ignore_fstypes = {'squashfs', 'overlay', 'tmpfs', 'devtmpfs', 'iso9660', 'tracefs', 'cgroup', 'sysfs', 'proc', 'autofs', 'fuse.sshfs'}
    ignore_paths = {'/proc', '/sys', '/dev', '/run', '/boot', '/snap'}
    ignore_path_prefixes = ('/var/lib/docker', '/var/lib/kubelet', '/var/lib/containers', '/run/docker', '/run/user', '/etc/')

    system_drive = None
    if os.name == 'nt':
        system_drive = os.environ.get('SystemDrive', 'C:') + '\\'

    try:
        partitions = psutil.disk_partitions(all=False)
        if os.name != 'nt':
                partitions = psutil.disk_partitions(all=True)

        seen_devices = set()
        for p in partitions:
            if p.mountpoint == '/':
                pass
            elif p.fstype in ignore_fstypes: continue
            
            if p.mountpoint in ignore_paths: continue
            if any(p.mountpoint.startswith(prefix) for prefix in ignore_path_prefixes): continue
            if 'ro' in p.opts and 'loop' in p.device: continue
            if p.device.startswith('/dev/'):
                if p.device in seen_devices: continue
                seen_devices.add(p.device)

            mp = p.mountpoint
            try:
                du = psutil.disk_usage(mp)
                if du.total < 100 * 1024 * 1024 and mp != '/': continue
                
                # Check system disk
                is_system = False
                if os.name == 'nt':
                     if system_drive and mp.upper().startswith(system_drive.upper()):
                         is_system = True
                elif mp == '/':
                     is_system = True
                
                add_disk(mp, p.fstype)
                if disks and disks[-1]["mount"] == mp:
                    disks[-1]["is_system"] = is_system
                    
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Error listing partitions: {e}")
        
    if len(disks) > 8:
        disks = disks[:8]

    if not disks and os.name == "nt":
        for code in range(ord('A'), ord('Z')+1):
            mp = chr(code) + ":\\"
            if os.path.exists(mp):
                add_disk(mp, "NTFS") # Assume NTFS usually
    
    if not disks and os.name != "nt":
        for mp in ["/", "/home", "/data", "/mnt", "/var", "/opt"]:
            if os.path.exists(mp):
                add_disk(mp, "ext4") # Guess
    
    t_used = sum(d["used_raw"] for d in disks)
    t_total = sum(d["total_raw"] for d in disks)
    return disks, t_used, t_total

async def net_sample(interfaces: List[str], interval: float = 1.0) -> Tuple[int, int, List[Dict]]:
    """Sample network IO over an interval."""
    try:
        pernic1 = psutil.net_io_counters(pernic=True)
        await asyncio.sleep(interval)
        pernic2 = psutil.net_io_counters(pernic=True)
        
        names = interfaces or [n for n in pernic2.keys() if n != "lo"]
        sent = 0
        recv = 0
        items = []
        
        for n in names:
            if n in pernic1 and n in pernic2:
                up = max(0, pernic2[n].bytes_sent - pernic1[n].bytes_sent) / interval
                down = max(0, pernic2[n].bytes_recv - pernic1[n].bytes_recv) / interval
                sent += up
                recv += down
                items.append({"name": n, "up": up, "down": down})
        return sent, recv, items
    except Exception as e:
        logger.error(f"Network sampling failed: {e}")
        return 0, 0, []

def get_top_processes(n: int, sort_key: str = "memory") -> List[Dict]:
    """Get top N processes sorted by memory or cpu."""
    def rss_fallback(pid):
        try:
            if os.name != "nt":
                path = f"/proc/{pid}/status"
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if line.startswith("VmRSS:"):
                                parts = line.split()
                                if len(parts) >= 2:
                                    return int(float(parts[1]) * 1024)
        except Exception: pass
        return None

    procs = []
    try:
        # Initial iteration to grab objects
        candidates = []
        for p in psutil.process_iter(attrs=["pid", "name", "username", "cmdline", "cpu_percent"]):
            candidates.append(p)
            
        # If sorting by CPU, we need a second sample or rely on the first one if it's been running
        # psutil.cpu_percent() on a process needs an interval or a previous call.
        # The first call returns 0.0.
        # Let's do a quick sleep-and-sample if we really want accuracy, but that blocks.
        # Ideally, we should use the one-shot if available or just accept 0 for first run.
        # However, in main.py logic, it did a pre-heat. We'll skip pre-heat here to keep it simple 
        # or assume caller handles pre-heat if they want strict accuracy.
        # But wait, main.py did: p.cpu_percent() (init) -> sleep -> p.cpu_percent() (val).
        # We can replicate that if we make this async or split it.
        # For now, let's just do the single pass and use whatever psutil gives, 
        # assuming the caller might have initialized psutil context or we accept 0 for new procs.
        # Actually, let's just implement the logic:
        
        for p in candidates:
            try:
                # If we want accurate CPU, we need to wait. But we can't wait per process.
                # The best way in a synchronous function without delay is to use the cached value 
                # or accept that the first call is 0.
                # However, since this function is called after a 1s sleep in main logic usually,
                # we can try to call cpu_percent(interval=None) again if it was called before.
                
                # To make this robust:
                cpu = 0
                try:
                    # This returns 0.0 immediately if it's the first call.
                    cpu = p.cpu_percent(interval=None)
                except: pass

                pid = p.info.get("pid")
                name = p.info.get("name")
                if not name:
                    cmd = p.info.get("cmdline") or []
                    if isinstance(cmd, list) and len(cmd) > 0:
                        name = os.path.basename(cmd[0])
                    else:
                        name = f"pid:{pid}"
                
                mem = None
                try:
                    mem = p.memory_info().rss
                except Exception:
                    mem = rss_fallback(pid)
                
                if mem is None: continue
                
                percent = 0
                try:
                    percent = int(p.memory_percent())
                except Exception: percent = 0

                procs.append({
                    "pid": pid,
                    "name": name,
                    "username": p.info.get("username") or "N/A",
                    "mem": mem,
                    "mem_h": fmt_bytes(mem),
                    "mem_percent": percent,
                    "cpu": cpu
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        logger.error(f"Error getting processes: {e}")
    
    if sort_key == "cpu":
        procs.sort(key=lambda x: x["cpu"], reverse=True)
    else:
        procs.sort(key=lambda x: x["mem"], reverse=True)
    return procs[:max(1, n)]

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _run_optional_command(command: List[str], timeout: float = 2.0) -> Optional[str]:
    binary = shutil.which(command[0])
    if not binary:
        return None
    try:
        completed = subprocess.run(
            [binary, *command[1:]],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug(f'Optional command failed: {command!r}: {exc}')
        return None
    if completed.returncode != 0:
        return None
    stdout = (completed.stdout or '').strip()
    return stdout or None


def _read_battery_info() -> Optional[Dict[str, Any]]:
    battery_reader = getattr(psutil, 'sensors_battery', None)
    if not callable(battery_reader):
        return None
    try:
        battery = battery_reader()
    except Exception as exc:
        logger.debug(f'Failed to read battery info: {exc}')
        return None
    if battery is None:
        return None

    percent = int(round(_safe_float(getattr(battery, 'percent', 0), 0.0)))
    plugged = bool(getattr(battery, 'power_plugged', False))
    seconds_left = getattr(battery, 'secsleft', None)
    unknown = getattr(psutil, 'POWER_TIME_UNKNOWN', -2)
    unlimited = getattr(psutil, 'POWER_TIME_UNLIMITED', -1)
    time_left = None
    if isinstance(seconds_left, (int, float)) and seconds_left >= 0 and seconds_left not in (unknown, unlimited):
        time_left = fmt_duration(float(seconds_left))

    return {
        'source': 'psutil.sensors_battery',
        'percent': max(0, min(100, percent)),
        'plugged': plugged,
        'secsleft': seconds_left if isinstance(seconds_left, (int, float)) else None,
        'time_left': time_left,
        'status': 'charging' if plugged else 'battery',
    }


def _normalize_temperature_samples(source_name: str, entries: Any) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for entry in entries or []:
        current_c = _safe_float(getattr(entry, 'current', None), float('nan'))
        if current_c != current_c:
            continue
        label = str(getattr(entry, 'label', '') or source_name).strip()
        high_c = _safe_float(getattr(entry, 'high', None), 0.0)
        critical_c = _safe_float(getattr(entry, 'critical', None), 0.0)
        normalized.append({
            'source': source_name,
            'label': label,
            'current_c': round(current_c, 1),
            'high_c': round(high_c, 1) if high_c > 0 else None,
            'critical_c': round(critical_c, 1) if critical_c > 0 else None,
        })
    return normalized


def _read_linux_thermal_zones() -> List[Dict[str, Any]]:
    base_dir = '/sys/class/thermal'
    samples: List[Dict[str, Any]] = []
    if not os.path.isdir(base_dir):
        return samples
    try:
        for entry in os.listdir(base_dir):
            if not entry.startswith('thermal_zone'):
                continue
            zone_dir = os.path.join(base_dir, entry)
            temp_path = os.path.join(zone_dir, 'temp')
            type_path = os.path.join(zone_dir, 'type')
            if not os.path.isfile(temp_path):
                continue
            try:
                raw_temp = Path(temp_path).read_text(encoding='utf-8', errors='ignore').strip()
                current_c = float(raw_temp) / 1000.0
            except Exception:
                continue
            try:
                label = Path(type_path).read_text(encoding='utf-8', errors='ignore').strip()
            except Exception:
                label = entry
            samples.append({
                'source': 'linux_thermal',
                'label': label or entry,
                'current_c': round(current_c, 1),
                'high_c': None,
                'critical_c': None,
            })
    except Exception as exc:
        logger.debug(f'Failed to read linux thermal zones: {exc}')
    return samples


def _read_temperature_info() -> Optional[Dict[str, Any]]:
    samples: List[Dict[str, Any]] = []
    probe_sources: List[str] = []
    temp_reader = getattr(psutil, 'sensors_temperatures', None)
    if callable(temp_reader):
        try:
            temp_map = temp_reader(fahrenheit=False) or {}
            for source_name, entries in temp_map.items():
                normalized = _normalize_temperature_samples(str(source_name), entries)
                if normalized and 'psutil.sensors_temperatures' not in probe_sources:
                    probe_sources.append('psutil.sensors_temperatures')
                samples.extend(normalized)
        except Exception as exc:
            logger.debug(f'Failed to read temperature sensors: {exc}')
    if not samples and platform.system() == 'Linux':
        samples = _read_linux_thermal_zones()
        if samples:
            probe_sources.append('linux_thermal')
    if not samples:
        return None

    hottest = max(samples, key=lambda item: item.get('current_c', 0.0))
    average_c = sum(item.get('current_c', 0.0) for item in samples) / max(1, len(samples))
    threshold_candidates = [item.get('critical_c') or item.get('high_c') for item in samples if item.get('critical_c') or item.get('high_c')]
    reference_c = max(threshold_candidates) if threshold_candidates else 100.0
    if not probe_sources:
        probe_sources = sorted({str(item.get('source') or '').strip() for item in samples if str(item.get('source') or '').strip()})
    return {
        'source': ' / '.join(probe_sources) if probe_sources else str(hottest.get('source') or 'sensor'),
        'sources': probe_sources,
        'current_c': round(_safe_float(hottest.get('current_c'), 0.0), 1),
        'average_c': round(average_c, 1),
        'label': str(hottest.get('label') or hottest.get('source') or 'sensor'),
        'sensor_count': len(samples),
        'reference_c': round(reference_c, 1),
        'samples': samples[:6],
    }


def _read_gpu_info() -> Optional[Dict[str, Any]]:
    output = _run_optional_command([
        'nvidia-smi',
        '--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total',
        '--format=csv,noheader,nounits',
    ], timeout=2.5)
    if not output:
        return None

    gpus: List[Dict[str, Any]] = []
    for raw_line in output.splitlines():
        parts = [part.strip() for part in raw_line.split(',')]
        if len(parts) < 5:
            continue
        name = parts[0] or 'NVIDIA GPU'
        util_percent = max(0.0, min(100.0, _safe_float(parts[1], 0.0)))
        temp_c = _safe_float(parts[2], 0.0)
        memory_used_mib = max(0.0, _safe_float(parts[3], 0.0))
        memory_total_mib = max(0.0, _safe_float(parts[4], 0.0))
        mem_percent = (memory_used_mib * 100.0 / memory_total_mib) if memory_total_mib > 0 else 0.0
        gpus.append({
            'name': name,
            'util_percent': round(util_percent, 1),
            'temp_c': round(temp_c, 1) if temp_c > 0 else None,
            'mem_percent': round(mem_percent, 1),
            'memory_used_h': fmt_bytes(memory_used_mib * 1024 * 1024),
            'memory_total_h': fmt_bytes(memory_total_mib * 1024 * 1024),
        })
    if not gpus:
        return None

    primary = max(gpus, key=lambda item: (item.get('util_percent', 0.0), item.get('mem_percent', 0.0)))
    return {
        'source': 'nvidia-smi',
        'name': primary.get('name', 'NVIDIA GPU'),
        'util_percent': primary.get('util_percent', 0.0),
        'temp_c': primary.get('temp_c'),
        'mem_percent': primary.get('mem_percent', 0.0),
        'memory_used_h': primary.get('memory_used_h', '0 B'),
        'memory_total_h': primary.get('memory_total_h', '0 B'),
        'count': len(gpus),
        'gpus': gpus[:4],
    }


def _read_container_info() -> Optional[Dict[str, Any]]:
    output = _run_optional_command(['docker', 'ps', '-a', '--format', '{{.Names}}	{{.State}}'], timeout=2.5)
    if output is None:
        return None

    items: List[Dict[str, str]] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if '	' in line:
            name, state = line.split('	', 1)
        else:
            name, state = line, ''
        items.append({'name': name.strip(), 'state': state.strip().lower() or 'unknown'})

    state_counts: Dict[str, int] = {}
    running_names: List[str] = []
    stopped_names: List[str] = []
    for item in items:
        state = item['state']
        state_counts[state] = state_counts.get(state, 0) + 1
        if state == 'running':
            running_names.append(item['name'])
        else:
            stopped_names.append(item['name'])

    total_count = len(items)
    running_count = len(running_names)
    stopped_count = len(stopped_names)
    return {
        'source': 'docker ps -a',
        'runtime': 'docker',
        'running': running_count,
        'total': total_count,
        'stopped': stopped_count,
        'paused': state_counts.get('paused', 0),
        'restarting': state_counts.get('restarting', 0),
        'dead': state_counts.get('dead', 0),
        'states': state_counts,
        'names': running_names[:4],
        'stopped_names': stopped_names[:4],
    }


def _build_host_capabilities(battery: Optional[Dict[str, Any]], temperature: Optional[Dict[str, Any]], gpu: Optional[Dict[str, Any]], containers: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    available = []
    sources: Dict[str, str] = {}
    if battery:
        available.append('battery')
        if battery.get('source'):
            sources['battery'] = str(battery.get('source'))
    if temperature:
        available.append('temperature')
        if temperature.get('source'):
            sources['temperature'] = str(temperature.get('source'))
    if gpu:
        available.append('gpu')
        if gpu.get('source'):
            sources['gpu'] = str(gpu.get('source'))
    if containers:
        available.append('containers')
        if containers.get('source'):
            sources['containers'] = str(containers.get('source'))
    return {
        'battery': bool(battery),
        'temperature': bool(temperature),
        'gpu': bool(gpu),
        'containers': bool(containers),
        'available': available,
        'available_count': len(available),
        'temperature_sensors': int((temperature or {}).get('sensor_count', 0) or 0),
        'gpu_count': int((gpu or {}).get('count', 0) or 0),
        'container_total': int((containers or {}).get('total', 0) or 0),
        'sources': sources,
    }


async def collect_system_info(
    show_cpu: bool = True,
    show_memory: bool = True,
    show_swap: bool = True,
    show_disk: bool = True,
    disk_partitions: List[str] = None,
    show_disk_total: bool = True,
    show_network: bool = True,
    network_interfaces: List[str] = None,
    show_network_per_iface: bool = False,
    show_top_processes: bool = True,
    top_n: int = 10,
    process_sort_key: str = "cpu",
    enable_deep_host_metrics: bool = True,
    show_battery: bool = True,
    show_temperature: bool = True,
    show_gpu: bool = True,
    show_containers: bool = True,
) -> Dict[str, Any]:
    """Collect all system metrics."""
    
    # --- Phase 1: Initialization & Pre-heat ---
    if show_cpu:
        psutil.cpu_percent(interval=None)

    net_start = None
    if show_network:
        try:
            net_start = psutil.net_io_counters(pernic=True)
        except Exception: pass

    procs_list = []
    if show_top_processes:
        try:
            for p in psutil.process_iter(['pid', 'name', 'username', 'cmdline']):
                try:
                    p.cpu_percent() # Init call
                    procs_list.append(p)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception: pass

    # --- Phase 2: Sampling Window ---
    await asyncio.sleep(1.0)

    # --- Phase 3: Collection ---
    data = {}

    # Basic Info
    try:
        data["processor"] = platform.processor() or "Unknown CPU"
        # Try to get more detailed CPU name on Linux
        if platform.system() == "Linux":
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            data["processor"] = line.split(":")[1].strip()
                            break
            except: pass
            
        data["kernel"] = platform.release()
        data["distro"] = detect_linux_distro().title() if platform.system() == "Linux" else platform.system()
        data["load_avg"] = " / ".join([f"{x:.2f}" for x in os.getloadavg()]) if hasattr(os, "getloadavg") else "N/A"
    except Exception:
        data["processor"] = "Unknown"
        data["kernel"] = "Unknown"
        data["distro"] = "Unknown"
        data["load_avg"] = "N/A"

    # CPU
    data["cpu_percent"] = psutil.cpu_percent(interval=None) if show_cpu else 0

    # Memory
    if show_memory:
        mem = psutil.virtual_memory()
        data["mem"] = {
            "percent": int(mem.percent),
            "used_h": fmt_bytes(mem.used),
            "total_h": fmt_bytes(mem.total),
        }
    else:
        data["mem"] = None

    # Swap
    if show_swap:
        swap = psutil.swap_memory()
        data["swap"] = {
            "percent": int(swap.percent),
            "used_h": fmt_bytes(swap.used),
            "total_h": fmt_bytes(swap.total),
        }
    else:
        data["swap"] = None

    # Disk
    data["disk_info"] = []
    data["disk_total"] = None
    if show_disk:
        norm_parts = norm_mounts(disk_partitions)
        d_list, t_used, t_total = list_disks(norm_parts)
        data["disk_info"] = d_list
        
        if t_total > 0:
            data["disk_total"] = {
                "percent": int(t_used * 100 / t_total),
                "used_h": fmt_bytes(t_used),
                "total_h": fmt_bytes(t_total),
            }
        elif show_disk_total:
             # Fallback
             try:
                used_b = 0
                total_b = 0
                for p in psutil.disk_partitions(all=True):
                    try:
                        du = psutil.disk_usage(p.mountpoint)
                        used_b += du.used
                        total_b += du.total
                    except: pass
                if total_b > 0:
                    data["disk_total"] = {
                        "percent": int(used_b * 100 / total_b),
                        "used_h": fmt_bytes(used_b),
                        "total_h": fmt_bytes(total_b),
                    }
             except: pass

    # Network
    data["net_sent"] = 0
    data["net_recv"] = 0
    data["net_per"] = []
    data["net_sent_str"] = "0 B/s"
    data["net_recv_str"] = "0 B/s"
    
    if show_network and net_start:
        try:
            net_end = psutil.net_io_counters(pernic=True)
            names = network_interfaces or [n for n in net_end.keys() if n != "lo" and n in net_start]
            
            for n in names:
                if n in net_start and n in net_end:
                    up = max(0, net_end[n].bytes_sent - net_start[n].bytes_sent)
                    down = max(0, net_end[n].bytes_recv - net_start[n].bytes_recv)
                    data["net_sent"] += up
                    data["net_recv"] += down
                    if show_network_per_iface:
                        data["net_per"].append({"name": n, "up": up, "down": down})
            
            data["net_sent_str"] = fmt_rate(data["net_sent"])
            data["net_recv_str"] = fmt_rate(data["net_recv"])
        except Exception: pass

    # Deep Host Metrics
    battery_info = None
    temperature_info = None
    gpu_info = None
    container_info = None
    if enable_deep_host_metrics:
        if show_battery:
            battery_info = _read_battery_info()
        if show_temperature:
            temperature_info = _read_temperature_info()
        if show_gpu:
            gpu_info = _read_gpu_info()
        if show_containers:
            container_info = _read_container_info()
    data["battery"] = battery_info
    data["temperature"] = temperature_info
    data["gpu"] = gpu_info
    data["containers"] = container_info
    data["host_capabilities"] = _build_host_capabilities(
        battery_info,
        temperature_info,
        gpu_info,
        container_info,
    )

    # Processes
    data["top_procs"] = []
    if show_top_processes and procs_list:
        processed_procs = []
        for p in procs_list:
            try:
                cpu = p.cpu_percent()
                mem_info = p.memory_info()
                mem_rss = mem_info.rss
                
                name = p.info.get('name')
                if not name:
                    cmd = p.info.get('cmdline')
                    if cmd: name = os.path.basename(cmd[0])
                    else: name = f"pid:{p.pid}"

                processed_procs.append({
                    "pid": p.pid,
                    "name": name,
                    "username": p.info.get('username') or "N/A",
                    "mem": mem_rss,
                    "mem_h": fmt_bytes(mem_rss),
                    "cpu": cpu
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if process_sort_key == "cpu":
            processed_procs.sort(key=lambda x: (x["cpu"], x["mem"]), reverse=True)
        else:
            processed_procs.sort(key=lambda x: (x["mem"], x["cpu"]), reverse=True)
        
        data["top_procs"] = processed_procs[:top_n]

    return data
