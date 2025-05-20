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
import uuid
from mcp_server import MCPServer

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
mcp_server = MCPServer()

class QueryRequest(BaseModel):
    query: str
    session_id: str = None
    web_search: bool = False

class FeedbackRequest(BaseModel):
    query: str
    doc_id: str
    is_helpful: bool
    session_id: str
    metadata: dict = {}

@app.post("/chat")
async def chat(req: QueryRequest):
    try:
        # if not session_id, generate a new one
        if not req.session_id:
            req.session_id = str(uuid.uuid4())
            
        # Initialize MCP session if needed
        if not mcp_server.mcp.get_context(req.session_id):
            await mcp_server.initialize_session(req.session_id)
            
        # Process query using ReAct agent with MCP support
        result = react_agent.run(req.query, req.session_id)
        
        # If web search is requested, perform it
        if req.web_search:
            search_results = await mcp_server.web_search(req.query, req.session_id)
            result["web_search_results"] = search_results
            
        # Enrich context with additional data
        await mcp_server.enrich_context(req.session_id, {
            "query": req.query,
            "result": result
        })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    try:
        feedback = Feedback(
            query=req.query,
            doc_id=req.doc_id,
            is_helpful=req.is_helpful,
            timestamp=datetime.now().isoformat(),
            metadata={
                **req.metadata,
                "session_id": req.session_id
            }
        )
        feedback_manager.add_feedback(feedback)
        
        # Notify MCP server about feedback
        await mcp_server.enrich_context(req.session_id, {
            "feedback": feedback.dict()
        })
        
        return {"status": "success", "message": "Feedback recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/feedback/stats")
async def get_feedback_stats():
    try:
        stats = feedback_manager.get_feedback_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "Welcome to the B2B Sales Intelligence API with ReAct Architecture, MCP Protocol, and Feedback System"} 