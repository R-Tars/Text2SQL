from __future__ import annotations

import os
import sqlite3

from sqlalchemy import create_engine, inspect


def get_schema_from_sqlite(db_path: str) -> str:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        lines: list[str] = []
        for table in tables:
            if table.startswith("sqlite_"):
                continue
            cursor.execute(f"PRAGMA table_info('{table}')")
            cols = cursor.fetchall()
            col_defs = []
            for _, name, col_type, _, _, _ in cols:
                col_defs.append(f"{name} {col_type}".strip())
            lines.append(f"Table {table}: " + ", ".join(col_defs))
        return "\n".join(lines)
    finally:
        conn.close()


def get_schema(db_path: str) -> str:
    db_url = os.getenv("DB_URL")
    if not db_url:
        # SQLite 增强版：带示例数据
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            lines: list[str] = []
            for table in tables:
                if table.startswith("sqlite_"): continue
                cursor.execute(f"PRAGMA table_info('{table}')")
                cols = cursor.fetchall()
                col_defs = []
                for _, name, col_type, _, _, _ in cols:
                    # 抓取示例数据
                    try:
                        cursor.execute(f"SELECT DISTINCT {name} FROM {table} WHERE {name} IS NOT NULL LIMIT 3")
                        samples = [str(r[0]) for r in cursor.fetchall()]
                        sample_str = f" (示例: {', '.join(samples)})" if samples else ""
                    except:
                        sample_str = ""
                    col_defs.append(f"{name} {col_type}{sample_str}")
                lines.append(f"Table {table}: " + ", ".join(col_defs))
            return "\n".join(lines)
        finally:
            conn.close()
    
    # PostgreSQL 保持原样
    engine = create_engine(db_url)
    inspector = inspect(engine)
    lines: list[str] = []
    for table in sorted(inspector.get_table_names()):
        cols = inspector.get_columns(table)
        col_defs = []
        for col in cols:
            col_defs.append(f"{col['name']} {col['type']}")
        lines.append(f"Table {table}: " + ", ".join(col_defs))
    return "\n".join(lines)
