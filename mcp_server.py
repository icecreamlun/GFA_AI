from fastapi import FastAPI, HTTPException, WebSocket
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import httpx
import json
from datetime import datetime
import asyncio
from mcp_protocol import MCPProtocol, MCPContext, MCPMessage
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MCPServer:
    """Enhanced MCP Server with additional capabilities"""
    
    def __init__(self):
        self.mcp = MCPProtocol()
        self.active_websockets: Dict[str, List[WebSocket]] = {}
        self.http_client = httpx.AsyncClient()
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")
        
    async def initialize_session(self, session_id: str) -> MCPContext:
        """Initialize a new session with enhanced capabilities"""
        context = self.mcp.create_context(session_id)
        self.mcp.update_context(session_id, {
            "capabilities": {
                "web_browsing": True,
                "real_time_updates": True,
                "context_compression": True
            },
            "session_start_time": datetime.now().isoformat()
        })
        return context
    
    async def web_search(self, query: str, session_id: str) -> Dict[str, Any]:
        """Perform web search using Google Custom Search API and integrate results into context"""
        try:
            if not self.google_api_key or not self.google_cse_id:
                raise HTTPException(
                    status_code=500,
                    detail="Google API credentials not configured"
                )

            # Construct Google Custom Search API URL
            base_url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_api_key,
                "cx": self.google_cse_id,
                "q": query,
                "num": 5  # Number of results to return
            }

            # Make API request
            async with httpx.AsyncClient() as client:
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                search_data = response.json()

            # Process and format search results
            search_results = {
                "query": query,
                "total_results": search_data.get("searchInformation", {}).get("totalResults", "0"),
                "search_time": search_data.get("searchInformation", {}).get("searchTime", 0),
                "results": []
            }

            # Extract relevant information from each result
            for item in search_data.get("items", []):
                result = {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": item.get("displayLink", ""),
                    "metadata": {
                        "pagemap": item.get("pagemap", {}),
                        "mime": item.get("mime", ""),
                        "fileFormat": item.get("fileFormat", "")
                    }
                }
                search_results["results"].append(result)

            # Update MCP context with search results
            self.mcp.update_context(session_id, {
                "web_search_results": search_results,
                "last_search_time": datetime.now().isoformat(),
                "search_metadata": {
                    "query": query,
                    "total_results": search_results["total_results"],
                    "search_time": search_results["search_time"]
                }
            })

            # Notify connected clients about new search results
            await self.real_time_update(session_id, {
                "type": "search_completed",
                "data": {
                    "query": query,
                    "result_count": len(search_results["results"])
                }
            })

            return search_results

        except httpx.HTTPError as e:
            error_msg = f"HTTP error occurred: {str(e)}"
            await self.real_time_update(session_id, {
                "type": "search_error",
                "data": {"error": error_msg}
            })
            raise HTTPException(status_code=500, detail=error_msg)
        except Exception as e:
            error_msg = f"Web search failed: {str(e)}"
            await self.real_time_update(session_id, {
                "type": "search_error",
                "data": {"error": error_msg}
            })
            raise HTTPException(status_code=500, detail=error_msg)
    
    async def real_time_update(self, session_id: str, data: Dict[str, Any]):
        """Send real-time updates to connected clients"""
        if session_id in self.active_websockets:
            for websocket in self.active_websockets[session_id]:
                try:
                    await websocket.send_json({
                        "type": "update",
                        "timestamp": datetime.now().isoformat(),
                        "data": data
                    })
                except Exception as e:
                    print(f"Error sending update: {str(e)}")
    
    async def connect_websocket(self, websocket: WebSocket, session_id: str):
        """Handle new WebSocket connection"""
        await websocket.accept()
        if session_id not in self.active_websockets:
            self.active_websockets[session_id] = []
        self.active_websockets[session_id].append(websocket)
        
        # Send initial context
        context = self.mcp.get_context(session_id)
        if context:
            await websocket.send_json({
                "type": "context",
                "data": context.dict()
            })
    
    async def disconnect_websocket(self, websocket: WebSocket, session_id: str):
        """Handle WebSocket disconnection"""
        if session_id in self.active_websockets:
            self.active_websockets[session_id].remove(websocket)
            if not self.active_websockets[session_id]:
                del self.active_websockets[session_id]
    
    async def compress_context(self, session_id: str) -> Dict[str, Any]:
        """Compress and optimize context for better performance"""
        context = self.mcp.get_context(session_id)
        if not context:
            return {}
            
        # Implement context compression logic
        compressed = {
            "session_id": context.session_id,
            "current_context": {
                k: v for k, v in context.current_context.items()
                if k in ["current_query", "search_results", "generated_suggestions"]
            },
            "metadata": context.metadata
        }
        
        return compressed
    
    async def enrich_context(self, session_id: str, data: Dict[str, Any]):
        """Enrich context with additional data"""
        if session_id in self.mcp.contexts:
            self.mcp.update_context(session_id, {
                "enriched_data": data,
                "enrichment_time": datetime.now().isoformat()
            })
            
            # Notify connected clients
            await self.real_time_update(session_id, {
                "type": "context_enriched",
                "data": data
            })

# Create FastAPI app for MCP Server
mcp_app = FastAPI(title="MCP Server")
mcp_server = MCPServer()

@mcp_app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await mcp_server.connect_websocket(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            # Handle incoming WebSocket messages
            if data.get("type") == "web_search":
                results = await mcp_server.web_search(data["query"], session_id)
                await websocket.send_json({"type": "search_results", "data": results})
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        await mcp_server.disconnect_websocket(websocket, session_id)

@mcp_app.post("/enrich/{session_id}")
async def enrich_context(session_id: str, data: Dict[str, Any]):
    await mcp_server.enrich_context(session_id, data)
    return {"status": "success"}

@mcp_app.get("/context/{session_id}")
async def get_context(session_id: str):
    context = mcp_server.mcp.get_context(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    return context.dict()

@mcp_app.post("/compress/{session_id}")
async def compress_context(session_id: str):
    compressed = await mcp_server.compress_context(session_id)
    return compressed 