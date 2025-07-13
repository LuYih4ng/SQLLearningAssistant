# 作用: 封装所有与练习数据库交互的逻辑，包括执行SQL、比对结果等。

import sqlite3
import hashlib
import json
from typing import List, Any, Tuple, Optional


def _execute_sql(db_path: str, sql: str) -> Tuple[Optional[List[Any]], Optional[str]]:
    """
    在一个独立的函数中执行SQL语句，方便错误捕获。
    返回 (结果, 错误信息) 的元组。
    """
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            result = [dict(row) for row in cursor.fetchall()]
            return result, None
    except sqlite3.Error as e:
        return None, str(e)


def _hash_result(result: List[Any]) -> str:
    """
    【重要修改】将查询结果（一个字典列表）标准化处理后计算其哈希值。
    这个新算法可以忽略行和列的顺序，以及列的别名。
    """
    if not result:
        # 对空结果集返回一个固定的哈希值
        return hashlib.sha256(b"[]").hexdigest()

    # 1. 将每一行（字典）都转换为一个只包含其值的、经过排序的元组。
    #    例如：{"name": "研发部", "count": 3} -> (3, "研发部")
    #    我们先将所有值转为字符串，以确保可以排序。
    standardized_rows = []
    for row in result:
        # sorted() 会返回一个排序后的列表
        sorted_values = sorted([str(v) for v in row.values()])
        standardized_rows.append(tuple(sorted_values))

    # 2. 对所有代表“行”的元组进行排序。
    #    这确保了即便结果集的行顺序不同，最终的哈希值也相同。
    standardized_rows.sort()

    # 3. 将整个结果转换为一个巨大的、规范化的JSON字符串。
    #    这比简单拼接字符串更健壮。
    final_string_to_hash = json.dumps(standardized_rows)

    # --- 调试代码 ---
    print("--- DEBUG: Hashing following final canonical string ---")
    print(final_string_to_hash)
    print("-------------------------------------------------------")

    # 4. 对这个最终的、完全标准化的字符串进行哈希
    return hashlib.sha256(final_string_to_hash.encode('utf-8')).hexdigest()


class SQLExecutor:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_db_schema(self) -> str:
        """
        读取并返回练习数据库的表结构 (CREATE TABLE 语句)。
        """
        schema_str = ""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                tables = cursor.fetchall()
                for table in tables:
                    schema_str += table[1] + ";\n"
            return schema_str
        except sqlite3.Error as e:
            print(f"获取数据库表结构失败: {e}")
            return "无法获取表结构。"

    def execute_and_get_hash(self, sql: str) -> Tuple[Optional[str], Optional[str]]:
        """
        执行SQL并返回结果的哈希值。
        如果执行出错，返回 (None, 错误信息)。
        """
        result, error = _execute_sql(self.db_path, sql)
        if error:
            return None, error

        result_hash = _hash_result(result)
        return result_hash, None

    def execute_and_compare(self, user_sql: str, correct_result_hash: str) -> Tuple[
        bool, Optional[str], Optional[List[Any]]]:
        """
        执行用户的SQL，并将结果哈希与正确的哈希进行比较。
        返回 (是否正确, 错误信息, 用户查询结果) 的元组。
        """
        user_result, error = _execute_sql(self.db_path, user_sql)
        if error:
            return False, error, None

        user_result_hash = _hash_result(user_result)

        print("\n--- DEBUG: Hash Comparison ---")
        print(f"User Hash:   {user_result_hash}")
        print(f"Correct Hash:{correct_result_hash}")
        print("----------------------------\n")

        is_correct = user_result_hash == correct_result_hash
        return is_correct, None, user_result
