/**
 * Chatbot API 전용 서비스
 * backend/app/domain/chatbot 모듈과 통신
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';
const SESSION_KEY = 'chatbot_session_id';

// JWT 토큰 저장
let accessToken = null;

/**
 * 챗봇 서비스 초기화 (토큰 설정)
 * @param {string} token - JWT 액세스 토큰
 */
export function initChatbotService(token) {
  accessToken = token;
  }

/**
 * 세션 ID 가져오기 (없으면 새로 생성)
 * @returns {Promise<string>} session_id
 */
export async function getOrCreateSession() {
  let sessionId = localStorage.getItem(SESSION_KEY);
  
  if (!sessionId) {
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
        headers: headers,
        credentials: 'include'  // 쿠키 자동 전송
      });
      
      if (!response.ok) {
        throw new Error('세션 생성 실패');
      }
      
      const data = await response.json();
      sessionId = data.session_id;
      localStorage.setItem(SESSION_KEY, sessionId);
      
          } catch (error) {
            throw error;
    }
  }
  
  return sessionId;
}

/**
 * 챗봇에 메시지 전송
 * @param {string} userMessage - 사용자 입력 메시지
 * @returns {Promise<string>} 챗봇 응답 메시지
 */
export async function sendChatMessage(userMessage) {
  try {
    // 일반 질문은 기존 챗봇 API 사용
    let sessionId = await getOrCreateSession();
    
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
      credentials: 'include',  // 쿠키 자동 전송
      body: JSON.stringify({
        session_id: sessionId,
        message: userMessage
      })
    });
    
    // 404 에러 = 세션이 백엔드에 없음 (재시작 등으로 메모리에서 삭제됨)
    if (response.status === 404) {
            // localStorage의 오래된 세션 삭제
      localStorage.removeItem(SESSION_KEY);
      
      // 새 세션 생성
      sessionId = await getOrCreateSession();
      
      // 재시도
      const retryHeaders = {
        'Content-Type': 'application/json',
      };
      
      if (accessToken) {
        retryHeaders['Authorization'] = `Bearer ${accessToken}`;
      }
      
      const retryResponse = await fetch(`${API_BASE_URL}/chatbot/message`, {
        method: 'POST',
        headers: retryHeaders,
        credentials: 'include',  // 쿠키 자동 전송
        body: JSON.stringify({
          session_id: sessionId,
          message: userMessage
        })
      });
      
      if (!retryResponse.ok) {
        throw new Error(`Chatbot API 재시도 실패: ${retryResponse.status}`);
      }
      
      const retryResult = await retryResponse.json();
            return retryResult.assistant_message;
    }
    
    if (!response.ok) {
      throw new Error(`Chatbot API 호출 실패: ${response.status}`);
    }
    
    const result = await response.json();
        return result.assistant_message;
  } catch (error) {
        throw error;
  }
}

/**
 * 대화 히스토리 조회
 * @returns {Promise<Array>} 대화 히스토리
 */
export async function getChatHistory() {
  try {
    const sessionId = await getOrCreateSession();
    
    const response = await fetch(`${API_BASE_URL}/chatbot/history/${sessionId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include'  // 쿠키 자동 전송
    });
    
    if (!response.ok) {
      throw new Error('히스토리 조회 실패');
    }
    
    const result = await response.json();
    return result.messages || [];
  } catch (error) {
        return [];
  }
}

/**
 * 세션 삭제
 */
export async function deleteChatSession() {
  try {
    const sessionId = localStorage.getItem(SESSION_KEY);
    if (!sessionId) return;
    
    await fetch(`${API_BASE_URL}/chatbot/session/${sessionId}`, {
      method: 'DELETE',
      credentials: 'include'  // 쿠키 자동 전송
    });
    
    localStorage.removeItem(SESSION_KEY);
      } catch (error) {
      }
}

