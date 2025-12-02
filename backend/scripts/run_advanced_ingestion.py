"""
목업 데이터 Ingestion 실행 스크립트 (레거시 호환)
새로운 ingest_mock_reports.py를 사용합니다.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from ingestion.ingest_mock_reports import main


if __name__ == "__main__":
    main()

