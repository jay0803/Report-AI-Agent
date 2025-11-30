"""
KPI 문서 Ingestion

KPI 컬렉션에 청크 업로드
"""
from typing import List, Dict, Any
from chromadb import Collection

from ingestion.embed import embed_texts
from ingestion.chroma_client import get_kpi_collection


def ingest_kpi(
    chunks: List[Dict[str, Any]],
    api_key: str = None,
    batch_size: int = 100
) -> dict:
    """
    KPI 청크를 로컬 ChromaDB에 업로드
    
    Args:
        chunks: 청크 리스트
            [
                {
                    "id": "...",
                    "chunk_text": "...",
                    "metadata": {...}
                },
                ...
            ]
        api_key: OpenAI API 키
        batch_size: 배치 크기
        
    Returns:
        업로드 결과 딕셔너리
    """
    print("=" * 70)
    print("📊 KPI Ingestion 시작")
    print("=" * 70)
    print(f"총 청크 수: {len(chunks)}")
    print()
    
    if not chunks:
        print("⚠️  청크가 비어있습니다.")
        return {"success": False, "message": "No chunks to ingest"}
    
    # 1. 데이터 추출
    ids = [chunk["id"] for chunk in chunks]
    texts = [chunk["chunk_text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]
    
    # 2. 임베딩 생성
    print("⏳ 임베딩 생성 중...")
    embeddings = embed_texts(texts, api_key=api_key, batch_size=batch_size)
    print()
    
    # 3. Chroma 컬렉션 가져오기
    print("⏳ Chroma 컬렉션 연결 중...")
    collection = get_kpi_collection()
    print()
    
    # 4. 배치 upsert
    print("⏳ 로컬 ChromaDB에 업로드 중...")
    total = len(chunks)
    
    for i in range(0, total, batch_size):
        batch_end = min(i + batch_size, total)
        
        batch_ids = ids[i:batch_end]
        batch_embeddings = embeddings[i:batch_end]
        batch_documents = texts[i:batch_end]
        batch_metadatas = metadatas[i:batch_end]
        
        print(f"  업로드 중... ({i + 1}-{batch_end}/{total})")
        
        try:
            collection.upsert(
                ids=batch_ids,
                embeddings=batch_embeddings,
                documents=batch_documents,
                metadatas=batch_metadatas
            )
        except Exception as e:
            print(f"❌ 배치 업로드 오류 ({i}-{batch_end}): {e}")
            return {
                "success": False,
                "message": f"Upload failed at batch {i}-{batch_end}",
                "error": str(e)
            }
    
    print()
    print("=" * 70)
    print("✅ KPI Ingestion 완료")
    print("=" * 70)
    print(f"업로드된 청크: {total}개")
    print(f"컬렉션 총 문서 수: {collection.count()}개")
    print()
    
    return {
        "success": True,
        "collection": "kpi",
        "uploaded": total,
        "total_documents": collection.count()
    }


def delete_kpi_by_ids(ids: List[str]) -> dict:
    """
    특정 ID의 KPI 청크 삭제
    
    Args:
        ids: 삭제할 청크 ID 리스트
        
    Returns:
        삭제 결과 딕셔너리
    """
    print(f"🗑️  KPI 청크 삭제 중... ({len(ids)}개)")
    
    collection = get_kpi_collection()
    
    try:
        collection.delete(ids=ids)
        print(f"✅ {len(ids)}개 청크 삭제 완료")
        
        return {
            "success": True,
            "deleted": len(ids),
            "total_documents": collection.count()
        }
    
    except Exception as e:
        print(f"❌ 삭제 오류: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def query_kpi(
    query_text: str,
    n_results: int = 5,
    where: Dict[str, Any] = None
) -> dict:
    """
    KPI 컬렉션 검색
    
    Args:
        query_text: 검색 쿼리
        n_results: 반환할 결과 수
        where: 메타데이터 필터
        
    Returns:
        검색 결과
    """
    from ingestion.embed import embed_text
    
    collection = get_kpi_collection()
    
    # 쿼리 임베딩
    query_embedding = embed_text(query_text)
    
    # 검색
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where
    )
    
    return results

