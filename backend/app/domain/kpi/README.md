### KPI 문서 처리 파이프라인

보험사 KPI 자료 PDF를 Vision API로 구조화하여 RAG용 청크로 변환하는 모듈입니다.

## 파이프라인

```
PDF 파일
  ↓
KPIVisionService (GPT-4o Vision)
  ↓
KPIRawDocument (Raw JSON)
  ↓
normalize_kpi_document()
  ↓
List[CanonicalKPI] (정규화)
  ↓
build_kpi_chunks()
  ↓
청크 리스트
  ↓
enhance_chunks_with_metadata()
  ↓
최종 청크 (메타데이터 포함)
```

## 파일 구조

```
backend/app/domain/kpi/
├── __init__.py              # 모듈 export
├── schemas.py               # Pydantic 스키마
├── vision_service.py        # PDF → Vision → Raw JSON
├── normalize_service.py     # Raw → Canonical 변환
├── chunker.py              # Canonical → 청크
├── metadata.py             # 메타데이터 생성
└── README.md               # 이 파일
```

## 사용 방법

### 1. 기본 사용

```python
from app.domain.kpi import (
    KPIVisionService,
    normalize_kpi_document,
    build_kpi_chunks,
    enhance_chunks_with_metadata
)

# 1) Vision 서비스로 PDF 처리
service = KPIVisionService(api_key="your_openai_key")
raw_doc = service.process_pdf("Data/보험사_KPI_자료.pdf")

# 2) Canonical 변환
canonical_kpis = normalize_kpi_document(raw_doc)

# 3) 청킹
chunks = build_kpi_chunks(canonical_kpis)

# 4) 메타데이터 추가
final_chunks = enhance_chunks_with_metadata(chunks)

print(f"총 {len(final_chunks)}개 청크 생성")
```

### 2. CLI 테스트

```bash
cd backend
python test_kpi_pipeline.py
```

### 3. 통계 확인

```python
from app.domain.kpi import get_normalization_stats, get_chunk_statistics, get_metadata_summary

# 정규화 통계
stats = get_normalization_stats(canonical_kpis)
print(f"KPI 수: {stats['total_kpis']}")
print(f"카테고리별: {stats['by_category']}")

# 청크 통계
chunk_stats = get_chunk_statistics(chunks)
print(f"평균 길이: {chunk_stats['avg_text_length']}")

# 메타데이터 통계
meta_summary = get_metadata_summary(final_chunks)
print(f"고유 카테고리: {meta_summary['unique_categories']}")
```

## 스키마

### Raw JSON (Vision 출력)

```json
{
  "문서제목": "보험사 KPI 자료",
  "총페이지수": 12,
  "pages": [
    {
      "page_index": 0,
      "KPI_항목": [
        {
          "kpi_name": "신규계약률",
          "category": "영업",
          "unit": "%",
          "values": "85.2",
          "delta": "+2.3%",
          "설명": "전월 대비 증가"
        }
      ],
      "표": [],
      "텍스트요약": "..."
    }
  ]
}
```

### Canonical KPI

```python
{
  "kpi_id": "uuid",
  "page_index": 0,
  "kpi_name": "신규계약률",
  "category": "영업",
  "unit": "%",
  "values": "85.2",
  "delta": "+2.3%",
  "description": "전월 대비 증가",
  "table": {...},
  "raw_text_summary": "...",
  "metadata": {}
}
```

### 최종 청크

```python
{
  "chunk_id": "uuid",
  "kpi_id": "uuid",
  "page_index": 0,
  "text": "[KPI] 신규계약률\n카테고리: 영업\n값: 85.2 (%)\n증감: +2.3%\n...",
  "source": "kpi_pdf",
  "tags": ["신규계약률", "영업", "%"],
  "metadata": {
    "dataset": "kpi",
    "kpi_name": "신규계약률",
    "category": "영업",
    "unit": "%",
    "page_index": 0,
    "keywords": ["신규계약률", "영업", "%"]
  }
}
```

## Vector DB 통합 예시

```python
import chromadb
from chromadb.utils import embedding_functions

# ChromaDB 클라이언트
client = chromadb.Client()
collection = client.create_collection(
    name="kpi_documents",
    embedding_function=embedding_functions.OpenAIEmbeddingFunction(
        api_key="your_key",
        model_name="text-embedding-3-large"
    )
)

# 청크 추가
for chunk in final_chunks:
    collection.add(
        ids=[chunk["chunk_id"]],
        documents=[chunk["text"]],
        metadatas=[chunk["metadata"]]
    )

# 검색
results = collection.query(
    query_texts=["신규계약"],
    n_results=5,
    where={"category": "영업"}
)
```

## 특징

- ✅ Report 모듈과 완전 분리
- ✅ GPT-4o Vision 사용
- ✅ 페이지별 병렬 처리 가능
- ✅ 오류 페이지 Fallback 처리
- ✅ 표 데이터 flatten
- ✅ 풍부한 메타데이터

## 다음 단계

- [ ] Vector DB 연동 (ChromaDB/Pinecone)
- [ ] 임베딩 API 통합
- [ ] 검색 API 엔드포인트
- [ ] RAG 시스템 구현

