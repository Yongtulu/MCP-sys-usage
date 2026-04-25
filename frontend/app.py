"""
Streamlit 主应用
系统监控仪表盘 + AI 对话界面
布局：左栏（指标卡片 + 进程列表）| 右栏（AI Chat）
"""

import streamlit as st
import pandas as pd
from mcp_client import fetch_cpu, fetch_memory, fetch_disk, fetch_processes
from ollama_client import chat, build_system_prompt
import mcp_client

# ── 页面配置 ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="System Monitor",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 全局样式 ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 页面边距 */
.block-container { padding-top: 2rem; padding-bottom: 1rem; padding-left: 2rem; padding-right: 2rem; }

/* 标题不被截断 */
h4 { overflow: visible !important; line-height: 1.5 !important; }

/* 指标卡片：三列等高 */
.metric-card {
    background: #f4f6f9;
    border: 1px solid #dde2ea;
    border-radius: 10px;
    padding: 12px 14px 10px 14px;
    height: 210px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
}
.metric-label {
    font-size: 0.68rem;
    font-weight: 700;
    color: #5a6475;          /* 深化，原来太浅 */
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 3px;
}
.metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    line-height: 1.15;
    margin-bottom: 5px;
}
.metric-sub {
    font-size: 0.71rem;
    color: #5a6475;          /* 深化，原来太浅 */
    margin-top: 4px;
}
.metric-sub b { color: #1f2937; }   /* 数值加粗，对比更强 */

/* 进度条 */
.bar-wrap {
    background: #dde2ea;
    border-radius: 4px;
    height: 5px;
    width: 100%;
    overflow: hidden;
    margin: 2px 0;
}
.bar-fill { height: 5px; border-radius: 4px; }
.bar-green  { background: #16a34a; }
.bar-orange { background: #d97706; }
.bar-red    { background: #dc2626; }

/* 核心列表：弹性填满剩余高度并滚动 */
.core-scroll {
    flex: 1;
    overflow-y: auto;
    margin-top: 6px;
    padding-right: 2px;
    min-height: 0;
}
.core-scroll::-webkit-scrollbar { width: 3px; }
.core-scroll::-webkit-scrollbar-thumb { background: #c4cad5; border-radius: 2px; }
.core-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 3px;
}
.core-label { font-size: 0.63rem; color: #5a6475; width: 38px; flex-shrink: 0; }
.core-pct   { font-size: 0.63rem; color: #1f2937; width: 28px; text-align: right; flex-shrink: 0; }

/* 区块小标题 */
.section-title {
    font-size: 0.7rem;
    font-weight: 700;
    color: #5a6475;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin: 0 0 6px 0;
}

/* 分割线 */
hr { border-color: #dde2ea !important; margin: 0.7rem 0 !important; }

/* 聊天消息行间距 + 字体压缩 */
.stChatMessage { padding-top: 3px !important; padding-bottom: 3px !important; margin-bottom: 0px !important; }
.stChatMessage p { margin: 0 !important; line-height: 1.3 !important; font-size: 0.78rem !important; }
.stChatMessage li { font-size: 0.78rem !important; line-height: 1.3 !important; }
[data-testid="stChatMessageContent"] { gap: 0px !important; padding: 4px 8px !important; }

/* dataframe 行高与字号 */
.stDataFrame { font-size: 0.78rem; }

/* 右栏 AI Chat 撑满整列高度 */
.chat-col { display: flex; flex-direction: column; height: 100%; }
</style>
""", unsafe_allow_html=True)


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def bar_color(pct: float) -> str:
    """根据使用率返回 CSS 颜色类名：绿 / 橙 / 红"""
    if pct < 60:   return "bar-green"
    elif pct < 85: return "bar-orange"
    return "bar-red"


def value_color(pct: float) -> str:
    """根据使用率返回文字颜色"""
    if pct < 60:   return "#16a34a"
    elif pct < 85: return "#d97706"
    return "#dc2626"


def render_bar(pct: float) -> str:
    """生成 HTML 细进度条"""
    return (
        f'<div class="bar-wrap">'
        f'<div class="bar-fill {bar_color(pct)}" style="width:{min(pct,100):.1f}%"></div>'
        f'</div>'
    )


# ── 初始化 session_state ──────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "system", "content": build_system_prompt()}
    ]
if "display_messages" not in st.session_state:
    st.session_state.display_messages = []


# ── 顶级两栏布局：左侧监控面板 | 右侧 AI Chat ─────────────────────────────────
left_col, right_col = st.columns([3, 2], gap="large")


# ════════════════════════════════════════════════
#  左栏：标题 + 指标卡片 + 进程列表
# ════════════════════════════════════════════════
with left_col:

    # 标题
    st.markdown(
        '<h4 style="margin:0 0 2px 0;line-height:1.5;overflow:visible">🖥️ &nbsp;Local System Monitor</h4>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="color:#5a6475;font-size:0.73rem;margin:0 0 10px 0;">'
        'Real-time metrics · MCP + Ollama gemma4:31b</p>',
        unsafe_allow_html=True,
    )

    # 指标卡片（三列）
    col_cpu, col_mem, col_disk = st.columns(3, gap="small")

    # CPU 卡片
    with col_cpu:
        cpu_data = fetch_cpu(interval=0.5)
        if "error" in cpu_data:
            st.error(cpu_data["error"])
        else:
            total = cpu_data["total_percent"]
            cores_html = "".join(
                f'<div class="core-row">'
                f'<span class="core-label">Core {i}</span>'
                f'<div class="bar-wrap" style="flex:1">'
                f'<div class="bar-fill {bar_color(p)}" style="width:{p:.1f}%"></div>'
                f'</div>'
                f'<span class="core-pct">{p:.0f}%</span>'
                f'</div>'
                for i, p in enumerate(cpu_data.get("per_core_percent", []))
            )
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">CPU Usage</div>
              <div class="metric-value" style="color:{value_color(total)}">{total:.1f}%</div>
              {render_bar(total)}
              <div class="metric-sub">
                {cpu_data['core_count_physical']}P &nbsp;·&nbsp; {cpu_data['core_count_logical']}L cores
              </div>
              <div class="core-scroll">{cores_html}</div>
            </div>""", unsafe_allow_html=True)

    # 内存卡片
    with col_mem:
        mem_data = fetch_memory()
        if "error" in mem_data:
            st.error(mem_data["error"])
        else:
            pct = mem_data["percent"]
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">Memory Usage</div>
              <div class="metric-value" style="color:{value_color(pct)}">{pct:.1f}%</div>
              {render_bar(pct)}
              <div class="metric-sub">Used &nbsp;<b>{mem_data['used_gb']} GB</b> / {mem_data['total_gb']} GB</div>
              <div class="metric-sub">Available &nbsp;<b>{mem_data['available_gb']} GB</b></div>
              <div class="metric-sub">Free &nbsp;<b>{mem_data['free_gb']} GB</b></div>
            </div>""", unsafe_allow_html=True)

    # 磁盘卡片
    with col_disk:
        disk_data = fetch_disk(path="/")
        if "error" in disk_data:
            st.error(disk_data["error"])
        else:
            pct = disk_data["percent"]
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">Disk Usage &nbsp;<span style="font-weight:400">/</span></div>
              <div class="metric-value" style="color:{value_color(pct)}">{pct:.1f}%</div>
              {render_bar(pct)}
              <div class="metric-sub">Used &nbsp;<b>{disk_data['used_gb']} GB</b> / {disk_data['total_gb']} GB</div>
              <div class="metric-sub">Free &nbsp;<b>{disk_data['free_gb']} GB</b></div>
            </div>""", unsafe_allow_html=True)

    st.divider()

    # 进程列表标题行
    t_col, s_col, r_col = st.columns([3, 1.5, 0.8], gap="small")
    with t_col:
        st.markdown('<p class="section-title">Process List</p>', unsafe_allow_html=True)
    with s_col:
        sort_by = st.selectbox(
            "sort",
            options=["cpu", "memory"],
            format_func=lambda x: "Sort: CPU" if x == "cpu" else "Sort: Memory",
            label_visibility="collapsed",
        )
    with r_col:
        refresh = st.button("↺ Refresh", use_container_width=True)

    # 缓存进程数据，排序变化或点刷新时重新拉取
    if (
        "process_data" not in st.session_state
        or refresh
        or st.session_state.get("process_sort") != sort_by
    ):
        st.session_state.process_data = fetch_processes(limit=20, sort_by=sort_by)
        st.session_state.process_sort = sort_by

    proc_data = st.session_state.process_data
    if "error" in proc_data:
        st.error(proc_data["error"])
    else:
        st.caption(f"Total processes: {proc_data['total_processes']}")
        df = pd.DataFrame(proc_data["processes"]).rename(columns={
            "pid": "PID", "name": "Name",
            "cpu_percent": "CPU %", "memory_percent": "Mem %",
            "status": "Status", "username": "User",
        })
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True, height=240)


# ════════════════════════════════════════════════
#  右栏：AI Chat（固定高度滚动区 + 输入框）
# ════════════════════════════════════════════════
with right_col:

    st.markdown(
        '<h4 style="margin:0 0 2px 0;line-height:1.5;overflow:visible">💬 &nbsp;AI Chat</h4>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="color:#5a6475;font-size:0.73rem;margin:0 0 10px 0;">'
        'Ask anything about your system</p>',
        unsafe_allow_html=True,
    )

    # 固定高度聊天消息区，超出后出现滚动条
    # 高度设为 540px，与左栏总高度大致对齐
    chat_container = st.container(height=540)
    with chat_container:
        if not st.session_state.display_messages:
            st.markdown(
                '<p style="color:#9aa3b0;font-size:0.8rem;text-align:center;margin-top:2rem;">'
                'Ask me about CPU, memory, disk, or processes...</p>',
                unsafe_allow_html=True,
            )
        for msg in st.session_state.display_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # 对话输入框始终在聊天区域下方
    user_input = st.chat_input("Ask about your system...")


def process_user_message(text: str):
    """
    处理用户输入，执行完整的 LLM → tool_call → LLM 调用链

    流程：
    1. 用户消息追加到对话历史
    2. 调用 Ollama，LLM 决定是否需要调用工具
    3. 若需要工具，执行对应 MCP 工具获取实时数据
    4. 将工具结果注回 LLM，生成最终回答
    """
    st.session_state.chat_history.append({"role": "user", "content": text})
    st.session_state.display_messages.append({"role": "user", "content": text})

    # 新消息渲染在固定聊天区域内
    with chat_container:
        with st.chat_message("user"):
            st.markdown(text)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = chat(st.session_state.chat_history)

            if "error" in response:
                error_msg = f"⚠️ {response['error']}"
                st.error(error_msg)
                st.session_state.display_messages.append({"role": "assistant", "content": error_msg})
                return

            if "tool_call" in response:
                tc = response["tool_call"]
                tool_name = tc["name"]
                tool_args = tc["arguments"]

                # 将 LLM 的 tool_call 请求记录到对话历史
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{"function": {"name": tool_name, "arguments": tool_args}}],
                })

                with st.spinner(f"Calling `{tool_name}`..."):
                    tool_func_map = {
                        "get_cpu_usage":    lambda: mcp_client.fetch_cpu(**tool_args),
                        "get_memory_usage": lambda: mcp_client.fetch_memory(),
                        "get_disk_usage":   lambda: mcp_client.fetch_disk(**tool_args),
                        "get_process_list": lambda: mcp_client.fetch_processes(**tool_args),
                    }
                    tool_result = tool_func_map.get(
                        tool_name, lambda: {"error": f"Unknown tool: {tool_name}"}
                    )()

                with st.spinner("Generating answer..."):
                    final_response = chat(st.session_state.chat_history, tool_results=tool_result)

                if "error" in final_response:
                    error_msg = f"⚠️ {final_response['error']}"
                    st.error(error_msg)
                    st.session_state.display_messages.append({"role": "assistant", "content": error_msg})
                else:
                    final_text = final_response.get("content", "")
                    st.markdown(final_text)
                    st.session_state.chat_history.append({"role": "assistant", "content": final_text})
                    st.session_state.display_messages.append({"role": "assistant", "content": final_text})
            else:
                # LLM 直接回答，无需工具调用
                answer = response.get("content", "")
                st.markdown(answer)
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                st.session_state.display_messages.append({"role": "assistant", "content": answer})


if user_input:
    process_user_message(user_input)
