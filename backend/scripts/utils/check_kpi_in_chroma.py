"""
ChromaDB에 KPI 문서가 저장되어 있는지 확인하는 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.infrastructure.vector_store import get_unified_collection

def main():
    collection = get_unified_collection()
    
    # KPI 문서 검색
    results = collection.get(
        where={"doc_type": "kpi"},
        limit=10
    )
    
    kpi_count = len(results.get("ids", []))
    print(f"📊 ChromaDB에 저장된 KPI 문서 개수: {kpi_count}")
    
    if kpi_count > 0:
        print(f"\n✅ KPI 문서가 ChromaDB에 저장되어 있습니다.")
        print(f"\n샘플 메타데이터:")
        for i, metadata in enumerate(results.get("metadatas", [])[:3], 1):
            print(f"  {i}. {metadata}")
    else:
        print(f"\n❌ KPI 문서가 ChromaDB에 저장되어 있지 않습니다.")
        print(f"\nKPI 문서를 ChromaDB에 저장하려면 다음 명령을 실행하세요:")
        print(f"  python -m ingestion.reindex_unified")
    
    # chunk_type이 "kpi"인 청크 검색
    chunk_results = collection.get(
        where={"chunk_type": "kpi"},
        limit=10
    )
    
    chunk_count = len(chunk_results.get("ids", []))
    print(f"\n📊 chunk_type='kpi'인 청크 개수: {chunk_count}")
    
    if chunk_count > 0:
        print(f"\n✅ KPI 청크가 ChromaDB에 저장되어 있습니다.")
        print(f"\n샘플 메타데이터:")
        for i, metadata in enumerate(chunk_results.get("metadatas", [])[:3], 1):
            print(f"  {i}. {metadata}")
    else:
        print(f"\n❌ KPI 청크가 ChromaDB에 저장되어 있지 않습니다.")

if __name__ == "__main__":
    main()

