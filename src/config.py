from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

@dataclass(frozen=True)
class AppConfig:
    data_root: str
    db_path: str
    train_json: str
    test_json: str
    test_gold_sql: str

    model_name: str
    api_key: str | None
    base_url: str | None
    temperature: float
    top_k_examples: int


def load_config() -> AppConfig:
    data_root = os.getenv(
        "DATA_ROOT",
        os.path.join(os.getcwd(), "data"),
    )
    db_path = os.path.join(
        data_root, "database", "college_2", "college_2.sqlite"
    )

    return AppConfig(
        data_root=data_root,
        db_path=db_path,
        train_json=os.path.join(data_root, "train.json"),
        test_json=os.path.join(data_root, "test.json"),
        test_gold_sql=os.path.join(data_root, "test_gold.sql"),
        model_name=os.getenv("LLM_MODEL_NAME", "deepseek-chat"),
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=float(os.getenv("TEMPERATURE", "0")),
        top_k_examples=int(os.getenv("TOP_K", "5")),
    )
