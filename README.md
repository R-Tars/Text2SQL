# Text2SQL 智能查询分析系统

## 项目简介
本项目是一个面向领域数据库的智能查询分析系统，利用大语言模型（DeepSeek/Qwen）将自然语言问题转换为 SQL 查询，执行并展示结果。

## 技术栈
- **核心框架**: LangChain
- **LLM**: DeepSeek / Qwen (通过 OpenAI 兼容接口)
- **数据库**: PostgreSQL
- **前端**: Streamlit

## 快速开始

### 1. 环境配置
```bash
# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量
复制 `.env.example` 为 `.env`，并填入以下信息：
- LLM API Key (DeepSeek 或 Qwen)
- PostgreSQL 数据库连接串

### 3. 运行系统
```bash
streamlit run src/app.py
```

## 核心功能
1. **查询预处理**: 识别用户意图。
2. **SQL 生成**: 基于 Schema 生成准确 SQL。
3. **结果分析**: 解释查询结果。
4. **可视化**: 自动生成相关图表。



