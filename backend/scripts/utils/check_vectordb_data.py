"""
VectorDB 데이터 확인 스크립트

벡터DB에 저장된 일일보고서 데이터를 확인합니다.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime

load_dotenv()

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.vector_store import get_unified_collection

print("=" * 80)
print("📊 VectorDB 데이터 확인")
print("=" * 80)
print()

collection = get_unified_collection()

# 전체 문서 수
total_count = collection.count()
print(f"총 문서 수: {total_count}개")
print()

# 샘플 데이터 조회 (최대 100개)
print("⏳ 데이터 조회 중...")
all_data = collection.get(limit=min(1000, total_count))

if not all_data or not all_data.get('ids'):
    print("❌ 데이터가 없습니다.")
    sys.exit(0)

ids = all_data['ids']
metadatas = all_data['metadatas']
documents = all_data.get('documents', [])

print(f"✅ {len(ids)}개 문서 조회 완료")
print()

# 통계 수집
stats = {
    'by_owner': defaultdict(int),
    'by_report_type': defaultdict(int),
    'by_chunk_type': defaultdict(int),
    'by_date': defaultdict(int),
    'by_month': defaultdict(int),
    'doc_types': set(),
    'report_types': set(),
    'owners': set(),
    'dates': set(),
}

for i, metadata in enumerate(metadatas):
    # Owner 통계
    owner = metadata.get('owner', 'N/A')
    stats['by_owner'][owner] += 1
    if owner != 'N/A':
        stats['owners'].add(owner)
    
    # Report Type 통계
    report_type = metadata.get('report_type', 'N/A')
    stats['by_report_type'][report_type] += 1
    if report_type != 'N/A':
        stats['report_types'].add(report_type)
    
    # Doc Type 통계
    doc_type = metadata.get('doc_type', 'N/A')
    stats['by_chunk_type'][doc_type] += 1
    if doc_type != 'N/A':
        stats['doc_types'].add(doc_type)
    
    # Chunk Type 통계
    chunk_type = metadata.get('chunk_type', 'N/A')
    stats['by_chunk_type'][chunk_type] += 1
    
    # Date 통계
    date = metadata.get('date', None)
    period_start = metadata.get('period_start', None)
    
    if date:
        stats['by_date'][date] += 1
        stats['dates'].add(date)
        # 월별 통계
        try:
            month = date[:7]  # YYYY-MM
            stats['by_month'][month] += 1
        except:
            pass
    elif period_start:
        stats['by_date'][period_start] += 1
        stats['dates'].add(period_start)
        # 월별 통계
        try:
            month = period_start[:7]  # YYYY-MM
            stats['by_month'][month] += 1
        except:
            pass

# 결과 출력
print("=" * 80)
print("📋 통계 정보")
print("=" * 80)
print()

# Owner별 통계
print("👤 Owner별 문서 수:")
for owner, count in sorted(stats['by_owner'].items(), key=lambda x: -x[1]):
    print(f"  {owner}: {count}개")
print()

# Report Type별 통계
print("📄 Report Type별 문서 수:")
for report_type, count in sorted(stats['by_report_type'].items(), key=lambda x: -x[1]):
    print(f"  {report_type}: {count}개")
print()

# Chunk Type별 통계
print("🔖 Chunk Type별 문서 수:")
for chunk_type, count in sorted(stats['by_chunk_type'].items(), key=lambda x: -x[1]):
    print(f"  {chunk_type}: {count}개")
print()

# 월별 통계
print("📅 월별 문서 수:")
for month in sorted(stats['by_month'].keys()):
    count = stats['by_month'][month]
    print(f"  {month}: {count}개")
print()

# 날짜 범위
if stats['dates']:
    sorted_dates = sorted(stats['dates'])
    print(f"📆 날짜 범위: {sorted_dates[0]} ~ {sorted_dates[-1]}")
    print(f"   총 {len(sorted_dates)}개 고유 날짜")
    print()

# 샘플 메타데이터 출력
print("=" * 80)
print("🔍 샘플 메타데이터 (처음 5개)")
print("=" * 80)
for i in range(min(5, len(metadatas))):
    print(f"\n[{i+1}]")
    meta = metadatas[i]
    for key, value in sorted(meta.items()):
        if isinstance(value, (list, dict)):
            print(f"  {key}: {type(value).__name__} (길이: {len(value)})")
        else:
            print(f"  {key}: {value}")
    if documents and i < len(documents):
        doc_preview = documents[i][:100] + "..." if len(documents[i]) > 100 else documents[i]
        print(f"  text: {doc_preview}")

print()
print("=" * 80)
print("✅ 확인 완료")
print("=" * 80)

