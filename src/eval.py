from __future__ import annotations

import argparse
import os
import time
from tqdm import tqdm

from .config import load_config
from .data_loader import load_examples, load_gold_sql, load_questions
    # 修正：直接从 test.json 加载 SQL 以保证对齐
from .llm import LLMClient
from .prompt import build_prompt
from .retrieval import HybridRetriever
from .schema import get_schema
from .sql_executor import execute_sql


def _normalize_val(v):
    if v is None: return None
    if isinstance(v, (int, float)): return float(v)
    return str(v).strip().lower()

def _compare_results(pred: list[tuple], gold: list[tuple]) -> bool:
    if not pred and not gold: return True
    if not pred or not gold: return False
    if len(pred) != len(gold): return False
    
    norm_pred = [tuple(_normalize_val(x) for x in row) for row in pred]
    norm_gold = [tuple(_normalize_val(x) for x in row) for row in gold]
    
    if set(norm_pred) == set(norm_gold): return True
    
    import itertools
    num_cols = len(norm_gold[0])
    if num_cols <= 4:
        gold_set = set(norm_gold)
        for p in itertools.permutations(range(num_cols)):
            permuted_pred = set(tuple(row[i] for i in p) for row in norm_pred)
            if permuted_pred == gold_set: return True
    return False


def evaluate(
    db_path: str,
    train_json: str,
    test_json: str,
    model_name: str,
    api_key: str | None,
    base_url: str | None,
    top_k: int,
    limit: int | None,
) -> None:
    schema_text = get_schema(db_path)
    examples = load_examples(train_json, "college_2")
    
    print("正在初始化混合检索索引...")
    retriever = HybridRetriever(examples)

    questions = load_questions(test_json, "college_2")
    gold_sqls = load_gold_sql(test_json, "college_2")
    
    total = min(len(questions), len(gold_sqls))
    questions = questions[:total]
    gold_sqls = gold_sqls[:total]
    
    if limit:
        questions = questions[:limit]
        gold_sqls = gold_sqls[:limit]
        total = len(questions)

    llm = LLMClient(model_name=model_name, api_key=api_key, base_url=base_url, temperature=0.0)

    correct = 0
    start_time = time.time()
    results_detail = []

    for i, (question, gold_sql) in enumerate(tqdm(list(zip(questions, gold_sqls))[:total])):
        few_shot = retriever.search(question, k=top_k)
        prompt = build_prompt(schema_text, few_shot, question)
        
        step_start = time.time()
        pred_sql = llm.generate_sql(prompt)
        step_time = time.time() - step_start
        
        is_correct = False
        error_msg = None
        try:
            try:
                pred_res = execute_sql(db_path, pred_sql)
            except Exception as e:
                # Execution-guided self-correction (retry once)
                pred_sql = llm.repair_sql(prompt, pred_sql, str(e))
                pred_res = execute_sql(db_path, pred_sql)
            gold_res = execute_sql(db_path, gold_sql)
            if _compare_results(pred_res.rows, gold_res.rows):
                correct += 1
                is_correct = True
        except Exception as e:
            error_msg = str(e)

        results_detail.append({
            "id": i + 1,
            "question": question,
            "gold_sql": gold_sql,
            "pred_sql": pred_sql,
            "is_correct": is_correct,
            "time": step_time,
            "error": error_msg
        })

    elapsed = time.time() - start_time
    accuracy = correct / total if total else 0.0
    avg_time = elapsed / max(total, 1)
    
    print("\n" + "="*50)
    print(f"{'ID':<4} | {'状态':<4} | {'耗时':<6} | {'问题'}")
    print("-" * 50)
    for res in results_detail:
        status_str = "✅" if res["is_correct"] else "❌"
        print(f"{res['id']:<4} | {status_str:<4} | {res['time']:>5.2f}s | {res['question'][:50]}...")
        if not res["is_correct"]:
            print(f"   - 预测SQL: {res['pred_sql']}")
            print(f"   - 标准SQL: {res['gold_sql']}")
            if res["error"]: print(f"   - 错误信息: {res['error']}")
    print("="*50 + "\n")

    print(f"执行准确率: {accuracy:.4f} ({correct}/{total})")
    print(f"平均响应时间: {avg_time:.2f}s")
    
    with open("eval_report.txt", "w", encoding="utf-8") as f:
        f.write(f"评测时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"模型: {model_name} | Top-K: {top_k}\n")
        f.write(f"执行准确率: {accuracy:.4f} ({correct}/{total})\n")
        f.write(f"平均响应时间: {avg_time:.2f}s\n")
        f.write("-" * 30 + "\n")
        for res in results_detail:
            f.write(f"ID: {res['id']} | {'PASS' if res['is_correct'] else 'FAIL'} | Time: {res['time']:.2f}s\n")
            f.write(f"Q: {res['question']}\n")
            f.write(f"Pred: {res['pred_sql']}\n")
            f.write(f"Gold: {res['gold_sql']}\n")
            if res['error']: f.write(f"Error: {res['error']}\n")
            f.write("-" * 20 + "\n")


def main() -> None:
    config = load_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("--db_path", default=config.db_path)
    parser.add_argument("--model_name", default=config.model_name)
    parser.add_argument("--api_key", default=config.api_key)
    parser.add_argument("--base_url", default=config.base_url)
    parser.add_argument("--top_k", type=int, default=config.top_k_examples)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--use_train_set", action="store_true")
    args = parser.parse_args()

    eval_json = config.train_json if args.use_train_set else config.test_json
    print(f"正在使用 {'训练集' if args.use_train_set else '测试集'} 进行评测...")

    evaluate(
        db_path=args.db_path,
        train_json=config.train_json,
        test_json=eval_json,
        model_name=args.model_name,
        api_key=args.api_key,
        base_url=args.base_url,
        top_k=args.top_k,
        limit=args.limit,
    )

if __name__ == "__main__":
    main()
