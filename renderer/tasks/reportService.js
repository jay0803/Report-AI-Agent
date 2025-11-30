/**
 * 일일보고서 서비스
 * 일일보고서 FSM 관련 기능
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

// 보고서 상태 관리
let chatMode = 'normal'; // 'normal' 또는 'daily_fsm'
let dailySessionId = null;
let dailyOwner = '김보험'; // TODO: 실제 로그인 사용자로 변경

/**
 * 일일보고서 입력 트리거 감지
 * @param {string} text - 사용자 입력 텍스트
 * @returns {boolean}
 */
export function isDailyStartTrigger(text) {
  const t = text.replace(/\s+/g, '').toLowerCase();
  return (
    t.includes('일일보고서입력할래') ||
    t.includes('일일보고서작성할래') ||
    t.includes('오늘보고서입력') ||
    t.includes('일일보고서입력') ||
    t.includes('보고서작성할래')
  );
}

/**
 * 일일보고서 FSM 시작
 * @param {Function} addMessage - 메시지 추가 함수
 * @param {HTMLElement} chatInput - 채팅 입력 요소
 * @returns {Promise<void>}
 */
export async function handleDailyStart(addMessage, chatInput) {
  console.log('📝 일일보고서 FSM 시작...');
  
  try {
    const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
    
    const response = await fetch(`${API_BASE_URL}/daily/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        owner: dailyOwner,
        target_date: today
      })
    });
    
    if (!response.ok) {
      throw new Error(`API 호출 실패: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('✅ FSM 시작 완료:', result);
    
    // FSM 모드로 전환
    chatMode = 'daily_fsm';
    dailySessionId = result.session_id;
    
    // Placeholder 변경
    if (chatInput) {
      chatInput.placeholder = '해당 시간대에 했던 업무를 자유롭게 적어주세요...';
    }
    
    // 첫 질문 출력
    addMessage('assistant', result.question);
    
  } catch (error) {
    console.error('❌ FSM 시작 오류:', error);
    addMessage('assistant', '일일보고서를 시작하는 중 오류가 발생했습니다. 😢');
  }
}

/**
 * 일일보고서 FSM 답변 처리
 * @param {string} answer - 사용자 답변
 * @param {Function} addMessage - 메시지 추가 함수
 * @param {HTMLElement} chatInput - 채팅 입력 요소
 * @returns {Promise<void>}
 */
export async function handleDailyAnswer(answer, addMessage, chatInput) {
  console.log('📝 FSM 답변 전송:', answer);
  
  try {
    const response = await fetch(`${API_BASE_URL}/daily/answer`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: dailySessionId,
        answer: answer
      })
    });
    
    if (!response.ok) {
      throw new Error(`API 호출 실패: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('✅ FSM 답변 처리 완료:', result);
    
    if (result.status === 'finished') {
      // 완료 처리
      addMessage('assistant', result.message || '일일보고서 작성이 완료되었습니다! 🙌');
      
      // 보고서 요약 출력
      if (result.report && result.report.tasks) {
        addReportSummary(result.report, addMessage);
      }
      
      // 모드 초기화
      chatMode = 'normal';
      dailySessionId = null;
      if (chatInput) {
        chatInput.placeholder = '메시지를 입력하세요...';
      }
      
    } else {
      // 다음 질문 출력
      addMessage('assistant', result.question);
    }
    
  } catch (error) {
    console.error('❌ FSM 답변 오류:', error);
    addMessage('assistant', '답변 처리 중 오류가 발생했습니다. 😢');
  }
}

/**
 * 보고서 요약 출력
 * @param {Object} report - 보고서 객체
 * @param {Function} addMessage - 메시지 추가 함수
 */
function addReportSummary(report, addMessage) {
  const summaryLines = [];
  
  // 📋 예정 업무 (plans)
  if (report.plans && report.plans.length > 0) {
    summaryLines.push('📋 오늘 예정했던 업무:');
    report.plans.forEach((plan, index) => {
      summaryLines.push(`  ${index + 1}. ${plan}`);
    });
    summaryLines.push('');
  }
  
  // ✅ 실제 완료 업무 (tasks)
  if (report.tasks && report.tasks.length > 0) {
    summaryLines.push('✅ 실제 완료한 업무:');
    const tasks = report.tasks.slice(0, 5);
    tasks.forEach((task, index) => {
      const timeInfo = task.time_start && task.time_end ? ` (${task.time_start}~${task.time_end})` : '';
      summaryLines.push(`  ${index + 1}. ${task.title}${timeInfo}`);
    });
    if (report.tasks.length > 5) {
      summaryLines.push(`  ... 외 ${report.tasks.length - 5}개 업무`);
    }
    summaryLines.push('');
  }
  
  // ⚠️ 미종결 업무 (issues)
  if (report.issues && report.issues.length > 0) {
    summaryLines.push('⚠️ 미종결 업무:');
    report.issues.forEach((issue, index) => {
      summaryLines.push(`  ${index + 1}. ${issue}`);
    });
    summaryLines.push('');
  }
  
  // 📈 완료율
  const metadata = report.metadata || {};
  if (metadata.completion_rate) {
    summaryLines.push(`📈 예정 업무 완료율: ${metadata.completion_rate}`);
  }
  
  const summaryText = summaryLines.join('\n');
  addMessage('assistant', summaryText);
}

/**
 * 현재 채팅 모드 가져오기
 * @returns {string}
 */
export function getChatMode() {
  return chatMode;
}

/**
 * 채팅 모드 설정
 * @param {string} mode - 모드 ('normal' 또는 'daily_fsm')
 */
export function setChatMode(mode) {
  chatMode = mode;
}

/**
 * 일일보고서 소유자 설정
 * @param {string} owner - 소유자 이름
 */
export function setDailyOwner(owner) {
  dailyOwner = owner;
}

