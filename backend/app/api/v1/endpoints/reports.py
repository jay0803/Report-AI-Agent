"""
보고서 처리 API 엔드포인트
"""
from typing import Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse

from app.domain.report.service import ReportProcessingService
from app.domain.report.schemas import (
    ReportParseResponse,
    ReportParseWithCanonicalResponse,
    ReportTypeDetectionResponse,
    ReportType
)
from app.core.config import settings


router = APIRouter(prefix="/reports", tags=["reports"])


def get_report_service() -> ReportProcessingService:
    """보고서 처리 서비스 의존성"""
    api_key = settings.OPENAI_API_KEY
    return ReportProcessingService(api_key=api_key)


@router.post("/parse", response_model=ReportParseWithCanonicalResponse)
async def parse_report(
    file: UploadFile = File(...),
    service: ReportProcessingService = Depends(get_report_service)
):
    """
    보고서 PDF 파일을 업로드하여 JSON으로 파싱 (Raw + Canonical)
    
    Args:
        file: 업로드할 PDF 파일
        
    Returns:
        파싱된 보고서 데이터 (Raw JSON + Canonical JSON)
    """
    # PDF 파일 검증
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")
    
    try:
        # 임시 파일로 저장
        temp_dir = Path("temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_path = temp_dir / file.filename
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 보고서 처리 (Vision API → Raw JSON)
        report_type, raw_json = service.process_report(str(temp_path))
        
        # Raw JSON → Canonical JSON 변환
        canonical_report = service.normalize_report(report_type, raw_json)
        
        # 임시 파일 삭제
        temp_path.unlink()
        
        return ReportParseWithCanonicalResponse(
            report_type=report_type.value,
            raw=raw_json,
            canonical=canonical_report,
            message=f"{report_type.value} 보고서를 성공적으로 파싱했습니다."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 처리 중 오류 발생: {str(e)}")


@router.post("/parse/raw", response_model=ReportParseResponse)
async def parse_report_raw_only(
    file: UploadFile = File(...),
    service: ReportProcessingService = Depends(get_report_service)
):
    """
    보고서 PDF 파일을 업로드하여 Raw JSON만 파싱 (기존 방식)
    
    Args:
        file: 업로드할 PDF 파일
        
    Returns:
        파싱된 보고서 데이터 (Raw JSON만)
    """
    # PDF 파일 검증
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")
    
    try:
        # 임시 파일로 저장
        temp_dir = Path("temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_path = temp_dir / file.filename
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 보고서 처리
        report_type, json_data = service.process_report(str(temp_path))
        
        # 임시 파일 삭제
        temp_path.unlink()
        
        return ReportParseResponse(
            report_type=report_type,
            data=json_data,
            message=f"{report_type.value} 보고서를 성공적으로 파싱했습니다."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 처리 중 오류 발생: {str(e)}")


@router.post("/detect-type", response_model=ReportTypeDetectionResponse)
async def detect_report_type(
    file: UploadFile = File(...),
    service: ReportProcessingService = Depends(get_report_service)
):
    """
    보고서 PDF 파일의 타입만 감지
    
    Args:
        file: 업로드할 PDF 파일
        
    Returns:
        감지된 보고서 타입
    """
    # PDF 파일 검증
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")
    
    try:
        # 임시 파일로 저장
        temp_dir = Path("temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_path = temp_dir / file.filename
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 이미지로 변환
        images = service.pdf_to_images(str(temp_path))
        
        # 타입 감지
        report_type = service.detect_report_type(images)
        
        # 임시 파일 삭제
        temp_path.unlink()
        
        return ReportTypeDetectionResponse(
            report_type=report_type,
            confidence=1.0
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 타입 감지 중 오류 발생: {str(e)}")


@router.get("/templates/{report_type}")
async def get_report_template(report_type: ReportType):
    """
    보고서 타입에 따른 JSON 템플릿 반환
    
    Args:
        report_type: 보고서 타입 (daily, weekly, monthly, performance)
        
    Returns:
        JSON 템플릿
    """
    try:
        import json
        service = ReportProcessingService()
        schema_str = service.SCHEMA_MAP.get(report_type)
        
        if not schema_str:
            raise HTTPException(status_code=404, detail="해당 타입의 템플릿을 찾을 수 없습니다.")
        
        schema_json = json.loads(schema_str)
        return JSONResponse(content=schema_json)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"템플릿 로드 중 오류 발생: {str(e)}")

