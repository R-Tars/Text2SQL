# Text2SQL 智能问数查询分析系统

本项目基于老师提供的 `college_2` 数据库与 Spider 格式数据集，使用 LangChain + LLM（DeepSeek/Qwen3/OpenAI兼容接口）实现自然语言到 SQL 的生成与执行，并通过 Streamlit 提供 Web 交互界面。

## 目录结构

- `app.py`：Streamlit Web 界面
- `src/`：核心模块（schema、prompt、检索、执行、评测）
- `data/`：数据集与数据库文件

## 环境依赖（一次安装）

```bash
pip install -r requirements.txt
```

## 运行 Web 系统

1. 在项目根目录创建 `.env` 文件并配置 API 信息（已为您创建）：
   ```env
   LLM_API_KEY=你的key
   LLM_BASE_URL=你的base_url
   LLM_MODEL_NAME=qwen-plus
   ```

2. 启动 Streamlit：
   ```bash
   streamlit run app.py
   ```

说明：
- 若使用 Qwen3/DeepSeek/OpenAI 兼容接口，请填写对应的 `OPENAI_BASE_URL` 与 `MODEL_NAME`。
- 默认使用 `data/database/college_2/college_2.sqlite` 作为数据库。
- 可选设置 `DB_URL` 连接 PostgreSQL，未设置则默认 SQLite。

## 功能说明

- **查询预处理**：自动规范化用户输入的空白符。
- **混合 RAG 检索 (推荐)**：统一采用 **TF-IDF + 向量检索** 的混合方案，兼顾关键词精准度与语义理解。
- **LLM 生成 SQL**：基于 LangChain 调用大模型，支持 Few-shot 学习与多轮对话重写。
- **安全执行**：仅允许 `SELECT` 语句，自动处理 `LIMIT` 冲突，防止大表崩溃。
- **卡片式交互 UI**：支持左右气泡对话、分步生成状态展示。
- **结果可视化**：集成 **Plotly**，支持柱状图、折线图、饼图、散点图。
- **会话记忆**：支持多轮对话消歧（问题重写），记忆可配置轮数并支持一键清空。
- **自动化评测**：内置详细评测脚本，支持结果归一化比对与列顺序无关匹配。

## 执行评测（自动化测试）

项目内置了详细的评测脚本，用于验证 SQL 生成的准确率与响应时间。系统统一使用**混合检索 (Hybrid)** 模式以获得最佳效果。

```bash
# 运行评测（默认测试测试集）
python -m src.eval

# 常用选项：
# --limit 10      限制测试前10条数据（快速调试）
# --top_k 8       设置检索示例数量（推荐 5-10）
# --use_train_set  使用训练集进行评测
```

### 评测输出说明：
- **执行准确率**：基于执行结果集比对（Execution Accuracy），支持列顺序无关匹配与数值归一化。
- **控制台输出**：实时显示每个 ID 的状态（✅/❌）、耗时及问题。针对失败用例，会对比预测 SQL 与标准 SQL。
- **报告文件**：自动生成 `eval_report.txt`，包含详细对比记录。

## 技术栈

- LangChain
- DeepSeek / Qwen3（OpenAI 兼容 API）
- SQLite（默认，便于部署）
- PostgreSQL（可选：设置 `DB_URL=postgresql+psycopg2://user:pass@host:5432/dbname`）
- Streamlit
- FAISS + Sentence-Transformers (用于语义 RAG)

> 已内置 SQLAlchemy 连接逻辑，若未设置 `DB_URL` 则自动使用 SQLite。
