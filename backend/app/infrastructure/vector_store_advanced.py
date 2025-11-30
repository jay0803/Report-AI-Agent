"""
고급 VectorDB 저장 (Chroma/pgVector 지원)
"""
import os
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb import Collection


BASE_DIR = Path(__file__).resolve().parent.parent.parent
CHROMA_PERSIST_DIR = BASE_DIR / "Data" / "chroma"
COLLECTION_NAME = "daily_reports_advanced"
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.78"))


class AdvancedVectorStore:
    def __init__(self, db_type: str = "chroma"):
        self.db_type = db_type or os.getenv("VECTOR_DB_TYPE", "chroma")
        
        if self.db_type == "chroma":
            CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
            self._collection: Optional[Collection] = None
        else:
            raise NotImplementedError("pgVector support coming soon")
    
    def get_collection(self) -> Collection:
        if self._collection is None:
            try:
                self._collection = self.client.get_collection(name=COLLECTION_NAME)
            except:
                self._collection = self.client.create_collection(
                    name=COLLECTION_NAME,
                    metadata={"description": "Advanced daily reports collection"}
                )
        return self._collection
    
    def insert_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ):
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


_vector_store = None


def get_vector_store(db_type: Optional[str] = None) -> AdvancedVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = AdvancedVectorStore(db_type)
    return _vector_store

