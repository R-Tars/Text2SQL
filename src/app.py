import streamlit as st
import os
import pandas as pd
import sys
from dotenv import load_dotenv
from db import get_db_connection
from llm import get_llm
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="智能问数查询系统 (Text2SQL)",
    page_icon="🔍",
    layout="wide"
)

def main():
    st.title("🤖 智能问数查询系统 (Text2SQL)")
    st.markdown("基于 DeepSeek/Qwen + LangChain + PostgreSQL")
    
    # Sidebar Configuration
    with st.sidebar:
        st.header("配置与状态")
        if st.button("重新加载配置"):
            st.cache_resource.clear()
            st.rerun()
        
        # Check DB Connection
        db = get_db_connection()
        if db:
            st.success(f"✅ 数据库已连接")
            with st.expander("查看数据表 Schema"):
                st.code(db.get_table_info(), language="sql")
        else:
            st.error("❌ 数据库未连接")

    # Main Chat Interface
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "你好！我是你的智能数据助手。请告诉我你想查询什么？"}]

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

        # If there's a dataframe in the message (saved as 'data'), verify if we should display it
        if "data" in msg and msg["data"] is not None:
            st.dataframe(msg["data"])

    if prompt := st.chat_input("请输入你的问题（例如：查询最近一周的销售额）"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        if not db:
            st.error("请先配置并连接数据库！")
            return

        llm = get_llm()
        if not llm:
            st.error("请先配置 LLM API！")
            return
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.write("🤔 正在思考并生成 SQL...")

            try:
                # 1. Define the Prompt Template
                template = """You are a PostgreSQL expert. Given an input question, create a syntactically correct PostgreSQL query to run.
Unless the user specifies in the question a specific number of examples to obtain, query for at most 5 results using the LIMIT clause.
Never query for all columns from a table. You must query only the columns that are needed to answer the question.
Wrap each column name in double quotes (") to denote them as delimited identifiers if they contain upper case.
Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist.

Only use the following tables:
{table_info}

Question: {input}
SQLQuery: """
                
                prompt_template = PromptTemplate.from_template(template)

                # 2. Generate SQL using simple Chain (Prompt | LLM | StrParser)
                # This bypasses complex LangChain agents/chains that might have import issues
                chain = prompt_template | llm | StrOutputParser()
                
                # Get Schema
                table_info = db.get_table_info()
                
                # Invoke
                sql_query = chain.invoke({"table_info": table_info, "input": prompt})
                
                # Clean up SQL
                cleaned_sql = sql_query.replace("```sql", "").replace("```", "").strip()
                # Remove any 'SQLQuery:' prefix if LLM repeated it
                if cleaned_sql.startswith("SQLQuery:"):
                    cleaned_sql = cleaned_sql.replace("SQLQuery:", "").strip()
                
                # Display the generated SQL
                st.code(cleaned_sql, language="sql")

                # 3. Execute SQL
                try:
                    with db._engine.connect() as connection:
                         result_df = pd.read_sql_query(text(cleaned_sql), connection)
                    
                    if not result_df.empty:
                        st.dataframe(result_df)
                        final_response = f"查询成功！共找到 {len(result_df)} 条记录。"
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": final_response,
                            "data": result_df
                        })
                    else:
                        final_response = "查询执行成功，但没有返回任何结果。"
                        st.session_state.messages.append({"role": "assistant", "content": final_response})
                    
                    message_placeholder.write(final_response)

                except Exception as e:
                    error_msg = f"SQL 执行失败: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

            except Exception as e:
                error_msg = f"处理失败: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

if __name__ == "__main__":
    main()
