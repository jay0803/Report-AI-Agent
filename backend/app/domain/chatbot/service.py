"""
채팅 서비스

OpenAI GPT-4를 사용한 대화형 AI 서비스입니다.
- 세션별 대화 히스토리 유지
- 시스템 프롬프트로 AI 비서 페르소나 설정
- 추후 RAG 통합 가능한 구조
"""

import os
from typing import Optional
from openai import OpenAI
from app.domain.chatbot.session_manager import SessionManager
from app.domain.chatbot.memory_manager import MemoryManager
from app.domain.chatbot.summarizer import Summarizer

# Tools Function Calling 지원 (추가)
import sys
from pathlib import Path
tools_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "tools"
if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path))

try:
    from tools.schemas import function_definitions
    TOOLS_AVAILABLE = True
except ImportError:
    function_definitions = []
    TOOLS_AVAILABLE = False
    print("⚠️ Tools module not available. Function calling disabled.")


class ChatService:
    """
    채팅 서비스
    
    OpenAI API를 사용하여 사용자와 대화합니다.
    세션별 히스토리를 유지하여 맥락 있는 대화가 가능합니다.
    """
    
    def __init__(self):
        """서비스 초기화"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it in backend/.env file or as an environment variable."
            )
        self.openai_client = OpenAI(api_key=api_key)
        
        # 대화 히스토리 크기 설정 (환경변수 or 기본값 15)
        max_history = int(os.getenv("CHAT_HISTORY_SIZE", "15"))
        self.session_manager = SessionManager(max_history=max_history)
        
        # 메모리 및 요약 관리
        self.memory_manager = MemoryManager()
        self.summarizer = Summarizer()
        
        self.model = os.getenv("LLM_MODEL", "gpt-4o")
        self.system_prompt_base = self._get_system_prompt()
        self.rag_service = None  # 추후 RAG 통합용
        
        # Tool 함수 매핑 (Function Calling 실행용)
        if TOOLS_AVAILABLE:
            from tools import drive_tool, gmail_tool, slack_tool, notion_tool
            self.tool_map = {
                "create_folder": drive_tool.create_folder,
                "upload_file": drive_tool.upload_file,
                "search_files": drive_tool.search_files,
                "download_file": drive_tool.download_file,
                "send_email": gmail_tool.send_email,
                "list_messages": gmail_tool.list_messages,
                "get_message": gmail_tool.get_message,
                "send_dm": slack_tool.send_dm,
                "send_channel_message": slack_tool.send_channel_message,
                "create_page": notion_tool.create_page,
                "add_database_item": notion_tool.add_database_item,
            }
        else:
            self.tool_map = {}
    
    def _get_system_prompt(self) -> str:
        """
        시스템 프롬프트 생성
        
        AI 비서의 페르소나와 응답 스타일을 정의합니다.
        """
        return """당신은 친절하고 유능한 AI 비서입니다.

역할:
- 사용자의 질문에 명확하고 도움이 되는 답변을 제공합니다.
- 필요시 추가 정보를 요청하여 더 나은 답변을 제공합니다.
- 전문적이면서도 친근한 톤을 유지합니다.

응답 스타일:
- 간결하고 핵심적인 답변을 제공합니다.
- 불확실한 정보는 추측하지 않고 솔직히 말합니다.
- 이모지를 적절히 사용하여 친근함을 표현합니다.
- 사용자의 이전 대화 내용을 기억하고 맥락을 유지합니다.

대화 관리 정책:
- 최근 15개 대화를 상세히 기억합니다.
- 그 이전 대화는 신속한 응답을 위해 관리하고 있습니다.
- 사용자가 오래된 대화(16개 이전)를 물어보면:
  "죄송하지만 신속한 대화를 위해 최근 15개 대화만 상세히 기억하고 있습니다. 😊
   다시 말씀해 주시면 기꺼이 도와드리겠습니다!"

제약사항:
- 불법적이거나 비윤리적인 요청은 정중히 거절합니다.
- 개인정보나 민감한 정보는 요청하지 않습니다.
- 확실하지 않은 정보는 "확인이 필요합니다"라고 답변합니다."""
    
    def enable_rag(self, rag_service):
        """
        RAG 서비스 활성화 (추후 사용)
        
        Args:
            rag_service: RAG 검색 서비스 인스턴스
        """
        self.rag_service = rag_service
    
    def create_session(self, user_id: int = None) -> str:
        """
        새로운 채팅 세션 생성
        
        Args:
            user_id: 사용자 ID (선택)
        
        Returns:
            str: 세션 ID
        """
        return self.session_manager.create_session(user_id=user_id)
    
    async def process_message(
        self,
        session_id: str,
        user_message: str,
        user_id: int = None,
        temperature: float = 0.7
    ) -> str:
        """
        사용자 메시지 처리 및 응답 생성
        
        Args:
            session_id: 세션 ID
            user_message: 사용자 입력 메시지
            temperature: LLM temperature (0.0~1.0, 기본 0.7)
            
        Returns:
            str: AI 응답 메시지
        """
        # 1. deque가 꽉 찼는지 확인 (16번째 메시지 추가 직전)
        current_history = self.session_manager.get_history(session_id)
        is_full = len(current_history) >= self.session_manager.max_history
        
        # 2. 꽉 찼으면 가장 오래된 메시지를 MD 파일에 저장
        if is_full and current_history:
            oldest_message = current_history[0]  # deque의 첫 번째 = 가장 오래된 것
            self.memory_manager.append_message(session_id, oldest_message)
            
            # 요약 업데이트 (매번 or 특정 간격)
            # 현재: 매 16번째마다 전체 백업된 대화로 요약 생성
            self._update_summary(session_id)
        
        # 3. 사용자 메시지 저장 (deque에 추가, 16번째면 자동으로 1번째 삭제)
        self.session_manager.add_message(session_id, "user", user_message)
        
        # 4. 대화 히스토리 가져오기
        history = self.session_manager.get_history_for_llm(session_id)
        
        # 5. 요약 로드 (있으면)
        summary = self.memory_manager.get_summary(session_id)
        
        # 6. RAG 검색 (활성화된 경우)
        rag_context = ""
        if self.rag_service:
            # 추후 구현
            # rag_results = self.rag_service.search(user_message)
            # rag_context = f"\n\n[참고 자료]\n{rag_results}"
            pass
        
        # 7. 시스템 프롬프트 구성 (요약 포함)
        system_prompt = self._build_system_prompt(summary)
        
        # 8. LLM 메시지 구성
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 히스토리 추가 (최근 15개)
        messages.extend(history)
        
        # RAG 컨텍스트가 있으면 마지막 사용자 메시지에 추가
        if rag_context:
            messages[-1]["content"] += rag_context
        
        # 9. OpenAI API 호출
        try:
            # Function Calling 지원 추가
            if TOOLS_AVAILABLE and function_definitions:
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=1000,
                    functions=function_definitions,
                    function_call="auto"
                )
            else:
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=1000
                )
            
            ai_message = response.choices[0].message.content
            
            # Function Call 처리 추가
            if TOOLS_AVAILABLE and hasattr(response.choices[0].message, 'function_call') and response.choices[0].message.function_call:
                function_name = response.choices[0].message.function_call.name
                import json
                function_args = json.loads(response.choices[0].message.function_call.arguments)
                
                if function_name in self.tool_map:
                    try:
                        tool_func = self.tool_map[function_name]
                        
                        # 모든 도구는 user_id가 필요함
                        if function_name in ["send_email", "list_messages", "get_message", 
                                            "send_dm", "send_channel_message", 
                                            "create_page", "add_database_item",
                                            "create_folder", "upload_file", "search_files", "download_file"]:
                            # user_id를 문자열로 변환하여 전달
                            if user_id:
                                function_args["user_id"] = str(user_id)
                            else:
                                # user_id가 없으면 에러 메시지 설정하고 tool 실행 건너뛰기
                                ai_message = f"❌ {function_name} 실행 실패: 로그인이 필요합니다."
                                # 10. AI 응답 저장으로 바로 이동
                                self.session_manager.add_message(session_id, "assistant", ai_message)
                                self.memory_manager.append_message(
                                    session_id,
                                    {"role": "assistant", "content": ai_message, "timestamp": ""}
                                )
                                return ai_message
                        
                        result = await tool_func(**function_args)
                        
                        if result["success"]:
                            ai_message = f"✅ 작업 완료!\n\n{json.dumps(result['data'], ensure_ascii=False, indent=2)}"
                        else:
                            ai_message = f"❌ 작업 실패: {result['error']}"
                    except Exception as e:
                        ai_message = f"❌ Tool 실행 중 오류: {str(e)}"
                else:
                    ai_message = f"⚠️ {function_name} 함수를 찾을 수 없습니다."
            
            # 10. AI 응답 저장 (deque + MD 파일)
            self.session_manager.add_message(session_id, "assistant", ai_message)
            
            # MD 파일에도 저장 (백업용)
            self.memory_manager.append_message(
                session_id,
                {"role": "assistant", "content": ai_message, "timestamp": ""}
            )
            
            return ai_message
        
        except Exception as e:
            error_message = f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"
            self.session_manager.add_message(session_id, "assistant", error_message)
            return error_message
    
    def _update_summary(self, session_id: str):
        """
        세션의 요약 업데이트
        
        Args:
            session_id: 세션 ID
        """
        try:
            # MD 파일에서 전체 대화 읽기
            all_history_text = self.memory_manager.get_all_messages(session_id)
            
            if not all_history_text:
                return
            
            # 기존 요약 확인
            existing_summary = self.memory_manager.get_summary(session_id)
            
            # 현재 deque의 대화 (요약 대상)
            current_messages = self.session_manager.get_history(session_id)
            
            # 요약 생성 또는 업데이트
            if not existing_summary:
                # 첫 요약 생성
                summary = self.summarizer.create_summary(current_messages)
            else:
                # 기존 요약 업데이트 (누적)
                summary = self.summarizer.update_summary(existing_summary, current_messages)
            
            # 요약 저장
            self.memory_manager.save_summary(session_id, summary)
        
        except Exception as e:
            # 요약 생성 실패해도 대화는 계속
            print(f"⚠️  요약 업데이트 실패: {e}")
    
    def _build_system_prompt(self, summary: str) -> str:
        """
        시스템 프롬프트 구성 (요약 포함)
        
        Args:
            summary: 대화 요약 (Markdown)
            
        Returns:
            str: 완성된 시스템 프롬프트
        """
        if summary and len(summary) > 50:  # 요약이 있으면
            return f"""{self.system_prompt_base}

---

# 이전 대화 요약
{summary}

**참고:** 위 요약은 사용자와의 이전 대화(16번째 이전) 내용입니다.
사용자가 과거 대화를 언급하면 요약을 참고하여 답변하세요."""
        else:
            return self.system_prompt_base
    
    def get_session_history(self, session_id: str):
        """
        세션의 전체 대화 히스토리 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            List[dict]: 대화 히스토리
        """
        return self.session_manager.get_history(session_id)
    
    def get_session_info(self, session_id: str):
        """
        세션 정보 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            dict: 세션 메타데이터
        """
        return self.session_manager.get_session_info(session_id)
    
    def delete_session(self, session_id: str):
        """
        세션 삭제
        
        Args:
            session_id: 세션 ID
        """
        self.session_manager.delete_session(session_id)
        self.memory_manager.delete_session(session_id)

