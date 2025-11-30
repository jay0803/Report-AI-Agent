# Activity Monitor Module

사용자의 마우스/키보드 입력을 감지하여 **Idle 상태**와 **장시간 활동**을 탐지하는 모듈입니다.

## 📁 파일 구조

```
renderer/activity-monitor/
├── activityMonitor.js  # 핵심 로직
├── index.js            # Public API
└── README.md           # 이 문서
```

---

## 🎯 주요 기능

### 1. **Idle 감지**
- 마우스/키보드 입력이 일정 시간 이상 없을 때 감지
- `onIdle()` 콜백 호출
- 사용 예: "조금 쉬고 계신가요?" 메시지 표시

### 2. **장시간 활동 감지**
- 짧은 휴식을 끼고 오래 활동할 때 감지
- `onLongActive()` 콜백 호출
- 사용 예: "스트레칭 어때요?" 알림

---

## ⚙️ 모드별 설정

### Dev 모드 (테스트용)
```javascript
mode: 'dev'
```
- **Idle 기준**: 3초
- **장시간 활동 기준**: 10초
- **체크 간격**: 1초

### Prod 모드 (실제 사용)
```javascript
mode: 'prod'
```
- **Idle 기준**: 5분 (300초)
- **장시간 활동 기준**: 50분 (3000초)
- **체크 간격**: 2초

---

## 📖 사용 방법

### 기본 사용

```javascript
import { setupActivityMonitor } from './renderer/activity-monitor/index.js';

const cleanup = setupActivityMonitor({
  mode: 'dev', // 또는 'prod'
  
  onIdle: () => {
    console.log('😴 사용자가 쉬고 있습니다');
    // 원하는 동작 구현
  },
  
  onLongActive: () => {
    console.log('⏰ 장시간 활동 감지!');
    // 원하는 동작 구현
  }
});

// 정리가 필요할 때 (예: 컴포넌트 unmount)
cleanup();
```

---

## 🎭 캐릭터 모션 연동 예시

### index.html에서 사용 (현재 구현됨)

```javascript
setupActivityMonitor({
  mode: 'dev',
  
  onIdle: () => {
    // 캐릭터 Idle 모션 재생
    if (model) {
      model.motion('Idle');
    }
    
    // 채팅창에 메시지 추가
    addMessage('assistant', '조금 쉬고 계신가요? 😊');
  },
  
  onLongActive: () => {
    // 캐릭터 특별 모션 재생
    if (model) {
      model.motion('Tap@Body');
    }
    
    // 채팅창에 알림 메시지
    addMessage('assistant', '오래 일하셨네요! 잠깐 스트레칭 어때요? 🤸‍♀️');
  }
});
```

---

## 🔧 감지되는 이벤트

다음 window 이벤트들을 감지합니다:
- `mousemove` - 마우스 이동
- `mousedown` - 마우스 클릭
- `wheel` - 마우스 휠
- `keydown` - 키보드 입력

---

## 🧪 테스트 방법

### Dev 모드 테스트

1. 모드를 `'dev'`로 설정
2. 앱 실행
3. **3초 동안 아무 입력 안 함** → Idle 콜백 실행 확인
4. 다시 입력 시작
5. **10초 동안 계속 입력** → 장시간 활동 콜백 실행 확인

콘솔 출력 예시:
```
🔍 Activity Monitor 시작 (dev 모드)
   - Idle 기준: 3초
   - 장시간 활동 기준: 10초
👂 입력 이벤트 리스너 등록 완료
⏱️  장시간 활동까지 9.0초 남음
⏱️  장시간 활동까지 8.0초 남음
...
⏰ 장시간 활동 감지 (10초)
```

### Prod 모드 테스트

1. 모드를 `'prod'`로 변경
2. **5분 동안 입력 없음** → Idle 콜백 실행
3. **5분 미만의 짧은 휴식을 끼고 50분 활동** → 장시간 활동 콜백 실행

---

## 🎨 커스터마이징

### 기준 시간 변경

`activityMonitor.js`의 `CONFIG` 객체 수정:

```javascript
const CONFIG = {
  dev: {
    idleThresholdMs: 5 * 1000,        // 5초로 변경
    longActiveThresholdMs: 20 * 1000, // 20초로 변경
    checkIntervalMs: 1000,
  },
  prod: {
    idleThresholdMs: 10 * 60 * 1000,     // 10분으로 변경
    longActiveThresholdMs: 60 * 60 * 1000, // 1시간으로 변경
    checkIntervalMs: 2000,
  }
};
```

### 추가 이벤트 감지

`activityMonitor.js`의 `events` 배열 수정:

```javascript
const events = [
  'mousemove', 
  'mousedown', 
  'wheel', 
  'keydown',
  'touchstart',  // 터치 이벤트 추가
  'touchmove'
];
```

---

## 🚫 제한사항

이 모듈은 **순수 입력 감지 모듈**입니다. 다음 기능은 포함하지 않습니다:

- ❌ 화면 캡처
- ❌ 활성 창 이름 읽기
- ❌ RAG/Agent 호출
- ❌ Vision API 사용

이러한 기능이 필요하면 `onIdle` / `onLongActive` 콜백에서 별도로 구현하세요.

---

## 🐛 디버깅

### 콘솔 로그 확인

Dev 모드에서는 다음과 같은 로그가 출력됩니다:

```
🔍 Activity Monitor 시작 (dev 모드)
👂 입력 이벤트 리스너 등록 완료
⏱️  장시간 활동까지 5.0초 남음
✅ 활동 재개 - 새 세션 시작
😴 Idle 상태 진입 (3초 동안 입력 없음)
⏰ 장시간 활동 감지 (10초)
```

### 문제 해결

**콜백이 호출되지 않음**
- 모드 설정 확인 (`'dev'` 또는 `'prod'`)
- 콘솔에서 이벤트 리스너 등록 로그 확인
- 타이머가 제대로 시작되었는지 확인

**모션이 재생되지 않음**
- `model` 객체가 준비되었는지 확인
- 콘솔에서 모션 재생 로그 확인
- Live2D 모델에 해당 모션이 있는지 확인

---

## 📝 TODO

- [ ] TypeScript 버전 작성 (현재 JavaScript)
- [ ] React 환경용 Hook 버전 (`useActivityMonitor`)
- [ ] 설정 저장/불러오기 기능
- [ ] 통계 기능 (총 활동 시간, Idle 횟수 등)

---

## 📄 라이선스

프로젝트 라이선스를 따릅니다.

