"""청크 타입 확인"""
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.vector_store import get_unified_collection
from app.domain.search.retriever import UnifiedRetriever
from datetime import date

collection = get_unified_collection()
retriever = UnifiedRetriever(collection)

# 2025-01-24 데이터 검색
results = retriever.search_daily(
    query="업무",
    single_date="2025-01-24",
    n_results=20
)

print(f"총 {len(results)}개 청크 발견")
print()

# chunk_type 별로 분류
by_type = {}
for r in results:
    ct = r.chunk_type
    if ct not in by_type:
        by_type[ct] = []
    by_type[ct].append(r)

for chunk_type, items in by_type.items():
    print(f"{chunk_type}: {len(items)}개")
    for item in items[:2]:
        print(f"  - {item.text[:100]}")

