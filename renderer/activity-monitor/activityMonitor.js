/**
 * Activity Monitor Module
 * 사용자의 마우스/키보드 입력을 감지하여 Idle 및 장시간 활동을 탐지합니다.
 * 
 * 주요 기능:
 * - Idle 감지: 일정 시간 이상 입력이 없을 때
 * - 장시간 활동 감지: 일정 시간 이상 연속으로 활동할 때
 * - 모드별 설정: dev(테스트용), prod(실제 사용)
 */

// ============================================
// 설정 상수
// ============================================
const CONFIG = {
  dev: {
    idleThresholdMs: 3 * 1000,        // 3초 - Idle 판단 기준
    longActiveThresholdMs: 10 * 1000, // 10초 - 장시간 활동 기준
    checkIntervalMs: 1000,             // 1초마다 체크
  },
  prod: {
    idleThresholdMs: 5 * 60 * 1000,      // 5분 - Idle 판단 기준
    longActiveThresholdMs: 50 * 60 * 1000, // 50분 - 장시간 활동 기준
    checkIntervalMs: 2000,                  // 2초마다 체크
  }
};

/**
 * Activity Monitor 설정 및 시작
 * 
 * @param {Object} options - 설정 옵션
 * @param {'dev' | 'prod'} options.mode - 동작 모드
 * @param {Function} options.onIdle - Idle 상태 진입 시 콜백
 * @param {Function} options.onLongActive - 장시간 활동 감지 시 콜백
 * @returns {Function} cleanup 함수 (이벤트 리스너 및 타이머 정리용)
 */
export function setupActivityMonitor(options) {
  // ============================================
  // 옵션 검증
  // ============================================
  const { mode, onIdle, onLongActive } = options;
  
  if (!['dev', 'prod'].includes(mode)) {
    throw new Error('mode must be "dev" or "prod"');
  }
  
  if (typeof onIdle !== 'function') {
    throw new Error('onIdle must be a function');
  }
  
  if (typeof onLongActive !== 'function') {
    throw new Error('onLongActive must be a function');
  }
  
  // 현재 모드의 설정 가져오기
  const config = CONFIG[mode];
  
  console.log(`🔍 Activity Monitor 시작 (${mode} 모드)`);
  console.log(`   - Idle 기준: ${config.idleThresholdMs / 1000}초`);
  console.log(`   - 장시간 활동 기준: ${config.longActiveThresholdMs / 1000}초`);
  
  // ============================================
  // 내부 상태 변수
  // ============================================
  let lastInputAt = Date.now();           // 마지막 입력 시각
  let sessionStartAt = Date.now();        // 현재 활동 세션 시작 시각
  let isIdle = false;                     // 현재 Idle 상태인지 여부
  let hasNotifiedLongActive = false;      // 장시간 활동 알림을 이미 보냈는지 여부
  let checkTimer = null;                  // 주기적 체크 타이머
  
  // ============================================
  // 입력 이벤트 핸들러
  // ============================================
  function handleUserInput() {
    const now = Date.now();
    lastInputAt = now;
    
    // Idle 상태에서 벗어남 → 새 세션 시작
    if (isIdle) {
      console.log('✅ 활동 재개 - 새 세션 시작');
      isIdle = false;
      sessionStartAt = now;
      hasNotifiedLongActive = false;
    }
  }
  
  // ============================================
  // 주기적 체크 로직
  // ============================================
  function checkActivity() {
    const now = Date.now();
    const timeSinceLastInput = now - lastInputAt;
    const currentSessionDuration = now - sessionStartAt;
    
    // ------------------------
    // 1. Idle 상태 체크
    // ------------------------
    if (!isIdle && timeSinceLastInput >= config.idleThresholdMs) {
      // Idle 상태로 전환
      isIdle = true;
      console.log(`😴 Idle 상태 진입 (${timeSinceLastInput / 1000}초 동안 입력 없음)`);
      
      // Idle 콜백 호출
      try {
        onIdle();
      } catch (error) {
        console.error('❌ onIdle 콜백 실행 중 오류:', error);
      }
      
      // 세션 리셋 (Idle 상태에서는 세션 종료)
      sessionStartAt = now;
      hasNotifiedLongActive = false;
      
      return; // Idle 상태에서는 장시간 활동 체크 안 함
    }
    
    // ------------------------
    // 2. 장시간 활동 체크 (Idle이 아닐 때만)
    // ------------------------
    if (!isIdle && !hasNotifiedLongActive) {
      if (currentSessionDuration >= config.longActiveThresholdMs) {
        hasNotifiedLongActive = true;
        console.log(`⏰ 장시간 활동 감지 (${currentSessionDuration / 1000}초)`);
        
        // 장시간 활동 콜백 호출
        try {
          onLongActive();
        } catch (error) {
          console.error('❌ onLongActive 콜백 실행 중 오류:', error);
        }
      }
    }
    
    // 디버깅용 로그 (dev 모드에서만)
    if (mode === 'dev' && !isIdle) {
      const remaining = (config.longActiveThresholdMs - currentSessionDuration) / 1000;
      if (remaining > 0) {
        console.log(`⏱️  장시간 활동까지 ${remaining.toFixed(1)}초 남음`);
      }
    }
  }
  
  // ============================================
  // 이벤트 리스너 등록
  // ============================================
  const events = ['mousemove', 'mousedown', 'wheel', 'keydown'];
  
  events.forEach(eventType => {
    window.addEventListener(eventType, handleUserInput, { passive: true });
  });
  
  console.log('👂 입력 이벤트 리스너 등록 완료:', events.join(', '));
  
  // ============================================
  // 주기적 체크 타이머 시작
  // ============================================
  checkTimer = setInterval(checkActivity, config.checkIntervalMs);
  console.log(`⏲️  ${config.checkIntervalMs}ms 간격으로 체크 시작`);
  
  // ============================================
  // Cleanup 함수 반환
  // ============================================
  return function cleanup() {
    console.log('🧹 Activity Monitor 정리 중...');
    
    // 이벤트 리스너 제거
    events.forEach(eventType => {
      window.removeEventListener(eventType, handleUserInput);
    });
    
    // 타이머 정리
    if (checkTimer) {
      clearInterval(checkTimer);
      checkTimer = null;
    }
    
    console.log('✅ Activity Monitor 정리 완료');
  };
}

/**
 * 현재 활동 상태 가져오기 (디버깅용)
 * @returns {Object} 현재 상태 정보
 */
export function getActivityStatus() {
  return {
    timestamp: Date.now(),
    message: 'Activity Monitor is running'
  };
}

