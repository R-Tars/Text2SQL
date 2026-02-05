from __future__ import annotations

import os
import time
import pandas as pd
import streamlit as st

from src.config import load_config
from src.data_loader import load_examples
from src.llm import LLMClient
from src.memory import MemoryTurn, trim_memory
from src.preprocess import normalize_question
from src.prompt import build_prompt, rewrite_question
from src.retrieval import HybridRetriever
from src.schema import get_schema
from src.sql_executor import execute_sql

st.set_page_config(page_title="Text2SQL 智能问数系统", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; max-width: 85%; }
    div[data-testid="stChatMessageUser"] { margin-left: auto; background-color: #e3f2fd; border: 1px solid #bbdefb; }
    div[data-testid="stChatMessageAssistant"] { margin-right: auto; background-color: #ffffff; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stStatus { border-radius: 10px; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Text2SQL 智能问数系统")

config = load_config()

if "chat" not in st.session_state: st.session_state["chat"] = []
if "memory" not in st.session_state: st.session_state["memory"] = []

with st.sidebar:
    st.subheader("⚙️ 模型配置")
    model_name = st.text_input("模型名称", value=config.model_name)
    base_url = st.text_input("Base URL", value=config.base_url or "")
    api_key = st.text_input("API Key", value=config.api_key or "", type="password")
    temperature = st.slider("Temperature", 0.0, 1.0, config.temperature, 0.05)
    top_k = st.slider("示例数量 (Top-K)", 0, 10, config.top_k_examples)
    memory_turns = st.slider("记忆轮数", 0, 10, 3)

    st.subheader("📂 数据路径")
    db_path = st.text_input("SQLite DB", value=config.db_path)
    enable_chart = st.checkbox("启用图表可视化", value=True)

    st.subheader("🧹 记忆管理")
    if st.button("清空记忆"): st.session_state["memory"] = []
    if st.button("清空对话记录"):
        st.session_state["chat"] = []
        st.session_state["last_prompt"] = None
        st.rerun()

@st.cache_resource(show_spinner=False)
def _load_resources(train_path: str, db_path_val: str):
    schema = get_schema(db_path_val)
    examples = load_examples(train_path, "college_2")
    retriever = HybridRetriever(examples)
    return schema, retriever

schema_text, retriever = _load_resources(os.path.join(config.data_root, "train.json"), db_path)

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("💬 智能对话")
    chat_placeholder = st.container()
    
    if prompt_input := st.chat_input("请输入自然语言问题..."):
        normalized = normalize_question(prompt_input)
        st.session_state["chat"].append({"role": "user", "content": normalized})
        
        llm = LLMClient(model_name=model_name, api_key=api_key or None, base_url=base_url or None, temperature=temperature)
        history = trim_memory(st.session_state["memory"], memory_turns)

        with st.status("🚀 智能体正在思考...", expanded=True) as status:
            # 1. 重写
            target_q = normalized
            if history:
                st.write("🔄 正在分析上下文...")
                rewritten = rewrite_question(llm, normalized, history)
                if rewritten != normalized:
                    st.write(f"📝 重写问题: **{rewritten}**")
                    target_q = rewritten
            
            # 2. 检索
            st.write("🔍 正在检索混合示例...")
            few_shot = retriever.search(target_q, k=top_k)
            
            # 3. 生成
            st.write("🤖 正在生成 SQL...")
            full_prompt = build_prompt(schema_text, few_shot, target_q, history)
            st.session_state["last_prompt"] = full_prompt
            st.session_state["last_example_count"] = len(few_shot)
            
            start_time = time.time()
            sql = llm.generate_sql(full_prompt)
            latency = time.time() - start_time
            
            if not sql.strip().lower().startswith("select"):
                status.update(label="⚠️ 未能生成有效查询", state="error")
                st.session_state["chat"].append({"role": "assistant", "content": f"未能生成有效 SQL。LLM 输出：\n\n```\n{sql}\n```"})
            else:
                st.write("⚡ 正在执行查询...")
                try:
                    try:
                        result = execute_sql(db_path, sql)
                    except Exception as e:
                        # Execution-guided self-correction (retry once)
                        fixed_sql = llm.repair_sql(full_prompt, sql, str(e))
                        result = execute_sql(db_path, fixed_sql)
                        sql = fixed_sql
                    status.update(label=f"✅ 完成 (耗时 {latency:.2f}s)", state="complete")
                    st.session_state["chat"].append({
                        "role": "assistant",
                        "content": f"已生成 SQL：\n```sql\n{sql}\n```\n查询到 {result.row_count} 条结果。",
                        "result": result
                    })
                    st.session_state["memory"].append(MemoryTurn(question=target_q, sql=sql))
                    st.session_state["memory"] = trim_memory(st.session_state["memory"], memory_turns)
                except Exception as e:
                    status.update(label="❌ 执行出错", state="error")
                    st.session_state["chat"].append({"role": "assistant", "content": f"SQL 执行出错：{str(e)}\n\nSQL：\n```sql\n{sql}\n```"})

    with chat_placeholder:
        for i, msg in enumerate(st.session_state["chat"]):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "result" in msg:
                    res = msg["result"]
                    df = pd.DataFrame(res.rows, columns=res.columns)
                    with st.expander("📊 数据详情与可视化", expanded=(i == len(st.session_state["chat"])-1)):
                        st.dataframe(df, use_container_width=True)
                        if enable_chart and not df.empty:
                            for col in df.columns: df[col] = pd.to_numeric(df[col], errors="ignore")
                            num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                            if num_cols:
                                st.divider()
                                c_type = st.selectbox(f"图表类型_{i}", ["柱状图", "折线图", "饼图", "散点图"], key=f"t_{i}")
                                x_c = st.selectbox(f"X轴 (维度)_{i}", list(df.columns), index=0, key=f"x_{i}")
                                y_c = st.selectbox(f"Y轴 (指标)_{i}", num_cols, index=0, key=f"y_{i}")
                                try:
                                    import plotly.express as px
                                    if c_type == "柱状图": fig = px.bar(df, x=x_c, y=y_c)
                                    elif c_type == "折线图": fig = px.line(df, x=x_c, y=y_c)
                                    elif c_type == "饼图": fig = px.pie(df, names=x_c, values=y_c)
                                    else: fig = px.scatter(df, x=x_c, y=y_c)
                                    st.plotly_chart(fig, use_container_width=True)
                                except Exception as e: st.error(f"绘图失败: {e}")

with col_right:
    st.subheader("📋 数据库 Schema")
    st.code(schema_text, language="sql")
    if st.session_state.get("last_prompt"):
        with st.expander("🔍 上次生成的 Prompt"):
            st.caption(f"检索到 {st.session_state.get('last_example_count', 0)} 条 Few-shot 示例")
            st.code(st.session_state["last_prompt"])
