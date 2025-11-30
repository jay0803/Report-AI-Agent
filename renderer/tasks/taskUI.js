/**
 * 추천 업무 UI 관리
 * 
 * 구조:
 * 1. 요약은 일반 bubble 메시지로 표시
 * 2. 추천 UI는 .no-bubble로 독립 렌더링
 *    - 안내 문구
 *    - "직접 작성하기" 버튼
 *    - 250px 스크롤 카드 리스트
 *    - "선택 완료" 버튼
 */

import { saveSelectedTasks } from './taskService.js';

// 추천 업무 선택 상태
let selectedTasks = new Set();
let currentRecommendation = null;

/**
 * 추천 업무 UI 표시 (bubble 밖 독립 렌더링)
 */
export function addTaskRecommendations(data, addMessage, messagesContainer) {
  console.log('🔥 [TaskUI] addTaskRecommendations 호출:', data);
  
  const { tasks, summary, owner, target_date } = data;
  
  // 이전 상태 초기화 (Intent 고착 방지)
  resetTaskState();
  
  currentRecommendation = { owner, target_date, tasks };
  
  // 1) 요약은 일반 bubble 메시지로 표시
  addMessage('assistant', summary || '오늘의 추천 업무입니다!');
  
  // 2) 추천 UI는 bubble 밖 독립 메시지로 표시
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message assistant no-bubble';
  
  const container = document.createElement('div');
  container.className = 'task-recommendations-container';
  
  // 안내 문구
  const guideDiv = document.createElement('div');
  guideDiv.className = 'task-guide';
  guideDiv.textContent = '📌 수행할 업무를 선택하거나 직접 입력해주세요';
  container.appendChild(guideDiv);
  
  // 직접 작성하기 버튼 (카드 리스트 위)
  const customTaskButton = document.createElement('button');
  customTaskButton.className = 'task-custom-button';
  customTaskButton.textContent = '✏️ 직접 작성하기';
  customTaskButton.addEventListener('click', () => {
    console.log('🔥 [TaskUI] 직접 작성하기 버튼 클릭');
    showCustomTaskInput(owner, target_date, addMessage);
  });
  container.appendChild(customTaskButton);
  
  // 카드 리스트 (스크롤 영역)
  const cardsContainer = document.createElement('div');
  cardsContainer.className = 'task-cards';
  
  tasks.forEach((task, index) => {
    const card = createTaskCard(task, index, container);
    cardsContainer.appendChild(card);
  });
  
  container.appendChild(cardsContainer);
  
  // 선택 완료 버튼
  const saveButton = document.createElement('button');
  saveButton.className = 'task-save-button';
  saveButton.textContent = '선택 완료';
  saveButton.disabled = true;
  saveButton.addEventListener('click', (e) => {
    handleSaveSelectedTasks(e, addMessage);
  });
  container.appendChild(saveButton);
  
  messageDiv.appendChild(container);
  messagesContainer.appendChild(messageDiv);
  
  // 스크롤
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  console.log(`✅ [TaskUI] 추천 업무 ${tasks.length}개 표시 완료`);
}

/**
 * 업무 카드 생성
 */
function createTaskCard(task, index, container) {
  const card = document.createElement('div');
  card.className = 'task-card';
  card.dataset.index = index;
  
  const priorityBadge = document.createElement('span');
  priorityBadge.className = `priority-badge priority-${task.priority}`;
  priorityBadge.textContent = {
    high: '높음',
    medium: '보통',
    low: '낮음'
  }[task.priority] || '보통';
  
  const title = document.createElement('div');
  title.className = 'task-title';
  title.textContent = task.title;
  
  const description = document.createElement('div');
  description.className = 'task-description';
  description.textContent = task.description;
  
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
  
  card.addEventListener('click', () => {
    toggleTaskSelection(card, index, container);
  });
  
  return card;
}

/**
 * 업무 선택 토글
 */
function toggleTaskSelection(card, index, container) {
  if (selectedTasks.has(index)) {
    selectedTasks.delete(index);
    card.classList.remove('selected');
  } else {
    selectedTasks.add(index);
    card.classList.add('selected');
  }
  
  const saveButton = container.querySelector('.task-save-button');
  if (saveButton) {
    saveButton.disabled = selectedTasks.size === 0;
  }
  
  console.log(`✅ [TaskUI] 선택된 업무: ${selectedTasks.size}개`);
}

/**
 * 선택한 업무 저장 (금일 진행 업무로 등록)
 */
async function handleSaveSelectedTasks(event, addMessage) {
  if (!currentRecommendation || selectedTasks.size === 0) {
    return;
  }
  
  const { owner, target_date, tasks } = currentRecommendation;
  const selectedTasksList = Array.from(selectedTasks).map(i => tasks[i]);
  
  const saveButton = event.target;
  saveButton.disabled = true;
  saveButton.textContent = '저장 중...';
  
  try {
    const result = await saveSelectedTasks(owner, target_date, selectedTasksList);
    
    if (result.success) {
      addMessage('assistant', `✅ ${result.saved_count}개의 업무가 금일 진행 업무로 저장되었습니다!`);
      
      // 상태 초기화 (Intent 고착 방지)
      resetTaskState();
      
      saveButton.closest('.task-recommendations-container').style.opacity = '0.5';
      saveButton.textContent = '저장 완료';
      
      console.log('✅ [TaskUI] 업무 저장 완료 & 상태 초기화');
    } else {
      addMessage('assistant', `❌ 저장 실패: ${result.message}`);
      saveButton.disabled = false;
      saveButton.textContent = '선택 완료';
    }
  } catch (error) {
    console.error('❌ [TaskUI] 저장 오류:', error);
    addMessage('assistant', '❌ 업무 저장 중 오류가 발생했습니다.');
    saveButton.disabled = false;
    saveButton.textContent = '선택 완료';
  }
}

/**
 * 직접 작성하기 모달 표시
 */
export function showCustomTaskInput(owner, targetDate, addMessage) {
  console.log('🔥 [TaskUI] 직접 작성하기 모달 표시');
  
  const existingModal = document.querySelector('.custom-task-modal');
  if (existingModal) existingModal.remove();
  
  const modal = document.createElement('div');
  modal.className = 'custom-task-modal';
  
  const modalContent = document.createElement('div');
  modalContent.className = 'custom-task-modal-content';
  
  const title = document.createElement('h3');
  title.textContent = '✏️ 직접 업무 작성하기';
  title.style.cssText = 'margin-bottom: 16px; color: #333;';
  
  const label = document.createElement('label');
  label.textContent = '업무 내용을 입력해주세요:';
  label.style.cssText = 'display: block; margin-bottom: 8px; color: #555; font-size: 14px;';
  
  const textarea = document.createElement('textarea');
  textarea.className = 'custom-task-input';
  textarea.placeholder = '예: 4주차 상담 일정 정리';
  textarea.rows = 3;
  textarea.style.cssText = `
    width: 100%;
    padding: 10px;
    border: 2px solid rgba(100, 150, 255, 0.3);
    border-radius: 8px;
    font-size: 14px;
    resize: vertical;
    font-family: inherit;
  `;
  
  const btnWrap = document.createElement('div');
  btnWrap.style.cssText = 'display: flex; gap: 10px; margin-top: 16px;';
  
  const saveBtn = document.createElement('button');
  saveBtn.className = 'custom-task-save-btn';
  saveBtn.textContent = '저장';
  saveBtn.style.cssText = `
    flex: 1;
    padding: 10px;
    border: none;
    border-radius: 8px;
    background: linear-gradient(135deg, rgba(100, 200, 100, 0.9), rgba(80, 180, 80, 0.9));
    color: white;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  `;
  
  const cancelBtn = document.createElement('button');
  cancelBtn.textContent = '취소';
  cancelBtn.style.cssText = `
    flex: 1;
    padding: 10px;
    border: 2px solid rgba(150, 150, 150, 0.5);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.9);
    color: #666;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  `;
  
  cancelBtn.addEventListener('click', () => modal.remove());
  
  saveBtn.addEventListener('click', async () => {
    const text = textarea.value.trim();
    if (!text) {
      alert('업무 내용을 입력해주세요.');
      return;
    }
    
    saveBtn.disabled = true;
    saveBtn.textContent = '저장 중...';
    
    try {
      await saveCustomTask(owner, targetDate, text);
      modal.remove();
      addMessage('assistant', `✅ "${text}" 업무가 금일 진행 업무로 저장되었습니다!`);
      
      // 상태 초기화 (Intent 고착 방지)
      resetTaskState();
      
      console.log('✅ [TaskUI] 직접 입력 업무 저장 완료 & 상태 초기화');
    } catch (err) {
      console.error('❌ [TaskUI] 업무 저장 오류:', err);
      addMessage('assistant', '❌ 업무 저장 중 오류가 발생했습니다.');
      saveBtn.disabled = false;
      saveBtn.textContent = '저장';
    }
  });
  
  btnWrap.appendChild(saveBtn);
  btnWrap.appendChild(cancelBtn);
  
  modalContent.appendChild(title);
  modalContent.appendChild(label);
  modalContent.appendChild(textarea);
  modalContent.appendChild(btnWrap);
  
  modal.appendChild(modalContent);
  document.body.appendChild(modal);
  
  // ESC 키로 닫기
  const handleEsc = (e) => {
    if (e.key === 'Escape') {
      modal.remove();
      document.removeEventListener('keydown', handleEsc);
    }
  };
  document.addEventListener('keydown', handleEsc);
  
  // 모달 외부 클릭 시 닫기
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.remove();
  });
  
  setTimeout(() => textarea.focus(), 80);
}

/**
 * 사용자가 직접 입력한 업무 저장
 */
async function saveCustomTask(owner, targetDate, text) {
  const task = {
    title: text,
    description: text,
    priority: 'medium',
    category: '기타',
    expected_time: '30분'
  };
  
  const result = await saveSelectedTasks(owner, targetDate, [task]);
  
  if (!result.success) {
    throw new Error(result.message || '업무 저장 실패');
  }
}

/**
 * 추천 업무 상태 초기화 (Intent 고착 방지)
 */
export function resetTaskState() {
  selectedTasks.clear();
  currentRecommendation = null;
  console.log('🔄 [TaskUI] 추천 업무 상태 초기화 (Intent 고착 방지)');
}
