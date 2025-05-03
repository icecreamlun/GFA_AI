import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from feedback_manager import FeedbackManager
from typing import List, Dict, Any

class VectorDB:
    def __init__(self, db_dir="vectordb"):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.feedback_manager = FeedbackManager()
        try:
            self.index = faiss.read_index(f"{db_dir}/index.faiss")
            with open(f"{db_dir}/metadata.pkl", "rb") as f:
                meta = pickle.load(f)
            self.texts = meta["texts"]
            self.contractors = meta["contractors"]
            self.urls = meta.get("urls", [])
        except Exception as e:
            print(f"Error loading vector database: {e}")
            raise

    def _calculate_relevance_score(self, doc_id: str, similarity_score: float) -> float:
        """计算综合相关性分数，结合语义相似度和用户反馈"""
        feedback_score = self.feedback_manager.get_doc_score(doc_id)
        
        # 计算反馈分数（使用威尔逊区间下限）
        total_feedback = feedback_score["helpful_count"] + feedback_score["unhelpful_count"]
        if total_feedback > 0:
            p = feedback_score["helpful_count"] / total_feedback
            z = 1.96  # 95% 置信区间
            n = total_feedback
            feedback_score = (p + z*z/(2*n) - z*np.sqrt((p*(1-p)+z*z/(4*n))/n))/(1+z*z/n)
        else:
            feedback_score = 0.5  # 默认分数
            
        # 结合语义相似度和反馈分数
        # 使用加权平均，可以根据需要调整权重
        semantic_weight = 0.7
        feedback_weight = 0.3
        
        return semantic_weight * similarity_score + feedback_weight * feedback_score

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """搜索并返回排序后的结果"""
        # 获取语义相似度分数
        query_vec = self.model.encode([query]).astype("float32")
        D, I = self.index.search(query_vec, top_k * 2)  # 获取更多结果用于重排序
        
        # 计算综合分数并排序
        results = []
        for idx, similarity_score in zip(I[0], D[0]):
            contractor = self.contractors[idx]
            contractor["url"] = self.urls[idx] if self.urls else ""
            contractor["doc_id"] = str(idx)  # 添加文档ID用于反馈
            
            # 计算综合分数
            relevance_score = self._calculate_relevance_score(
                contractor["doc_id"],
                float(similarity_score)
            )
            
            # 根据查询类型调整分数
            if "years" in query.lower() and "experience" in query.lower():
                # 如果有经验年限信息，将其纳入评分
                if 'years_in_business' in contractor:
                    try:
                        years = int(contractor['years_in_business'])
                        # 经验年限越长，分数越高
                        relevance_score *= (1 + years / 100)  # 将经验年限作为加分项
                    except (ValueError, TypeError):
                        pass
            
            if "new york" in query.lower():
                # 检查地址是否在纽约
                if 'address' in contractor and 'new york' in contractor['address'].lower():
                    relevance_score *= 1.5  # 纽约的承包商获得更高的分数
                else:
                    relevance_score *= 0.5  # 非纽约的承包商分数降低
            
            contractor["relevance_score"] = relevance_score
            contractor["similarity_score"] = float(similarity_score)
            
            results.append(contractor)
        
        # 按综合分数排序
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # 返回前top_k个结果
        return results[:top_k] 