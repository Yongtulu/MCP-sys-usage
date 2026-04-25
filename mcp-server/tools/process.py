"""
系统进程列表工具模块
使用 psutil 库获取本地机器当前运行的系统进程信息
"""

import psutil


def get_process_list(limit: int = 20, sort_by: str = "cpu") -> dict:
    """
    获取系统进程列表

    参数:
        limit: 返回的进程数量上限，默认 20 条
        sort_by: 排序依据，支持 "cpu"（按 CPU 使用率）或 "memory"（按内存使用率），默认 "cpu"

    返回:
        包含以下字段的字典:
            - total_processes: 系统当前总进程数
            - sort_by: 实际使用的排序字段
            - processes: 进程信息列表，每条包含:
                - pid: 进程 ID
                - name: 进程名称
                - cpu_percent: CPU 使用率（%）
                - memory_percent: 内存使用率（%）
                - status: 进程状态（running / sleeping 等）
                - username: 运行该进程的用户名
    """
    processes = []

    # 遍历所有进程，获取每个进程的详细信息
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status", "username"]):
        try:
            info = proc.info

            # 过滤掉 cpu_percent 和 memory_percent 为 None 的进程（通常是系统内核线程）
            if info["cpu_percent"] is None or info["memory_percent"] is None:
                continue

            processes.append({
                "pid": info["pid"],
                "name": info["name"] or "unknown",
                "cpu_percent": round(info["cpu_percent"], 1),
                "memory_percent": round(info["memory_percent"], 2),
                "status": info["status"] or "unknown",
                "username": info["username"] or "unknown",
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # 进程在遍历过程中已结束，或当前用户无权限访问，直接跳过
            continue

    # 根据 sort_by 参数决定排序字段，不合法的值默认按 cpu 排序
    sort_key = "memory_percent" if sort_by == "memory" else "cpu_percent"

    # 按指定字段降序排列，取前 limit 条
    processes.sort(key=lambda x: x[sort_key], reverse=True)
    processes = processes[:limit]

    return {
        "total_processes": len(psutil.pids()),  # 系统当前总进程数
        "sort_by": sort_key,
        "processes": processes,
    }
