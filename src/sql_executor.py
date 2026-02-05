from __future__ import annotations

import sqlite3
import os
from dataclasses import dataclass

from sqlalchemy import create_engine, text


@dataclass(frozen=True)
class QueryResult:
    columns: list[str]
    rows: list[tuple]
    row_count: int


def execute_sql(db_path: str, sql: str, max_rows: int = 200) -> QueryResult:
    cleaned = _sanitize_sql(sql)
    if cleaned is None:
        raise ValueError("只允许执行单条SELECT语句。")

    final_sql = _ensure_limit(cleaned, max_rows)
    db_url = os.getenv("DB_URL")
    if db_url:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text(final_sql))
            rows = result.fetchall()
            columns = list(result.keys())
            return QueryResult(columns=columns, rows=rows, row_count=len(rows))
    else:
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(final_sql)
            rows = cursor.fetchall()
            columns = (
                [d[0] for d in cursor.description] if cursor.description else []
            )
            return QueryResult(columns=columns, rows=rows, row_count=len(rows))
        finally:
            conn.close()


def _sanitize_sql(sql: str) -> str | None:
    cleaned = sql.strip().rstrip(";")
    if not cleaned:
        return None
    lowered = cleaned.lower()
    if not lowered.startswith("select"):
        return None
    if ";" in cleaned:
        return None
    return cleaned


def _ensure_limit(sql: str, max_rows: int) -> str:
    import re
    lowered = sql.lower()
    # 使用正则表达式单词边界匹配，无论前面是空格、换行还是制表符都能识别
    if re.search(r"\blimit\b", lowered):
        return sql
    return f"{sql} LIMIT {max_rows}"
