"""Memory Monitoring and Process Inspection Engine.

Provides real-time system memory metrics (RAM, Swap, Pagefile),
process-level memory usage analysis, application grouping,
safety-guarded process termination, and memory health recommendations.
"""

from collections import deque
from datetime import datetime, timezone
import os
import platform
import socket
import time
from typing import Any, Dict, List, Optional, Set

import psutil

# Protected Windows and core OS processes that should never be terminated
SYSTEM_PROTECTED_PROCESSES: Set[str] = {
    "system",
    "system idle process",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "winlogon.exe",
    "dwm.exe",
    "fontdrvhost.exe",
    "svchost.exe",
    "memory compression",
}

# Known applications mapping for enhanced display name & categorization
KNOWN_APPS: Dict[str, Dict[str, str]] = {
    "chrome.exe": {"name": "Google Chrome", "category": "Browsers"},
    "msedge.exe": {"name": "Microsoft Edge", "category": "Browsers"},
    "firefox.exe": {"name": "Mozilla Firefox", "category": "Browsers"},
    "brave.exe": {"name": "Brave Browser", "category": "Browsers"},
    "opera.exe": {"name": "Opera Browser", "category": "Browsers"},
    "code.exe": {"name": "Visual Studio Code", "category": "Development"},
    "devenv.exe": {"name": "Visual Studio", "category": "Development"},
    "antigravity.exe": {"name": "Antigravity IDE / Agent", "category": "Development"},
    "pycharm64.exe": {"name": "JetBrains PyCharm", "category": "Development"},
    "idea64.exe": {"name": "JetBrains IntelliJ", "category": "Development"},
    "node.exe": {"name": "Node.js Engine", "category": "Development"},
    "python.exe": {"name": "Python Runtime", "category": "Development"},
    "python3.exe": {"name": "Python 3 Runtime", "category": "Development"},
    "git.exe": {"name": "Git CLI", "category": "Development"},
    "docker.exe": {"name": "Docker Engine", "category": "Development"},
    "com.docker.backend.exe": {"name": "Docker Desktop Backend", "category": "Development"},
    "explorer.exe": {"name": "Windows File Explorer", "category": "System UI"},
    "taskmgr.exe": {"name": "Windows Task Manager", "category": "System Tools"},
    "msmpeng.exe": {"name": "Microsoft Defender Antivirus", "category": "Security"},
    "serviceshell.exe": {"name": "Service Shell", "category": "Background Services"},
    "searchhost.exe": {"name": "Windows Search Indexer Host", "category": "System Services"},
    "searchindexer.exe": {"name": "Windows Search Indexer", "category": "System Services"},
    "runtimebroker.exe": {"name": "Windows Runtime Broker", "category": "System Services"},
    "slack.exe": {"name": "Slack", "category": "Communication"},
    "discord.exe": {"name": "Discord", "category": "Communication"},
    "teams.exe": {"name": "Microsoft Teams", "category": "Communication"},
    "spotify.exe": {"name": "Spotify", "category": "Media"},
    "vlc.exe": {"name": "VLC Media Player", "category": "Media"},
    "steam.exe": {"name": "Steam", "category": "Gaming"},
}


def format_bytes(num_bytes: int) -> str:
    """Format bytes into readable units (B, KB, MB, GB, TB)."""
    if num_bytes < 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0 or unit == "TB":
            return f"{num_bytes:.2f} {unit}" if unit in ["MB", "GB", "TB"] else f"{num_bytes:.0f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


def get_process_category(name: str) -> str:
    """Determine the likely category of a process."""
    lower_name = name.lower()
    if lower_name in KNOWN_APPS:
        return KNOWN_APPS[lower_name]["category"]
    if lower_name.startswith("system") or lower_name in SYSTEM_PROTECTED_PROCESSES:
        return "Windows Core"
    if "agent" in lower_name or "svc" in lower_name or "service" in lower_name:
        return "Background Services"
    if any(ext in lower_name for ext in ["driver", "host", "broker"]):
        return "System Drivers / Hosts"
    return "Applications"


def get_process_display_name(name: str) -> str:
    """Get user-friendly display name for a binary name."""
    lower_name = name.lower()
    if lower_name in KNOWN_APPS:
        return KNOWN_APPS[lower_name]["name"]
    # Strip .exe extension for cleaner display
    if lower_name.endswith(".exe"):
        clean = name[:-4]
        return clean.replace("_", " ").title()
    return name


class MemoryMonitor:
    """Monitors system memory and process-level memory allocations."""

    def __init__(self, max_history_points: int = 60):
        self.max_history_points = max_history_points
        self.history: deque = deque(maxlen=max_history_points)
        self.boot_time = psutil.boot_time()
        self.hostname = socket.gethostname()
        self.os_info = f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"
        self.cpu_cores = psutil.cpu_count(logical=True)
        self._procs_cache: List[Dict[str, Any]] = []
        self._procs_cache_time: float = 0.0
        self._cache_ttl: float = 1.0
        # Pre-seed history with current state
        self.record_history_snapshot()

    def get_system_summary(self) -> Dict[str, Any]:
        """Fetch comprehensive system memory and hardware overview."""
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Calculate uptime
        uptime_seconds = int(time.time() - self.boot_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        # Determine health status based on RAM usage percentage
        if vm.percent < 70.0:
            health_status = "Optimal"
            health_color = "emerald"
            health_msg = "Memory consumption is within healthy levels."
        elif vm.percent < 85.0:
            health_status = "Moderate"
            health_color = "amber"
            health_msg = "Memory usage is moderate. Plenty of buffer remaining."
        elif vm.percent < 95.0:
            health_status = "High Pressure"
            health_color = "orange"
            health_msg = "High memory usage detected. Consider closing unnecessary background apps."
        else:
            health_status = "Critical"
            health_color = "rose"
            health_msg = "Extremely high memory usage (>95%). System may experience slowdown or swapping."

        return {
            "system": {
                "hostname": self.hostname,
                "os": self.os_info,
                "cpu_cores": self.cpu_cores,
                "uptime": uptime_str,
                "boot_time_iso": datetime.fromtimestamp(self.boot_time, tz=timezone.utc).isoformat(),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            },
            "ram": {
                "total_bytes": vm.total,
                "total_formatted": format_bytes(vm.total),
                "total_gb": round(vm.total / (1024**3), 2),
                "used_bytes": vm.used,
                "used_formatted": format_bytes(vm.used),
                "used_gb": round(vm.used / (1024**3), 2),
                "free_bytes": vm.free,
                "free_formatted": format_bytes(vm.free),
                "free_gb": round(vm.free / (1024**3), 2),
                "available_bytes": vm.available,
                "available_formatted": format_bytes(vm.available),
                "available_gb": round(vm.available / (1024**3), 2),
                "percent": vm.percent,
            },
            "swap": {
                "total_bytes": swap.total,
                "total_formatted": format_bytes(swap.total),
                "total_gb": round(swap.total / (1024**3), 2),
                "used_bytes": swap.used,
                "used_formatted": format_bytes(swap.used),
                "used_gb": round(swap.used / (1024**3), 2),
                "free_bytes": swap.free,
                "free_formatted": format_bytes(swap.free),
                "free_gb": round(swap.free / (1024**3), 2),
                "percent": swap.percent,
            },
            "health": {
                "status": health_status,
                "color": health_color,
                "message": health_msg,
            },
        }

    def record_history_snapshot(self) -> Dict[str, Any]:
        """Record current memory snapshot into rolling history deque."""
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        snapshot = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "ram_percent": round(vm.percent, 1),
            "ram_used_gb": round(vm.used / (1024**3), 2),
            "ram_free_gb": round(vm.available / (1024**3), 2),
            "swap_percent": round(swap.percent, 1),
            "swap_used_gb": round(swap.used / (1024**3), 2),
        }
        self.history.append(snapshot)
        return snapshot

    def get_history(self) -> List[Dict[str, Any]]:
        """Return rolling history of memory data points."""
        return list(self.history)

    def get_raw_processes(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch all running processes with their memory metrics and metadata."""
        now = time.time()
        if not force_refresh and self._procs_cache and (now - self._procs_cache_time < self._cache_ttl):
            return self._procs_cache

        procs: List[Dict[str, Any]] = []
        total_ram = psutil.virtual_memory().total

        # Collect attributes efficiently
        for p in psutil.process_iter(
            attrs=[
                "pid",
                "name",
                "username",
                "memory_info",
                "memory_percent",
                "cpu_percent",
                "status",
                "create_time",
                "num_threads",
            ]
        ):
            try:
                info = p.info
                name = info.get("name") or "Unknown"
                lower_name = name.lower()

                mem_info = info.get("memory_info")
                rss = mem_info.rss if mem_info else 0
                vms = mem_info.vms if mem_info else 0
                mem_mb = round(rss / (1024 * 1024), 2)
                mem_percent = round(info.get("memory_percent") or ((rss / total_ram) * 100 if total_ram else 0.0), 2)

                # Flag protected processes
                is_protected = (
                    info.get("pid") in [0, 4]  # Idle or System on Windows
                    or lower_name in SYSTEM_PROTECTED_PROCESSES
                )

                procs.append({
                    "pid": info.get("pid"),
                    "name": name,
                    "display_name": get_process_display_name(name),
                    "category": get_process_category(name),
                    "username": info.get("username") or "SYSTEM",
                    "rss_bytes": rss,
                    "rss_mb": mem_mb,
                    "rss_formatted": format_bytes(rss),
                    "vms_bytes": vms,
                    "vms_formatted": format_bytes(vms),
                    "memory_percent": mem_percent,
                    "cpu_percent": round(info.get("cpu_percent") or 0.0, 1),
                    "status": info.get("status") or "running",
                    "num_threads": info.get("num_threads") or 1,
                    "create_time": info.get("create_time"),
                    "is_protected": is_protected,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                continue

        self._procs_cache = procs
        self._procs_cache_time = now
        return procs

    def get_processes(
        self,
        grouped: bool = False,
        sort_by: str = "rss",
        sort_order: str = "desc",
        search: str = "",
        min_mb: float = 0.0,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get filtered, sorted, and optionally grouped list of processes."""
        raw_list = self.get_raw_processes()

        if grouped:
            result = self._group_processes(raw_list)
        else:
            result = raw_list

        # Apply Search Filter
        if search:
            search_lower = search.lower().strip()
            result = [
                p
                for p in result
                if search_lower in p["name"].lower()
                or search_lower in p["display_name"].lower()
                or str(p.get("pid", "")).startswith(search_lower)
                or search_lower in p.get("category", "").lower()
                or search_lower in p.get("username", "").lower()
            ]

        # Apply Minimum MB Filter
        if min_mb > 0:
            result = [p for p in result if p["rss_mb"] >= min_mb]

        # Sort items
        reverse = sort_order.lower() == "desc"
        sort_keys = {
            "rss": lambda x: x["rss_bytes"],
            "percent": lambda x: x["memory_percent"],
            "cpu": lambda x: x["cpu_percent"],
            "name": lambda x: x["display_name"].lower(),
            "pid": lambda x: x.get("pid", 0),
            "instances": lambda x: x.get("instance_count", 1),
        }
        key_fn = sort_keys.get(sort_by, sort_keys["rss"])
        result.sort(key=key_fn, reverse=reverse)

        # Apply Limit if specified
        if limit and limit > 0:
            result = result[:limit]

        return result

    def _group_processes(self, procs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group processes with the same binary name to show aggregated app impact."""
        groups: Dict[str, Dict[str, Any]] = {}

        for p in procs:
            app_key = p["name"].lower()
            if app_key not in groups:
                groups[app_key] = {
                    "name": p["name"],
                    "display_name": p["display_name"],
                    "category": p["category"],
                    "instance_count": 0,
                    "pids": [],
                    "rss_bytes": 0,
                    "rss_mb": 0.0,
                    "rss_formatted": "0 B",
                    "vms_bytes": 0,
                    "vms_formatted": "0 B",
                    "memory_percent": 0.0,
                    "cpu_percent": 0.0,
                    "num_threads": 0,
                    "is_protected": p["is_protected"],
                    "usernames": set(),
                }

            group = groups[app_key]
            group["instance_count"] += 1
            group["pids"].append(p["pid"])
            group["rss_bytes"] += p["rss_bytes"]
            group["vms_bytes"] += p["vms_bytes"]
            group["memory_percent"] += p["memory_percent"]
            group["cpu_percent"] += p["cpu_percent"]
            group["num_threads"] += p["num_threads"]
            if p["is_protected"]:
                group["is_protected"] = True
            if p.get("username"):
                group["usernames"].add(p["username"])

        # Format calculated values
        grouped_list = []
        for g in groups.values():
            g["rss_mb"] = round(g["rss_bytes"] / (1024 * 1024), 2)
            g["rss_formatted"] = format_bytes(g["rss_bytes"])
            g["vms_formatted"] = format_bytes(g["vms_bytes"])
            g["memory_percent"] = round(g["memory_percent"], 2)
            g["cpu_percent"] = round(g["cpu_percent"], 1)
            g["username"] = ", ".join(sorted(g["usernames"])) if g["usernames"] else "SYSTEM"
            g["pid"] = g["pids"][0] if len(g["pids"]) == 1 else None
            del g["usernames"]
            grouped_list.append(g)

        return grouped_list

    def get_process_details(self, pid: int) -> Optional[Dict[str, Any]]:
        """Fetch in-depth metadata for a specific process ID."""
        try:
            p = psutil.Process(pid)
            with p.oneshot():
                name = p.name()
                mem_info = p.memory_info()
                total_ram = psutil.virtual_memory().total
                mem_percent = round((mem_info.rss / total_ram) * 100 if total_ram else 0.0, 2)

                try:
                    exe = p.exe()
                except Exception:
                    exe = "Access Denied / Not Available"

                try:
                    cmdline = " ".join(p.cmdline())
                except Exception:
                    cmdline = "Access Denied / Not Available"

                try:
                    cwd = p.cwd()
                except Exception:
                    cwd = "Access Denied"

                create_dt = datetime.fromtimestamp(p.create_time(), tz=timezone.utc)

                is_protected = (
                    pid in [0, 4]
                    or name.lower() in SYSTEM_PROTECTED_PROCESSES
                )

                return {
                    "pid": pid,
                    "name": name,
                    "display_name": get_process_display_name(name),
                    "category": get_process_category(name),
                    "status": p.status(),
                    "username": p.username() if hasattr(p, "username") else "SYSTEM",
                    "rss_bytes": mem_info.rss,
                    "rss_formatted": format_bytes(mem_info.rss),
                    "vms_bytes": mem_info.vms,
                    "vms_formatted": format_bytes(mem_info.vms),
                    "memory_percent": mem_percent,
                    "cpu_percent": round(p.cpu_percent(interval=None), 1),
                    "num_threads": p.num_threads(),
                    "create_time": create_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "exe": exe,
                    "cmdline": cmdline,
                    "cwd": cwd,
                    "is_protected": is_protected,
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None

    def terminate_process(self, pid: int, force: bool = False) -> Dict[str, Any]:
        """Safely terminate a process by PID with OS protection checks."""
        if pid in [0, 4]:
            return {"success": False, "error": f"Cannot terminate Windows core kernel process (PID {pid})."}

        try:
            p = psutil.Process(pid)
            name = p.name().lower()
            if name in SYSTEM_PROTECTED_PROCESSES:
                return {
                    "success": False,
                    "error": f"Termination blocked: '{p.name()}' is a protected Windows core system process.",
                }

            if force:
                p.kill()
            else:
                p.terminate()

            self._procs_cache = []
            return {
                "success": True,
                "message": f"Successfully {'killed' if force else 'terminated'} {p.name()} (PID {pid}).",
            }
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process PID {pid} is no longer running."}
        except psutil.AccessDenied:
            return {
                "success": False,
                "error": f"Access Denied: Administrative privileges required to terminate PID {pid}.",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_recommendations(self) -> Dict[str, Any]:
        """Generate smart memory insights and optimization recommendations."""
        summary = self.get_system_summary()
        grouped = self.get_processes(grouped=True, sort_by="rss", sort_order="desc", limit=10)

        # Separate system vs user applications
        user_apps = [p for p in grouped if not p["is_protected"]]
        top_hogs = user_apps[:5]

        total_hog_mb = sum(p["rss_mb"] for p in top_hogs)
        total_ram_gb = summary["ram"]["total_gb"]
        ram_percent = summary["ram"]["percent"]

        recommendations = []

        if ram_percent >= 90:
            recommendations.append({
                "type": "critical",
                "title": "Severe Memory Constraint",
                "description": f"Physical RAM is at {ram_percent}%. System performance may degrade severely. Review top memory-consuming applications below.",
            })
        elif ram_percent >= 75:
            recommendations.append({
                "type": "warning",
                "title": "Elevated Memory Pressure",
                "description": f"RAM usage is at {ram_percent}%. Closing high-memory background applications can recover significant headroom.",
            })
        else:
            recommendations.append({
                "type": "info",
                "title": "Healthy Memory Balance",
                "description": f"RAM usage is at {ram_percent}% with ample available memory.",
            })

        # Check multi-instance apps
        multi_instances = [p for p in user_apps if p["instance_count"] >= 5 and p["rss_mb"] > 200]
        for mi in multi_instances:
            recommendations.append({
                "type": "tip",
                "title": f"Multiple Instances: {mi['display_name']}",
                "description": f"{mi['display_name']} has {mi['instance_count']} processes running, occupying {mi['rss_formatted']} ({mi['memory_percent']}% of RAM).",
            })

        return {
            "ram_percent": ram_percent,
            "total_hog_mb": round(total_hog_mb, 1),
            "total_hog_formatted": format_bytes(int(total_hog_mb * 1024 * 1024)),
            "top_hogs": top_hogs,
            "recommendations": recommendations,
        }
