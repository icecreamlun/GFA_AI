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

class DocScore(BaseModel):
    doc_id: str
    helpful_count: int
    unhelpful_count: int

class FeedbackStats(BaseModel):
    total_feedback: int
    helpful_count: int
    unhelpful_count: int
    helpful_ratio: float

class FeedbackManager:
    """管理用户反馈的类"""
    
    def __init__(self, db_path: str = "feedback.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database and create necessary tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create feedback table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    is_helpful INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Create document scores table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS doc_scores (
                    doc_id TEXT PRIMARY KEY,
                    helpful_count INTEGER DEFAULT 0,
                    unhelpful_count INTEGER DEFAULT 0
                )
            """)
            
            conn.commit()
    
    def add_feedback(self, feedback: Feedback):
        """Add new feedback and update document scores"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert feedback record
            cursor.execute("""
                INSERT INTO feedback (query, doc_id, is_helpful, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                feedback.query,
                feedback.doc_id,
                int(feedback.is_helpful),
                feedback.timestamp,
                str(feedback.metadata)
            ))
            
            # Update document scores
            if feedback.is_helpful:
                cursor.execute("""
                    INSERT INTO doc_scores (doc_id, helpful_count)
                    VALUES (?, 1)
                    ON CONFLICT(doc_id) DO UPDATE SET
                        helpful_count = helpful_count + 1
                """, (feedback.doc_id,))
            else:
                cursor.execute("""
                    INSERT INTO doc_scores (doc_id, unhelpful_count)
                    VALUES (?, 1)
                    ON CONFLICT(doc_id) DO UPDATE SET
                        unhelpful_count = unhelpful_count + 1
                """, (feedback.doc_id,))
            
            conn.commit()
    
    def get_doc_score(self, doc_id: str) -> DocScore:
        """Get score information for a specific document"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT doc_id, helpful_count, unhelpful_count
                FROM doc_scores
                WHERE doc_id = ?
            """, (doc_id,))
            
            result = cursor.fetchone()
            if result:
                return DocScore(
                    doc_id=result[0],
                    helpful_count=result[1],
                    unhelpful_count=result[2]
                )
            return DocScore(doc_id=doc_id, helpful_count=0, unhelpful_count=0)
    
    def get_feedback_stats(self) -> FeedbackStats:
        """Get overall feedback statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get total feedback count
            cursor.execute("SELECT COUNT(*) FROM feedback")
            total_feedback = cursor.fetchone()[0]
            
            # Get helpful and unhelpful counts
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN is_helpful = 1 THEN 1 ELSE 0 END) as helpful_count,
                    SUM(CASE WHEN is_helpful = 0 THEN 1 ELSE 0 END) as unhelpful_count
                FROM feedback
            """)
            helpful_count, unhelpful_count = cursor.fetchone()
            
            # Calculate helpful ratio
            helpful_ratio = helpful_count / total_feedback if total_feedback > 0 else 0
            
            return FeedbackStats(
                total_feedback=total_feedback,
                helpful_count=helpful_count,
                unhelpful_count=unhelpful_count,
                helpful_ratio=helpful_ratio
            ) 