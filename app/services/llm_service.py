# 作用: 封装与大模型API的交互逻辑。

import openai
import dashscope
import json
from typing import List, AsyncGenerator
from ..config import settings
from ..schemas import LLMGeneratedQuestion

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
                # 【重要修复】根据官方文档修正通义千问流式响应的处理方式
                if response.status_code == 200:
                    # 直接从 response.output.text 获取增量内容
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

async def generate_question_from_llm(topics: List[str], schema: str, llm_provider: str) -> LLMGeneratedQuestion:
    """调用LLM根据数据库表结构和指定知识点生成题目。"""
    system_prompt = "你是一个SQL题目生成专家。你的任务是根据提供的数据库表结构和知识点，生成一个SQL查询问题和对应的正确SQL答案。你必须以一个不包含任何其他解释的、纯粹的JSON格式返回结果。"
    user_prompt = f"""
数据库表结构如下:
---
{schema}
---
请生成一个SQL查询问题，该问题必须同时考察以下知识点: {', '.join(topics)}。

请严格按照以下JSON格式返回，不要有任何多余的文字或解释:
{{
  "question": "这里是给用户看的问题描述，例如：'查询每个部门中工资最高的员工姓名及其工资。'",
  "sql": "SELECT ... FROM ...;"
}}
"""
    response_text = await _call_llm(llm_provider, system_prompt, user_prompt)
    try:
        data = json.loads(response_text)
        return LLMGeneratedQuestion(**data)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"解析LLM返回的JSON失败: {e}\n原始返回: {response_text}")
        return LLMGeneratedQuestion(
            question="抱歉，生成题目时发生错误，请稍后再试。",
            sql="SELECT 'error';"
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
