import os
import streamlit as st
from langchain_openai import ChatOpenAI

@st.cache_resource
def get_llm():
    """
    Initializes the LLM (DeepSeek/Qwen) using OpenAI compatible interface.
    """
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model_name = os.getenv("LLM_MODEL_NAME", "deepseek-chat")

    if not api_key or not base_url:
        st.error("Please set LLM_API_KEY and LLM_BASE_URL in your .env file.")
        return None

    llm = ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0,  # Low temperature for deterministic SQL generation
        streaming=True
    )
    return llm



