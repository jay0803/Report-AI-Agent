# Report AI Agent Backend

## 폴더 구조

```
backend/
├── app/                    # 메인 애플리케이션 코드
│   ├── api/               # API 엔드포인트
│   ├── core/              # 핵심 설정 및 보안
│   ├── domain/            # 도메인 로직
│   ├── infrastructure/    # 인프라스트럭처 (DB, Vector Store)
│   ├── llm/               # LLM 클라이언트
│   ├── reporting/         # PDF 생성 등 리포트 관련
│   └── services/          # 서비스 레이어
├── alembic/               # 데이터베이스 마이그레이션
├── ingestion/             # 데이터 수집 및 임베딩 파이프라인
├── scripts/               # 유틸리티 스크립트
│   └── utils/            # 디버깅 및 체크 스크립트
├── tests/                 # 테스트 파일
├── tools/                 # 도구 스크립트 (bulk ingest 등)
├── Data/                  # 데이터 파일 (ChromaDB, PDF 등)
└── output/                # 출력 파일 (PDF, JSON 등)
```

## 주요 디렉토리 설명

- **app/**: FastAPI 애플리케이션의 메인 코드
- **ingestion/**: 보고서 데이터를 ChromaDB에 수집하는 파이프라인
- **scripts/**: 개발 및 운영에 필요한 유틸리티 스크립트
- **tests/**: API 및 벡터DB 테스트
- **tools/**: 대량 데이터 처리 도구

