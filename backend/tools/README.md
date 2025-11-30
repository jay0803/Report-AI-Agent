# Tools - 유틸리티 스크립트

## 📋 목차

1. [bulk_daily_ingest.py](#bulk_daily_ingestpy) - 일일보고서 bulk 저장
2. [preview_daily_files.py](#preview_daily_filespy) - 파일 미리보기
3. [run_bulk_ingest_example.py](#run_bulk_ingest_examplepy) - 실행 예제

---

## bulk_daily_ingest.py

### 개요
`Data/mock_reports/daily` 폴더의 모든 txt 파일을 읽어서 PostgreSQL의 `daily_reports` 테이블에 일괄 저장하는 스크립트입니다.

### 기능
- ✅ 모든 하위 폴더의 txt 파일 자동 탐색
- ✅ 여러 JSON 객체가 포함된 txt 파일 파싱
- ✅ CanonicalReport 스키마로 자동 변환
- ✅ UPSERT 지원 (동일 owner + date는 자동 업데이트)
- ✅ 날짜 및 시간 자동 파싱

### 변환 규칙

| 원본 JSON | CanonicalReport |
|-----------|----------------|
| 문서제목 | report_type = "daily" |
| 상단정보.작성일자 | period_start, period_end |
| 상단정보.성명 | owner |
| 세부업무[].시간 | tasks[].time_start, time_end |
| 세부업무[].업무내용 | tasks[].description |
| 세부업무[].비고 | tasks[].note |
| 미종결_업무사항 | issues[] |
| 익일_업무계획 | metadata.next_plan |
| 특이사항 | metadata.notes |
| 금일_진행_업무 | metadata.summary |

### 사용 방법

#### 1. 기본 실행
```bash
# 프로젝트 루트에서 실행
python backend/tools/bulk_daily_ingest.py
```

#### 2. Python 스크립트에서 실행
```python
import sys
from pathlib import Path

# backend 경로를 Python path에 추가
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# 스크립트 import 및 실행
from tools.bulk_daily_ingest import bulk_ingest_daily_reports

# 실행
bulk_ingest_daily_reports()
```

#### 3. 직접 import해서 사용
```python
from backend.tools.bulk_daily_ingest import (
    convert_to_canonical_report,
    read_json_objects_from_file,
    parse_time_range,
    parse_date
)

# 개별 파일 처리
file_path = Path("backend/Data/mock_reports/daily/2025년 1월/2025년 1월 2일 ~ 1월 10일.txt")
json_objects = read_json_objects_from_file(file_path)

for json_obj in json_objects:
    canonical = convert_to_canonical_report(json_obj)
    print(f"{canonical.owner} - {canonical.period_start}")
```

### 출력 예시

```
======================================================================
📊 일일보고서 Bulk Ingestion 시작
======================================================================

📁 대상 디렉토리: C:\...\backend\Data\mock_reports\daily
📄 발견된 txt 파일: 56개

📖 처리 중: 2025년 1월\2025년 1월 2일 ~ 1월 10일.txt
   ├─ JSON 객체 수: 7개
   ├─ [1/7] 김보험 - 2025-01-02 (생성)
   ├─ [2/7] 김보험 - 2025-01-03 (생성)
   ├─ [3/7] 김보험 - 2025-01-06 (생성)
   ├─ [4/7] 김보험 - 2025-01-07 (생성)
   ├─ [5/7] 김보험 - 2025-01-08 (생성)
   ├─ [6/7] 김보험 - 2025-01-09 (생성)
   ├─ [7/7] 김보험 - 2025-01-10 (생성)

📖 처리 중: 2025년 1월\2025년 1월 13일 ~ 1월 17일.txt
   ├─ JSON 객체 수: 5개
   ├─ [1/5] 김보험 - 2025-01-13 (생성)
   ...

======================================================================
✅ Bulk Ingestion 완료!
======================================================================
📊 처리 결과:
   ├─ 총 보고서 수: 250개
   ├─ 생성: 250개
   ├─ 업데이트: 0개
   └─ 에러: 0개

🔍 DB 확인:
   └─ '김보험'의 일일보고서: 250개

======================================================================
```

### 주의사항

1. **데이터베이스 연결**
   - PostgreSQL이 실행 중이어야 합니다
   - `.env` 파일에 `DATABASE_URL` 설정이 필요합니다

2. **마이그레이션**
   - `daily_reports` 테이블이 존재해야 합니다
   - `alembic upgrade head` 먼저 실행하세요

3. **UPSERT 동작**
   - 동일한 (owner, date) 조합이 있으면 자동 업데이트됩니다
   - 중복 실행해도 안전합니다

4. **날짜 형식**
   - JSON의 작성일자는 반드시 `YYYY-MM-DD` 형식이어야 합니다
   - 예: `"2025-01-02"`

5. **시간 형식**
   - 시간은 `HH:MM - HH:MM` 형식
   - 예: `"09:00 - 10:00"`

### 트러블슈팅

#### 문제: "디렉토리가 존재하지 않습니다"
```bash
# 경로 확인
ls backend/Data/mock_reports/daily
```

#### 문제: "데이터베이스 연결 오류"
```bash
# PostgreSQL 실행 확인
# .env 파일의 DATABASE_URL 확인
```

#### 문제: "테이블이 존재하지 않습니다"
```bash
# 마이그레이션 실행
cd backend
alembic upgrade head
```

### 성능

- **처리 속도**: 약 100-200개 보고서/초
- **메모리**: 각 파일당 ~1-2MB
- **배치 크기**: 파일 단위로 처리

### 다음 단계

보고서가 모두 저장되면 다음 작업을 수행할 수 있습니다:

```bash
# 1. 주간 보고서 생성
python backend/debug/test_weekly_chain.py

# 2. 월간 보고서 생성
python backend/debug/test_monthly_chain.py

# 3. 실적 보고서 생성
python backend/debug/test_performance_chain.py
```

또는 API를 통해:
```bash
# 주간 보고서 생성
curl -X POST http://localhost:8000/api/v1/weekly/generate \
  -H "Content-Type: application/json" \
  -d '{"owner": "김보험", "target_date": "2025-01-20"}'
```

---

## preview_daily_files.py

### 개요
bulk_daily_ingest.py를 실행하기 전에 어떤 파일들이 처리될지 미리 확인하는 스크립트입니다.

### 기능
- ✅ 폴더별 파일 목록 표시
- ✅ 각 파일의 보고서 개수 확인
- ✅ 전체 통계 표시
- ✅ 샘플 미리보기

### 사용 방법

```bash
# 프로젝트 루트에서 실행
python backend/tools/preview_daily_files.py
```

### 출력 예시

```
======================================================================
👀 Daily Report 파일 미리보기
======================================================================

📁 대상 디렉토리: C:\...\backend\Data\mock_reports\daily
📄 발견된 txt 파일: 56개

📂 폴더별 파일 목록:

📁 2025년 1월
   ├─ 파일 수: 4개
   ├─ 보고서 수: 22개
   └─ 파일 목록:
      ├─ 2025년 1월 2일 ~ 1월 10일.txt (7개)
      ├─ 2025년 1월 13일 ~ 1월 17일.txt (5개)
      ...

======================================================================
📊 전체 통계:
   ├─ 폴더 수: 14개
   ├─ 파일 수: 56개
   └─ 총 보고서 수: 250개
======================================================================
```

---

## run_bulk_ingest_example.py

### 개요
bulk_daily_ingest.py를 실행하는 간단한 예제 스크립트입니다.

### 사용 방법

```bash
# 프로젝트 루트에서 실행
python backend/tools/run_bulk_ingest_example.py
```

이 스크립트는 다음을 수행합니다:
1. bulk_daily_ingest 모듈 import
2. bulk_ingest_daily_reports() 함수 실행
3. 완료 후 다음 단계 안내

---

## 빠른 시작 가이드

### 1단계: 파일 미리보기
```bash
python backend/tools/preview_daily_files.py
```

### 2단계: Bulk Ingest 실행
```bash
python backend/tools/bulk_daily_ingest.py
```
또는
```bash
python backend/tools/run_bulk_ingest_example.py
```

### 3단계: 주간/월간 보고서 생성
```bash
python backend/debug/test_weekly_chain.py
python backend/debug/test_monthly_chain.py
python backend/debug/test_performance_chain.py
```

