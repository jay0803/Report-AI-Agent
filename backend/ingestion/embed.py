"""
OpenAI 임베딩 생성 모듈

text-embedding-3-large 모델 사용
"""
import os
from typing import List
from openai import OpenAI


# 임베딩 설정
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSION = 3072


class EmbeddingService:
    """OpenAI 임베딩 생성 서비스"""
    
    def __init__(self, api_key: str = None):
        """
        서비스 초기화
        
        Args:
            api_key: OpenAI API 키 (None인 경우 환경변수에서 읽음)
        """
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        self.client = OpenAI()
        self.model = EMBEDDING_MODEL
    
    def embed_text(self, text: str) -> List[float]:
        """
        단일 텍스트를 임베딩 벡터로 변환
        
        Args:
            text: 임베딩할 텍스트
            
        Returns:
            임베딩 벡터 (3072차원)
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            return embedding
        
        except Exception as e:
            print(f"❌ 임베딩 생성 오류: {e}")
            raise
    
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
            
            print(f"⏳ 임베딩 생성 중... ({i + 1}-{batch_end}/{total})")
            
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    encoding_format="float"
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
            
            except Exception as e:
                print(f"❌ 배치 임베딩 오류 ({i}-{batch_end}): {e}")
                raise
        
        print(f"✅ 총 {len(embeddings)}개 임베딩 생성 완료")
        return embeddings


# 전역 서비스 인스턴스 (lazy initialization)
_embedding_service = None


def get_embedding_service(api_key: str = None) -> EmbeddingService:
    """
    임베딩 서비스 싱글톤 인스턴스 반환
    
    Args:
        api_key: OpenAI API 키
        
    Returns:
        EmbeddingService 인스턴스
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(api_key)
    return _embedding_service


def embed_text(text: str, api_key: str = None) -> List[float]:
    """
    단일 텍스트 임베딩 (헬퍼 함수)
    
    Args:
        text: 임베딩할 텍스트
        api_key: OpenAI API 키
        
    Returns:
        임베딩 벡터
    """
    service = get_embedding_service(api_key)
    return service.embed_text(text)


def embed_texts(texts: List[str], api_key: str = None, batch_size: int = 100) -> List[List[float]]:
    """
    여러 텍스트 배치 임베딩 (헬퍼 함수)
    
    Args:
        texts: 임베딩할 텍스트 리스트
        api_key: OpenAI API 키
        batch_size: 배치 크기
        
    Returns:
        임베딩 벡터 리스트
    """
    service = get_embedding_service(api_key)
    return service.embed_texts(texts, batch_size)

