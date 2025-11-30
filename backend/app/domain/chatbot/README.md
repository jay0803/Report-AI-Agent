# 채팅봇 모듈

사용자와의 대화형 인터랙션을 처리하는 AI 채팅봇 모듈입니다.

## 📁 구조

```
chatbot/
├── __init__.py             # 모듈 초기화
├── session_manager.py      # 세션 및 대화 히스토리 관리 (deque)
├── memory_manager.py       # MD 파일 저장/읽기
├── summarizer.py           # 대화 요약 생성 (LLM)
├── service.py              # 채팅 로직 (OpenAI API 호출)
├── schemas.py              # Pydantic 스키마 (FastAPI 연동용)
├── test_console.py         # 콘솔 테스트 스크립트
├── data/
│   └── sessions/           # 세션별 데이터 (Git 제외)
│       └── {session_id}/
│           ├── history.md   # 전체 대화 백업
│           └── summary.md   # 구조화된 요약
└── README.md               # 이 파일
```

## 🎯 주요 기능

### 1. **세션 관리**
- 사용자별 독립적인 채팅 세션
- 세션당 최대 15개 메시지 유지 (FIFO)
- 스레드 안전한 동시성 처리

### 2. **대화 히스토리 (Tiered Memory)**
- **Short-term (deque):** 최근 15개 대화 유지
- **Long-term (MD 파일):** 16번째부터 자동 백업
- **요약 (summary.md):** 구조화된 요약 생성 및 활용
- 오래된 대화도 요약을 통해 맥락 유지 가능

### 3. **AI 대화**
- OpenAI GPT-4 기반 자연어 대화
- 맥락 있는 응답 (이전 대화 기억)
- 시스템 프롬프트로 페르소나 정의

### 4. **확장 가능한 구조**
- RAG 통합을 위한 플러그인 구조 (추후)
- FastAPI 엔드포인트 추가 용이
- Pydantic 스키마 준비 완료

### 5. **Tiered Memory (계층적 메모리) ✨**
- **실시간 메모리:** 최근 15개 대화 (deque)
- **장기 저장:** 16번째부터 MD 파일 자동 백업
- **요약 활용:** LLM이 요약을 참고하여 맥락 유지
- **비용 효율:** 요약만 LLM에 전달 (~200 토큰)

## 🚀 사용법

### 1. 콘솔 테스트

```bash
# 백엔드 폴더에서 가상환경 활성화
cd backend
source venv/bin/activate  # Mac/Linux
# 또는
.\venv\Scripts\Activate.ps1  # Windows

# 채팅봇 테스트 실행
cd app/domain/chatbot
python test_console.py
```

### 2. 명령어

콘솔 테스트 중 사용 가능한 명령어:

- `/new` - 새로운 세션 시작
- `/history` - 현재 세션의 대화 히스토리 보기
- `/info` - 세션 정보 조회 (생성 시간, 메시지 수 등)
- `/help` - 도움말 표시
- `/exit` - 종료

### 3. Python 코드에서 사용

```python
from app.domain.chatbot.service import ChatService

# 서비스 초기화
chat_service = ChatService()

# 세션 생성
session_id = chat_service.create_session()

# 메시지 전송 및 응답 받기
response = chat_service.process_message(session_id, "안녕하세요!")
print(response)

# 대화 히스토리 조회
history = chat_service.get_session_history(session_id)
print(history)

# 세션 정보 조회
info = chat_service.get_session_info(session_id)
print(info)

# 세션 삭제
chat_service.delete_session(session_id)
```

## 🔧 환경 변수

`.env` 파일에 다음 변수가 필요합니다:

```env
# OpenAI API (필수)
OPENAI_API_KEY=your_openai_api_key_here

# LLM 모델 (선택사항, 기본값: gpt-4o)
LLM_MODEL=gpt-4o

# 대화 히스토리 크기 (선택사항, 기본값: 15)
# 권장: 회사 챗봇 12~15, 고객 상담 15~20, 개인 비서 20+
CHAT_HISTORY_SIZE=15
```

## 📊 데이터 구조

### 대화 히스토리 (deque)

```python
[
    {
        "role": "user",
        "content": "안녕하세요!",
        "timestamp": "2025-11-20T10:30:00"
    },
    {
        "role": "assistant",
        "content": "안녕하세요! 무엇을 도와드릴까요?",
        "timestamp": "2025-11-20T10:30:02"
    }
]
```

### 세션 메타데이터

```python
{
    "created_at": "2025-11-20T10:30:00",
    "last_activity": "2025-11-20T10:35:00",
    "message_count": 10,
    "current_message_count": 10  # 최대 20개
}
```

## 🎯 **동작 흐름**

### **대화 1~15:** 정상 작동
```
사용자 메시지 → deque에 저장 (실시간)
LLM 호출: 시스템 프롬프트 + 최근 15개
```

### **대화 16:** 백업 & 요약 시작
```
1. 가장 오래된 대화(1번) → history.md에 저장
2. 전체 대화 요약 → summary.md 생성
3. 사용자 메시지 추가 (deque에서 1번 자동 삭제)
4. LLM 호출: 시스템 프롬프트 + 요약 + 최근 15개
```

### **대화 17+:** 지속적 관리
```
- 매번 가장 오래된 대화 → MD 저장
- 주기적으로 요약 업데이트
- LLM은 항상 요약 + 최근 15개만 참고
```

---

## 🔮 추후 확장 계획

### 1. FastAPI 엔드포인트 추가

```python
# backend/app/api/v1/endpoints/chatbot.py
from fastapi import APIRouter
from app.domain.chatbot.service import ChatService

router = APIRouter()
chat_service = ChatService()

@router.post("/chat")
async def chat(request: ChatRequest):
    response = await chat_service.process_message(
        request.session_id,
        request.message
    )
    return {"message": response}
```

### 3. 프론트엔드 연결

```javascript
// renderer/chat/chatService.js
async function sendChatMessage(userText) {
    const response = await fetch('/api/v1/chatbot/chat', {
        method: 'POST',
        body: JSON.stringify({
            session_id: sessionId,
            message: userText
        })
    });
    return await response.json();
}
```

## 🧪 테스트 시나리오

1. **기본 대화**
   - "안녕하세요" → 인사 응답 확인
   - "오늘 날씨 어때?" → 일반 대화 응답 확인

2. **맥락 유지**
   - "내 이름은 철수야" → 정보 저장
   - "내 이름이 뭐야?" → 기억 확인

3. **히스토리 제한**
   - 21개 이상 메시지 전송 → 오래된 것 삭제 확인
   - `/history`로 최대 20개만 유지되는지 확인

4. **세션 관리**
   - `/new`로 새 세션 → 이전 대화 기억 안 함 확인
   - 여러 세션 동시 생성 → 세션별 독립성 확인

## 📝 참고사항

- 대화 히스토리는 **메모리에만 저장**됩니다 (재시작 시 초기화)
- 영구 저장이 필요한 경우 Redis/PostgreSQL 연동 필요
- 동시성은 `threading.Lock`으로 처리 (싱글톤 패턴)
- Temperature는 기본 0.7 (조절 가능)

