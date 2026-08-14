from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
import os

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com"
)

SYSTEM_PROMPT = """你是一个技术文档问答助手。请严格基于下面提供的资料回答问题。

要求:
1. 只使用资料中的信息,不要用你自己的知识补充
2. 如果资料中没有相关信息,直接说"提供的资料中没有相关内容",不要编造
3. 回答时标注信息来自哪一条资料,格式如 [1]
"""


def build_context(chunks):
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"[{i}] (来自:{c['metadata']['source']} - {c['metadata']['topic']})\n{c['document']}"
        )
    return "\n\n".join(parts)


def generate(question, chunks, history=None):
    """生成回答，history 为之前多轮的 user/assistant 消息列表，用于多轮记忆"""
    history = history or []
    context = build_context(chunks)
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    messages += history
    messages.append(
        {"role": "user", "content": f"【资料】\n{context}\n\n【问题】\n{question}"}
    )
    resp = client.chat.completions.create(model="deepseek-v4-flash", messages=messages)
    return resp.choices[0].message.content


def generate_title(first_message, max_len=20):
    """根据首条用户消息生成一个简洁的会话标题"""
    prompt = (
        f"请为下面的对话起一个简洁的标题（不超过{max_len}个字），"
        "只返回标题本身，不要加引号或标点符号：\n" + first_message
    )
    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": prompt}],
    )
    title = (resp.choices[0].message.content or "").strip()
    return title[:max_len] if title else first_message[:max_len]


def generate_query(question, history=None):
    """根据对话历史以及当前用户提问的问题给出合适的query"""
    prompt = (
        "请为下面用户的问题生成合适的query用于RAG检索，"
        "只返回query本身："
        f"{question}"
    )
    history = history or []
    messages: list[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": (
                "你是一个检索查询改写助手。根据对话历史，把用户的问题改写成一个"
                "独立、完整、包含具体技术术语的检索查询。只输出查询本身，不要解释。"
            ),
        }
    ]
    messages.extend(history[-4:])
    messages.append(
        {"role":"user","content":prompt}
    )
    resp = client.chat.completions.create(model="deepseek-v4-flash", messages=messages)
    query = (resp.choices[0].message.content or "").strip()
    query = query.strip('"\'“”‘’「」『』`')
    return query or question