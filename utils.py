import os
import base64
import platform
import subprocess
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("astrbot")

def detect_linux_distro() -> str:
    """Detect Linux distribution."""
    try:
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if line.startswith('ID='):
                        return line.split('=')[1].strip().strip('"').lower()

        try:
            result = subprocess.run(['lsb_release', '-i'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.stdout:
                return result.stdout.split(':')[1].strip().lower()
        except Exception:
            pass

        if os.path.exists('/usr/bin/apt-get'):
            return 'ubuntu'
        if os.path.exists('/usr/bin/dnf'):
            return 'fedora'
        if os.path.exists('/usr/bin/yum'):
            return 'centos'
        if os.path.exists('/usr/bin/zypper'):
            return 'opensuse'
        if os.path.exists('/usr/bin/pacman'):
            return 'arch'

        return 'unknown'
    except Exception as e:
        logger.warning(f"Failed to detect Linux distro: {e}")
        return 'unknown'

def install_chinese_fonts():
    """Install Chinese fonts on Linux if missing."""
    if platform.system() == "Windows":
        return

    try:
        distro = detect_linux_distro()
        logger.info(f"Detected Linux distro for font check: {distro}")

        common_paths = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        ]
        if any(os.path.exists(p) for p in common_paths):
            logger.info("Chinese fonts seem to be present.")
            return

        install_commands = {
            'ubuntu': ['apt-get', 'update', '-y'],
            'debian': ['apt-get', 'update', '-y'],
            'linuxmint': ['apt-get', 'update', '-y'],
            'fedora': ['dnf', 'update', '-y'],
            'centos': ['yum', 'update', '-y'],
            'redhat': ['yum', 'update', '-y'],
            'opensuse': ['zypper', 'refresh'],
            'arch': ['pacman', '-Syu', '--noconfirm'],
        }

        font_packages = {
            'ubuntu': ['fonts-wqy-microhei', 'fonts-wqy-zenhei', 'fonts-noto-cjk'],
            'debian': ['fonts-wqy-microhei', 'fonts-wqy-zenhei', 'fonts-noto-cjk'],
            'linuxmint': ['fonts-wqy-microhei', 'fonts-wqy-zenhei', 'fonts-noto-cjk'],
            'fedora': ['wqy-microhei-fonts', 'wqy-zenhei-fonts', 'google-noto-cjk-fonts-common'],
            'centos': ['wqy-microhei-fonts', 'wqy-zenhei-fonts', 'google-noto-cjk-fonts-common'],
            'redhat': ['wqy-microhei-fonts', 'wqy-zenhei-fonts', 'google-noto-cjk-fonts-common'],
            'opensuse': ['wqy-microhei-fonts', 'wqy-zenhei-fonts', 'google-noto-cjk-fonts'],
            'arch': ['ttf-wqy-microhei', 'ttf-wqy-zenhei', 'noto-fonts-cjk'],
        }

        if distro in install_commands and distro in font_packages:
            logger.info(f"Attempting to install fonts for {distro}...")
            subprocess.run(install_commands[distro], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            pkgs = font_packages[distro]
            if distro in ['ubuntu', 'debian', 'linuxmint']:
                cmd = ['apt-get', 'install', '-y'] + pkgs
            elif distro == 'fedora':
                cmd = ['dnf', 'install', '-y'] + pkgs
            elif distro in ['centos', 'redhat']:
                cmd = ['yum', 'install', '-y'] + pkgs
            elif distro == 'opensuse':
                cmd = ['zypper', 'install', '-y'] + pkgs
            else:
                cmd = ['pacman', '-S', '--noconfirm'] + pkgs

            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info("Fonts installed successfully.")

            try:
                subprocess.run(['fc-cache', '-fv'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception:
                pass
        else:
            logger.warning(f"Automatic font installation not supported for {distro}")

    except Exception as e:
        logger.warning(f"Font installation failed: {e}")

def fmt_bytes(n: int) -> str:
    """Format bytes to human-readable string."""
    units = ["B", "KB", "MB", "GB", "TB"]
    step = 0
    value = float(n)
    while value >= 1024 and step < len(units) - 1:
        value /= 1024
        step += 1
    return f"{value:.1f}{units[step]}"

def fmt_duration(seconds: float) -> str:
    """Format seconds to duration string."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def fmt_rate(b_per_sec: float) -> str:
    """Format bytes per second to rate string."""
    if b_per_sec < 1024:
        return f"{int(b_per_sec)} B/s"
    if b_per_sec < 1024 * 1024:
        return f"{b_per_sec / 1024:.1f} KB/s"
    return f"{b_per_sec / 1024 / 1024:.1f} MB/s"

def merge_config(plugin_config: Dict[str, Any],
                 session_config: Optional[Dict[str, Any]],
                 command_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    effective = dict(plugin_config or {})
    if session_config and isinstance(session_config, dict):
        for key in list(effective.keys()):
            if key in session_config:
                effective[key] = session_config[key]
    if command_params and isinstance(command_params, dict):
        for key, value in command_params.items():
            if value is not None:
                effective[key] = value
    return effective

def resolve_background(mode: str,
                       url: str,
                       file_path: str,
                       auto_background: bool,
                       fit: str) -> Tuple[str, str]:
    """Resolve background image URL/data and CSS fit property."""
    if auto_background and mode == "none":
        if url:
            mode = "url"
        elif file_path:
            mode = "file"

    bg_image = ""
    if mode == "url" and url:
        bg_image = url
    elif mode == "file" and file_path:
        try:
            fp = file_path
            if not os.path.isabs(fp):
                if not os.path.exists(fp):
                    parent = os.path.dirname(os.path.dirname(__file__))
                    if os.path.exists(os.path.join(parent, fp)):
                        fp = os.path.join(parent, fp)
                    else:
                        fp = os.path.join(os.path.dirname(__file__), fp)

            with open(fp, "rb") as f:
                data = f.read()
            ext = os.path.splitext(fp)[1][1:] or "jpeg"
            mime = f"image/{ext}"
            bg_image = "data:" + mime + ";base64," + base64.b64encode(data).decode()
        except Exception:
            bg_image = ""

    if fit == "fill":
        fit_css = "100% 100%"
    elif fit == "contain":
        fit_css = "contain"
    else:
        fit_css = "cover"

    return bg_image, fit_css

LABELS = {
    "zh": {
        "cpu": "CPU",
        "memory": "内存",
        "disk": "磁盘",
        "network": "网络",
        "swap": "交换内存",
        "total": "总览",
        "no_part": "无可用分区",
        "top": "进程榜单",
        "powered": "Powered by AstrBot",
        "system_info": "系统信息",
        "basic_info": "基础信息",
        "hostname": "主机名",
        "processor": "处理器",
        "kernel": "内核版本",
        "uptime": "运行时长",
        "load_avg": "系统负载",
        "current_time": "当前时间",
        "upload": "上传速率",
        "download": "下载速率",
        "interfaces": "网卡明细",
        "summary": "摘要",
        "disk_usage": "磁盘占用",
        "used": "已用",
        "total_capacity": "总容量",
        "status": "状态",
        "user": "用户",
        "usage": "占用",
        "no_data": "暂无数据",
        "auto_layout": "自适应布局",
        "astrbot": "AstrBot",
        "dashboard_user": "Dashboard 用户",
        "provider": "当前提供商",
        "model": "当前模型",
        "plugins": "插件数",
        "platforms": "平台数",
        "providers": "提供商数"
    },
    "en": {
        "cpu": "CPU",
        "memory": "Memory",
        "disk": "Disk",
        "network": "Network",
        "swap": "Swap",
        "total": "Total",
        "no_part": "No partitions",
        "top": "Top Processes",
        "powered": "Powered by AstrBot",
        "system_info": "System Info",
        "basic_info": "Overview",
        "hostname": "Hostname",
        "processor": "Processor",
        "kernel": "Kernel",
        "uptime": "Uptime",
        "load_avg": "Load Average",
        "current_time": "Current Time",
        "upload": "Upload",
        "download": "Download",
        "interfaces": "Interfaces",
        "summary": "Summary",
        "disk_usage": "Disk Usage",
        "used": "Used",
        "total_capacity": "Total",
        "status": "Status",
        "user": "User",
        "usage": "Usage",
        "no_data": "No data",
        "auto_layout": "Adaptive Layout",
        "astrbot": "AstrBot",
        "dashboard_user": "Dashboard User",
        "provider": "Current Provider",
        "model": "Current Model",
        "plugins": "Plugins",
        "platforms": "Platforms",
        "providers": "Providers"
    }
}

def get_labels(locale: str) -> Dict[str, str]:
    if locale not in LABELS:
        locale = "en"

    labels = {}
    for key in LABELS["en"].keys():
        if locale in LABELS and key in LABELS[locale]:
            labels[f"label_{key}"] = LABELS[locale][key]
        else:
            labels[f"label_{key}"] = LABELS["en"][key]
    return labels
