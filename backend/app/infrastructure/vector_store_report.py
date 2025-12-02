"""
보고서 전용 VectorDB 저장 (ChromaDB)
backend/Data/ChromaDB/report 경로에 저장
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb import Collection


BASE_DIR = Path(__file__).resolve().parent.parent.parent
CHROMA_PERSIST_DIR = BASE_DIR / "Data" / "ChromaDB" / "report"
COLLECTION_NAME = "reports"
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.78"))


class ReportVectorStore:
    """보고서 전용 Vector Store"""
    
    def __init__(self):
        """초기화 - ChromaDB PersistentClient 사용"""
        CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
        self._collection: Optional[Collection] = None
        print(f"📁 ChromaDB 저장 경로: {CHROMA_PERSIST_DIR}")
    
    def get_collection(self) -> Collection:
        """컬렉션 가져오기 또는 생성"""
        if self._collection is None:
            try:
                self._collection = self.client.get_collection(name=COLLECTION_NAME)
                print(f"✅ 기존 컬렉션 사용: {COLLECTION_NAME}")
            except:
                self._collection = self.client.create_collection(
                    name=COLLECTION_NAME,
                    metadata={"description": "All reports collection (daily, weekly, monthly)"}
                )
                print(f"✅ 새 컬렉션 생성: {COLLECTION_NAME}")
        return self._collection
    
    def insert_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ):
        """청크와 임베딩을 VectorDB에 저장"""
        collection = self.get_collection()
        
        ids = [chunk["id"] for chunk in chunks]
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
    
    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        threshold: float = SIMILARITY_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """벡터 검색"""
        collection = self.get_collection()
        
        try:
            if filters:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results * 2,
                    where=filters
                )
            else:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results * 2
                )
        except Exception as e:
            print(f"검색 오류: {e}")
            return []
        
        if not results['ids'] or not results['ids'][0]:
            return []
        
        formatted = []
        for idx in range(len(results['ids'][0])):
            distance = results['distances'][0][idx]
            similarity = 1 - distance
            
            if similarity < threshold:
                continue
            
            formatted.append({
                "id": results['ids'][0][idx],
                "text": results['documents'][0][idx],
                "metadata": results['metadatas'][0][idx],
                "similarity": round(similarity, 4)
            })
        
        return sorted(formatted, key=lambda x: x["similarity"], reverse=True)[:n_results]


_report_vector_store = None


def get_report_vector_store() -> ReportVectorStore:
    """ReportVectorStore 싱글톤 인스턴스"""
    global _report_vector_store
    if _report_vector_store is None:
        _report_vector_store = ReportVectorStore()
    return _report_vector_store

