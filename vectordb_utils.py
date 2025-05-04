import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import os
from feedback_manager import FeedbackManager

class VectorDB:
    def __init__(self, db_dir: str = "vectordb"):
        self.db_dir = db_dir
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.feedback_manager = FeedbackManager()
        
        # Load vector index
        self.index = faiss.read_index(os.path.join(db_dir, "index.faiss"))
        
        # Load metadata
        with open(os.path.join(db_dir, "metadata.pkl"), "rb") as f:
            self.metadata = pickle.load(f)
            self.texts = self.metadata["texts"]
            self.contractors = self.metadata["contractors"]
            self.urls = self.metadata["urls"]

    def _calculate_relevance_score(self, similarity_score: float, doc_id: str) -> float:
        """Calculate the relevance score combining semantic similarity and feedback"""
        # Calculate feedback score (using Wilson score interval lower bound)
        doc_score = self.feedback_manager.get_doc_score(doc_id)
        n = doc_score.helpful_count + doc_score.unhelpful_count
        
        if n > 0:
            p = doc_score.helpful_count / n
            z = 1.96  # 95% confidence interval
            feedback_score = (p + z*z/(2*n) - z*np.sqrt((p*(1-p)+z*z/(4*n))/n))/(1+z*z/n)
        else:
            feedback_score = 0.5  # Default score
        
        # Combine semantic similarity and feedback score
        # Using weighted average, weights can be adjusted as needed
        semantic_weight = 0.7
        feedback_weight = 0.3
        
        return similarity_score * semantic_weight + feedback_score * feedback_weight

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant contractors based on the query"""
        # Get semantic similarity scores
        query_vec = self.model.encode([query])[0]
        D, I = self.index.search(query_vec.reshape(1, -1), top_k * 2)  # Get more results for re-ranking
        
        # Calculate combined scores and sort
        results = []
        for i, (score, idx) in enumerate(zip(D[0], I[0])):
            contractor = self.contractors[idx].copy()
            contractor["doc_id"] = str(idx)  # Add document ID for feedback
            
            # Calculate combined score
            relevance_score = self._calculate_relevance_score(1 - score, str(idx))
            
            # Adjust score based on query type
            if "years" in query.lower() or "experience" in query.lower():
                # If years of experience information is available, include it in scoring
                if "years_in_business" in contractor:
                    years = float(contractor["years_in_business"])
                    # The longer the experience, the higher the score
                    relevance_score *= (1 + years / 100)  # Add experience years as a bonus
            
            if "new york" in query.lower():
                # Check if address is in New York
                if "new york" in contractor.get("address", "").lower():
                    relevance_score *= 1.5  # New York contractors get higher scores
                else:
                    relevance_score *= 0.5  # Non-New York contractors get lower scores
            
            results.append({
                **contractor,
                "similarity_score": 1 - score,
                "relevance_score": relevance_score
            })
        
        # Sort by combined score
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Return top k results
        return results[:top_k] 