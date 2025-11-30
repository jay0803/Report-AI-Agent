"""
전체 Ingestion 파이프라인 실행 스크립트

1. JSON 파일에서 청크 데이터 로드
2. KPI 컬렉션에 업로드

참고: 보고서 양식은 JSON 파일로만 관리하며 ChromaDB에 저장하지 않습니다.
"""
import os
import sys
import json
import codecs
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Windows CMD에서 UTF-8 출력 설정
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# 프로젝트 루트를 Python Path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.ingest_kpi import ingest_kpi
from ingestion.chroma_client import get_chroma_service


def load_chunks_from_json(json_path: str) -> List[Dict[str, Any]]:
    """
    JSON 파일에서 청크 데이터 로드
    
    Args:
        json_path: JSON 파일 경로
        
    Returns:
        청크 리스트
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 청크 구조 변환: backend/output 형식 → ingestion 형식
    chunks = []
    
    if isinstance(data, list):
        # KPI 청크 형식 또는 보고서 청크 형식
        for item in data:
            # chunk_id → id, text → chunk_text로 변환
            chunk = {
                "id": item.get("chunk_id", item.get("id", "")),
                "chunk_text": item.get("text", item.get("chunk_text", "")),
                "metadata": item.get("metadata", {})
            }
            chunks.append(chunk)
    
    return chunks


def main():
    """전체 Ingestion 파이프라인 실행"""
    print("=" * 70)
    print("🚀 전체 Ingestion 파이프라인 시작")
    print("=" * 70)
    print()
    
    # .env 파일 로드
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("💡 .env 파일에 OPENAI_API_KEY를 추가하세요.")
        sys.exit(1)
    
    # 로컬 ChromaDB 연결 확인
    print("🔗 로컬 ChromaDB 연결 확인...")
    chroma_service = get_chroma_service()
    print()
    
    # === KPI 청크 ingestion ===
    kpi_chunks_path = "output/KPI 자료_kpi_chunks.json"
    
    if Path(kpi_chunks_path).exists():
        print(f"📊 KPI 청크 로드 중: {kpi_chunks_path}")
        kpi_chunks = load_chunks_from_json(kpi_chunks_path)
        print(f"✅ 로드된 KPI 청크: {len(kpi_chunks)}개")
        print()
        
        if kpi_chunks:
            result = ingest_kpi(
                chunks=kpi_chunks,
                api_key=api_key,
                batch_size=100
            )
            
            if result["success"]:
                print("✅ KPI Ingestion 성공")
            else:
                print(f"❌ KPI Ingestion 실패: {result.get('message', 'Unknown error')}")
        else:
            print("⚠️  KPI 청크가 비어있습니다.")
        
        print()
    else:
        print(f"⚠️  KPI 청크 파일을 찾을 수 없습니다: {kpi_chunks_path}")
        print()
    
    # === 최종 결과 출력 ===
    print("=" * 70)
    print("✅ 전체 Ingestion 파이프라인 완료")
    print("=" * 70)
    print()
    
    # 컬렉션 정보 출력
    kpi_collection = chroma_service.get_kpi_collection()
    kpi_info = chroma_service.get_collection_info(kpi_collection)
    
    print("📊 컬렉션 현황:")
    print(f"  - KPI: {kpi_info['count']}개 문서")
    print()


if __name__ == "__main__":
    main()

