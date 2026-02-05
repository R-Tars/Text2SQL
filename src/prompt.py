from __future__ import annotations

from .data_loader import Example
from .memory import MemoryTurn
from .llm import LLMClient

REWRITE_INSTRUCTION = (
    "你是一个对话重写助手。你的任务是根据对话历史，将用户最新的、不完整的提问重写为一个完整的、"
    "独立的自然语言查询问题，以便于 Text2SQL 系统理解。"
    "注意：只需输出重写后的问题，不要有任何解释。"
)

def rewrite_question(llm: LLMClient, question: str, memory: list[MemoryTurn]) -> str:
    if not memory:
        return question
    
    history_text = ""
    for turn in memory:
        history_text += f"问：{turn.question}\n答：(生成了对应的SQL)\n"
    
    prompt = f"{REWRITE_INSTRUCTION}\n\n对话历史：\n{history_text}\n最新提问：{question}\n\n重写后的完整问题："
    
    try:
        rewritten = llm.generate_text(prompt)
        return rewritten
    except:
        return question

SYSTEM_INSTRUCTION = (
    "你是一个顶级的 Text2SQL 专家。你的任务是将自然语言准确转换为 SQLite 兼容的 SQL。"
    "请严格遵守以下规则：\n"
    "1. **只输出 SQL**：只输出一条可执行的 SQL 语句，不要解释、不要前后缀、不要 Markdown。\n"
    "2. **回答内容必须匹配问题**：问题要“title/name”等可读字段时，SELECT 必须返回对应字段；不要返回 course_id / ID / prereq_id 之类的编号，除非问题明确要编号。\n"
    "3. **字段顺序**：严格按照问题中提到的先后顺序在 SELECT 中排列字段。例如问题是“姓名和薪水”，SQL 必须是 SELECT name, salary。\n"
    "4. **JOIN 选择**：默认优先使用 INNER JOIN。只有当问题明确要求“包含没有匹配/没有记录的项/即使为 0 也要显示”时，才使用 LEFT JOIN。\n"
    "5. **Top-1/最高/最多/最少**：处理“最高、最多、最少、最低”等问题，优先使用 ORDER BY ... DESC/ASC LIMIT 1（避免用 MAX/MIN 子查询导致并列时结果不一致）。\n"
    "6. **DISTINCT 非默认**：除非问题明确要求 distinct/不同/不重复/unique/different，否则不要使用 DISTINCT（评测按执行结果，重复行会影响正确性）。\n"
    "7. **去重与统计**：统计人数时优先 COUNT(DISTINCT ...)；但若问题语义是计数行或计数记录，则用 COUNT(*)。\n"
    "7. **避免多余结构**：不要随意加 GROUP BY/ORDER BY。只有在题目需要聚合或排序时才使用。\n"
    "8. **表关联**：仔细分析 Schema 中的外键关系，确保 JOIN 条件正确（如 advisor.i_ID = instructor.ID）。\n"
    "9. **空值处理**：在涉及聚合函数（如 AVG, SUM）时，注意是否需要过滤 NULL 值。\n"
    "10. **输出要求**：最终输出必须以 SELECT 开头。"
)


def build_prompt(
    schema_text: str,
    examples: list[Example],
    question: str,
    memory: list[MemoryTurn] | None = None,
) -> str:
    parts = [SYSTEM_INSTRUCTION, "", "数据库Schema:", schema_text, ""]
    if examples:
        parts.append("示例:")
        for ex in examples:
            parts.append(f"Q: {ex.question}")
            parts.append(f"SQL: {ex.sql}")
            parts.append("")
    if memory:
        parts.append("最近对话记忆(仅供参考):")
        for turn in memory:
            parts.append(f"Q: {turn.question}")
            parts.append(f"SQL: {turn.sql}")
            parts.append("")
    parts.append("请将下列问题转换为SQL，只输出SQL:")
    parts.append(f"问题: {question}")
    parts.append("SQL:")
    return "\n".join(parts)
