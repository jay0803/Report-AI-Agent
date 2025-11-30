"""
ChromaDB 컬렉션 재생성 스크립트

_type 에러를 해결하기 위해 ChromaDB 데이터 디렉토리를 완전히 삭제하고 재생성합니다.
"""
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.vector_store import CHROMA_PERSIST_DIR, UNIFIED_COLLECTION_NAME
import chromadb
from chromadb.config import Settings

print("=" * 80)
print("🔧 ChromaDB 완전 재생성")
print("=" * 80)
print()

# 1. 기존 ChromaDB 데이터 디렉토리 삭제
if CHROMA_PERSIST_DIR.exists():
    print(f"🗑️  기존 ChromaDB 데이터 디렉토리 삭제 중: {CHROMA_PERSIST_DIR}")
    try:
        # SQLite 파일도 함께 삭제
        sqlite_file = CHROMA_PERSIST_DIR / "chroma.sqlite3"
        if sqlite_file.exists():
            print(f"   SQLite 파일 삭제: {sqlite_file}")
            sqlite_file.unlink()
        shutil.rmtree(CHROMA_PERSIST_DIR)
        print(f"✅ 데이터 디렉토리 삭제 완료")
    except Exception as e:
        print(f"❌ 삭제 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
else:
    print(f"ℹ️  데이터 디렉토리가 없습니다: {CHROMA_PERSIST_DIR}")

# 2. 새 디렉토리 생성
print()
print(f"📁 새 ChromaDB 데이터 디렉토리 생성 중...")
CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
print(f"✅ 디렉토리 생성 완료")

# 3. 새 ChromaDB 클라이언트 생성
print()
print(f"🔗 새 ChromaDB 클라이언트 생성 중...")
client = chromadb.PersistentClient(
    path=str(CHROMA_PERSIST_DIR),
    settings=Settings(anonymized_telemetry=False)
)
print(f"✅ 클라이언트 생성 완료")

# 4. 컬렉션 생성
print()
print(f"📦 새 컬렉션 '{UNIFIED_COLLECTION_NAME}' 생성 중...")
try:
    collection = client.create_collection(
        name=UNIFIED_COLLECTION_NAME,
        metadata={"description": "Unified documents collection"}
    )
    print(f"✅ 컬렉션 생성 완료")
    print(f"   컬렉션 ID: {collection.id}")
    print()
    print("=" * 80)
    print("✅ 완료!")
    print("=" * 80)
    print()
    print("⚠️  주의: ChromaDB가 완전히 재생성되었으므로 데이터를 다시 저장해야 합니다.")
    print("   다음 명령어를 실행하세요:")
    print("   python -m ingestion.ingest_daily_reports")
except Exception as e:
    print(f"❌ 컬렉션 생성 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

