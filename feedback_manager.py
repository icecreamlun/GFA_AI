from typing import Dict, List, Any
from pydantic import BaseModel
import sqlite3
from datetime import datetime
import json

class Feedback(BaseModel):
    """用户反馈模型"""
    query: str
    doc_id: str
    is_helpful: bool
    timestamp: str
    metadata: Dict[str, Any] = {}

class FeedbackManager:
    """管理用户反馈的类"""
    
    def __init__(self, db_path: str = "feedback.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建反馈表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            doc_id TEXT NOT NULL,
            is_helpful INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            metadata TEXT
        )
        ''')
        
        # 创建文档评分表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS doc_scores (
            doc_id TEXT PRIMARY KEY,
            helpful_count INTEGER DEFAULT 0,
            unhelpful_count INTEGER DEFAULT 0,
            last_updated TEXT NOT NULL
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_feedback(self, feedback: Feedback):
        """添加新的反馈"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 插入反馈记录
        cursor.execute('''
        INSERT INTO feedback (query, doc_id, is_helpful, timestamp, metadata)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            feedback.query,
            feedback.doc_id,
            1 if feedback.is_helpful else 0,
            feedback.timestamp,
            json.dumps(feedback.metadata)
        ))
        
        # 更新文档评分
        if feedback.is_helpful:
            cursor.execute('''
            INSERT INTO doc_scores (doc_id, helpful_count, last_updated)
            VALUES (?, 1, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                helpful_count = helpful_count + 1,
                last_updated = ?
            ''', (feedback.doc_id, feedback.timestamp, feedback.timestamp))
        else:
            cursor.execute('''
            INSERT INTO doc_scores (doc_id, unhelpful_count, last_updated)
            VALUES (?, 1, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                unhelpful_count = unhelpful_count + 1,
                last_updated = ?
            ''', (feedback.doc_id, feedback.timestamp, feedback.timestamp))
        
        conn.commit()
        conn.close()
    
    def get_doc_score(self, doc_id: str) -> Dict[str, Any]:
        """获取文档的评分信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT helpful_count, unhelpful_count, last_updated
        FROM doc_scores
        WHERE doc_id = ?
        ''', (doc_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "helpful_count": result[0],
                "unhelpful_count": result[1],
                "last_updated": result[2]
            }
        return {
            "helpful_count": 0,
            "unhelpful_count": 0,
            "last_updated": datetime.now().isoformat()
        }
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """获取反馈统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            COUNT(*) as total_feedback,
            SUM(CASE WHEN is_helpful = 1 THEN 1 ELSE 0 END) as helpful_count,
            SUM(CASE WHEN is_helpful = 0 THEN 1 ELSE 0 END) as unhelpful_count
        FROM feedback
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            "total_feedback": result[0],
            "helpful_count": result[1],
            "unhelpful_count": result[2],
            "helpful_ratio": result[1] / result[0] if result[0] > 0 else 0
        } 