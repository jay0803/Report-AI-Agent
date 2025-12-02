"""
목업 데이터 Ingestion 스크립트
일일/주간/월간 보고서 목업 데이터를 청킹, 임베딩하여 ChromaDB에 저장

사용법:
    python -m ingestion.ingest_mock_reports
"""
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import date
from dotenv import load_dotenv

# 프로젝트 루트 경로 설정
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 환경 변수 로드
load_dotenv(project_root / ".env")
report_env_path = project_root / ".env.report"
if report_env_path.exists():
    load_dotenv(report_env_path, override=False)

from app.domain.report.core.service import ReportProcessingService
from app.domain.report.core.chunker import chunk_canonical_report
from app.domain.report.core.embedding_pipeline import EmbeddingPipeline
from app.infrastructure.vector_store_report import get_report_vector_store


# 데이터 디렉토리
MOCK_DATA_DIR = project_root / "Data" / "mock_reports"
BATCH_SIZE = 100


def parse_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """JSON 파일 파싱"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        if not content:
            return None
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON 파싱 오류: {e}")
        return None
    except Exception as e:
        print(f"  ⚠️  파일 읽기 오류: {e}")
        return None


def scan_report_files(report_type: str = "daily") -> List[Path]:
    """
    보고서 파일 스캔
    
    Args:
        report_type: "daily", "weekly", "monthly"
    
    Returns:
        파일 경로 리스트 (날짜 순 정렬)
    """
    type_dir = MOCK_DATA_DIR / report_type
    
    if not type_dir.exists():
        print(f"⚠️  디렉토리 없음: {type_dir}")
        return []
    
    txt_files = list(type_dir.rglob("*.txt"))
    
    def extract_date(file_path: Path) -> tuple:
        """파일명에서 날짜 추출 (YYYY, MM, DD)"""
        filename = file_path.stem
        try:
            parts = filename.split('-')
            if len(parts) >= 3:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                return (year, month, day)
        except (ValueError, IndexError):
            pass
        return (0, 0, 0)
    
    return sorted(txt_files, key=extract_date)


def ingest_daily_reports(
    service: ReportProcessingService,
    embedding_pipeline: EmbeddingPipeline,
    vector_store
) -> int:
    """일일 보고서 ingestion"""
    print("\n" + "=" * 80)
    print("📅 일일 보고서 Ingestion 시작")
    print("=" * 80)
    
    txt_files = scan_report_files("daily")
    print(f"✅ {len(txt_files)}개 파일 발견\n")
    
    if not txt_files:
        print("⚠️  일일 보고서 파일이 없습니다.\n")
        return 0
    
    all_chunks = []
    
    for idx, file_path in enumerate(txt_files, 1):
        print(f"[{idx}/{len(txt_files)}] 처리 중: {file_path.name}")
        
        raw_json = parse_json_file(file_path)
        if not raw_json:
            print(f"  ⚠️  JSON 파싱 실패")
            continue
        
        try:
            # Raw → Canonical 변환
            canonical = service.normalize_daily(raw_json)
            
            # 의미 단위 청킹
            chunks = chunk_canonical_report(canonical)
            
            if not chunks:
                print(f"  ⚠️  청크 생성 실패")
                continue
            
            # 메타데이터 정리 (None 값 제거)
            for chunk in chunks:
                metadata = chunk["metadata"]
                metadata_cleaned = {k: v for k, v in metadata.items() if v is not None}
                chunk["metadata"] = metadata_cleaned
            
            all_chunks.extend(chunks)
            print(f"  ✅ {len(chunks)}개 청크 생성")
        
        except Exception as e:
            print(f"  ❌ 오류: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    if not all_chunks:
        print("\n⚠️  생성된 청크가 없습니다.\n")
        return 0
    
    # 임베딩 및 저장
    print(f"\n⏳ 임베딩 생성 중... (총 {len(all_chunks)}개 청크)")
    texts = [chunk["text"] for chunk in all_chunks]
    embeddings = embedding_pipeline.embed_texts(texts, batch_size=BATCH_SIZE)
    
    print(f"✅ {len(embeddings)}개 임베딩 생성 완료")
    print(f"⏳ ChromaDB 저장 중...")
    vector_store.insert_chunks(all_chunks, embeddings)
    
    collection = vector_store.get_collection()
    total_count = collection.count()
    
    print(f"✅ 저장 완료 (총 문서 수: {total_count}개)\n")
    
    return len(all_chunks)


def ingest_weekly_reports(
    service: ReportProcessingService,
    embedding_pipeline: EmbeddingPipeline,
    vector_store
) -> int:
    """주간 보고서 ingestion (향후 구현)"""
    print("\n" + "=" * 80)
    print("📅 주간 보고서 Ingestion")
    print("=" * 80)
    print("⚠️  주간 보고서 목업 데이터가 아직 없습니다.\n")
    return 0


def ingest_monthly_reports(
    service: ReportProcessingService,
    embedding_pipeline: EmbeddingPipeline,
    vector_store
) -> int:
    """월간 보고서 ingestion (향후 구현)"""
    print("\n" + "=" * 80)
    print("📅 월간 보고서 Ingestion")
    print("=" * 80)
    print("⚠️  월간 보고서 목업 데이터가 아직 없습니다.\n")
    return 0


def main():
    """메인 함수"""
    print("=" * 80)
    print("🚀 목업 데이터 Ingestion 시작")
    print("=" * 80)
    print(f"📁 데이터 경로: {MOCK_DATA_DIR}")
    print(f"💾 ChromaDB 저장 경로: {project_root / 'Data' / 'ChromaDB' / 'report'}")
    print()
    
    # 서비스 초기화
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        return
    
    service = ReportProcessingService(api_key=api_key)
    
    # Vector Store 초기화
    vector_store = get_report_vector_store()
    
    # 임베딩 파이프라인 초기화 (보고서 전용 vector store 사용)
    embedding_pipeline = EmbeddingPipeline(vector_store=vector_store)
    
    # 각 보고서 타입별 ingestion
    total_chunks = 0
    
    total_chunks += ingest_daily_reports(service, embedding_pipeline, vector_store)
    total_chunks += ingest_weekly_reports(service, embedding_pipeline, vector_store)
    total_chunks += ingest_monthly_reports(service, embedding_pipeline, vector_store)
    
    # 최종 요약
    print("=" * 80)
    print("✅ Ingestion 완료!")
    print("=" * 80)
    print(f"📊 총 {total_chunks}개 청크가 ChromaDB에 저장되었습니다.")
    
    collection = vector_store.get_collection()
    print(f"📦 ChromaDB 총 문서 수: {collection.count()}개")
    print(f"💾 저장 위치: {project_root / 'Data' / 'ChromaDB' / 'report'}")
    print()


if __name__ == "__main__":
    main()

