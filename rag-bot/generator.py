from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
import os
import json

from opentelemetry import trace

tracer = trace.get_tracer("rag-service")

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


def generate(question, chunks, history: list[ChatCompletionMessageParam] | None = None):
    """生成回答，history 为之前多轮的 user/assistant 消息列表，用于多轮记忆"""
    history = history or []
    context = build_context(chunks)
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    messages += history
    user_msg: ChatCompletionMessageParam = {
        "role": "user",
        "content": f"【资料】\n{context}\n\n【问题】\n{question}",
    }
    messages.append(user_msg)
    with tracer.start_as_current_span("generate_answer") as span:
        span.set_attribute("rag.chunk_count", len(chunks))
        resp = client.chat.completions.create(model="deepseek-v4-flash", messages=messages)
        return resp.choices[0].message.content

# 待优化 generate可以与召回并行执行
def generate_title(first_message, max_len=20):
    """根据首条用户消息生成一个简洁的会话标题"""
    prompt = (
        f"请为下面的对话起一个简洁的标题（不超过{max_len}个字），"
        "只返回标题本身，不要加引号或标点符号：\n" + first_message
    )
    with tracer.start_as_current_span("generate_title"):
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
        )
        title = (resp.choices[0].message.content or "").strip()
        return title[:max_len] if title else first_message[:max_len]


def generate_query_and_corpus(
    question, history: list[ChatCompletionMessageParam] | None = None
) -> tuple[str, str]:
    """根据对话历史以及当前用户提问的问题给出合适的query,并判断在哪个语料范围内搜索"""
    history = history or []
    recent = history[-4:]
    system = (
        "你是检索请求分析器。根据用户问题和最近的对话，输出一个 JSON 对象：\n"
        '{"query": "改写后的检索query，应包含具体技术术语", '
        '"corpus": "my-notes 或 go-official 或 all"}\n\n'
        "corpus 判断规则：\n"
        "- my-notes：用户自己的 Redis/MySQL/消息队列/微服务等项目笔记和踩坑记录，"
        "问'我的项目'、'我们的实现'、具体技术原理时选这个\n"
        "- go-official：Go 语言官方文档，问 Go 语法、标准库用法、defer/panic/recover "
        "这类语言本身的问题时选这个\n"
        "- all：不确定属于哪一类，或问题同时涉及两者时选这个\n\n"
        "只返回 JSON，不要任何解释或代码块标记。"
    )
    messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": system}]
    messages += recent
    messages.append({"role": "user", "content": question})
    with tracer.start_as_current_span("generate_query") as span:
        span.set_attribute("rag.question", question)
        span.set_attribute("rag.history_len", len(history))
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0
        )
        raw = (resp.choices[0].message.content or "").strip()
        try:
            result: dict = json.loads(raw)
            query = result.get("query", "").strip() or question
            corpus = result.get("corpus", "all")
            if corpus not in ("my-notes", "go-official", "all"):
                corpus = "all"
            span.set_attribute("rag.query", query)
            span.set_attribute("rag.corpus", corpus)
            return query, corpus
        except json.JSONDecodeError:
            span.set_attribute("rag.query", question)
            span.set_attribute("rag.corpus", "all")
            return question, "all"
