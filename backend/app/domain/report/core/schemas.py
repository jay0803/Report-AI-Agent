"""
보고서 관련 스키마 정의
"""
from enum import Enum
from typing import List, Optional, Dict, Any, Literal, Union
from datetime import date
from pydantic import BaseModel, Field


class ReportType(str, Enum):
    """보고서 타입"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# ========================================
# 일일 업무 보고서 스키마
# ========================================
class DailyWorkDetail(BaseModel):
    """일일 업무 세부사항"""
    시간: str = Field(..., description="시간대 (예: 09:00 - 10:00)")
    업무내용: str = Field(default="", description="업무 내용")
    비고: str = Field(default="", description="비고")


class DailyReportHeader(BaseModel):
    """일일 보고서 상단 정보"""
    작성일자: str = Field(default="", description="작성 일자")
    성명: str = Field(default="", description="작성자 성명")


class DailyReportSchema(BaseModel):
    """일일 업무 보고서 전체 구조"""
    문서제목: str = Field(default="일일 업무 보고서")
    상단정보: DailyReportHeader
    금일_진행_업무: Union[str, List[str]] = Field(default="", description="금일 진행 업무 요약")
    세부업무: List[DailyWorkDetail] = Field(default_factory=list)
    미종결_업무사항: Union[str, List[str]] = Field(default="", description="미종결 업무사항")
    익일_업무계획: Union[str, List[str]] = Field(default="", description="익일 업무계획")
    특이사항: str = Field(default="", description="특이사항")


# ========================================
# 주간 업무 보고서 스키마
# ========================================
class WeeklyGoal(BaseModel):
    """주간 업무 목표"""
    항목: str = Field(..., description="항목 번호")
    목표: str = Field(default="", description="목표 내용")
    비고: str = Field(default="", description="비고")


class DayWork(BaseModel):
    """요일별 업무"""
    업무내용: str = Field(default="", description="업무 내용")
    비고: str = Field(default="", description="비고")


class WeeklyReportHeader(BaseModel):
    """주간 보고서 상단 정보"""
    작성일자: str = Field(default="", description="작성 일자")
    성명: str = Field(default="", description="작성자 성명")


class WeeklyReportSchema(BaseModel):
    """주간 업무 보고서 전체 구조"""
    문서제목: str = Field(default="주간 업무 보고서")
    상단정보: WeeklyReportHeader
    주간업무목표: List[WeeklyGoal] = Field(default_factory=list)
    요일별_세부_업무: Dict[str, DayWork] = Field(default_factory=dict)
    주간_중요_업무: str = Field(default="", description="주간 중요 업무")
    특이사항: str = Field(default="", description="특이사항")


# ========================================
# 월간 업무 보고서 스키마
# ========================================
class WeekWork(BaseModel):
    """주차별 업무"""
    업무내용: str = Field(default="", description="업무 내용")
    비고: str = Field(default="", description="비고")


class MonthlyReportHeader(BaseModel):
    """월간 보고서 상단 정보"""
    월: str = Field(default="", description="해당 월")
    작성일자: str = Field(default="", description="작성 일자")
    성명: str = Field(default="", description="작성자 성명")


class MonthlyReportSchema(BaseModel):
    """월간 업무 보고서 전체 구조"""
    문서제목: str = Field(default="월간 업무 보고서")
    상단정보: MonthlyReportHeader
    주차별_세부_업무: Dict[str, WeekWork] = Field(default_factory=dict)
    익월_계획: str = Field(default="", description="익월 계획")


# ========================================
# Canonical 스키마는 canonical_models.py로 이동
# ========================================
# 기존 CanonicalReport는 canonical_models.py의 새 구조로 대체됨
# 하위 호환성을 위해 임시로 import 제공
from app.domain.report.core.canonical_models import CanonicalReport


# ========================================
# 응답 스키마
# ========================================
class ReportParseResponse(BaseModel):
    """보고서 파싱 응답"""
    report_type: ReportType
    data: Dict[str, Any]
    message: str = Field(default="보고서를 성공적으로 파싱했습니다.")


class ReportParseWithCanonicalResponse(BaseModel):
    """보고서 파싱 응답 (Canonical 포함)"""
    report_type: str
    raw: Dict[str, Any] = Field(..., description="원본 Raw JSON")
    canonical: CanonicalReport = Field(..., description="정규화된 Canonical JSON")
    message: str = Field(default="보고서를 성공적으로 파싱했습니다.")


class ReportTypeDetectionResponse(BaseModel):
    """보고서 타입 감지 응답"""
    report_type: ReportType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

