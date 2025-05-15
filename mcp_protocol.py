from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import json

class MCPContext(BaseModel):
    """MCP Context class for storing and managing model context"""
    session_id: str
    timestamp: str
    query_history: List[Dict[str, Any]]
    current_context: Dict[str, Any]
    metadata: Dict[str, Any] = {}

class MCPMessage(BaseModel):
    """MCP Message class for defining message format"""
    role: str
    content: str
    context: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}

class MCPProtocol:
    """MCP Protocol implementation class"""
    
    def __init__(self):
        self.contexts: Dict[str, MCPContext] = {}
    
    def create_context(self, session_id: str) -> MCPContext:
        """Create a new context"""
        context = MCPContext(
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            query_history=[],
            current_context={},
            metadata={}
        )
        self.contexts[session_id] = context
        return context
    
    def get_context(self, session_id: str) -> Optional[MCPContext]:
        """Get existing context"""
        return self.contexts.get(session_id)
    
    def update_context(self, session_id: str, new_context: Dict[str, Any]) -> None:
        """Update context"""
        if session_id in self.contexts:
            self.contexts[session_id].current_context.update(new_context)
            self.contexts[session_id].timestamp = datetime.now().isoformat()
    
    def add_to_history(self, session_id: str, message: MCPMessage) -> None:
        """Add message to history"""
        if session_id in self.contexts:
            self.contexts[session_id].query_history.append({
                "timestamp": datetime.now().isoformat(),
                "message": message.dict()
            })
    
    def get_formatted_context(self, session_id: str) -> str:
        """Get formatted context string"""
        if session_id not in self.contexts:
            return ""
        
        context = self.contexts[session_id]
        return json.dumps({
            "session_id": context.session_id,
            "timestamp": context.timestamp,
            "current_context": context.current_context,
            "metadata": context.metadata
        }, indent=2)
    
    def clear_context(self, session_id: str) -> None:
        """Clear context"""
        if session_id in self.contexts:
            del self.contexts[session_id] 