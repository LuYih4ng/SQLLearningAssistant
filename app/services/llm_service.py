# 作用: 封装与大模型API的交互逻辑。

import openai
import dashscope
import json
import re # 导入正则表达式模块
from typing import List, AsyncGenerator
from ..config import settings
# 【重要修复】导入了正确的模型名称 LLMGeneratedQuestionData
from ..schemas import LLMGeneratedQuestionData

# --- 底层LLM调用函数 ---
async def _call_llm_stream(llm_provider: str, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
    """一个统一的LLM流式调用函数。"""
    try:
        if llm_provider == "deepseek":
            client = openai.AsyncOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_API_BASE,
            )
            stream = await client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=True
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content or ""
                yield content
        elif llm_provider == "qwen":
            dashscope.api_key = settings.QWEN_API_KEY
            responses = dashscope.Generation.call(
                model='qwen-max',
                prompt=user_prompt,
                system_prompt=system_prompt,
                stream=True,
                incremental_output=True
            )
            for response in responses:
                if response.status_code == 200:
                    if response.output and response.output.text:
                        yield response.output.text
                else:
                    yield f"API Error: {response.code}, {response.message}"
                    break
        else:
            yield "错误：不支持的大模型提供商。"
    except Exception as e:
        print(f"调用LLM流式API时发生错误: {e}")
        yield "抱歉，调用大模型服务时出现问题，请稍后再试。"

async def _call_llm(llm_provider: str, system_prompt: str, user_prompt: str) -> str:
    """一个统一的LLM非流式调用函数，它内部使用流式调用来构建完整响应。"""
    full_content = []
    async for chunk in _call_llm_stream(llm_provider, system_prompt, user_prompt):
        full_content.append(chunk)
    return "".join(full_content)


async def get_llm_explanation(topic: str, llm_provider: str) -> AsyncGenerator[str, None]:
    """以流式方式获取关于SQL知识点的解释。"""
    system_prompt = "你是一个友好的SQL知识讲解专家。"
    user_prompt = f"请用简体中文，为一位SQL初学者详细解释一下'{topic}'这个知识点。请确保解释清晰易懂，并包含一个简单的代码示例。请使用Markdown格式进行排版。"
    async for chunk in _call_llm_stream(llm_provider, system_prompt, user_prompt):
        yield chunk


# --- 【核心修改】题目生成 ---
async def generate_question_from_llm(topics: List[str], llm_provider: str) -> LLMGeneratedQuestionData:
    """
    调用LLM生成一个包含题目描述、建表/插数据SQL和正确查询SQL的完整题目。
    """
    system_prompt = "你是一个高级SQL课程设计师和数据工程师。你的任务是创建一个完整的、自包含的SQL练习题。这包括问题描述、用于创建和填充数据表的SQL语句，以及解决该问题的正确查询语句。你必须以一个不包含任何其他解释的、纯粹的JSON格式返回结果。"
    user_prompt = f"""
请围绕以下SQL知识点: **{', '.join(topics)}** 设计一道题目。

题目要求:
1.  **setup_sql**: 提供一段SQL脚本，包含`CREATE TABLE`语句来定义1到2个相关的表，以及足够的`INSERT INTO`语句来填充这些表，数据量大约在5到10条之间，以便能进行有意义的查询。
2.  **question**: 根据你创建的表和数据，设计一个清晰、明确的查询问题。
3.  **correct_sql**: 提供能解决上述问题的、标准的正确SQL查询语句。

请严格按照以下JSON格式返回，不要有任何多余的文字或解释:
{{
  "question": "这里是给用户看的问题描述。",
  "setup_sql": "CREATE TABLE ...; INSERT INTO ...; INSERT INTO ...;",
  "correct_sql": "SELECT ... FROM ...;"
}}
"""
    response_text = await _call_llm(llm_provider, system_prompt, user_prompt)

    try:
        # 【重要修复】清洗LLM返回的文本，移除Markdown代码块标记
        # 使用正则表达式匹配被 ```json ... ``` 包围的内容
        match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # 如果没有匹配到 ```json, 则假设整个字符串就是JSON
            json_str = response_text

        data = json.loads(json_str)
        return LLMGeneratedQuestionData(**data)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"解析LLM返回的JSON失败: {e}\n原始返回: {response_text}")
        return LLMGeneratedQuestionData(
            question="AI生成题目失败，请检查LLM的返回格式或重试。",
            setup_sql="-- error",
            correct_sql="-- error"
        )

async def analyze_syntax_error(user_sql: str, db_error: str, llm_provider: str) -> str:
    """调用LLM分析用户的SQL语法错误。"""
    system_prompt = "你是一个经验丰富的数据库开发者和SQL导师。你的任务是帮助初学者理解他们的SQL语法错误。"
    user_prompt = f"""
一个SQL初学者提交了下面的SQL语句:
---
{user_sql}
---

数据库返回了以下错误信息:
---
{db_error}
---

请用友好、鼓励的语气，清晰地向这位初学者解释他/她的代码为什么会产生这个语法错误，并给出正确的代码示例。不要谈论其他无关话题。
"""
    return await _call_llm(llm_provider, system_prompt, user_prompt)

async def analyze_result_error(question: str, user_sql: str, correct_sql: str, llm_provider: str) -> str:
    """调用LLM分析用户的SQL逻辑错误。"""
    system_prompt = "你是一个顶尖的SQL逻辑分析专家和导师。你的任务是帮助用户理解为什么他们的SQL语句虽然语法正确，但查询结果却是错误的。"
    user_prompt = f"""
任务背景:
用户需要解决以下SQL问题: "{question}"

正确的SQL答案是:
---
{correct_sql}
---

用户提交的SQL是:
---
{user_sql}
---

用户的SQL语句语法正确，但查询结果与正确答案不符。请仔细比对用户和正确答案的SQL，分析用户代码中可能存在的逻辑错误（例如：JOIN条件错误、聚合函数使用不当、WHERE子句过滤条件错误等）。请用清晰、有条理的方式向用户解释，并引导他/她思考如何修正。
"""
    return await _call_llm(llm_provider, system_prompt, user_prompt)

async def analyze_for_improvement(question: str, user_sql: str, correct_sql: str, llm_provider: str) -> str:
    """
    在用户回答正确后，调用LLM分析其SQL语句，并提供优化建议。
    """
    system_prompt = "你是一位资深的数据库架构师（DBA）和代码审查专家。你的语气专业、友善且富有建设性。"
    user_prompt = f"""
在一个SQL练习中，对于问题：“{question}”，用户提交了以下**正确**的答案：

```sql
-- 用户提交的SQL
{user_sql}
```

作为参考，标准的正确答案是：
```sql
-- 标准答案
{correct_sql}
```

请对用户提交的SQL进行分析，并从以下几个角度提供反馈：
1.  **可读性**: 代码风格是否清晰？命名是否规范？
2.  **性能**: 是否有潜在的性能问题？有没有更高效的写法（例如，使用不同的JOIN类型、避免子查询等）？
3.  **其他方法**: 是否有其他解决问题的思路或可以使用的更高级的SQL特性（如窗口函数）？

如果用户的写法已经非常优秀，请直接夸奖他们。你的回答将直接展示给用户。
"""
    return await _call_llm(llm_provider, system_prompt, user_prompt)
