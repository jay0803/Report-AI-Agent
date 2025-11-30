/**
 * 채팅 패널 UI 및 상태 관리
 * Cmd/Ctrl + Enter로 토글 가능
 */

import { callChatModule, saveSelectedTasks } from './chatService.js';

// 메시지 상태 (메모리)
let messages = [];

// 패널 표시 상태
let isPanelVisible = true;

// 추천 업무 선택 상태
let selectedTasks = new Set();
let currentRecommendation = null; // { owner, target_date, tasks }

// DOM 요소 참조
let chatPanel = null;
let messagesContainer = null;
let chatInput = null;
let sendBtn = null;

/**
 * 채팅 패널 초기화
 */
export function initChatPanel() {
  console.log('💬 채팅 패널 초기화 중...');
  
  // DOM 요소 가져오기
  chatPanel = document.getElementById('chat-panel');
  messagesContainer = document.getElementById('messages');
  chatInput = document.getElementById('chat-input');
  sendBtn = document.getElementById('send-btn');
  
  if (!chatPanel || !messagesContainer || !chatInput || !sendBtn) {
    console.error('❌ 채팅 패널 요소를 찾을 수 없습니다.');
    return;
  }
  
  // 초기 메시지 추가
  addMessage('assistant', '안녕하세요! 무엇을 도와드릴까요? 😊');
  
  // 이벤트 리스너 등록
  setupEventListeners();
  
  console.log('✅ 채팅 패널 초기화 완료');
}

/**
 * 이벤트 리스너 설정
 */
function setupEventListeners() {
  // 전송 버튼 클릭
  sendBtn.addEventListener('click', handleSendMessage);
  
  // Enter 키로 전송
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });
  
  // Cmd/Ctrl + Enter로 패널 토글
  window.addEventListener('keydown', (e) => {
    // Cmd (Mac) 또는 Ctrl (Windows/Linux)
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      togglePanel();
    }
  });
}

/**
 * 메시지 전송 핸들러
 */
async function handleSendMessage() {
  const text = chatInput.value.trim();
  
  if (!text) return;
  
  // 사용자 메시지 추가
  addMessage('user', text);
  
  // 입력창 초기화
  chatInput.value = '';
  
  // 버튼 비활성화 (응답 대기)
  sendBtn.disabled = true;
  sendBtn.textContent = '...';
  
  try {
    // AI 응답 받기
    const response = await callChatModule(text);
    
    // 응답 타입에 따라 처리
    if (response.type === 'task_recommendations') {
      // 추천 업무 카드 UI 표시
      addTaskRecommendations(response.data);
    } else if (response.type === 'error') {
      addMessage('assistant', response.data);
    } else {
      // 일반 텍스트 응답
      addMessage('assistant', response.data);
    }
  } catch (error) {
    console.error('❌ 채팅 오류:', error);
    addMessage('assistant', '죄송합니다. 오류가 발생했습니다. 😢');
  } finally {
    // 버튼 다시 활성화
    sendBtn.disabled = false;
    sendBtn.textContent = '전송';
  }
}

/**
 * 메시지 추가
 * @param {'user' | 'assistant'} role - 메시지 역할
 * @param {string} text - 메시지 내용
 */
function addMessage(role, text) {
  // 상태에 저장
  messages.push({ role, text });
  
  // DOM에 추가
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;
  
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  
  messageDiv.appendChild(bubble);
  messagesContainer.appendChild(messageDiv);
  
  // 스크롤을 맨 아래로
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  console.log(`💬 [${role}]: ${text}`);
}

/**
 * 추천 업무 카드 UI 추가
 * @param {Object} data - { tasks, summary, owner, target_date }
 */
function addTaskRecommendations(data) {
  const { tasks, summary, owner, target_date } = data;
  
  // 현재 추천 저장
  currentRecommendation = { owner, target_date, tasks };
  selectedTasks.clear();
  
  // 상태에 저장
  messages.push({ role: 'assistant', type: 'task_recommendations', data });
  
  // DOM에 추가
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message assistant';
  
  const container = document.createElement('div');
  container.className = 'task-recommendations-container';
  
  // 요약 메시지
  const summaryDiv = document.createElement('div');
  summaryDiv.className = 'bubble';
  summaryDiv.textContent = summary || '오늘의 추천 업무입니다!';
  container.appendChild(summaryDiv);
  
  // 안내 메시지
  const guideDiv = document.createElement('div');
  guideDiv.className = 'task-guide';
  guideDiv.textContent = '📌 수행할 업무를 선택해주세요 (2~4개 권장)';
  container.appendChild(guideDiv);
  
  // 업무 카드 리스트
  const cardsContainer = document.createElement('div');
  cardsContainer.className = 'task-cards';
  
  tasks.forEach((task, index) => {
    const card = createTaskCard(task, index);
    cardsContainer.appendChild(card);
  });
  
  container.appendChild(cardsContainer);
  
  // 저장 버튼
  const saveButton = document.createElement('button');
  saveButton.className = 'task-save-button';
  saveButton.textContent = '선택 완료';
  saveButton.disabled = true;
  saveButton.addEventListener('click', handleSaveSelectedTasks);
  container.appendChild(saveButton);
  
  messageDiv.appendChild(container);
  messagesContainer.appendChild(messageDiv);
  
  // 스크롤을 맨 아래로
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  console.log(`🎯 추천 업무 ${tasks.length}개 표시`);
}

/**
 * 업무 카드 생성
 * @param {Object} task - { title, description, priority, expected_time, category }
 * @param {number} index - 카드 인덱스
 * @returns {HTMLElement}
 */
function createTaskCard(task, index) {
  const card = document.createElement('div');
  card.className = 'task-card';
  card.dataset.index = index;
  
  // 우선순위 뱃지
  const priorityBadge = document.createElement('span');
  priorityBadge.className = `priority-badge priority-${task.priority}`;
  priorityBadge.textContent = {
    'high': '높음',
    'medium': '보통',
    'low': '낮음'
  }[task.priority] || '보통';
  
  // 제목
  const title = document.createElement('div');
  title.className = 'task-title';
  title.textContent = task.title;
  
  // 설명
  const description = document.createElement('div');
  description.className = 'task-description';
  description.textContent = task.description;
  
  // 메타 정보
  const meta = document.createElement('div');
  meta.className = 'task-meta';
  meta.innerHTML = `
    <span class="task-category">📁 ${task.category}</span>
    <span class="task-time">⏰ ${task.expected_time}</span>
  `;
  
  card.appendChild(priorityBadge);
  card.appendChild(title);
  card.appendChild(description);
  card.appendChild(meta);
  
  // 클릭 이벤트
  card.addEventListener('click', () => {
    toggleTaskSelection(card, index);
  });
  
  return card;
}

/**
 * 업무 선택/해제 토글
 * @param {HTMLElement} card - 카드 요소
 * @param {number} index - 카드 인덱스
 */
function toggleTaskSelection(card, index) {
  if (selectedTasks.has(index)) {
    // 선택 해제
    selectedTasks.delete(index);
    card.classList.remove('selected');
  } else {
    // 선택
    selectedTasks.add(index);
    card.classList.add('selected');
  }
  
  // 저장 버튼 활성화/비활성화
  const saveButton = card.closest('.task-recommendations-container').querySelector('.task-save-button');
  saveButton.disabled = selectedTasks.size === 0;
  
  console.log(`✅ 선택된 업무: ${selectedTasks.size}개`);
}

/**
 * 선택된 업무 저장
 */
async function handleSaveSelectedTasks() {
  if (!currentRecommendation || selectedTasks.size === 0) {
    return;
  }
  
  const { owner, target_date, tasks } = currentRecommendation;
  
  // 선택된 업무만 추출
  const selectedTasksList = Array.from(selectedTasks).map(index => tasks[index]);
  
  // 버튼 비활성화
  const saveButton = event.target;
  saveButton.disabled = true;
  saveButton.textContent = '저장 중...';
  
  try {
    // API 호출
    const result = await saveSelectedTasks(owner, target_date, selectedTasksList);
    
    if (result.success) {
      // 성공 메시지
      addMessage('assistant', `✅ ${result.saved_count}개의 업무가 저장되었습니다! 금일 진행 업무 선택이 완료되었습니다.`);
      
      // 선택 초기화
      selectedTasks.clear();
      currentRecommendation = null;
      
      // 카드 컨테이너 숨기기
      saveButton.closest('.task-recommendations-container').style.opacity = '0.5';
      saveButton.textContent = '저장 완료';
    } else {
      addMessage('assistant', `❌ 저장 실패: ${result.message}`);
      saveButton.disabled = false;
      saveButton.textContent = '선택 완료';
    }
  } catch (error) {
    console.error('❌ 저장 오류:', error);
    addMessage('assistant', '❌ 업무 저장 중 오류가 발생했습니다.');
    saveButton.disabled = false;
    saveButton.textContent = '선택 완료';
  }
}

/**
 * 채팅 패널 토글 (Cmd/Ctrl + Enter)
 */
function togglePanel() {
  isPanelVisible = !isPanelVisible;
  
  if (isPanelVisible) {
    chatPanel.style.display = 'flex';
    console.log('👁️ 채팅 패널 표시');
  } else {
    chatPanel.style.display = 'none';
    console.log('🙈 채팅 패널 숨김');
  }
}

/**
 * 메시지 상태 가져오기 (외부에서 접근 가능)
 */
export function getMessages() {
  return [...messages];
}

/**
 * 메시지 초기화 (외부에서 접근 가능)
 */
export function clearMessages() {
  messages = [];
  messagesContainer.innerHTML = '';
  console.log('🗑️ 메시지 초기화');
}

