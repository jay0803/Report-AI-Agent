"""
Ingestion 모듈

로컬 ChromaDB에 문서를 임베딩하고 업로드하는 파이프라인
"""
from ingestion.embed import embed_text, embed_texts, get_embedding_service
from ingestion.chroma_client import (
    get_chroma_service,
)

__all__ = [
    # Embedding
    "embed_text",
    "embed_texts",
    "get_embedding_service",
    
    # Chroma Client
    "get_chroma_service",
]

