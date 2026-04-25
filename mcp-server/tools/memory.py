"""
内存利用率工具模块
使用 psutil 库获取本地机器的内存使用情况
"""

import psutil


def _bytes_to_gb(byte_value: int) -> float:
    """将字节转换为 GB，保留两位小数"""
    return round(byte_value / (1024 ** 3), 2)


def get_memory_usage() -> dict:
    """
    获取内存使用情况

    返回:
        包含以下字段的字典:
            - total_gb: 总内存容量（GB）
            - used_gb: 已使用内存（GB）
            - available_gb: 当前可用内存（GB）
            - percent: 内存使用率（%）
            - free_gb: 完全空闲内存（GB，不含缓存）

    注意:
        available_gb 与 free_gb 的区别：
        - free_gb 是完全未使用的内存
        - available_gb 包含可以被应用程序立即使用的内存（含可回收缓存）
        实际可用内存应参考 available_gb
    """
    # 获取虚拟内存信息
    mem = psutil.virtual_memory()

    return {
        "total_gb": _bytes_to_gb(mem.total),
        "used_gb": _bytes_to_gb(mem.used),
        "available_gb": _bytes_to_gb(mem.available),
        "free_gb": _bytes_to_gb(mem.free),
        "percent": mem.percent,
    }
