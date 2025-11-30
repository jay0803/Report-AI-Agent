"""
로컬 ChromaDB daily_reports 컬렉션 삭제 스크립트

사용법:
    python -m debug.clear_daily_reports
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from ingestion.chroma_client import get_chroma_service


COLLECTION_NAME = "daily_reports"


def clear_collection():
    """daily_reports 컬렉션 삭제"""
    print()
    print("=" * 80)
    print("🗑️  로컬 ChromaDB 컬렉션 삭제")
    print("=" * 80)
    print()
    
    try:
        chroma_service = get_chroma_service()
        
        # 삭제 전 확인
        try:
            collection = chroma_service.get_or_create_collection(name=COLLECTION_NAME)
            count = collection.count()
            print(f"📦 컬렉션 '{COLLECTION_NAME}' 현재 문서 수: {count}개")
            print()
        except:
            print(f"⚠️  컬렉션 '{COLLECTION_NAME}'를 찾을 수 없습니다.")
            print()
            return
        
        # 사용자 확인
        print(f"⚠️  정말로 '{COLLECTION_NAME}' 컬렉션을 삭제하시겠습니까?")
        print(f"   ({count}개의 문서가 모두 삭제됩니다)")
        response = input("   계속하려면 'yes'를 입력하세요: ")
        
        if response.lower() != 'yes':
            print("❌ 삭제가 취소되었습니다.")
            return
        
        print()
        print(f"🗑️  컬렉션 '{COLLECTION_NAME}' 삭제 중...")
        
        # 컬렉션 삭제
        chroma_service.delete_collection(name=COLLECTION_NAME)
        
        print()
        print("=" * 80)
        print("✅ 삭제 완료!")
        print("=" * 80)
        print(f"컬렉션 '{COLLECTION_NAME}'이(가) 삭제되었습니다.")
        print()
        print("이제 ingestion 스크립트를 실행하여 데이터를 다시 업로드할 수 있습니다:")
        print("  python -m ingestion.ingest_daily_reports")
        print()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print()


if __name__ == "__main__":
    clear_collection()

