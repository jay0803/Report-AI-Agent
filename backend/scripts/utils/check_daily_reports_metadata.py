"""
reports 컬렉션의 실제 메타데이터 확인
"""
import sys
from pathlib import Path
from collections import Counter

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.vector_store_report import get_report_vector_store

try:
    vector_store = get_report_vector_store()
    collection = vector_store.get_collection()
    
    print("=" * 80)
    print(f"reports 컬렉션 메타데이터 분석")
    print("=" * 80)
    print(f"총 문서 수: {collection.count()}개\n")
    
    # 샘플 데이터 가져오기 (최대 100개)
    print("메타데이터 샘플 조회 중...")
    results = collection.get(limit=100, include=["metadatas", "documents"])
    
    if not results['ids']:
        print("데이터가 없습니다!")
        sys.exit(1)
    
    # 메타데이터 필드 분석
    print("\n메타데이터 필드 분석:")
    all_keys = set()
    for metadata in results['metadatas']:
        all_keys.update(metadata.keys())
    
    print(f"발견된 메타데이터 필드: {sorted(all_keys)}\n")
    
    # 주요 필드별 값 분포
    print("주요 필드별 값 분포:")
    
    # owner 분포
    owners = Counter()
    for metadata in results['metadatas']:
        owner = metadata.get('owner', 'N/A')
        owners[owner] += 1
    print(f"\n  owner: {dict(owners)}")
    
    # chunk_type 분포
    chunk_types = Counter()
    for metadata in results['metadatas']:
        chunk_type = metadata.get('chunk_type', 'N/A')
        chunk_types[chunk_type] += 1
    print(f"\n  chunk_type: {dict(chunk_types)}")
    
    # doc_type / report_type 분포
    doc_types = Counter()
    report_types = Counter()
    for metadata in results['metadatas']:
        doc_type = metadata.get('doc_type', 'N/A')
        report_type = metadata.get('report_type', 'N/A')
        doc_types[doc_type] += 1
        report_types[report_type] += 1
    print(f"\n  doc_type: {dict(doc_types)}")
    print(f"  report_type: {dict(report_types)}")
    
    # date 분포 (샘플)
    dates = Counter()
    for metadata in results['metadatas'][:20]:  # 처음 20개만
        date_val = metadata.get('date', 'N/A')
        dates[date_val] += 1
    print(f"\n  date (샘플 20개): {dict(dates)}")
    
    # 김보험 데이터 필터링 테스트
    print("\n" + "=" * 80)
    print("김보험 데이터 필터링 테스트")
    print("=" * 80)
    
    # owner 필터
    owner_filter_results = collection.get(
        where={"owner": "김보험"},
        limit=5,
        include=["metadatas", "documents"]
    )
    print(f"\n  owner='김보험' 필터: {len(owner_filter_results['ids'])}개 발견")
    
    # owner + chunk_type 필터
    owner_chunk_filter = collection.get(
        where={
            "$and": [
                {"owner": "김보험"},
                {"chunk_type": "detail_chunk"}
            ]
        },
        limit=5,
        include=["metadatas", "documents"]
    )
    print(f"  owner='김보험' AND chunk_type='detail_chunk' 필터: {len(owner_chunk_filter['ids'])}개 발견")
    
    # owner + date 필터 (2025-11-17)
    owner_date_filter = collection.get(
        where={
            "$and": [
                {"owner": "김보험"},
                {"date": "2025-11-17"}
            ]
        },
        limit=5,
        include=["metadatas", "documents"]
    )
    print(f"  owner='김보험' AND date='2025-11-17' 필터: {len(owner_date_filter['ids'])}개 발견")
    
    # doc_type 필터
    doc_type_filter = collection.get(
        where={"doc_type": "daily"},
        limit=5,
        include=["metadatas", "documents"]
    )
    print(f"  doc_type='daily' 필터: {len(doc_type_filter['ids'])}개 발견")
    
    # 샘플 메타데이터 출력
    print("\n" + "=" * 80)
    print("샘플 메타데이터 (처음 3개)")
    print("=" * 80)
    for i in range(min(3, len(results['ids']))):
        metadata = results['metadatas'][i]
        doc = results['documents'][i][:100] + "..." if len(results['documents'][i]) > 100 else results['documents'][i]
        print(f"\n[{i+1}] ID: {results['ids'][i]}")
        print(f"    owner: {metadata.get('owner', 'N/A')}")
        print(f"    chunk_type: {metadata.get('chunk_type', 'N/A')}")
        print(f"    doc_type: {metadata.get('doc_type', 'N/A')}")
        print(f"    report_type: {metadata.get('report_type', 'N/A')}")
        print(f"    date: {metadata.get('date', 'N/A')}")
        print(f"    period_start: {metadata.get('period_start', 'N/A')}")
        print(f"    text: {doc}")
    
    print("\n" + "=" * 80)
    
except Exception as e:
    print(f"\n오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

