"""
MCP Server 主入口（REST 模式）
使用 FastAPI 暴露标准 HTTP 接口，供 Streamlit 前端直接调用
每个 MCP Tool 对应一个 POST 端点，避免 SSE 长连接的复杂性
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

# 导入四个系统监控工具函数
from tools import get_cpu_usage, get_memory_usage, get_disk_usage, get_process_list

# 创建 FastAPI 应用实例
app = FastAPI(title="System Monitor MCP Server", version="1.0.0")

# 允许跨域请求，Streamlit 前端与本服务不同端口时需要
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 请求体模型定义 ─────────────────────────────────────────────────────────────

class CpuRequest(BaseModel):
    interval: float = 1.0  # 采样间隔（秒），默认 1.0


class DiskRequest(BaseModel):
    path: str = "/"  # 查询路径，默认根目录


class ProcessRequest(BaseModel):
    limit: int = 20          # 返回进程数量上限
    sort_by: str = "cpu"     # 排序依据：cpu 或 memory


# ── 工具接口端点 ───────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """健康检查接口，前端可用于确认 Server 是否在线"""
    return {"status": "ok"}


@app.post("/tools/get_cpu_usage")
def api_get_cpu_usage(req: CpuRequest):
    """
    获取 CPU 利用率
    返回总体使用率、每核使用率、核心数、主频
    """
    return get_cpu_usage(interval=req.interval)


@app.post("/tools/get_memory_usage")
def api_get_memory_usage():
    """
    获取内存利用率
    返回总量、已用、可用、空闲及使用百分比（单位 GB）
    """
    return get_memory_usage()


@app.post("/tools/get_disk_usage")
def api_get_disk_usage(req: DiskRequest):
    """
    获取磁盘利用率
    返回指定路径的总量、已用、剩余及使用百分比（单位 GB）
    """
    return get_disk_usage(path=req.path)


@app.post("/tools/get_process_list")
def api_get_process_list(req: ProcessRequest):
    """
    获取系统进程列表
    返回按 CPU 或内存排序的 Top N 进程信息
    """
    return get_process_list(limit=req.limit, sort_by=req.sort_by)


if __name__ == "__main__":
    print("MCP Server 启动中，监听 http://localhost:8000")
    print("API 文档：http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
