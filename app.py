import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from vectordb_utils import VectorDB
from openai import OpenAI
import httpx
from dotenv import load_dotenv
from react_agent import ReActAgent
from feedback_manager import Feedback, FeedbackManager
from datetime import datetime

# 加载环境变量
load_dotenv()

# 创建自定义的 httpx 客户端
http_client = httpx.Client()

# 初始化 OpenAI 客户端
client = OpenAI(http_client=http_client)

app = FastAPI()

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)

# 初始化向量数据库和ReAct代理
vectordb = VectorDB()
react_agent = ReActAgent(vectordb, client)
feedback_manager = FeedbackManager()

class QueryRequest(BaseModel):
    query: str

class FeedbackRequest(BaseModel):
    query: str
    doc_id: str
    is_helpful: bool
    metadata: dict = {}

@app.post("/chat")
def chat(req: QueryRequest):
    try:
        # 使用ReAct代理处理查询
        result = react_agent.run(req.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    try:
        feedback = Feedback(
            query=req.query,
            doc_id=req.doc_id,
            is_helpful=req.is_helpful,
            timestamp=datetime.now().isoformat(),
            metadata=req.metadata
        )
        feedback_manager.add_feedback(feedback)
        return {"status": "success", "message": "Feedback recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/feedback/stats")
def get_feedback_stats():
    try:
        stats = feedback_manager.get_feedback_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "Welcome to the B2B Sales Intelligence API with ReAct Architecture and Feedback System"} 