from fastapi import FastAPI
from contextlib import asynccontextmanager
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder
import chromadb
import asyncio
import api

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
    # 关闭时执行(如果需要清理)


app = FastAPI(lifespan=lifespan)

app.include_router(api.v1_router, prefix="/api/v1",tags=["v1"])

