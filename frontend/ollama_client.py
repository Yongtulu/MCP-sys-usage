"""
Ollama API 调用封装模块
负责与本地 Ollama 服务通信，支持 tool_call 工具调用流程
让 LLM 能够根据用户问题自动决定调用哪个 MCP 工具
"""

import json
import requests

# Ollama 本地服务地址，默认端口 11434
OLLAMA_BASE_URL = "http://localhost:11434"

# 使用的模型名称，需与 `ollama pull` 拉取的模型名一致
MODEL_NAME = "gemma4:31b"

# 将 MCP 工具定义转换为 Ollama tool_call 格式
# Ollama 使用 OpenAI 兼容的 tools 格式
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_cpu_usage",
            "description": "获取本机 CPU 利用率，包括总体使用率和每个核心的使用率",
            "parameters": {
                "type": "object",
                "properties": {
                    "interval": {
                        "type": "number",
                        "description": "采样时间间隔（秒），默认 1.0",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_memory_usage",
            "description": "获取本机内存利用率，包括总量、已用、可用及使用百分比",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_disk_usage",
            "description": "获取本机磁盘利用率，包括总量、已用、剩余及使用百分比",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要查询的磁盘路径，默认为 /",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_process_list",
            "description": "获取系统当前运行的进程列表，支持按 CPU 或内存排序",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回进程数量上限，默认 20",
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "排序依据：cpu 或 memory",
                        "enum": ["cpu", "memory"],
                    },
                },
            },
        },
    },
]


def chat(messages: list[dict], tool_results: dict = None) -> dict:
    """
    向 Ollama 发送对话请求

    参数:
        messages: 对话历史列表，每条格式为 {"role": "user/assistant/tool", "content": "..."}
        tool_results: 如果上一轮 LLM 发起了 tool_call，将工具执行结果注入此参数

    返回:
        包含以下字段的字典:
            - content: LLM 回复的文本内容（无 tool_call 时）
            - tool_call: LLM 请求调用的工具信息（有 tool_call 时），包含 name 和 arguments
            - error: 发生错误时的错误信息
    """
    # 如果有工具执行结果，将其追加到对话历史
    if tool_results:
        messages = messages + [
            {
                "role": "tool",
                "content": json.dumps(tool_results, ensure_ascii=False),
            }
        ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "tools": TOOLS,   # 告知 LLM 可以使用哪些工具
        "stream": False,  # 不使用流式输出，等待完整响应
    }

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=120,  # LLM 生成可能较慢，设置 120 秒超时
        )
        response.raise_for_status()
        data = response.json()

        message = data.get("message", {})
        tool_calls = message.get("tool_calls", [])

        # 如果 LLM 决定调用工具，返回 tool_call 信息
        if tool_calls:
            tc = tool_calls[0]  # 本项目每次只处理一个工具调用
            return {
                "tool_call": {
                    "name": tc["function"]["name"],
                    "arguments": tc["function"].get("arguments", {}),
                }
            }

        # 否则返回 LLM 的文本回复
        return {"content": message.get("content", "")}

    except requests.exceptions.ConnectionError:
        return {"error": "无法连接到 Ollama，请确认 `ollama serve` 已启动（端口 11434）"}
    except requests.exceptions.Timeout:
        return {"error": "Ollama 响应超时，模型可能正在加载，请稍后重试"}
    except Exception as e:
        return {"error": f"Ollama 调用失败：{str(e)}"}


def build_system_prompt() -> str:
    """
    构建系统提示词
    告知 LLM 它的角色和可以使用的工具能力
    """
    return (
        "你是一个本地系统监控助手。你可以使用工具查询用户机器的实时系统信息，"
        "包括 CPU 利用率、内存使用情况、磁盘使用情况和系统进程列表。"
        "当用户询问系统状态时，请主动调用相应工具获取最新数据，再根据数据给出清晰的回答。"
        "回答请使用中文，数值保留合理精度。"
    )
