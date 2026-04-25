"""
磁盘利用率工具模块
使用 psutil 库获取本地机器指定路径的磁盘使用情况
"""

import psutil


def _bytes_to_gb(byte_value: int) -> float:
    """将字节转换为 GB，保留两位小数"""
    return round(byte_value / (1024 ** 3), 2)


def get_disk_usage(path: str = "/") -> dict:
    """
    获取指定路径的磁盘使用情况

    参数:
        path: 要查询的磁盘路径，默认为根目录 "/"
              Windows 系统可传入 "C:\\" 等盘符

    返回:
        包含以下字段的字典:
            - path: 查询的路径
            - total_gb: 磁盘总容量（GB）
            - used_gb: 已使用空间（GB）
            - free_gb: 剩余可用空间（GB）
            - percent: 磁盘使用率（%）

    异常:
        当路径不存在或无权限访问时，返回包含 error 字段的字典
    """
    try:
        # 获取指定路径的磁盘使用情况
        disk = psutil.disk_usage(path)

        return {
            "path": path,
            "total_gb": _bytes_to_gb(disk.total),
            "used_gb": _bytes_to_gb(disk.used),
            "free_gb": _bytes_to_gb(disk.free),
            "percent": disk.percent,
        }
    except (PermissionError, FileNotFoundError) as e:
        # 路径不存在或没有访问权限时返回错误信息
        return {
            "path": path,
            "error": str(e),
        }
