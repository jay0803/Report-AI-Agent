/**
 * 채팅 서비스 모듈
 * 백엔드 API 호출을 담당
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

// 세션 ID 및 토큰 저장
let sessionId = null;
let accessToken = null;

/**
 * 액세스 토큰 설정
 * @param {string} token - JWT 액세스 토큰
 */
export function setAccessToken(token) {
  accessToken = token;
  }

/**
 * 세션 초기화
 */
async function initSession() {
  if (sessionId) return sessionId;
  
  try {
    const headers = {
      'Content-Type': 'application/json',
    };
    
    // 토큰이 있으면 Authorization 헤더 추가
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }
    
    const response = await fetch(`${API_BASE_URL}/chatbot/session`, {
      method: 'POST',
      headers: headers
    });
    
    if (!response.ok) {
      throw new Error(`세션 생성 실패: ${response.status}`);
    }
    
    const result = await response.json();
    sessionId = result.session_id;
        return sessionId;
  } catch (error) {
        throw error;
  }
}

/**
 * 챗봇에게 메시지를 전송하고 응답을 받음
 * @param {string} userText - 사용자 입력 텍스트
 * @returns {Promise<{type: string, data: any}>} 챗봇 응답 (type과 data 포함)
 */
export async function callChatModule(userText) {
    // "오늘 뭐할지 추천" 등의 키워드가 있으면 TodayPlan API 호출
  if (userText.includes('오늘') && (userText.includes('추천') || userText.includes('뭐할'))) {
    return await getTodayPlan();
  }
  
  // 챗봇 API 호출
  return await sendChatbotMessage(userText);
}

/**
 * 챗봇 메시지 전송
 * @param {string} userText - 사용자 입력 텍스트
 * @returns {Promise<{type: string, data: any}>}
 */
async function sendChatbotMessage(userText) {
  try {
    // 세션 초기화
    await initSession();
    
    const headers = {
      'Content-Type': 'application/json',
    };
    
    // 토큰이 있으면 Authorization 헤더 추가
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }
    
    const response = await fetch(`${API_BASE_URL}/chatbot/message`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({
        session_id: sessionId,
        message: userText
      })
    });
    
    if (!response.ok) {
      throw new Error(`챗봇 API 호출 실패: ${response.status}`);
    }
    
    const result = await response.json();
        return {
      type: 'text',
      data: result.assistant_message
    };
  } catch (error) {
        return {
      type: 'error',
      data: '챗봇 응답을 가져오는 중 오류가 발생했습니다. 로그인이 필요할 수 있습니다.'
    };
  }
}
