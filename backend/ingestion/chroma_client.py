"""
로컬 ChromaDB 클라이언트 설정

backend/Data/chroma/ 경로에 로컬 데이터 저장
"""
import chromadb
from chromadb import Collection
from pathlib import Path


# 로컬 ChromaDB 경로
CHROMA_PERSIST_DIR = Path(__file__).resolve().parent.parent / "Data" / "chroma"


class ChromaLocalService:
    """로컬 ChromaDB 서비스"""
    
    def __init__(self):
        """로컬 ChromaDB 클라이언트 초기화"""
        print(f"🔗 로컬 ChromaDB 연결 중... ({CHROMA_PERSIST_DIR})")
        
        # 디렉토리 생성
        CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        
        # 로컬 PersistentClient 사용
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR)
        )
        
        print("✅ 로컬 ChromaDB 연결 성공")
    
    def get_or_create_collection(self, name: str) -> Collection:
        """
        컬렉션 가져오기 또는 생성
        
        Args:
            name: 컬렉션 이름
            
        Returns:
            Collection 객체
        """
        print(f"📦 컬렉션 '{name}' 가져오기/생성 중...")
        
        try:
            # 먼저 기존 컬렉션이 있는지 확인
            try:
                collection = self.client.get_collection(name=name)
                print(f"✅ 컬렉션 '{name}' 준비 완료 (기존 컬렉션 사용)")
                return collection
            except Exception:
                # 컬렉션이 없으면 새로 생성
                collection = self.client.create_collection(
                    name=name,
                    metadata={"description": f"Collection: {name}"}
                )
                print(f"✅ 컬렉션 '{name}' 준비 완료 (새로 생성)")
                return collection
            
        except (KeyError, Exception) as e:
            # _type 오류나 다른 에러 발생 시 컬렉션 삭제 후 재생성
            print(f"[WARNING] 컬렉션 접근 오류: {e}")
            print(f"[INFO] 컬렉션 삭제 후 재생성 시도...")
            try:
                self.client.delete_collection(name=name)
            except:
                pass
            collection = self.client.create_collection(
                name=name,
                metadata={"description": f"Collection: {name}"}
            )
            print(f"✅ 컬렉션 '{name}' 준비 완료 (재생성)")
            return collection
    
    def get_collection_info(self, collection: Collection) -> dict:
        """
        컬렉션 정보 조회
        
        Args:
            collection: Collection 객체
            
        Returns:
            컬렉션 정보 딕셔너리
        """
        count = collection.count()
        
        return {
            "name": collection.name,
            "count": count,
            "metadata": collection.metadata
        }
    
    def delete_collection(self, name: str):
        """
        컬렉션 삭제
        
        Args:
            name: 컬렉션 이름
        """
        try:
            self.client.delete_collection(name=name)
            print(f"✅ 컬렉션 삭제됨: {name}")
        except Exception as e:
            print(f"❌ 컬렉션 삭제 오류: {e}")


# 전역 서비스 인스턴스 (lazy initialization)
_chroma_service = None


def get_chroma_service() -> ChromaLocalService:
    """
    로컬 ChromaDB 서비스 싱글톤 인스턴스 반환
    
    Returns:
        ChromaLocalService 인스턴스
    """
    global _chroma_service
    if _chroma_service is None:
        _chroma_service = ChromaLocalService()
    return _chroma_service

