"""
일일보고서 고급 Ingestion 파이프라인
"""
import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")  # 기본 .env 로드
# 보고서 전용 환경 변수 로드 (기존 환경 변수는 유지)
report_env_path = project_root / ".env.report"
if report_env_path.exists():
    load_dotenv(report_env_path, override=False)

from app.domain.report.service import ReportProcessingService
from app.domain.report.chunker import chunk_canonical_report
from app.domain.report.embedding_pipeline import get_embedding_pipeline


DATA_DIR = project_root / "Data" / "mock_reports" / "daily"
BATCH_SIZE = 100


def parse_single_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        return None
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON 파싱 오류: {e}")
        return None


def scan_daily_files(base_dir: Path) -> List[Path]:
    """
    일일보고서 파일을 날짜 순으로 정렬하여 반환
    
    파일명 형식: YYYY-MM-DD.txt
    """
    txt_files = list(base_dir.rglob("*.txt"))
    
    def extract_date(file_path: Path) -> tuple:
        """파일명에서 날짜 추출 (YYYY, MM, DD)"""
        filename = file_path.stem  # 확장자 제거
        try:
            # YYYY-MM-DD 형식 파싱
            parts = filename.split('-')
            if len(parts) >= 3:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                return (year, month, day)
        except (ValueError, IndexError):
            pass
        # 파싱 실패 시 (0, 0, 0) 반환하여 맨 앞으로
        return (0, 0, 0)
    
    # 날짜 기준으로 정렬
    return sorted(txt_files, key=extract_date)


def ingest_daily_reports_advanced(
    api_key: Optional[str] = None,
    model_type: Optional[str] = None,
    use_llm_refine: bool = True
):
    print("=" * 80)
    print("일일보고서 고급 Ingestion 시작")
    print("=" * 80)
    print()
    
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    
    service = ReportProcessingService(api_key=api_key)
    embedding_pipeline = get_embedding_pipeline()
    
    txt_files = scan_daily_files(DATA_DIR)
    print(f"[OK] {len(txt_files)}개 파일 발견")
    print()
    
    all_chunks = []
    
    for idx, file_path in enumerate(txt_files):
        print(f"[{idx+1}/{len(txt_files)}] 처리 중: {file_path.name}")
        
        raw_json = parse_single_json_file(file_path)
        if not raw_json:
            print(f"  [WARNING] JSON 파싱 실패")
            continue
        
        try:
            # Raw → Canonical 변환
            canonical = service.normalize_daily(raw_json)
            
            # 디버깅: Canonical 데이터 확인
            print(f"  [Canonical 데이터]")
            print(f"     - summary_tasks: {len(canonical.daily.summary_tasks)}개")
            print(f"     - detail_tasks: {len(canonical.daily.detail_tasks)}개")
            print(f"     - pending: {len(canonical.daily.pending)}개")
            print(f"     - plans: {len(canonical.daily.plans)}개")
            print(f"     - notes: {canonical.daily.notes[:50] if canonical.daily.notes else '없음'}")
            
            # 새 청킹 파이프라인 사용
            chunks = chunk_canonical_report(canonical, api_key, use_llm_refine)
            
            # 메타데이터 정리 (None 값 제거)
            for chunk in chunks:
                metadata = chunk["metadata"]
                metadata_cleaned = {k: v for k, v in metadata.items() if v is not None}
                chunk["metadata"] = metadata_cleaned
            
            all_chunks.extend(chunks)
            print(f"  [OK] {len(chunks)}개 청크 생성")
        
        except Exception as e:
            print(f"  [ERROR] 오류: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print()
    print(f"총 {len(all_chunks)}개 청크 생성 완료")
    print()
    
    # 임베딩 및 저장
    print("⏳ 임베딩 생성 및 저장 중...")
    result = embedding_pipeline.process_and_store(all_chunks)
    print(f"[OK] {result['embeddings_created']}개 임베딩 생성 완료")
    print(f"[OK] 저장 완료 (총 문서 수: {result['total_documents']}개)")
    print()


if __name__ == "__main__":
    ingest_daily_reports_advanced()

