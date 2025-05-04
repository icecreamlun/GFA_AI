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

# Load environment variables
load_dotenv()

# Create custom httpx client
http_client = httpx.Client()

# Initialize OpenAI client
client = OpenAI(http_client=http_client)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Initialize vector database and ReAct agent
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
        # Process query using ReAct agent
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