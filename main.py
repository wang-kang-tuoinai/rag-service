from fastapi import FastAPI
from contextlib import asynccontextmanager
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder
import chromadb
from chromadb.errors import NotFoundError
import asyncio
import logging
import knowledge_api
from knowledge import COLLECTION
from pathlib import Path

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# 过滤 uvicorn 访问日志中的健康探针请求，避免 /health 每 5s 刷屏
class _HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        # 过滤掉 Docker healthcheck 发出的 GET /health 200 日志
        return not ("GET /health" in msg and "200" in msg)

logging.getLogger("uvicorn.access").addFilter(_HealthCheckFilter())


# 初始化 OpenTelemetry（exporter 会自动读 OTEL_EXPORTER_OTLP_ENDPOINT）
tracer_provider = TracerProvider(resource=Resource.create({"service.name": "rag-service"}))
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(tracer_provider)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行一次
    model_task = asyncio.to_thread(SentenceTransformer, "BAAI/bge-base-zh-v1.5")
    reranker_task = asyncio.to_thread(CrossEncoder, "BAAI/bge-reranker-base")
    db_path = Path(__file__).resolve().parent / "my_chroma_data"
    client_task = asyncio.to_thread(chromadb.PersistentClient, path=str(db_path))

    model, reranker, client = await asyncio.gather(
        model_task, reranker_task, client_task
    )
    try:
        collection = await asyncio.to_thread(client.get_collection, COLLECTION)
    except NotFoundError as exc:
        raise RuntimeError(f"{COLLECTION} 索引不存在，请先运行 ingest.py 完成入库") from exc

    # 挂到 app.state 上，路由里用 request.app.state.xxx 访问
    app.state.model = model
    app.state.reranker = reranker
    app.state.collection = collection
    app.state.knowledge_snapshot_dir = db_path / "ops_knowledge_parents"
    try:
        yield
    finally:
        tracer_provider.shutdown()


app = FastAPI(lifespan=lifespan)
# 自动为每一个进入的HTTP请求创建span，并在请求结束时结束span
FastAPIInstrumentor.instrument_app(app)

# 就绪探针：只有 lifespan 加载完模型、Uvicorn 开始服务后才会响应
@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": hasattr(app.state, "model"),
            "collection_loaded": hasattr(app.state, "collection")}

app.include_router(knowledge_api.router, prefix="/api/v1", tags=["knowledge"])

