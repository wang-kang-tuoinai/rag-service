"""知识检索 HTTP 接口：不生成答案、不接入 Agent 工具。"""
import logging

from chromadb.errors import NotFoundError
from fastapi import APIRouter, HTTPException, Request

from knowledge import COLLECTION, KnowledgeUnavailable, search_knowledge
from knowledge_models import KnowledgeSearchRequest, KnowledgeSearchResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
def query_knowledge(params: KnowledgeSearchRequest, request: Request):
    # 同步路由由 FastAPI 在线程池执行，模型推理不阻塞事件循环。
    state = request.app.state
    if not all(hasattr(state, key) for key in ("client", "model", "reranker")):
        raise HTTPException(503, "知识检索依赖尚未就绪")
    try:
        collection = state.client.get_collection(COLLECTION)
        return search_knowledge(collection, state.model, state.reranker,
                                getattr(state, "knowledge_snapshot_dir", None), params.query,
                                params.doc_type, params.top_k)
    except NotFoundError as exc:
        raise HTTPException(503, "ops_knowledge 索引不存在，请先运行 ingest.py") from exc
    except KnowledgeUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        logger.exception("知识检索失败")
        raise HTTPException(503, "知识检索暂不可用，请检查索引和模型状态") from exc
