# 作用: 在隔离的内存数据库中执行和评测SQL语句。

import sqlite3
import hashlib
import json
from typing import List, Any, Tuple, Dict


def _hash_result(result: List[Dict]) -> str:
    """
    健壮的哈希算法，忽略行、列顺序和列别名。
    """
    if not result:
        return hashlib.sha256(b"[]").hexdigest()

    standardized_rows = []
    for row in result:
        sorted_values = sorted([str(v) for v in row.values()])
        standardized_rows.append(tuple(sorted_values))

    standardized_rows.sort()
    final_string_to_hash = json.dumps(standardized_rows)
    return hashlib.sha256(final_string_to_hash.encode('utf-8')).hexdigest()


def evaluate_sql_in_isolation(setup_sql: str, correct_sql: str, user_sql: str) -> Dict:
    """
    在隔离的内存数据库中评测用户的SQL。
    返回一个包含评测结果的字典。
    """
    # 1. 创建一个内存中的SQLite数据库
    try:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 2. 执行建表和插入数据脚本
        cursor.executescript(setup_sql)
        conn.commit()
    except sqlite3.Error as e:
        return {
            "status": "setup_error",
            "error": f"题目设置脚本执行失败: {e}",
        }

    # 3. 执行用户的SQL
    user_result = None
    try:
        cursor.execute(user_sql)
        user_result = [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        conn.close()
        return {
            "status": "syntax_error",
            "error": str(e),
        }

    # 4. 执行正确的SQL
    correct_result = None
    try:
        cursor.execute(correct_sql)
        correct_result = [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        conn.close()
        return {
            "status": "setup_error",  # 正确SQL出错也算题目设置问题
            "error": f"题库中的正确SQL执行失败: {e}",
        }

    conn.close()

    # 5. 比对结果
    user_hash = _hash_result(user_result)
    correct_hash = _hash_result(correct_result)

    is_correct = user_hash == correct_hash

    return {
        "status": "correct" if is_correct else "result_error",
        "is_correct": is_correct,
        "user_result": user_result,
        "correct_result": correct_result,
        "error": None
    }
