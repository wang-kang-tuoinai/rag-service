from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
import os

client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"),base_url="https://api.deepseek.com")

PROMPT_TEMPLATE = """你是一个技术文档问答助手。请严格基于下面提供的资料回答问题。

要求:
1. 只使用资料中的信息,不要用你自己的知识补充
2. 如果资料中没有相关信息,直接说"提供的资料中没有相关内容",不要编造
3. 回答时标注信息来自哪一条资料,格式如 [1]

【资料】
{context}

【问题】
{question}
"""

def build_context(chunks):
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[{i}] (来自:{c["metadata"]['source']} - {c["metadata"]['topic']})\n{c['document']}")
    return "\n\n".join(parts)

def generate(question, chunks):
    context = build_context(chunks)
    messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": PROMPT_TEMPLATE.format(
        context=context, question=question)}]
    resp = client.chat.completions.create(model="deepseek-v4-flash", messages=messages)
    return resp.choices[0].message.content