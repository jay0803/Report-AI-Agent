"""
유연한 임베딩 서비스 (HF/OpenAI 선택)
보고서 전용
"""
import os
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from openai import OpenAI


# backend/ingestion/embed_flexible.py 수정

class FlexibleEmbeddingService:
    def __init__(self, model_type: Optional[str] = None, api_key: Optional[str] = None):
        # REPORT_EMBEDDING_MODEL_TYPE으로 변경 (보고서 전용)
        self.model_type = model_type or os.getenv("REPORT_EMBEDDING_MODEL_TYPE", "openai")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if self.model_type == "hf":
            self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L12-v2')
            self.dimension = 384
        else:
            self.client = OpenAI(api_key=self.api_key)
            self.model = "text-embedding-3-large"  # 보고서도 기본값은 OpenAI
            self.dimension = 3072
    
    def embed_text(self, text: str) -> List[float]:
        if self.model_type == "hf":
            return self.model.encode(text, convert_to_numpy=True).tolist()
        else:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
    
    def embed_texts(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        embeddings = []
        total = len(texts)
        
        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            batch_end = min(i + batch_size, total)
            
            if self.model_type == "hf":
                batch_embeddings = self.model.encode(batch, convert_to_numpy=True).tolist()
                embeddings.extend(batch_embeddings)
            else:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    encoding_format="float"
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
        
        return embeddings


_embedding_service = None


def get_embedding_service(model_type: Optional[str] = None, api_key: Optional[str] = None) -> FlexibleEmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = FlexibleEmbeddingService(model_type, api_key)
    return _embedding_service


def embed_texts(texts: List[str], model_type: Optional[str] = None, api_key: Optional[str] = None, batch_size: int = 100) -> List[List[float]]:
    service = get_embedding_service(model_type, api_key)
    return service.embed_texts(texts, batch_size)

