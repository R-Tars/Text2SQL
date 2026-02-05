# 技术报告：Text2SQL 智能问数查询分析系统

## 1. 目标与场景

系统面向固定领域数据库（`college_2`），实现自然语言问题到 SQL 的自动生成、执行与结果展示，并提供可视化交互界面与批量评测能力。数据集存储在 `data/` 目录下。

## 2. 系统架构

1. **查询预处理**：对输入问题做轻量规范化。
2. **混合 RAG 检索**：结合 TF-IDF 关键词检索与 FAISS 向量语义检索，统一召回高质量 Few-shot 示例。
3. **对话重写**：针对多轮对话，利用 LLM 进行指代消歧，将模糊提问重写为独立完整的查询。
4. **Prompt 构建**：动态拼接 Schema（含示例数据）、Few-shot 示例、会话记忆。
5. **SQL 生成**：基于 LangChain 调用 LLM，强制执行 SQLite 兼容性与唯一性约束。
6. **SQL 执行与可视化**：安全执行引擎支持结果归一化；集成 Plotly 实现多维交互图表。
7. **自动化评测**：支持执行结果集比对（Execution Accuracy），内置列顺序无关匹配算法。

## 3. 核心模块说明

- `src/schema.py`：数据库结构自动提取。
- `src/retrieval.py`：基于 TF-IDF 的关键词检索。
- `src/vector_retrieval.py`：基于 FAISS 和 Sentence-Transformers 的语义检索。
- `src/prompt.py`：指令化 Prompt 工程，支持 Few-shot 与 Memory。
- `src/sql_executor.py`：SQL 安全执行与结果集封装。
- `src/eval.py`：自动化评测框架，支持准确率与响应时间统计，提供详细的错题对比分析报告。

## 4. 关键技术优化

### 4.1 问题重写 (Query Rewriting)
针对多轮对话中的指代不明问题（如“那属于 Physics 系的呢？”），系统引入了重写模块。在检索前利用 LLM 结合历史上下文将问题补全，显著提升了 RAG 检索的召回精度。

### 4.2 增强型可视化
集成 Plotly 图表库，支持柱状图、折线图、饼图、散点图。系统具备自动类型推断能力，确保可视化过程的鲁棒性。

### 4.3 自动化评测体系
建立了闭环的评测机制：
- **Execution Accuracy (EA)**：通过比对预测 SQL 与 Gold SQL 的执行结果集来衡量准确性。
- **性能监控**：记录端到端响应时间，确保满足 <10s 的工业级要求。
- **详细日志**：自动记录 `eval_report.txt`，支持对 Fail Case 的深度溯源。

## 6. 部署与运行

- 一次安装依赖：`pip install -r requirements.txt`
- 启动界面：`streamlit run app.py`
- 评测：`python -m src.eval --limit 50`

## 7. 后续可扩展

- 接入向量数据库做更强的 RAG 检索
- 增加语义缓存与多轮记忆管理
- 支持图表可视化（柱状/折线/饼图）
