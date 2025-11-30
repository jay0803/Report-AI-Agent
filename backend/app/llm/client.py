"""
LLM Client Wrapper

OpenAI Chat 모델에 대한 통합 인터페이스 제공

Author: AI Assistant
Created: 2025-11-18
"""
import os
import json
from typing import Optional, Dict, Any
import openai
from pydantic import BaseModel

from app.core.config import settings


class LLMClient:
    """OpenAI LLM 클라이언트"""
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        """
        초기화
        
        Args:
            model: 모델명
            api_key: OpenAI API 키 (None이면 환경변수에서 가져옴)
            temperature: 생성 온도
            max_tokens: 최대 토큰 수
        """
        self.model = model
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = openai.OpenAI(api_key=self.api_key)
    
    async def acomplete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        비동기 LLM 완성 (텍스트 응답)
        
        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            temperature: 생성 온도 (None이면 기본값 사용)
            max_tokens: 최대 토큰 (None이면 기본값 사용)
            
        Returns:
            생성된 텍스트
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            print(f"[ERROR] LLM completion error: {e}")
            raise
    
    async def acomplete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> dict:
        """
        비동기 LLM 완성 (JSON 응답)
        
        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            temperature: 생성 온도
            max_tokens: 최대 토큰
            
        Returns:
            파싱된 JSON 딕셔너리
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                response_format={"type": "json_object"}  # JSON 모드
            )
            
            content = response.choices[0].message.content
            
            # JSON 파싱
            return json.loads(content)
        
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parsing error: {e}")
            print(f"Raw response: {content}")
            raise
        
        except Exception as e:
            print(f"[ERROR] LLM JSON completion error: {e}")
            raise
    
    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> dict:
        """
        동기 LLM 완성 (JSON 응답)
        
        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            temperature: 생성 온도
            max_tokens: 최대 토큰
            
        Returns:
            파싱된 JSON 딕셔너리
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                response_format={"type": "json_object"}  # JSON 모드
            )
            
            content = response.choices[0].message.content
            
            # JSON 파싱
            return json.loads(content)
        
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parsing error: {e}")
            print(f"Raw response: {content}")
            raise
        
        except Exception as e:
            print(f"[ERROR] LLM JSON completion error: {e}")
            raise


def get_llm(
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> LLMClient:
    """
    LLM 클라이언트 팩토리 함수
    
    Args:
        model: 모델명
        api_key: OpenAI API 키
        temperature: 생성 온도
        max_tokens: 최대 토큰
        
    Returns:
        LLMClient 인스턴스
    """
    return LLMClient(
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens
    )

