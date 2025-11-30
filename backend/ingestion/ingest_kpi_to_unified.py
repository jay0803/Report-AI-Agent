"""
KPI 청크를 daily_reports_advanced 컬렉션에 추가

기존 KPI 자료_kpi_chunks.json 파일을 읽어서
daily_reports_advanced 컬렉션에 doc_type=kpi로 추가합니다.

사용법:
    python -m ingestion.ingest_kpi_to_unified
"""
import sys
import json
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ .env 파일 로드됨: {env_path}")
except Exception as e:
    print(f"⚠️  .env 파일 로드 오류: {e}")

from ingestion.embed import embed_texts
from ingestion.chroma_client import get_chroma_service


def main():
    print("=" * 80)
    print("📊 KPI 데이터 → daily_reports_advanced 컬렉션 추가")
    print("=" * 80)
    print()
    
    # 1. KPI 청크 JSON 파일 읽기
    kpi_chunks_file = project_root / "output" / "KPI 자료_kpi_chunks.json"
    
    if not kpi_chunks_file.exists():
        print(f"❌ KPI 청크 파일을 찾을 수 없습니다: {kpi_chunks_file}")
        print(f"\n먼저 다음 명령을 실행하세요:")
        print(f"  python process_all_reports.py")
        sys.exit(1)
    
    print(f"📂 KPI 청크 파일 로드 중: {kpi_chunks_file.name}")
    with open(kpi_chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    print(f"✅ 총 {len(chunks)}개 청크 로드 완료")
    print()
    
    # 2. 각 청크에 doc_type=kpi 메타데이터 추가
    print("⏳ 메타데이터 추가 중...")
    for chunk in chunks:
        # chunk_id → id로 키 이름 변경 (일관성)
        if "chunk_id" in chunk:
            chunk["id"] = chunk.pop("chunk_id")
        
        # text → chunk_text로 키 이름 변경 (일관성)
        if "text" in chunk:
            chunk["chunk_text"] = chunk.pop("text")
        
        # doc_type 추가
        chunk["metadata"]["doc_type"] = "kpi"
        
        # None 값 제거
        chunk["metadata"] = {
            k: v for k, v in chunk["metadata"].items()
            if v is not None
        }
    
    print(f"✅ 메타데이터 추가 완료")
    print()
    
    # 3. 임베딩 생성
    print("=" * 80)
    print("⏳ 임베딩 생성 중...")
    print("=" * 80)
    
    texts = [chunk["chunk_text"] for chunk in chunks]
    embeddings = embed_texts(texts, batch_size=100)
    
    print(f"✅ {len(embeddings)}개 임베딩 생성 완료")
    print()
    
    # 4. daily_reports_advanced 컬렉션에 업로드
    print("=" * 80)
    print("⏳ daily_reports_advanced 컬렉션에 업로드 중...")
    print("=" * 80)
    
    chroma = get_chroma_service()
    collection = chroma.get_or_create_collection('daily_reports_advanced')
    
    print(f"✅ 컬렉션 'daily_reports_advanced' 연결 완료")
    print(f"📦 현재 문서 수: {collection.count()}개")
    print()
    
    # 배치 업로드
    batch_size = 100
    total = len(chunks)
    
    for i in range(0, total, batch_size):
        batch_end = min(i + batch_size, total)
        
        batch_chunks = chunks[i:batch_end]
        batch_ids = [chunk["id"] for chunk in batch_chunks]
        batch_texts = [chunk["chunk_text"] for chunk in batch_chunks]
        batch_metadatas = [chunk["metadata"] for chunk in batch_chunks]
        batch_embeddings = embeddings[i:batch_end]
        
        print(f"  ⏳ 업로드 중... ({i + 1}-{batch_end}/{total})")
        
        try:
            collection.upsert(
                ids=batch_ids,
                documents=batch_texts,
                metadatas=batch_metadatas,
                embeddings=batch_embeddings
            )
        except Exception as e:
            print(f"❌ 배치 업로드 오류: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    print()
    print("=" * 80)
    print("✅ Ingestion 완료!")
    print("=" * 80)
    print(f"컬렉션: daily_reports_advanced")
    print(f"업로드된 KPI 청크: {total}개")
    print(f"컬렉션 총 문서 수: {collection.count()}개")
    print()


if __name__ == "__main__":
    main()

