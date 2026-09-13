"""知识检索 HTTP 接口：不生成答案、不接入 Agent 工具。"""
import logging
from typing import Literal

from chromadb.errors import NotFoundError
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from knowledge import COLLECTION, KnowledgeUnavailable, search_knowledge

router = APIRouter()
logger = logging.getLogger(__name__)


class KnowledgeSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    doc_type: Literal["architecture", "runbook", "technology"] | None = None
    top_k: int = Field(default=3, ge=1, le=5, strict=True)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query 不能只包含空白")
        return value


class KnowledgeItem(BaseModel):
    doc_id: str
    snapshot_id: str
    title: str
    doc_type: Literal["architecture", "runbook", "technology"]
    source: str
    score: float
    matched_sections: list[str]
    content: str
    content_mode: Literal["full"]


class KnowledgeSearchResponse(BaseModel):
    items: list[KnowledgeItem]
    notices: list[str]


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
def query_knowledge(params: KnowledgeSearchRequest, request: Request):
    # 同步路由由 FastAPI 在线程池执行，模型推理不阻塞事件循环。
    state = request.app.state
    if not all(hasattr(state, key) for key in ("client", "model", "reranker", "knowledge_snapshot_dir")):
        raise HTTPException(503, "知识检索依赖尚未就绪")
    try:
        collection = state.client.get_collection(COLLECTION)
        return search_knowledge(collection, state.model, state.reranker,
                                state.knowledge_snapshot_dir, params.query,
                                params.doc_type, params.top_k)
    except NotFoundError as exc:
        raise HTTPException(503, "ops_knowledge 索引不存在，请先运行 ingest.py") from exc
    except KnowledgeUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        logger.exception("知识检索失败")
        raise HTTPException(503, "知识检索暂不可用，请检查索引和模型状态") from exc
