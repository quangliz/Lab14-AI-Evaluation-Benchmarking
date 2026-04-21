import asyncio
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from openai import OpenAI

# Thêm thư mục gốc vào sys.path để import index.py
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from index import get_embedding, CHROMA_DB_DIR

TOP_K_SEARCH = 5

# =============================================================================
# RETRIEVAL — DENSE (Vector Search)
# =============================================================================

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Dense retrieval: tìm kiếm theo embedding similarity trong ChromaDB.
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        collection = client.get_collection("lab_rag")

        query_embedding = get_embedding(query)
        result = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        chunks = []
        num_results = len(result["documents"][0])
        for i in range(min(top_k, num_results)):
            chunks.append({
                "id": result["ids"][0][i],
                "text": result["documents"][0][i],
                "metadata": result["metadatas"][0][i],
                "score": 1 - result["distances"][0][i]
            })
        return chunks
    except Exception as e:
        print(f"Lỗi retrieve_dense: {e}")
        return []

# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# =============================================================================

def _get_all_chunks(db_dir: Path = CHROMA_DB_DIR) -> dict:
    import chromadb
    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_collection("lab_rag")
    result = collection.get()
    return result

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword (BM25).
    """
    from rank_bm25 import BM25Okapi
    
    try:
        all_chunks = _get_all_chunks()
        corpus = all_chunks["documents"]
        ids = all_chunks["ids"]
        if not corpus:
            return []
            
        tokenized_corpus = [doc.lower().split() for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        result = []
        for i in top_indices:
            if scores[i] > 0:
                result.append({
                    "id": ids[i],
                    "text": all_chunks["documents"][i],
                    "metadata": all_chunks["metadatas"][i],
                    "score": scores[i]
                })
        return result
    except Exception as e:
        print(f"Lỗi retrieve_sparse: {e}")
        return []

# =============================================================================
# RETRIEVAL — HYBRID (Dense + Sparse với Reciprocal Rank Fusion)
# =============================================================================

def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.95, # Tăng nhẹ dense weight để giảm nhiễu
    sparse_weight: float = 0.05,
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval: kết hợp dense và sparse bằng Reciprocal Rank Fusion (RRF).
    """
    # Tăng chiều sâu tìm kiếm để RRF hiệu quả hơn
    search_depth = max(top_k * 4, 40)

    dense_results = retrieve_dense(query, top_k=search_depth)
    sparse_results = retrieve_sparse(query, top_k=search_depth)

    rrf_scores = {}
    doc_map = {} 
    K = 60

    for rank, doc in enumerate(dense_results, 1):
        doc_id = doc["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + dense_weight * (1.0 / (K + rank))
        doc_map[doc_id] = doc

    for rank, doc in enumerate(sparse_results, 1):
        doc_id = doc["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + sparse_weight * (1.0 / (K + rank))
        if doc_id not in doc_map:
            doc_map[doc_id] = doc

    sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

    hybrid_results = []
    for doc_id in sorted_ids[:top_k]:
        doc = doc_map[doc_id].copy()
        doc["score"] = rrf_scores[doc_id]
        hybrid_results.append(doc)

    return hybrid_results

# =============================================================================
# MAIN AGENT
# =============================================================================

class MainAgent:
    """
    Agent sử dụng kiến trúc RAG với LLM Synthesis thật.
    """
    def __init__(self, mode: str = "hybrid"):
        self.name = f"SupportAgent-{mode}"
        self.mode = mode
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def _generate_answer(self, question: str, contexts: List[str]) -> str:
        """
        Sử dụng LLM để tổng hợp câu trả lời từ context.
        """
        if not contexts:
            return "Tôi không tìm thấy thông tin trong tài liệu để trả lời câu hỏi này."
            
        context_str = "\n---\n".join(contexts)
        prompt = f"""
Bạn là một chuyên gia hỗ trợ nội bộ chuyên nghiệp. 
Hãy trả lời câu hỏi dựa TRÊN CÁC ĐOẠN VĂN BẢN TRÍCH DẪN bên dưới.
Nếu thông tin không có trong trích dẫn, hãy nói bạn không biết, đừng tự bịa ra.

CÂU HỎI: {question}

TRÍCH DẪN TÀI LIỆU:
{context_str}

CÂU TRẢ LỜI (ngắn gọn, chính xác, chuyên nghiệp):
"""
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Lỗi khi sinh câu trả lời: {e}"

    async def query(self, question: str) -> Dict:
        """
        Quy trình RAG hoàn chỉnh.
        """
        # 1. Retrieval
        if self.mode == "dense":
            contexts_data = retrieve_dense(question, top_k=TOP_K_SEARCH)
        elif self.mode == "sparse":
            contexts_data = retrieve_sparse(question, top_k=TOP_K_SEARCH)
        else:
            contexts_data = retrieve_hybrid(question, top_k=TOP_K_SEARCH)
        
        contexts = [c["text"] for c in contexts_data]
        retrieved_ids = [c["id"] for c in contexts_data]
        display_sources = list(set([c["metadata"].get("source", "Unknown") for c in contexts_data]))

        # 2. Generation (Thật)
        answer = await self._generate_answer(question, contexts)

        return {
            "answer": answer,
            "contexts": contexts,
            "metadata": {
                "model": "gpt-4o-mini",
                "retrieval_mode": self.mode,
                "sources": retrieved_ids, 
                "display_sources": display_sources,
                "top_k": len(contexts)
            }
        }

if __name__ == "__main__":
    agent = MainAgent(mode="hybrid")
    async def test():
        resp = await agent.query("Định nghĩa sự cố mức độ P1 là gì?")
        print(json.dumps(resp, indent=2, ensure_ascii=False))
    asyncio.run(test())
