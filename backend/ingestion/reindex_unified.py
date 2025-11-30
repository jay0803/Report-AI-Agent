"""
통합 Ingestion 파이프라인

모든 문서 타입을 UnifiedCanonical로 변환하여 단일 컬렉션에 저장

처리 문서:
- 일일 보고서 (backend/Data/mock_reports/daily/*.txt)
- KPI 문서 (output/*_kpi_canonical.json)
- 보고서 템플릿 (output/reports/*_canonical.json)

플로우:
1. 파일 스캔
2. Raw → CanonicalReport/CanonicalKPI 변환 (기존 로직)
3. Canonical → UnifiedCanonical 변환 (merge_normalizer)
4. UnifiedCanonical → Chunks (unified_chunker)
5. Chunks → Embeddings (OpenAI)
6. Embeddings → Chroma (upsert)

Author: AI Assistant
Created: 2025-11-18

사용법:
    python -m ingestion.reindex_unified
    python -m ingestion.reindex_unified --dry-run  # 테스트용
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# 프로젝트 루트 설정
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# .env 로드
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ .env 파일 로드됨: {env_path}")
    # 보고서 전용 환경 변수 로드
    report_env_path = project_root / ".env.report"
    if report_env_path.exists():
        load_dotenv(report_env_path, override=False)
        print(f"✅ .env.report 파일 로드됨: {report_env_path}")
except ImportError:
    print("⚠️  python-dotenv가 설치되지 않았습니다.")
except Exception as e:
    print(f"⚠️  .env 파일 로드 오류: {e}")

# 모듈 임포트
from app.domain.report.service import ReportProcessingService
from app.domain.report.schemas import CanonicalReport
from app.domain.kpi.schemas import CanonicalKPI
from app.domain.common.canonical_schema import UnifiedCanonical
from app.services.canonical.merge_normalizer import (
    report_to_unified,
    kpi_to_unified,
    text_to_unified
)
from app.domain.common.unified_chunker import chunk_unified, get_chunk_statistics
from ingestion.embed import embed_texts
from ingestion.chroma_client import get_chroma_service
from ingestion.ingest_daily_reports import (
    scan_mock_reports,
    parse_multi_json_file
)


# ========================================
# 설정
# ========================================
DATA_DIR = project_root / "Data" / "mock_reports" / "daily"
OUTPUT_DIR = project_root / "output"
COLLECTION_NAME = "daily_reports_advanced"  # 통합 컬렉션
BATCH_SIZE = 100


# ========================================
# Step 1: 일일 보고서 처리
# ========================================
def process_daily_reports(
    service: ReportProcessingService
) -> List[UnifiedCanonical]:
    """
    일일 보고서 txt 파일 → UnifiedCanonical 변환
    
    Args:
        service: ReportProcessingService 인스턴스
        
    Returns:
        UnifiedCanonical 리스트
    """
    print("=" * 80)
    print("📊 Step 1: 일일 보고서 처리")
    print("=" * 80)
    print()
    
    # 파일 스캔
    print("⏳ mock_reports 폴더 스캔 중...")
    file_infos = scan_mock_reports(DATA_DIR)
    
    if not file_infos:
        print("❌ txt 파일을 찾을 수 없습니다.")
        return []
    
    print(f"✅ 총 {len(file_infos)}개 txt 파일 발견")
    print()
    
    unified_docs = []
    total_reports = 0
    
    # 각 파일 처리
    for idx, file_info in enumerate(file_infos):
        file_path = file_info["file_path"]
        relative_path = file_info["relative_path"]
        
        try:
            # JSON 파싱
            json_objects = parse_multi_json_file(file_path)
            
            if not json_objects:
                continue
            
            total_reports += len(json_objects)
            
            # 각 JSON → CanonicalReport → UnifiedCanonical
            for json_obj in json_objects:
                try:
                    # Normalize (Raw → CanonicalReport)
                    canonical_report = service.normalize_daily(json_obj)
                    
                    # 소스 파일 메타데이터 추가
                    canonical_report.metadata["source_file"] = relative_path
                    
                    # CanonicalReport → UnifiedCanonical
                    unified = report_to_unified(canonical_report)
                    unified_docs.append(unified)
                    
                except Exception as e:
                    print(f"  ⚠️  보고서 변환 오류: {e}")
                    continue
            
            if (idx + 1) % 10 == 0:
                print(f"  진행: {idx + 1}/{len(file_infos)} 파일 처리 완료...")
        
        except Exception as e:
            print(f"  ❌ 파일 처리 오류 ({relative_path}): {e}")
            continue
    
    print()
    print(f"✅ 일일 보고서 처리 완료")
    print(f"   - 총 파일: {len(file_infos)}개")
    print(f"   - 총 보고서: {total_reports}개")
    print(f"   - UnifiedCanonical: {len(unified_docs)}개")
    print()
    
    return unified_docs


# ========================================
# Step 2: KPI 문서 처리
# ========================================
def process_kpi_documents() -> List[UnifiedCanonical]:
    """
    KPI canonical JSON 파일 → UnifiedCanonical 변환
    
    Returns:
        UnifiedCanonical 리스트
    """
    print("=" * 80)
    print("📊 Step 2: KPI 문서 처리")
    print("=" * 80)
    print()
    
    unified_docs = []
    
    # KPI canonical 파일 찾기
    kpi_files = list(OUTPUT_DIR.glob("*_kpi_canonical.json"))
    
    if not kpi_files:
        print("⚠️  KPI canonical 파일을 찾을 수 없습니다.")
        print()
        return []
    
    print(f"✅ {len(kpi_files)}개 KPI 파일 발견")
    print()
    
    for kpi_file in kpi_files:
        try:
            with open(kpi_file, 'r', encoding='utf-8') as f:
                kpi_data = json.load(f)
            
            # CanonicalKPI 객체 생성
            if isinstance(kpi_data, list):
                canonical_kpis = [CanonicalKPI(**item) for item in kpi_data]
            else:
                canonical_kpis = [CanonicalKPI(**kpi_data)]
            
            # CanonicalKPI → UnifiedCanonical
            for canonical_kpi in canonical_kpis:
                try:
                    unified = kpi_to_unified(canonical_kpi)
                    unified.metadata["source_file"] = kpi_file.name
                    unified_docs.append(unified)
                except Exception as e:
                    print(f"  ⚠️  KPI 변환 오류: {e}")
                    continue
            
            print(f"  ✅ {kpi_file.name}: {len(canonical_kpis)}개 KPI 변환")
        
        except Exception as e:
            print(f"  ❌ 파일 처리 오류 ({kpi_file.name}): {e}")
            continue
    
    print()
    print(f"✅ KPI 문서 처리 완료")
    print(f"   - UnifiedCanonical: {len(unified_docs)}개")
    print()
    
    return unified_docs


# ========================================
# Step 3: 보고서 템플릿 처리
# ========================================
def process_report_templates() -> List[UnifiedCanonical]:
    """
    보고서 템플릿 canonical JSON → UnifiedCanonical 변환
    
    Returns:
        UnifiedCanonical 리스트
    """
    print("=" * 80)
    print("📊 Step 3: 보고서 템플릿 처리")
    print("=" * 80)
    print()
    
    unified_docs = []
    
    # 템플릿 canonical 파일 찾기 (kpi 제외)
    template_files = [
        f for f in OUTPUT_DIR.glob("*_canonical.json")
        if "kpi" not in f.name
    ]
    
    if not template_files:
        print("⚠️  템플릿 canonical 파일을 찾을 수 없습니다.")
        print()
        return []
    
    print(f"✅ {len(template_files)}개 템플릿 파일 발견")
    print()
    
    for template_file in template_files:
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            
            # CanonicalReport로 파싱 시도
            if isinstance(template_data, dict):
                try:
                    canonical_report = CanonicalReport(**template_data)
                    unified = report_to_unified(canonical_report)
                    unified.metadata["source_file"] = template_file.name
                    unified_docs.append(unified)
                    print(f"  ✅ {template_file.name}: 변환 완료")
                except Exception as e:
                    print(f"  ⚠️  {template_file.name}: CanonicalReport 파싱 실패, 텍스트로 처리")
                    # 실패 시 raw text로 처리
                    raw_text = json.dumps(template_data, ensure_ascii=False, indent=2)
                    unified = text_to_unified(
                        text=raw_text,
                        title=template_file.stem,
                        source_file=template_file.name,
                        doc_type="template"
                    )
                    unified_docs.append(unified)
        
        except Exception as e:
            print(f"  ❌ 파일 처리 오류 ({template_file.name}): {e}")
            continue
    
    print()
    print(f"✅ 템플릿 문서 처리 완료")
    print(f"   - UnifiedCanonical: {len(unified_docs)}개")
    print()
    
    return unified_docs


# ========================================
# Step 4: 청킹 및 임베딩
# ========================================
def process_chunks(
    unified_docs: List[UnifiedCanonical],
    api_key: str = None
) -> tuple[List[str], List[str], List[List[float]], List[Dict[str, Any]]]:
    """
    UnifiedCanonical → Chunks → Embeddings
    
    Args:
        unified_docs: UnifiedCanonical 리스트
        api_key: OpenAI API 키
        
    Returns:
        (ids, texts, embeddings, metadatas) 튜플
    """
    print("=" * 80)
    print("📊 Step 4: 청킹 및 임베딩 생성")
    print("=" * 80)
    print()
    
    all_chunks = []
    
    # 청킹
    print("⏳ 청킹 중...")
    for idx, unified in enumerate(unified_docs):
        try:
            chunks = chunk_unified(unified, include_summary=True)
            all_chunks.extend(chunks)
            
            if (idx + 1) % 50 == 0:
                print(f"  진행: {idx + 1}/{len(unified_docs)} 문서 청킹 완료...")
        
        except Exception as e:
            print(f"  ⚠️  청킹 오류 (doc_id: {unified.doc_id}): {e}")
            continue
    
    print(f"✅ 총 {len(all_chunks)}개 청크 생성")
    print()
    
    # 청크 통계
    stats = get_chunk_statistics(all_chunks)
    print("📊 청크 통계:")
    print(f"  - 총 청크 수: {stats['total_chunks']}")
    print(f"  - 청크 타입별:")
    for chunk_type, count in stats["chunk_types"].items():
        print(f"    • {chunk_type}: {count}")
    print(f"  - 평균 텍스트 길이: {stats['avg_text_length']:.1f}자")
    print()
    
    # 임베딩 생성
    print("⏳ 임베딩 생성 중...")
    ids = [chunk["id"] for chunk in all_chunks]
    texts = [chunk["text"] for chunk in all_chunks]
    metadatas = [chunk["metadata"] for chunk in all_chunks]
    
    try:
        embeddings = embed_texts(texts, api_key=api_key, batch_size=BATCH_SIZE)
        print(f"✅ {len(embeddings)}개 임베딩 생성 완료")
        print()
    except Exception as e:
        print(f"❌ 임베딩 생성 오류: {e}")
        raise
    
    return ids, texts, embeddings, metadatas


# ========================================
# Step 5: Chroma 업로드
# ========================================
def upload_to_chroma(
    ids: List[str],
    texts: List[str],
    embeddings: List[List[float]],
    metadatas: List[Dict[str, Any]],
    reset_collection: bool = True
):
    """
    로컬 ChromaDB에 업로드
    
    Args:
        ids: 청크 ID 리스트
        texts: 텍스트 리스트
        embeddings: 임베딩 리스트
        metadatas: 메타데이터 리스트
        reset_collection: True면 기존 컬렉션 삭제 후 재생성
    """
    print("=" * 80)
    print("📊 Step 5: 로컬 ChromaDB 업로드")
    print("=" * 80)
    print()
    
    try:
        chroma_service = get_chroma_service()
        
        # 기존 컬렉션 삭제 (옵션)
        if reset_collection:
            print(f"🗑️  기존 컬렉션 '{COLLECTION_NAME}' 삭제 중...")
            try:
                chroma_service.delete_collection(name=COLLECTION_NAME)
                print(f"✅ 컬렉션 삭제 완료")
            except Exception as e:
                print(f"⚠️  컬렉션 삭제 실패 (존재하지 않을 수 있음): {e}")
            print()
        
        # 컬렉션 생성
        print(f"📦 컬렉션 '{COLLECTION_NAME}' 생성 중...")
        collection = chroma_service.get_or_create_collection(name=COLLECTION_NAME)
        print(f"✅ 컬렉션 준비 완료")
        print()
        
        # 배치 업로드
        total = len(ids)
        print(f"⏳ {total}개 문서 업로드 중...")
        
        for i in range(0, total, BATCH_SIZE):
            batch_end = min(i + BATCH_SIZE, total)
            
            batch_ids = ids[i:batch_end]
            batch_embeddings = embeddings[i:batch_end]
            batch_documents = texts[i:batch_end]
            batch_metadatas = metadatas[i:batch_end]
            
            try:
                collection.upsert(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadatas
                )
                print(f"  ✅ {i + 1}-{batch_end}/{total} 업로드 완료")
            except Exception as e:
                print(f"  ❌ 배치 업로드 오류 ({i}-{batch_end}): {e}")
                raise
        
        print()
        print("=" * 80)
        print("✅ 로컬 ChromaDB 업로드 완료!")
        print("=" * 80)
        print(f"컬렉션: {COLLECTION_NAME}")
        print(f"총 문서 수: {collection.count()}개")
        print()
    
    except Exception as e:
        print(f"❌ 로컬 ChromaDB 오류: {e}")
        raise


# ========================================
# 메인 파이프라인
# ========================================
def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="통합 Ingestion 파이프라인"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="OpenAI API 키 (기본값: 환경변수 OPENAI_API_KEY)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run 모드 (Chroma 업로드 없이 통계만 출력)"
    )
    parser.add_argument(
        "--keep-collection",
        action="store_true",
        help="기존 컬렉션 유지 (삭제하지 않음)"
    )
    
    args = parser.parse_args()
    
    # API 키 확인
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key and not args.dry_run:
        print("❌ OpenAI API 키가 필요합니다.")
        print("   --api-key 옵션을 사용하거나 환경변수 OPENAI_API_KEY를 설정하세요.")
        sys.exit(1)
    
    print()
    print("=" * 80)
    print("🚀 통합 Ingestion 파이프라인 시작")
    print("=" * 80)
    print()
    
    try:
        # ReportProcessingService 초기화
        if args.dry_run:
            service = ReportProcessingService.__new__(ReportProcessingService)
            service.client = None
        else:
            service = ReportProcessingService(api_key=api_key)
        
        # Step 1: 일일 보고서 처리
        daily_docs = process_daily_reports(service)
        
        # Step 2: KPI 문서 처리
        kpi_docs = process_kpi_documents()
        
        # Step 3: 보고서 템플릿 처리
        template_docs = process_report_templates()
        
        # 전체 문서 통합
        all_unified_docs = daily_docs + kpi_docs + template_docs
        
        print("=" * 80)
        print("📊 전체 통계")
        print("=" * 80)
        print(f"일일 보고서: {len(daily_docs)}개")
        print(f"KPI 문서: {len(kpi_docs)}개")
        print(f"템플릿 문서: {len(template_docs)}개")
        print(f"총 UnifiedCanonical: {len(all_unified_docs)}개")
        print()
        
        if not all_unified_docs:
            print("❌ 처리할 문서가 없습니다.")
            return
        
        # Dry-run 체크
        if args.dry_run:
            print("🔍 Dry-run 모드: Chroma 업로드를 건너뜁니다.")
            return
        
        # Step 4: 청킹 및 임베딩
        ids, texts, embeddings, metadatas = process_chunks(
            all_unified_docs,
            api_key=api_key
        )
        
        # Step 5: Chroma 업로드
        upload_to_chroma(
            ids, texts, embeddings, metadatas,
            reset_collection=not args.keep_collection
        )
        
        print("=" * 80)
        print("🎉 통합 Ingestion 완료!")
        print("=" * 80)
        print()
    
    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ 오류 발생: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

