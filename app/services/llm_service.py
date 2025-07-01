
import openai
import dashscope

from ..config import settings

async def _call_llm(llm_provider: str, system_prompt: str, user_prompt: str) -> str:
    """一个统一的LLM非流式调用函数，返回完整响应。"""
    try:
        if llm_provider == "deepseek":
            client = openai.AsyncOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_API_BASE,
            )
            completion = await client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=False # 禁用流式输出
            )
            return completion.choices[0].message.content or ""
        elif llm_provider == "qwen":
            dashscope.api_key = settings.QWEN_API_KEY
            response = dashscope.Generation.call(
                model='qwen-max',
                prompt=user_prompt,
                system_prompt=system_prompt,
                stream=False, # 禁用流式输出
                incremental_output=False # 禁用增量输出
            )
            if response.status_code == 200:
                return response.output.text
            else:
                print(f"Qwen API error: {response.message}, Code: {response.code}")
                return f"大模型服务错误：{response.message}"
        else:
            return "不支持的LLM提供商。"
    except openai.APIConnectionError as e:
        print(f"LLM API连接错误: {e}")
        return f"与大模型服务连接失败：{e}"
    except openai.RateLimitError as e:
        print(f"LLM API限流错误: {e}")
        return "大模型请求过于频繁，请稍后再试。"
    except openai.APIStatusError as e:
        print(f"LLM API状态错误: {e.status_code} - {e.response}")
        return f"大模型服务返回错误：{e.status_code}"
    except Exception as e:
        print(f"调用LLM时发生未知错误: {e}")
        return f"发生未知错误：{e}"

async def get_llm_explanation(topic: str, llm_provider: str) -> str: # 返回类型改为 str
    """
    调用LLM解释一个SQL知识点（非流式）。
    """
    system_prompt = """你是一个友好的SQL知识讲解专家。你的任务是帮助用户理解复杂的SQL概念。
请使用清晰、简洁的语言，并尽可能包含实际的SQL代码示例。请以Markdown格式输出。
"""
    user_prompt = f"请详细解释SQL中的 '{topic}' 概念。"
    return await _call_llm(llm_provider, system_prompt, user_prompt)