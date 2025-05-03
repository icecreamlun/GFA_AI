from typing import List, Dict, Any
from pydantic import BaseModel
from openai import OpenAI
import httpx
from vectordb_utils import VectorDB
from datetime import datetime, timedelta
import random

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
        
    def observe(self, query: str) -> Observation:
        """观察阶段：获取当前状态和环境信息"""
        docs = self.vectordb.search(query, top_k=3)
        context = "\n\n".join([
            f"Name: {d.get('name')}\nAbout: {d.get('about_us','')}\nAddress: {d.get('address')}\nPhone: {d.get('phone')}\nURL: {d.get('url')}\n"
            for d in docs
        ])
        return Observation(
            query=query,
            context=context,
            docs=docs,
            current_time=datetime.now().isoformat()
        )
    
    def _generate_suggestions(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成具体的行动建议"""
        suggestions = []
        current_time = datetime.now()
        
        # 为每个承包商生成建议
        for doc in docs:
            # 随机生成一些动态数据（在实际应用中，这些数据应该来自真实的分析）
            activity_score = random.uniform(0.5, 1.0)  # 模拟活跃度分数
            last_contact_days = random.randint(0, 30)  # 模拟上次联系天数
            
            # 根据数据生成建议
            if activity_score > 0.8:
                # 高活跃度承包商
                next_contact = current_time + timedelta(days=random.randint(1, 3))
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
                # 长时间未联系的承包商
                next_contact = current_time + timedelta(days=random.randint(1, 7))
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
                # 常规跟进
                next_contact = current_time + timedelta(days=random.randint(7, 14))
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
        
        return suggestions
    
    def think(self, observation: Observation) -> Thought:
        """思考阶段：分析当前情况并决定下一步行动"""
        # 生成具体建议
        suggestions = self._generate_suggestions(observation.docs)
        
        # 构建分析提示
        prompt = (
            "You are a B2B sales assistant for a roofing distributor. "
            "Given the following contractor information and sales suggestions, analyze the situation and provide insights. "
            "Contractor info:\n"
            f"{observation.context}\n"
            f"Sales team question: {observation.query}\n"
            "Current suggestions:\n"
            f"{suggestions}\n"
            "Your analysis (in English, concise, and actionable):"
        )
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0.7,
        )
        
        reasoning = response.choices[0].message.content
        return Thought(
            reasoning=reasoning,
            next_action="generate_response",
            suggestions=suggestions
        )
    
    def act(self, thought: Thought, observation: Observation) -> Result:
        """行动阶段：执行具体的操作"""
        if thought.next_action == "generate_response":
            prompt = (
                "Based on your previous analysis, generate a final response to the sales team. "
                "Include the specific action items and their timing. "
                "Contractor info:\n"
                f"{observation.context}\n"
                f"Sales team question: {observation.query}\n"
                f"Suggested actions:\n{thought.suggestions}\n"
                "Your answer (in English, concise, actionable, and focused on helping the sales team engage decision-makers):"
            )
            
            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512,
                    temperature=0.7,
                )
                return Result(
                    success=True,
                    output=response.choices[0].message.content,
                    suggestions=thought.suggestions
                )
            except Exception as e:
                return Result(success=False, output="", error=str(e))
        else:
            return Result(success=False, output="", error="Unknown action type")
    
    def run(self, query: str) -> Dict[str, Any]:
        """运行完整的ReAct流程"""
        # 1. 观察
        observation = self.observe(query)
        
        # 2. 思考
        thought = self.think(observation)
        
        # 3. 行动
        result = self.act(thought, observation)
        
        # 4. 返回结果
        return {
            "answer": result.output if result.success else "Error: " + result.error,
            "reasoning": thought.reasoning,
            "suggestions": result.suggestions,
            "docs": observation.docs
        } 