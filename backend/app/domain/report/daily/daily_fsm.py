"""
Daily Report FSM

시간대별 일일보고서 입력 FSM (Simple State Machine)

Author: AI Assistant
Created: 2025-11-18
"""
from typing import Dict, Any
from app.domain.report.daily.fsm_state import DailyFSMContext, DailyState
from app.domain.report.daily.task_parser import TaskParser


class DailyReportFSM:
    """일일보고서 입력 FSM (단순 상태 머신)"""
    
    def __init__(self, task_parser: TaskParser):
        """
        초기화
        
        Args:
            task_parser: TaskParser 인스턴스
        """
        self.task_parser = task_parser
    
    def _ask_question(self, context: DailyFSMContext) -> DailyFSMContext:
        """시간대 질문 생성"""
        if context.current_index < len(context.time_ranges):
            time_range = context.time_ranges[context.current_index]
            context.current_question = f"{time_range} 무엇을 했나요?"
            context.current_state = DailyState.ASK_TIME_RANGE
        else:
            # 시간대가 끝나면 이슈사항 질문으로 이동
            context = self._ask_issues(context)
        
        return context
    
    def _parse_answer(self, context: DailyFSMContext) -> DailyFSMContext:
        """답변 파싱 및 저장"""
        if context.last_answer and context.current_index < len(context.time_ranges):
            time_range = context.time_ranges[context.current_index]
            
            # LLM으로 파싱
            task_dict = self.task_parser.parse_sync(
                text=context.last_answer,
                time_range=time_range
            )
            
            # time_tasks에 추가
            context.time_tasks.append(task_dict)
            context.current_state = DailyState.PARSE_TASK
        
        return context
    
    def _move_next(self, context: DailyFSMContext) -> DailyFSMContext:
        """다음 시간대로 이동"""
        context.current_index += 1
        context.last_answer = ""
        context.current_state = DailyState.NEXT_TIME_RANGE
        
        if context.current_index >= len(context.time_ranges):
            # 시간대 완료 후 이슈사항 질문으로 이동
            context.current_state = DailyState.ASK_ISSUES
        
        return context
    
    def _ask_issues(self, context: DailyFSMContext) -> DailyFSMContext:
        """이슈사항 질문 생성"""
        context.current_question = "오늘 업무 중 발생한 이슈사항이 있나요? (없으면 '없음'이라고 입력해주세요)"
        context.current_state = DailyState.ASK_ISSUES
        return context
    
    def _parse_issues(self, context: DailyFSMContext) -> DailyFSMContext:
        """이슈사항 파싱 및 저장"""
        if context.last_answer:
            answer = context.last_answer.strip()
            
            # "없음" 관련 키워드 체크 (더 유연하게)
            answer_lower = answer.lower().replace(" ", "")
            
            # 부정 키워드 리스트
            negative_keywords = [
                '없음', '없어요', '없습니다', '없네요', '없었어요',
                '딱히없음', '딱히없어요', '딱히없습니다',
                '특별히없음', '특별히없어요', '특별히없습니다',
                'x', '-', 'n/a', 'na', 'none'
            ]
            
            if answer_lower in negative_keywords:
                context.issues = []
            else:
                # 간단한 파싱 (줄바꿈으로 구분)
                issue_lines = [line.strip() for line in answer.split('\n') if line.strip()]
                
                # 각 라인도 부정 표현 필터링
                valid_issues = []
                for line in issue_lines:
                    line_lower = line.lower().replace(" ", "")
                    if line_lower not in negative_keywords and len(line) > 1:
                        valid_issues.append({"description": line})
                
                context.issues = valid_issues
            
            context.current_state = DailyState.RECEIVE_ISSUES
        
        return context
    
    def _ask_plans(self, context: DailyFSMContext) -> DailyFSMContext:
        """익일 업무 계획 질문 생성"""
        context.current_question = "내일 진행할 업무 계획을 입력해주세요. (없으면 '없음'이라고 입력해주세요)"
        context.current_state = DailyState.ASK_PLANS
        return context
    
    def _parse_plans(self, context: DailyFSMContext) -> DailyFSMContext:
        """익일 업무 계획 파싱 및 저장"""
        if context.last_answer:
            answer = context.last_answer.strip()
            
            # "없음" 관련 키워드 체크 (더 유연하게)
            answer_lower = answer.lower().replace(" ", "")
            
            # 부정 키워드 리스트
            negative_keywords = [
                '없음', '없어요', '없습니다', '없네요', '없었어요',
                '딱히없음', '딱히없어요', '딱히없습니다',
                '특별히없음', '특별히없어요', '특별히없습니다',
                'x', '-', 'n/a', 'na', 'none'
            ]
            
            if answer_lower in negative_keywords:
                context.plans = []
            else:
                # 간단한 파싱 (줄바꿈으로 구분)
                plan_lines = [line.strip() for line in answer.split('\n') if line.strip()]
                
                # 각 라인도 부정 표현 필터링
                valid_plans = []
                for line in plan_lines:
                    line_lower = line.lower().replace(" ", "")
                    if line_lower not in negative_keywords and len(line) > 1:
                        valid_plans.append({"title": line})
                
                context.plans = valid_plans
            
            context.current_state = DailyState.RECEIVE_PLANS
        
        return context
    
    def start_session(self, context: DailyFSMContext) -> Dict[str, Any]:
        """
        세션 시작
        
        Args:
            context: 초기 컨텍스트
            
        Returns:
            첫 질문 정보
        """
        # 초기화
        context.current_state = DailyState.WAIT_START
        context.current_index = 0
        context.finished = False
        
        # 첫 질문 생성
        context = self._ask_question(context)
        
        return {
            "session_id": context.session_id,
            "question": context.current_question,
            "current_index": context.current_index,
            "total_ranges": len(context.time_ranges),
            "finished": context.finished,
            "state": context
        }
    
    def process_answer(
        self,
        context: DailyFSMContext,
        answer: str
    ) -> Dict[str, Any]:
        """
        답변 처리
        
        Args:
            context: 현재 컨텍스트
            answer: 사용자 답변
            
        Returns:
            다음 질문 또는 완료 정보
        """
        # 답변 저장
        context.last_answer = answer
        
        # 현재 상태에 따라 처리
        if context.current_state == DailyState.ASK_TIME_RANGE:
            # 시간대 업무 답변 처리
            context.current_state = DailyState.RECEIVE_ANSWER
            context = self._parse_answer(context)
            context = self._move_next(context)
            
            # 다음 질문 생성
            if context.current_state == DailyState.ASK_ISSUES:
                context = self._ask_issues(context)
            elif not context.finished:
                context = self._ask_question(context)
        
        elif context.current_state == DailyState.ASK_ISSUES:
            # 이슈사항 답변 처리
            context = self._parse_issues(context)
            context = self._ask_plans(context)
        
        elif context.current_state == DailyState.ASK_PLANS:
            # 익일 계획 답변 처리
            context = self._parse_plans(context)
            context.current_state = DailyState.FINISHED
            context.finished = True
            context.current_question = ""
        
        return {
            "session_id": context.session_id,
            "question": context.current_question if not context.finished else "",
            "current_index": context.current_index,
            "total_ranges": len(context.time_ranges),
            "finished": context.finished,
            "state": context,
            "tasks_collected": len(context.time_tasks),
            "issues_collected": len(context.issues),
            "plans_collected": len(context.plans)
        }

