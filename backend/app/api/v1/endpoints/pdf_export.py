"""
PDF Export API

보고서 PDF 다운로드 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from datetime import date
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.reporting.service.report_export_service import ReportExportService


router = APIRouter(prefix="/pdf", tags=["PDF Export"])


@router.get("/daily/{owner}/{report_date}")
async def export_daily_pdf(
    owner: str,
    report_date: date,
    db: Session = Depends(get_db)
):
    """
    일일보고서 PDF 다운로드
    
    - **owner**: 작성자 이름
    - **report_date**: 보고서 날짜 (YYYY-MM-DD)
    """
    try:
        pdf_bytes = ReportExportService.export_daily_pdf(
            db=db,
            owner=owner,
            report_date=report_date
        )
        
        filename = f"일일보고서_{owner}_{report_date}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 생성 실패: {str(e)}")


@router.get("/weekly/{owner}/{period_start}/{period_end}")
async def export_weekly_pdf(
    owner: str,
    period_start: date,
    period_end: date,
    db: Session = Depends(get_db)
):
    """
    주간보고서 PDF 다운로드
    
    - **owner**: 작성자 이름
    - **period_start**: 시작일 (월요일, YYYY-MM-DD)
    - **period_end**: 종료일 (금요일, YYYY-MM-DD)
    """
    try:
        pdf_bytes = ReportExportService.export_weekly_pdf(
            db=db,
            owner=owner,
            period_start=period_start,
            period_end=period_end
        )
        
        filename = f"주간보고서_{owner}_{period_start}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 생성 실패: {str(e)}")


@router.get("/monthly/{owner}/{period_start}/{period_end}")
async def export_monthly_pdf(
    owner: str,
    period_start: date,
    period_end: date,
    db: Session = Depends(get_db)
):
    """
    월간보고서 PDF 다운로드
    
    - **owner**: 작성자 이름
    - **period_start**: 시작일 (1일, YYYY-MM-DD)
    - **period_end**: 종료일 (말일, YYYY-MM-DD)
    """
    try:
        pdf_bytes = ReportExportService.export_monthly_pdf(
            db=db,
            owner=owner,
            period_start=period_start,
            period_end=period_end
        )
        
        filename = f"월간보고서_{owner}_{period_start.year}년{period_start.month}월.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 생성 실패: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "service": "pdf_export"}

