"""
대화 요약 생성기

대화 히스토리를 구조화하여 요약합니다.
- 사용자 정보 추출
- 주요 질문 및 답변 정리
- 대화 맥락 파악
"""

import os
from typing import List
from openai import OpenAI


class Summarizer:
    """
    대화 요약 생성기
    
    LLM을 사용하여 대화를 구조화된 형태로 요약합니다.
    """
    
    def __init__(self):
        """요약 서비스 초기화"""
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("LLM_MODEL", "gpt-4o")
    
    def create_summary(self, messages: List[dict]) -> str:
        """
        대화 히스토리를 요약
        
        Args:
            messages: 메시지 리스트 [{"role": "user/assistant", "content": "..."}, ...]
            
        Returns:
            str: 구조화된 요약 (Markdown)
        """
        # 대화가 너무 짧으면 요약 생략
        if len(messages) < 5:
            return "## 요약 정보\n\n대화가 짧아 요약을 생성하지 않았습니다."
        
        # 대화 내용 포맷팅
        conversation_text = self._format_conversation(messages)
        
        # 요약 프롬프트
        summary_prompt = self._get_summary_prompt(conversation_text)
        
        try:
            # LLM 호출
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": summary_prompt}
                ],
                temperature=0.3,  # 일관된 요약을 위해 낮은 temperature
                max_tokens=500
            )
            
            summary = response.choices[0].message.content
            return summary
        
        except Exception as e:
            return f"## 요약 생성 실패\n\n오류: {str(e)}"
    
    def _format_conversation(self, messages: List[dict]) -> str:
        """대화 내용을 텍스트로 포맷팅"""
        lines = []
        for i, msg in enumerate(messages, 1):
            role_icon = "👤" if msg["role"] == "user" else "🤖"
            role_name = "사용자" if msg["role"] == "user" else "AI"
            lines.append(f"[{i}] {role_icon} {role_name}: {msg['content']}")
        
        return "\n".join(lines)
    
    def _get_summary_prompt(self, conversation_text: str) -> str:
        """요약 생성 프롬프트"""
        return f"""당신은 대화 내용을 구조화하여 요약하는 전문가입니다.

다음 대화를 분석하여 **미래에 참고할 중요한 정보**를 추출하세요.

# 요약 기준
1. **사용자 정보**: 이름, 직급, 선호 스타일 등 (언급된 경우만)
2. **핵심 질문**: 사용자가 물어본 중요한 내용 (재질문 가능성이 높은 것)
3. **사실 정보**: 규정, 설명, 구체적 답변
4. **대화 맥락**: 사용자의 관심사, 대화 흐름
5. **제외 대상**: 단순 인사, 의미 없는 잡담

# 출력 형식 (Markdown, 간결하게)
```markdown
## 사용자 정보
- 이름: [추출 or 없음]
- 특징: [직급/역할/특성 or 없음]

## 주요 질문 및 답변
1. [주제] (대화 번호)
   - 질문: [1-2문장 요약]
   - 답변: [핵심만 1-2문장]

(3개 이내로 가장 중요한 것만)

## 대화 맥락
- [사용자 관심사/패턴 2-3문장]

## 키워드
[관련 키워드 5개 이내]
```

# 대화 내역
{conversation_text}

**중요:** 단순 인사나 의미 없는 내용은 생략하고, **나중에 참고할 가치가 있는 정보만** 포함하세요.
요약은 200 토큰 이내로 간결하게 작성하세요."""
    
    def update_summary(self, existing_summary: str, new_messages: List[dict]) -> str:
        """
        기존 요약에 새로운 대화 추가 (누적 요약)
        
        Args:
            existing_summary: 기존 요약
            new_messages: 새로운 메시지들
            
        Returns:
            str: 업데이트된 요약
        """
        # 새로운 대화 포맷팅
        new_conversation = self._format_conversation(new_messages)
        
        # 업데이트 프롬프트
        update_prompt = f"""당신은 대화 요약을 업데이트하는 전문가입니다.

# 기존 요약
{existing_summary}

# 새로운 대화
{new_conversation}

위 새로운 대화 내용을 분석하여 **기존 요약을 업데이트**하세요.

업데이트 규칙:
- 새로운 중요 정보가 있으면 추가
- 중복된 내용은 통합
- 덜 중요한 내용은 제거
- 전체 길이는 200 토큰 이내 유지

동일한 Markdown 형식으로 출력하세요."""
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": update_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            # 업데이트 실패 시 기존 요약 유지
            return existing_summary

