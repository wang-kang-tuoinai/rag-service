import asyncio
from typing import cast

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request

import chat_scroll
import generator
import retriever

# ---------- 请求 / 响应模型 ----------


class ListHistoryRequest(BaseModel):
    limit: int = Field(20, ge=1, le=100, description="每页条数")
    cursor: int | None = Field(
        None, description="上一页最后一条的 updated_at，首页不传"
    )


class ConversationSummary(BaseModel):
    id: str
    title: str | None
    created_at: int
    updated_at: int  # TODO Update是秒级，两个会话同时更新可能会漏一条


class ListHistoryResponse(BaseModel):
    items: list[ConversationSummary]
    next_cursor: int | None = None  # 下一页锚点；None 表示到底了
    has_more: bool = False  # 是否还有更多，前端据此判断要不要继续滚


class ListMessagesRequest(BaseModel):
    limit: int = Field(20, ge=1, le=100, description="每页条数")
    cursor: int | None = Field(
        None, description="上一页最后一条的 timestamp，首页不传"
    )


class Reference(BaseModel):
    source: str
    topic: str


class MessageItem(BaseModel):
    role: str
    content: str
    timestamp: int
    references: list[Reference] = []


class ListMessagesResponse(BaseModel):
    conversation_id: str
    items: list[MessageItem]
    next_cursor: int | None = None
    has_more: bool = False


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    conversation_id: str
    references: list[Reference]


# ---------- 路由 ----------
# 版本管理：一个版本一个 APIRouter，在 main.py 里用 prefix 挂载
#   app.include_router(v1_router, prefix="/api/v1")  ->  /api/v1/history/
#   app.include_router(v2_router, prefix="/api/v2")  ->  /api/v2/history/
# 以后要改返回结构，只改 v2，v1 保持不变，老客户端不受影响。

v1_router = APIRouter()
v2_router = APIRouter()


def _paginate_history(params: ListHistoryRequest) -> ListHistoryResponse:
    """游标分页的核心逻辑，两个版本共用"""
    convs = chat_scroll.list_conversations()  # 已按 updated_at 降序
    if params.cursor is not None:
        convs = [c for c in convs if c["updated_at"] < params.cursor]

    page = convs[: params.limit + 1]  # 多取一条，用来判断有没有下一页
    has_more = len(page) > params.limit
    items = page[: params.limit]
    next_cursor = items[-1]["updated_at"] if has_more and items else None

    return ListHistoryResponse(
        items=[
            ConversationSummary(
                id=c["id"],
                title=c["title"],
                created_at=c["created_at"],
                updated_at=c["updated_at"],
            )
            for c in items
        ],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@v1_router.get("/history/", response_model=ListHistoryResponse)
def list_history_v1(params: ListHistoryRequest = Depends()):
    return _paginate_history(params)


@v2_router.get("/history/", response_model=ListHistoryResponse)
def list_history_v2(params: ListHistoryRequest = Depends()):
    return _paginate_history(params)


# ---------- 消息列表接口 ----------


@v1_router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ListMessagesResponse,
)
def list_messages_v1(
    conversation_id: str,
    params: ListMessagesRequest = Depends(),
):
    """游标分页加载对话消息，按 timestamp 倒序"""
    meta = chat_scroll.load_meta(conversation_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    result = chat_scroll.list_messages(
        conversation_id, limit=params.limit, cursor=params.cursor
    )
    return ListMessagesResponse(**result)


# ---------- 问答接口 ----------


def _ask(
    meta: dict | None, question: str, collection, model, reranker
) -> QueryResponse:
    """问答主流程：检索 + 生成 + 落库，两个接口共用（纯同步，调用方负责丢线程）"""
    if meta is None:
        meta = chat_scroll.new_conversation()

    # 从 JSONL 加载历史消息构造 LLM history
    all_msgs = chat_scroll.load_all_messages(meta["id"])
    history = cast(
        list[ChatCompletionMessageParam],
        [
            {"role": m["role"], "content": m["content"]}
            for m in all_msgs
        ],
    )

    query, corpus = generator.generate_query_and_corpus(question, history)
    chunks = retriever.retrieve_with_rank(
        collection, query, model=model, reranker=reranker, corpus=corpus
    )
    answer = (
        generator.generate(question, chunks, history) or "抱歉，生成回答失败，请重试。"
    )

    # 构造引用列表
    refs = [
        {"source": c["metadata"].get("source", ""), "topic": c["metadata"].get("topic", "")}
        for c in chunks
    ]

    # 追加消息并更新元数据（含 references 持久化）
    chat_scroll.save_conversation_with_messages(
        meta, user_content=question, assistant_content=answer, references=refs
    )

    return QueryResponse(
        answer=answer,
        conversation_id=meta["id"],
        references=[
            Reference(source=r["source"], topic=r["topic"])
            for r in refs
        ],
    )


@v1_router.post("/ask", response_model=QueryResponse)
async def ask_new(req: QueryRequest, request: Request):
    """新建对话并提问"""
    state = request.app.state
    return await asyncio.to_thread(
        _ask, None, req.question, state.collection, state.model, state.reranker
    )


@v1_router.post("/conversations/{conversation_id}/ask", response_model=QueryResponse)
async def ask(req: QueryRequest, conversation_id: str, request: Request):
    """在已有对话里继续提问"""
    meta = await asyncio.to_thread(chat_scroll.load_meta, conversation_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    state = request.app.state
    return await asyncio.to_thread(
        _ask, meta, req.question, state.collection, state.model, state.reranker
    )
