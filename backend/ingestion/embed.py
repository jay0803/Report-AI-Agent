"""
유연한 임베딩 서비스 (HF/OpenAI 선택)

HF와 OpenAI 중 선택 가능한 임베딩 서비스
기본값: HF (sentence-transformers/all-MiniLM-L12-v2)
"""
import os
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from openai import OpenAI


class EmbeddingService:
    """유연한 임베딩 생성 서비스 (HF/OpenAI 선택)"""
    
    def __init__(self, model_type: Optional[str] = None, api_key: Optional[str] = None):
        """
        서비스 초기화
        
        Args:
            model_type: 모델 타입 ("hf" 또는 "openai", None이면 환경변수에서 읽음, 기본값: "hf")
            api_key: OpenAI API 키 (None이면 환경변수에서 읽음)
        """
        # 기본값을 "hf"로 설정
        self.model_type = model_type or os.getenv("REPORT_EMBEDDING_MODEL_TYPE", "hf")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if self.model_type == "hf":
            self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L12-v2')
            self.dimension = 384
        else:
            self.client = OpenAI(api_key=self.api_key)
            self.model = "text-embedding-3-large"
            self.dimension = 3072
    
    def embed_text(self, text: str) -> List[float]:
        """
        단일 텍스트를 임베딩 벡터로 변환
        
        Args:
            text: 임베딩할 텍스트
            
        Returns:
            임베딩 벡터
        """
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
        """
        여러 텍스트를 배치로 임베딩
        
        Args:
            texts: 임베딩할 텍스트 리스트
            batch_size: 배치 크기 (기본값: 100)
            
        Returns:
            임베딩 벡터 리스트
        """
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


# 전역 서비스 인스턴스 (lazy initialization)
_embedding_service = None


def get_embedding_service(api_key: Optional[str] = None, model_type: Optional[str] = None) -> EmbeddingService:
    """
    임베딩 서비스 싱글톤 인스턴스 반환
    
    Args:
        api_key: OpenAI API 키 (None이면 환경변수에서 읽음)
        model_type: 모델 타입 ("hf" 또는 "openai", None이면 환경변수에서 읽음, 기본값: "hf")
        
    Returns:
        EmbeddingService 인스턴스
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(api_key=api_key, model_type=model_type)
    return _embedding_service


def embed_text(text: str, api_key: Optional[str] = None, model_type: Optional[str] = None) -> List[float]:
    """
    단일 텍스트 임베딩 (헬퍼 함수)
    
    Args:
        text: 임베딩할 텍스트
        api_key: OpenAI API 키 (None이면 환경변수에서 읽음)
        model_type: 모델 타입 ("hf" 또는 "openai", None이면 환경변수에서 읽음, 기본값: "hf")
        
    Returns:
        임베딩 벡터
    """
    service = get_embedding_service(api_key, model_type)
    return service.embed_text(text)


def embed_texts(texts: List[str], api_key: Optional[str] = None, batch_size: int = 100, model_type: Optional[str] = None) -> List[List[float]]:
    """
    여러 텍스트 배치 임베딩 (헬퍼 함수)
    
    Args:
        texts: 임베딩할 텍스트 리스트
        api_key: OpenAI API 키 (None이면 환경변수에서 읽음)
        batch_size: 배치 크기 (기본값: 100)
        model_type: 모델 타입 ("hf" 또는 "openai", None이면 환경변수에서 읽음, 기본값: "hf")
        
    Returns:
        임베딩 벡터 리스트
    """
    service = get_embedding_service(api_key, model_type)
    return service.embed_texts(texts, batch_size)

