"""
벡터DB 저장 테스트 스크립트

일일보고서가 벡터DB에 제대로 저장되는지 확인
"""
import os
import sys
from pathlib import Path
from datetime import date

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# .env 로드
from dotenv import load_dotenv
load_dotenv()

from app.domain.report.daily.repository import DailyReportRepository
from app.domain.report.core.schemas import CanonicalReport
from app.infrastructure.database.session import SessionLocal
from ingestion.auto_ingest import ingest_single_report
from app.infrastructure.vector_store_report import get_report_vector_store


def test_vector_ingest():
    """벡터DB 저장 테스트"""
    
    print("=" * 80)
    print("벡터DB 저장 테스트")
    print("=" * 80)
    
    # 1. PostgreSQL에서 최근 보고서 가져오기
    db = SessionLocal()
    
    try:
        # 가장 최근 보고서 가져오기
        reports = db.query(DailyReportRepository.model_class).order_by(
            DailyReportRepository.model_class.created_at.desc()
        ).limit(1).all()
        
        if not reports:
            print("❌ PostgreSQL에 보고서가 없습니다.")
            return
        
        db_report = reports[0]
        print(f"✅ 최근 보고서 발견:")
        print(f"   - Owner: {db_report.owner}")
        print(f"   - Date: {db_report.date}")
        print(f"   - Created: {db_report.created_at}")
        print()
        
        # 2. CanonicalReport로 변환
        report_dict = db_report.report_json
        report = CanonicalReport(**report_dict)
        
        print(f"📊 보고서 내용:")
        print(f"   - Tasks: {len(report.tasks)}개")
        print(f"   - Plans: {len(report.plans)}개")
        print(f"   - Issues: {len(report.issues)}개")
        print()
        
        # 3. 벡터DB에 저장
        print("⏳ 벡터DB 저장 시작...")
        result = ingest_single_report(
            report=report,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        if result["success"]:
            print(f"\n✅ 벡터DB 저장 성공!")
            print(f"   - 업로드된 청크: {result['uploaded_chunks']}개")
            print(f"   - 컬렉션 총 문서 수: {result['total_documents']}개")
        else:
            print(f"\n❌ 벡터DB 저장 실패:")
            print(f"   - 메시지: {result.get('message', 'Unknown')}")
            if 'error' in result:
                print(f"   - 에러: {result['error']}")
        
        # 4. 벡터DB에서 확인
        print("\n📦 벡터DB 컬렉션 확인...")
        vector_store = get_report_vector_store()
        collection = vector_store.get_collection()
        
        # 해당 날짜의 문서 검색
        date_str = str(db_report.date)
        results = collection.get(
            where={"date": date_str},
            limit=10
        )
        
        if results and results['ids']:
            print(f"✅ 벡터DB에서 {len(results['ids'])}개 청크 발견")
            print(f"   - 샘플 ID: {results['ids'][0]}")
            print(f"   - 샘플 메타데이터: {results['metadatas'][0]}")
        else:
            print("⚠️  벡터DB에서 해당 날짜의 문서를 찾을 수 없습니다.")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
    
    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    test_vector_ingest()

