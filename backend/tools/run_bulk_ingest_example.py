"""
Bulk Daily Ingest 실행 예제

이 스크립트는 bulk_daily_ingest.py를 실행하는 예제입니다.
"""
import sys
import os
from pathlib import Path

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# backend 경로를 Python path에 추가
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.insert(0, str(backend_dir))


def main():
    """메인 함수"""
    print("=" * 70)
    print("🚀 Bulk Daily Ingest 실행 예제")
    print("=" * 70)
    print()
    
    # bulk_daily_ingest 모듈 import
    from tools.bulk_daily_ingest import bulk_ingest_daily_reports
    
    # 실행
    try:
        bulk_ingest_daily_reports()
        
        print("\n✅ 실행 완료!")
        print("\n다음 단계:")
        print("  1. 주간 보고서 생성: python backend/debug/test_weekly_chain.py")
        print("  2. 월간 보고서 생성: python backend/debug/test_monthly_chain.py")
        print("  3. 실적 보고서 생성: python backend/debug/test_performance_chain.py")
        print("  4. API 서버 시작: python assistant.py")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

