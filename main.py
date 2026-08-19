from fastapi import FastAPI
from contextlib import asynccontextmanager
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder
import chromadb
import asyncio
import api

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# 初始化 OpenTelemetry（exporter 会自动读 OTEL_EXPORTER_OTLP_ENDPOINT）
tracer_provider = TracerProvider(resource=Resource.create({"service.name": "rag-service"}))
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(tracer_provider)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行一次
    model_task = asyncio.to_thread(SentenceTransformer, "BAAI/bge-base-zh-v1.5")
    reranker_task = asyncio.to_thread(CrossEncoder, "BAAI/bge-reranker-base")
    client_task = asyncio.to_thread(chromadb.PersistentClient, path="./my_chroma_data")

    model, reranker, client = await asyncio.gather(
        model_task, reranker_task, client_task
    )
    collection = await asyncio.to_thread(client.get_collection, "go_docs")

    # 挂到 app.state 上，路由里用 request.app.state.xxx 访问
    app.state.model = model
    app.state.reranker = reranker
    app.state.client = client
    app.state.collection = collection
    yield
    tracer_provider.shutdown()


app = FastAPI(lifespan=lifespan)
# 自动为每一个进入的HTTP请求创建span，并在请求结束时结束span
FastAPIInstrumentor.instrument_app(app)

# 就绪探针：只有 lifespan 加载完模型、Uvicorn 开始服务后才会响应
@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": hasattr(app.state, "model")}

app.include_router(api.v1_router, prefix="/api/v1",tags=["v1"])

