"""
자동 Ingestion 유틸리티

일일보고서 완료 시 자동으로 벡터DB에 저장하는 함수들
"""
import os
from pathlib import Path
from typing import Dict, Any
from datetime import date
from dotenv import load_dotenv

# 보고서 전용 .env 파일 로드
project_root = Path(__file__).resolve().parent.parent
report_env_path = project_root / ".env.report"
if report_env_path.exists():
    load_dotenv(report_env_path, override=False)

from app.domain.report.core.canonical_models import CanonicalReport
from app.domain.report.core.chunker import chunk_canonical_report
from app.domain.report.core.embedding_pipeline import get_embedding_pipeline


BATCH_SIZE = 50


def ingest_single_report(
    report: CanonicalReport,
    api_key: str = None
) -> Dict[str, Any]:
    """
    단일 보고서를 벡터DB에 자동 저장
    
    Args:
        report: CanonicalReport 객체
        api_key: OpenAI API 키 (None이면 환경변수에서 읽음)
        
    Returns:
        업로드 결과 딕셔너리
    """
    try:
        print(f"\n📤 [자동 Ingestion] 시작: {report.owner} - {report.period_start}")
        
        # 1. 청킹 (의미 단위 청킹)
        print("  ⏳ 청킹 중...")
        chunks = chunk_canonical_report(report)
        
        if not chunks:
            print("  ⚠️  생성된 청크가 없습니다.")
            return {"success": False, "message": "No chunks generated"}
        
        # 메타데이터 정리 (None 값 제거)
        for chunk in chunks:
            metadata = chunk["metadata"]
            metadata_cleaned = {k: v for k, v in metadata.items() if v is not None}
            chunk["metadata"] = metadata_cleaned
        
        print(f"  ✅ {len(chunks)}개 청크 생성 완료")
        
        # 2. 임베딩 및 저장
        print("  ⏳ 임베딩 생성 및 저장 중...")
        embedding_pipeline = get_embedding_pipeline()
        result = embedding_pipeline.process_and_store(chunks)
        
        print(f"  ✅ {result['embeddings_created']}개 임베딩 생성 완료")
        print(f"  ✅ 벡터DB 업로드 완료: {result['chunks_processed']}개 청크")
        print(f"  📦 컬렉션 총 문서 수: {result['total_documents']}개\n")
        
        return {
            "success": True,
            "collection": "reports",
            "uploaded_chunks": result['chunks_processed'],
            "total_documents": result['total_documents']
        }
        
    except Exception as e:
        print(f"  ❌ 자동 Ingestion 실패: {e}\n")
        return {
            "success": False,
            "message": f"Ingestion failed: {str(e)}",
            "error": str(e)
        }


def ingest_single_report_silent(
    report: CanonicalReport,
    api_key: str = None
) -> bool:
    """
    단일 보고서를 벡터DB에 저장 (로그 최소화 버전)
    
    Args:
        report: CanonicalReport 객체
        api_key: OpenAI API 키
        
    Returns:
        성공 여부 (True/False)
    """
    try:
        # 청킹 (의미 단위 청킹)
        chunks = chunk_canonical_report(report)
        
        if not chunks:
            return False
        
        # 메타데이터 정리 (None 값 제거)
        for chunk in chunks:
            metadata = chunk["metadata"]
            metadata_cleaned = {k: v for k, v in metadata.items() if v is not None}
            chunk["metadata"] = metadata_cleaned
        
        # 임베딩 및 저장
        embedding_pipeline = get_embedding_pipeline()
        result = embedding_pipeline.process_and_store(chunks)
        
        return result["success"]
        
    except Exception as e:
        print(f"❌ 벡터DB 자동 저장 실패: {e}")
        return False

