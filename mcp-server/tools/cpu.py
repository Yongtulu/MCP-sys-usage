"""
CPU 利用率工具模块
使用 psutil 库获取本地机器的 CPU 使用情况
"""

import psutil


def get_cpu_usage(interval: float = 1.0) -> dict:
    """
    获取 CPU 利用率信息

    参数:
        interval: 采样间隔（秒），psutil 会在此时间段内测量 CPU 使用率，默认 1.0 秒

    返回:
        包含以下字段的字典:
            - total_percent: 所有核心的平均 CPU 使用率（%）
            - per_core_percent: 每个核心的 CPU 使用率列表（%）
            - core_count_logical: 逻辑核心数（含超线程）
            - core_count_physical: 物理核心数
            - cpu_freq_mhz: 当前 CPU 主频（MHz），不支持时为 None
    """
    # 获取所有逻辑核心的使用率，percpu=True 表示返回每个核心的数据
    per_core = psutil.cpu_percent(interval=interval, percpu=True)

    # 计算所有核心的平均使用率
    total = psutil.cpu_percent(interval=0, percpu=False)

    # 获取 CPU 主频信息
    # Apple Silicon（M 系列）上 psutil.cpu_freq() 会抛 RuntimeError，捕获后返回 None
    try:
        freq = psutil.cpu_freq()
        freq_mhz = round(freq.current, 1) if freq else None
    except RuntimeError:
        freq_mhz = None

    return {
        "total_percent": total,
        "per_core_percent": per_core,
        "core_count_logical": psutil.cpu_count(logical=True),   # 逻辑核心数
        "core_count_physical": psutil.cpu_count(logical=False),  # 物理核心数
        "cpu_freq_mhz": freq_mhz,
    }
