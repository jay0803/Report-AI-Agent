"""
벡터 DB 확인 스크립트

reports 컬렉션에 데이터가 있는지 확인합니다. (로컬 ChromaDB)
"""
import sys
import os
from pathlib import Path

# Windows에서 UTF-8 출력 설정
if sys.platform == "win32":
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.vector_store_report import get_report_vector_store

try:
    print("=" * 60)
    print("📊 벡터 DB 상태 확인 (로컬 ChromaDB)")
    print("=" * 60)
    
    # Report Vector Store 가져오기
    vector_store = get_report_vector_store()
    collection = vector_store.get_collection()
    count = collection.count()
    
    print(f"\n📦 컬렉션: {collection.name}")
    print(f"📝 문서 개수: {count}개")
    
    if count > 0:
        print(f"\n✅ 벡터 DB에 데이터가 있습니다!")
        
        # 샘플 데이터 확인
        try:
            result = collection.get(limit=5)
            print(f"\n📄 샘플 데이터 (최대 5개):")
            for i in range(min(5, len(result["ids"]))):
                doc = result["documents"][i] if result.get("documents") else ""
                preview = doc[:80] + "..." if len(doc) > 80 else doc
                metadata = result["metadatas"][i] if result.get("metadatas") else {}
                chunk_type = metadata.get("chunk_type", "N/A")
                date = metadata.get("date", "N/A")
                print(f"  {i+1}. [{chunk_type}] {date}")
                print(f"     {preview}")
        except Exception as e:
            print(f"  샘플 데이터 조회 실패: {e}")
    else:
        print(f"\n⚠️  벡터 DB가 비어있습니다!")
        print(f"\n데이터 추가 방법:")
        print(f"  python -m ingestion.ingest_mock_reports")
    
    print("\n" + "=" * 60)
    
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

