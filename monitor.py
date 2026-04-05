import psutil
import os
import asyncio
import platform
from typing import List, Dict, Tuple, Optional, Any
from astrbot.api import logger
from utils import fmt_bytes, fmt_rate, detect_linux_distro

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
    process_sort_key: str = "cpu"
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
