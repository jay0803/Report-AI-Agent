"""
Bulk Daily Report Ingestion Script

backend/Data/mock_reports/daily 폴더의 모든 txt 파일을 읽어서
PostgreSQL의 daily_reports 테이블에 저장하는 스크립트

Usage:
    python backend/tools/bulk_daily_ingest.py
"""
import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any, Optional

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# 프로젝트 루트를 Python path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.infrastructure.database.session import SessionLocal
from app.domain.report.daily.repository import DailyReportRepository
from app.domain.report.daily.schemas import DailyReportCreate
from app.domain.report.core.canonical_models import CanonicalReport, CanonicalDaily, DetailTask
import uuid


def parse_time_range(time_str: str) -> tuple[Optional[str], Optional[str]]:
    """
    시간 범위 문자열을 파싱하여 (start, end) 튜플 반환
    
    예: "09:00 - 10:00" -> ("09:00", "10:00")
    
    Args:
        time_str: 시간 범위 문자열
        
    Returns:
        (time_start, time_end) 튜플
    """
    if not time_str or time_str.strip() == "":
        return (None, None)
    
    # "09:00 - 10:00" 패턴 매칭
    match = re.match(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', time_str.strip())
    if match:
        return (match.group(1), match.group(2))
    
    # 단일 시간만 있는 경우 (예: "09:00")
    match = re.match(r'(\d{1,2}:\d{2})', time_str.strip())
    if match:
        return (match.group(1), None)
    
    return (None, None)


def parse_date(date_str: str) -> date:
    """
    날짜 문자열을 date 객체로 변환
    
    예: "2025-01-02" -> date(2025, 1, 2)
    
    Args:
        date_str: 날짜 문자열 (YYYY-MM-DD)
        
    Returns:
        date 객체
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"날짜 형식 오류: {date_str}. YYYY-MM-DD 형식이어야 합니다. ({e})")


def convert_to_canonical_report(raw_json: Dict[str, Any]) -> CanonicalReport:
    """
    Raw JSON을 CanonicalReport로 변환
    
    Args:
        raw_json: 원본 JSON 딕셔너리
        
    Returns:
        CanonicalReport 객체
    """
    # 1. 기본 정보 추출
    작성일자 = raw_json["상단정보"]["작성일자"]
    성명 = raw_json["상단정보"]["성명"]
    
    period_date = parse_date(작성일자)
    
    # 2. 헤더 정보
    header = {
        "작성일자": 작성일자,
        "성명": 성명
    }
    
    # 3. summary_tasks (금일_진행_업무)
    summary_tasks = []
    금일진행업무 = raw_json.get("금일_진행_업무", "")
    if 금일진행업무:
        if isinstance(금일진행업무, list):
            summary_tasks = 금일진행업무
        else:
            summary_tasks = [금일진행업무] if 금일진행업무.strip() else []
    
    # 4. detail_tasks (세부업무)
    detail_tasks = []
    세부업무 = raw_json.get("세부업무", [])
    for task_data in 세부업무:
        업무내용 = task_data.get("업무내용", "")
        if not 업무내용 or not 업무내용.strip():
            continue
        
        time_str = task_data.get("시간", "")
        time_start, time_end = parse_time_range(time_str)
        
        detail_task = DetailTask(
            time_start=time_start,
            time_end=time_end,
            text=업무내용,
            note=task_data.get("비고", "")
        )
        detail_tasks.append(detail_task)
    
    # 5. pending (미종결_업무사항)
    pending = []
    미종결 = raw_json.get("미종결_업무사항", "")
    if 미종결:
        if isinstance(미종결, list):
            pending = 미종결
        else:
            pending = [미종결] if 미종결.strip() else []
    
    # 6. plans (익일_업무계획)
    plans = []
    익일계획 = raw_json.get("익일_업무계획", "")
    if 익일계획:
        if isinstance(익일계획, list):
            plans = 익일계획
        else:
            plans = [익일계획] if 익일계획.strip() else []
    
    # 7. notes (특이사항)
    notes = raw_json.get("특이사항", "") or ""
    
    # 8. CanonicalDaily 생성
    canonical_daily = CanonicalDaily(
        header=header,
        summary_tasks=summary_tasks,
        detail_tasks=detail_tasks,
        pending=pending,
        plans=plans,
        notes=notes
    )
    
    # 9. CanonicalReport 생성
    report = CanonicalReport(
        report_id=str(uuid.uuid4()),
        report_type="daily",
        owner=성명,
        period_start=period_date,
        period_end=period_date,
        daily=canonical_daily
    )
    
    return report


def read_json_objects_from_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    txt 파일에서 여러 JSON 객체를 읽어서 리스트로 반환
    
    각 JSON 객체는 빈 줄로 구분됨
    
    Args:
        file_path: txt 파일 경로
        
    Returns:
        JSON 객체 리스트
    """
    json_objects = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 빈 줄로 분리된 JSON 객체들을 추출
        # 중괄호로 시작하고 끝나는 패턴 찾기
        json_texts = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
        
        for json_text in json_texts:
            try:
                obj = json.loads(json_text)
                json_objects.append(obj)
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON 파싱 오류 ({file_path.name}): {e}")
                continue
    
    except Exception as e:
        print(f"❌ 파일 읽기 오류 ({file_path}): {e}")
    
    return json_objects


def find_all_txt_files(base_dir: Path, year: Optional[int] = None, month: Optional[int] = None) -> List[Path]:
    """
    base_dir 하위의 txt 파일 찾기 (날짜 필터링 옵션)
    
    Args:
        base_dir: 기본 디렉토리
        year: 필터링할 연도 (None이면 모든 연도)
        month: 필터링할 월 (None이면 모든 월, 예: 11 = 11월)
        
    Returns:
        txt 파일 경로 리스트
    """
    all_files = list(base_dir.rglob("*.txt"))
    
    # 날짜 필터링이 없으면 모든 파일 반환
    if year is None and month is None:
        return sorted(all_files)
    
    # 날짜 필터링
    filtered_files = []
    for file_path in all_files:
        filename = file_path.stem  # 확장자 제거
        
        try:
            # YYYY-MM-DD 형식 파싱
            parts = filename.split('-')
            if len(parts) >= 3:
                file_year = int(parts[0])
                file_month = int(parts[1])
                
                # 필터링 조건 확인
                if year is not None and file_year != year:
                    continue
                if month is not None and file_month != month:
                    continue
                
                filtered_files.append(file_path)
        except (ValueError, IndexError):
            # 날짜 파싱 실패한 파일은 제외
            continue
    
    return sorted(filtered_files)


def bulk_ingest_daily_reports(year: Optional[int] = None, month: Optional[int] = None):
    """
    메인 함수: 일일보고서를 DB에 저장
    
    Args:
        year: 필터링할 연도 (None이면 모든 연도)
        month: 필터링할 월 (None이면 모든 월, 예: 11 = 11월)
    """
    print("=" * 70)
    print("📊 일일보고서 Bulk Ingestion 시작")
    if year or month:
        filter_msg = []
        if year:
            filter_msg.append(f"{year}년")
        if month:
            filter_msg.append(f"{month}월")
        print(f"필터: {' '.join(filter_msg)}")
    print("=" * 70)
    
    # 1. 기본 경로 설정
    base_dir = backend_dir / "Data" / "mock_reports" / "daily"
    
    if not base_dir.exists():
        print(f"❌ 디렉토리가 존재하지 않습니다: {base_dir}")
        return
    
    print(f"\n📁 대상 디렉토리: {base_dir}")
    
    # 2. txt 파일 찾기 (날짜 필터링 적용)
    txt_files = find_all_txt_files(base_dir, year=year, month=month)
    print(f"📄 발견된 txt 파일: {len(txt_files)}개")
    if year or month:
        print(f"   (필터: {year or '모든 연도'}년 {month or '모든 월'}월)")
    
    if not txt_files:
        print("⚠️  txt 파일이 없습니다.")
        return
    
    # 3. DB 세션 생성
    db = SessionLocal()
    
    # 통계
    total_reports = 0
    created_count = 0
    updated_count = 0
    error_count = 0
    
    try:
        # 4. 각 파일 처리
        for file_path in txt_files:
            print(f"\n📖 처리 중: {file_path.relative_to(base_dir)}")
            
            # 4-1. 파일에서 JSON 객체들 읽기
            json_objects = read_json_objects_from_file(file_path)
            print(f"   ├─ JSON 객체 수: {len(json_objects)}개")
            
            # 4-2. 각 JSON 객체를 CanonicalReport로 변환 후 DB 저장
            for idx, json_obj in enumerate(json_objects, 1):
                try:
                    # CanonicalReport 변환
                    canonical_report = convert_to_canonical_report(json_obj)
                    
                    # DB 저장 (UPSERT)
                    report_dict = canonical_report.model_dump(mode='json')
                    report_create = DailyReportCreate(
                        owner=canonical_report.owner,
                        report_date=canonical_report.period_start,
                        report_json=report_dict
                    )
                    
                    db_report, is_created = DailyReportRepository.create_or_update(
                        db, report_create
                    )
                    
                    total_reports += 1
                    if is_created:
                        created_count += 1
                        action = "생성"
                    else:
                        updated_count += 1
                        action = "업데이트"
                    
                    print(f"   ├─ [{idx}/{len(json_objects)}] {canonical_report.owner} - {canonical_report.period_start} ({action})")
                
                except Exception as e:
                    error_count += 1
                    print(f"   ├─ ❌ [{idx}/{len(json_objects)}] 처리 실패: {e}")
                    continue
        
        # 5. 결과 출력
        print(f"\n{'=' * 70}")
        print(f"✅ Bulk Ingestion 완료!")
        print(f"{'=' * 70}")
        print(f"📊 처리 결과:")
        print(f"   ├─ 총 보고서 수: {total_reports}개")
        print(f"   ├─ 생성: {created_count}개")
        print(f"   ├─ 업데이트: {updated_count}개")
        print(f"   └─ 에러: {error_count}개")
        
        # 6. DB 확인
        print(f"\n🔍 DB 확인:")
        from app.domain.report.daily.models import DailyReport
        kim_reports = db.query(DailyReport).filter(
            DailyReport.owner == "김보험"
        ).count()
        print(f"   └─ '김보험'의 일일보고서: {kim_reports}개")
        
    except Exception as e:
        print(f"\n❌ 예상치 못한 에러: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
        print(f"\n{'=' * 70}")


if __name__ == "__main__":
    # 모든 목업 데이터를 PostgreSQL에 저장
    bulk_ingest_daily_reports()

