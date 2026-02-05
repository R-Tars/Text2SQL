from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Example:
    question: str
    sql: str


def _load_json(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_examples(train_json: str, db_id: str) -> list[Example]:
    data = _load_json(train_json)
    examples: list[Example] = []
    for item in data:
        if item.get("db_id") != db_id:
            continue
        question = item.get("question", "").strip()
        sql = item.get("query", "").strip()
        if question and sql:
            examples.append(Example(question=question, sql=sql))
    return examples


def load_questions(test_json: str, db_id: str) -> list[str]:
    data = _load_json(test_json)
    questions: list[str] = []
    # 过滤掉 test.json 中由于 Spider 数据集特性可能存在的重复或错位
    for item in data:
        if item.get("db_id") != db_id:
            continue
        question = item.get("question", "").strip()
        if question:
            questions.append(question)
    return questions


def load_gold_sql(test_json: str, db_id: str) -> list[str]:
    """
    直接从 test.json 中加载标准 SQL，确保问题和答案绝对对齐。
    """
    data = _load_json(test_json)
    sqls: list[str] = []
    for item in data:
        if item.get("db_id") != db_id:
            continue
        sql = item.get("query", "").strip()
        if sql:
            sqls.append(sql)
    return sqls


def chunk_iter(items: Iterable, n: int) -> list[list]:
    chunk: list = []
    chunks: list[list] = []
    for item in items:
        chunk.append(item)
        if len(chunk) >= n:
            chunks.append(chunk)
            chunk = []
    if chunk:
        chunks.append(chunk)
    return chunks
