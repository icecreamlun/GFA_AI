from typing import List, Dict, Any
from pydantic import BaseModel
from openai import OpenAI
import httpx
from vectordb_utils import VectorDB
from datetime import datetime, timedelta
import random
from mcp_protocol import MCPProtocol, MCPMessage

class Observation(BaseModel):
    """观察类，用于存储当前状态和环境信息"""
    query: str
    context: str
    docs: List[Dict[str, Any]]
    current_time: str

class Thought(BaseModel):
    """思考类，用于存储推理过程和决策"""
    reasoning: str
    next_action: str
    suggestions: List[Dict[str, Any]] = []

class Action(BaseModel):
    """行动类，用于执行具体的操作"""
    action_type: str
    parameters: Dict[str, Any]

class Result(BaseModel):
    """结果类，用于存储行动的结果"""
    success: bool
    output: str
    suggestions: List[Dict[str, Any]] = []
    error: str = None

class ReActAgent:
    """ReAct代理类，实现ReAct架构的核心逻辑"""
    
    def __init__(self, vectordb: VectorDB, openai_client: OpenAI):
        self.vectordb = vectordb
        self.client = openai_client
        self.mcp = MCPProtocol()
        
    def _generate_suggestions(self, docs: List[Dict[str, Any]], session_id: str) -> List[Dict[str, Any]]:
        """Generate actionable suggestions for each contractor"""
        suggestions = []
        
        # 更新 MCP 上下文
        self.mcp.update_context(session_id, {
            "current_docs": docs,
            "suggestion_generation_time": datetime.now().isoformat()
        })
        
        for doc in docs:
            # Generate some dynamic data (in a real application, this would come from actual analysis)
            activity_score = random.uniform(0.5, 1.0)  # Simulate activity score
            last_contact_days = random.randint(0, 30)  # Simulate days since last contact
            
            # Generate suggestions based on the data
            if activity_score > 0.8:
                # High activity contractors
                next_contact = datetime.now() + timedelta(days=random.randint(1, 3))
                suggestion = {
                    "type": "high_activity",
                    "contractor": doc["name"],
                    "action": "contact",
                    "reason": "recent high activity",
                    "suggested_date": next_contact.strftime("%Y-%m-%d"),
                    "priority": "high",
                    "details": {
                        "activity_score": round(activity_score, 2),
                        "last_contact_days": last_contact_days,
                        "contact_method": "phone" if doc.get("phone") else "email",
                        "contact_info": doc.get("phone", doc.get("url", ""))
                    }
                }
            elif last_contact_days > 14:
                # Contractors not contacted for a long time
                next_contact = datetime.now() + timedelta(days=random.randint(1, 7))
                suggestion = {
                    "type": "follow_up",
                    "contractor": doc["name"],
                    "action": "follow_up",
                    "reason": f"no contact for {last_contact_days} days",
                    "suggested_date": next_contact.strftime("%Y-%m-%d"),
                    "priority": "medium",
                    "details": {
                        "last_contact_days": last_contact_days,
                        "contact_method": "phone" if doc.get("phone") else "email",
                        "contact_info": doc.get("phone", doc.get("url", ""))
                    }
                }
            else:
                # Regular follow-up
                next_contact = datetime.now() + timedelta(days=random.randint(7, 14))
                suggestion = {
                    "type": "regular_follow_up",
                    "contractor": doc["name"],
                    "action": "schedule_meeting",
                    "reason": "regular follow-up",
                    "suggested_date": next_contact.strftime("%Y-%m-%d"),
                    "priority": "low",
                    "details": {
                        "last_contact_days": last_contact_days,
                        "contact_method": "phone" if doc.get("phone") else "email",
                        "contact_info": doc.get("phone", doc.get("url", ""))
                    }
                }
            
            suggestions.append(suggestion)
        
        # 更新 MCP 上下文
        self.mcp.update_context(session_id, {
            "generated_suggestions": suggestions
        })
        
        return suggestions
    
    def observe(self, query: str, session_id: str) -> Observation:
        """Observe the current state based on the query"""
        docs = self.vectordb.search(query, top_k=3)
        context = "\n\n".join([
            f"Name: {d.get('name')}\nAbout: {d.get('about_us','')}\nAddress: {d.get('address')}\nPhone: {d.get('phone')}\nURL: {d.get('url')}\n"
            for d in docs
        ])
        
        # 创建或获取 MCP 上下文
        if not self.mcp.get_context(session_id):
            self.mcp.create_context(session_id)
        
        # 更新 MCP 上下文
        self.mcp.update_context(session_id, {
            "current_query": query,
            "search_results": docs,
            "observation_time": datetime.now().isoformat()
        })
        
        # 添加消息到历史记录
        self.mcp.add_to_history(session_id, MCPMessage(
            role="system",
            content=f"Observing query: {query}",
            context={"docs": docs}
        ))
        
        return Observation(
            query=query,
            context=context,
            docs=docs,
            current_time=datetime.now().isoformat()
        )
    
    def think(self, observation: Observation, session_id: str) -> Thought:
        """Analyze the observation and generate insights"""
        # 获取 MCP 上下文
        mcp_context = self.mcp.get_context(session_id)
        context_str = self.mcp.get_formatted_context(session_id)
        
        prompt = f"""
        Analyze the following contractor search results and provide insights:
        
        Query: {observation.query}
        Context: {observation.context}
        Current Time: {observation.current_time}
        
        MCP Context:
        {context_str}
        
        Contractors:
        {[doc['name'] for doc in observation.docs]}
        
        Please provide:
        1. Key observations about the contractors
        2. Potential opportunities or concerns
        3. Recommended next steps
        """
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        
        reasoning = response.choices[0].message.content
        suggestions = self._generate_suggestions(observation.docs, session_id)
        
        # 添加思考过程到 MCP 历史记录
        self.mcp.add_to_history(session_id, MCPMessage(
            role="assistant",
            content=reasoning,
            context={"suggestions": suggestions}
        ))
        
        return Thought(reasoning=reasoning, next_action="generate_response", suggestions=suggestions)
    
    def act(self, thought: Thought, observation: Observation, session_id: str) -> Result:
        """Execute actions based on the analysis"""
        if thought.next_action == "generate_response":
            # 获取 MCP 上下文
            context_str = self.mcp.get_formatted_context(session_id)
            
            prompt = (
                "Based on your previous analysis, generate a final response to the sales team. "
                "Include the specific action items and their timing. "
                "Contractor info:\n"
                f"{observation.context}\n"
                f"Sales team question: {observation.query}\n"
                f"Suggested actions:\n{thought.suggestions}\n"
                f"MCP Context:\n{context_str}\n"
                "Your answer (in English, concise, actionable, and focused on helping the sales team engage decision-makers):"
            )
            
            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512,
                    temperature=0.7,
                )
                
                # 添加响应到 MCP 历史记录
                self.mcp.add_to_history(session_id, MCPMessage(
                    role="assistant",
                    content=response.choices[0].message.content,
                    context={"suggestions": thought.suggestions}
                ))
                
                return Result(
                    success=True,
                    output=response.choices[0].message.content,
                    suggestions=thought.suggestions
                )
            except Exception as e:
                # 添加错误到 MCP 历史记录
                self.mcp.add_to_history(session_id, MCPMessage(
                    role="system",
                    content=f"Error: {str(e)}",
                    context={"error": str(e)}
                ))
                return Result(success=False, output="", error=str(e))
        else:
            return Result(success=False, output="", error="Unknown action type")
    
    def run(self, query: str, session_id: str) -> Dict[str, Any]:
        """Run the complete ReAct process"""
        # 1. Observe
        observation = self.observe(query, session_id)
        
        # 2. Think
        thought = self.think(observation, session_id)
        
        # 3. Act
        result = self.act(thought, observation, session_id)
        
        # 4. Return result with MCP context
        return {
            "answer": result.output if result.success else "Error: " + result.error,
            "reasoning": thought.reasoning,
            "suggestions": result.suggestions,
            "docs": observation.docs,
            "mcp_context": self.mcp.get_formatted_context(session_id)
        } 