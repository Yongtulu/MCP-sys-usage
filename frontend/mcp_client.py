"""
MCP Server 调用封装模块
通过 HTTP REST 接口调用本地 MCP Server 的各个工具端点
"""

import requests

# MCP Server 基础地址，与 server.py 中 uvicorn 监听端口一致
MCP_SERVER_URL = "http://localhost:8000"


def _post(endpoint: str, payload: dict = None) -> dict:
    """
    通用 POST 请求封装

    参数:
        endpoint: 接口路径，如 "/tools/get_cpu_usage"
        payload: 请求体字典，无参数时传 None 或 {}

    返回:
        接口返回的字典；发生错误时返回含 "error" 字段的字典
    """
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}{endpoint}",
            json=payload or {},
            timeout=15,  # 超时 15 秒，cpu 采样需要一点时间
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.ConnectionError:
        return {"error": "无法连接到 MCP Server，请确认 server.py 已启动（端口 8000）"}
    except requests.exceptions.Timeout:
        return {"error": "MCP Server 响应超时"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP 错误：{e.response.status_code} - {e.response.text}"}
    except Exception as e:
        return {"error": f"调用失败：{str(e)}"}


# ── 各工具的便捷封装函数，供 app.py 直接调用 ─────────────────────────────────

def fetch_cpu(interval: float = 1.0) -> dict:
    """获取 CPU 利用率"""
    return _post("/tools/get_cpu_usage", {"interval": interval})


def fetch_memory() -> dict:
    """获取内存利用率"""
    return _post("/tools/get_memory_usage")


def fetch_disk(path: str = "/") -> dict:
    """获取磁盘利用率"""
    return _post("/tools/get_disk_usage", {"path": path})


def fetch_processes(limit: int = 20, sort_by: str = "cpu") -> dict:
    """获取进程列表"""
    return _post("/tools/get_process_list", {"limit": limit, "sort_by": sort_by})
