"""
Daily Report API

시간대별 일일보고서 입력 API

Author: AI Assistant
Created: 2025-11-18
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session
from pathlib import Path
import os

from app.domain.report.daily.fsm_state import DailyFSMContext
from app.domain.report.daily.time_slots import generate_time_slots
from app.domain.report.daily.task_parser import TaskParser
from app.domain.report.daily.daily_fsm import DailyReportFSM
from app.domain.report.daily.daily_builder import build_daily_report
from app.domain.report.daily.session_manager import get_session_manager
from app.domain.report.daily.main_tasks_store import get_main_tasks_store
from app.domain.report.daily.repository import DailyReportRepository
from app.domain.report.daily.schemas import DailyReportCreate
from app.llm.client import get_llm
from app.domain.report.core.schemas import CanonicalReport
from app.infrastructure.database.session import get_db
from app.reporting.pdf_generator.daily_report_pdf import DailyReportPDFGenerator
from ingestion.auto_ingest import ingest_single_report


router = APIRouter(prefix="/daily", tags=["daily"])


# 요청/응답 스키마
class DailyStartRequest(BaseModel):
    """일일보고서 작성 시작 요청"""
    owner: str = Field(..., description="작성자")
    target_date: date = Field(..., description="보고서 날짜")
    time_ranges: List[str] = Field(
        default_factory=list,
        description="시간대 목록 (비어있으면 자동 생성)"
    )


class DailyStartResponse(BaseModel):
    """일일보고서 작성 시작 응답"""
    status: str = Field(default="in_progress", description="항상 in_progress")
    session_id: str
    question: str
    meta: Dict[str, Any] = Field(default_factory=dict, description="메타 정보")


class DailyAnswerRequest(BaseModel):
    """답변 입력 요청"""
    session_id: str = Field(..., description="세션 ID")
    answer: str = Field(..., description="사용자 답변")


class DailyAnswerResponse(BaseModel):
    """답변 입력 응답"""
    status: str = Field(..., description="in_progress 또는 finished")
    session_id: str
    question: Optional[str] = Field(None, description="다음 질문 (finished 시 None)")
    message: Optional[str] = Field(None, description="완료 메시지 (finished 시)")
    meta: Optional[Dict[str, Any]] = Field(None, description="메타 정보")
    report: Optional[CanonicalReport] = Field(None, description="완료 시 보고서")


@router.post("/start", response_model=DailyStartResponse)
async def start_daily_report(request: DailyStartRequest):
    """
    일일보고서 작성 시작
    
    저장소에서 금일 진행 업무(main_tasks)를 자동으로 불러와서
    FSM 세션을 시작하고, 첫 번째 시간대 질문을 반환합니다.
    
    main_tasks는 /select_main_tasks로 미리 저장되어 있어야 합니다.
    """
    try:
        # 시간대 생성 (제공되지 않으면 기본값: 09:00~18:00, 60분 간격)
        time_ranges = request.time_ranges
        if not time_ranges:
            time_ranges = generate_time_slots()  # 기본값 사용
        
        # 저장소에서 main_tasks 불러오기
        store = get_main_tasks_store()
        main_tasks = store.get(
            owner=request.owner,
            target_date=request.target_date
        )
        
        # main_tasks가 없으면 에러 반환 (프론트엔드에서 업무 플래닝 기능으로 리다이렉트)
        if main_tasks is None or len(main_tasks) == 0:
            print(f"[WARNING] main_tasks가 저장되지 않음: {request.owner}, {request.target_date}")
            raise HTTPException(
                status_code=400,
                detail="금일 업무 계획이 설정되지 않았습니다. 먼저 '금일 업무 플래닝' 기능을 사용하여 오늘의 업무를 설정해주세요."
            )
        
        # FSM 컨텍스트 생성
        context = DailyFSMContext(
            owner=request.owner,
            target_date=request.target_date,
            time_ranges=time_ranges,
            today_main_tasks=main_tasks,
            current_index=0,
            finished=False
        )
        
        # 세션 생성
        session_manager = get_session_manager()
        session_id = session_manager.create_session(context)
        
        # FSM 초기화
        llm_client = get_llm()
        task_parser = TaskParser(llm_client)
        fsm = DailyReportFSM(task_parser)
        
        # 첫 질문 가져오기
        result = fsm.start_session(context)
        
        # 세션 업데이트
        session_manager.update_session(session_id, result["state"])
        
        # 현재 시간대 가져오기
        current_time_range = time_ranges[result["current_index"]] if result["current_index"] < len(time_ranges) else ""
        
        return DailyStartResponse(
            status="in_progress",
            session_id=session_id,
            question=result["question"],
            meta={
                "owner": request.owner,
                "date": request.target_date.isoformat(),
                "time_range": current_time_range,
                "current_index": result["current_index"],
                "total_ranges": result["total_ranges"]
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 시작 실패: {str(e)}")


@router.post("/answer", response_model=DailyAnswerResponse)
async def answer_daily_question(
    request: DailyAnswerRequest,
    db: Session = Depends(get_db)
):
    """
    시간대 질문에 답변
    
    사용자의 답변을 받아서 다음 질문을 반환하거나,
    모든 시간대가 완료되면 최종 보고서를 반환합니다.
    """
    try:
        # 세션 조회
        session_manager = get_session_manager()
        context = session_manager.get_session(request.session_id)
        
        if not context:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        # FSM 실행
        llm_client = get_llm()
        task_parser = TaskParser(llm_client)
        fsm = DailyReportFSM(task_parser)
        
        # 답변 처리
        result = fsm.process_answer(context, request.answer)
        
        # 세션 업데이트
        updated_context = result["state"]
        session_manager.update_session(request.session_id, updated_context)
        
        # 완료 여부 확인
        if result["finished"]:
            # 보고서 생성
            report = build_daily_report(
                owner=updated_context.owner,
                target_date=updated_context.target_date,
                main_tasks=updated_context.today_main_tasks,
                time_tasks=updated_context.time_tasks,
                issues=updated_context.issues,
                plans=updated_context.plans
            )
            
            # 🔥 운영 DB에 저장 (PostgreSQL) - 기존 데이터 병합
            try:
                # 기존 보고서 확인 (금일 진행 업무가 이미 저장되어 있을 수 있음)
                existing_report = DailyReportRepository.get_by_owner_and_date(
                    db, report.owner, report.period_start
                )
                
                if existing_report:
                    # 기존 보고서가 있으면 병합 (CanonicalReport 구조 내에서)
                    print(f"📝 기존 보고서 발견 - 병합 모드")
                    
                    existing_json = existing_report.report_json.copy()
                    
                    # 기존 데이터를 CanonicalReport로 파싱
                    from app.domain.report.core.canonical_models import CanonicalReport
                    try:
                        existing_canonical = CanonicalReport(**existing_json)
                    except Exception as e:
                        print(f"⚠️  기존 데이터 파싱 실패, 새 데이터로 덮어쓰기: {e}")
                        existing_canonical = None
                    
                    # 병합 전략: CanonicalReport 구조 내에서 병합
                    if existing_canonical and existing_canonical.daily:
                        # 기존 daily.plans (익일 계획) 유지, 새 보고서의 다른 데이터로 업데이트
                        merged_daily = existing_canonical.daily.model_copy(deep=True)
                        
                        # 새로운 보고서의 데이터로 업데이트
                        if report.daily:
                            merged_daily.summary_tasks = report.daily.summary_tasks
                            merged_daily.detail_tasks = report.daily.detail_tasks
                            merged_daily.pending = report.daily.pending
                            # plans는 기존 것 유지 (이미 저장된 익일 계획 보존)
                            if not merged_daily.plans and report.daily.plans:
                                merged_daily.plans = report.daily.plans
                            merged_daily.notes = report.daily.notes if report.daily.notes else merged_daily.notes
                        
                        # 병합된 CanonicalReport 생성
                        merged_report = CanonicalReport(
                            report_id=report.report_id,
                            report_type=report.report_type,
                            owner=report.owner,
                            period_start=report.period_start,
                            period_end=report.period_end,
                            daily=merged_daily
                        )
                    else:
                        # 기존 데이터가 형식이 맞지 않으면 새 데이터 사용
                        merged_report = report
                    
                    # 순수한 CanonicalReport 형식으로 저장 (추가 필드 없음)
                    report_dict = merged_report.model_dump(mode='json')
                    
                    from app.domain.report.daily.schemas import DailyReportUpdate
                    db_report = DailyReportRepository.update(
                        db,
                        existing_report,
                        DailyReportUpdate(report_json=report_dict)
                    )
                    
                    print(f"💾 운영 DB 병합 완료: {report.owner} - {report.period_start}")
                    if merged_report.daily:
                        print(f"   - 익일 계획(plans): {len(merged_report.daily.plans)}개")
                        print(f"   - 세부 업무(detail_tasks): {len(merged_report.daily.detail_tasks)}개")
                    is_created = False
                else:
                    # 기존 보고서가 없으면 새로 생성 (순수 CanonicalReport 형식)
                    report_dict = report.model_dump(mode='json')
                    
                    report_create = DailyReportCreate(
                        owner=report.owner,
                        report_date=report.period_start,
                        report_json=report_dict
                    )
                    db_report = DailyReportRepository.create(db, report_create)
                    
                    print(f"💾 운영 DB 생성 완료: {report.owner} - {report.period_start}")
                    is_created = True
                
                # 🔥 PDF 자동 생성 및 저장
                try:
                    # PDF 생성 (파일명만 지정, 경로는 Generator가 처리)
                    pdf_filename = f"{report.owner}_{report.period_start}_일일보고서.pdf"
                    
                    pdf_generator = DailyReportPDFGenerator()
                    pdf_bytes = pdf_generator.generate(report, pdf_filename)
                    
                    print(f"📄 일일 보고서 PDF 생성 완료: backend/output/report_result/daily/{pdf_filename}")
                except Exception as pdf_error:
                    print(f"⚠️  PDF 생성 실패 (보고서는 저장됨): {str(pdf_error)}")
                    import traceback
                    traceback.print_exc()
                
                # 🔥 벡터 DB 자동 저장 (비동기 작업, 실패해도 계속 진행)
                try:
                    print(f"⏳ 벡터 DB 저장 시작...")
                    
                    # 최종 보고서 가져오기 (병합된 버전)
                    final_report_json = db_report.report_json
                    final_report = CanonicalReport(**final_report_json)
                    
                    # 자동 인제스트 함수 호출
                    result = ingest_single_report(
                        report=final_report,
                        api_key=os.getenv("OPENAI_API_KEY")
                    )
                    
                    if result["success"]:
                        print(f"✅ 벡터 DB 저장 완료: {result.get('uploaded_chunks', 0)}개 청크")
                    else:
                        print(f"⚠️  벡터 DB 저장 실패: {result.get('message', 'Unknown error')}")
                
                except Exception as vector_error:
                    print(f"⚠️  벡터 DB 저장 실패 (보고서는 저장됨): {str(vector_error)}")
                    
            except Exception as db_error:
                print(f"⚠️  운영 DB 저장 실패 (계속 진행): {str(db_error)}")
                # DB 저장 실패해도 보고서는 반환 (사용자에게는 성공으로 표시)
            
            # 세션 삭제
            session_manager.delete_session(request.session_id)
            
            return DailyAnswerResponse(
                status="finished",
                session_id=request.session_id,
                message="모든 시간대 입력이 완료되었습니다. 오늘 일일보고서를 정리했어요.",
                report=report
            )
        else:
            # 다음 질문 반환
            current_time_range = updated_context.time_ranges[result["current_index"]] if result["current_index"] < len(updated_context.time_ranges) else ""
            
            return DailyAnswerResponse(
                status="in_progress",
                session_id=request.session_id,
                question=result["question"],
                meta={
                    "time_range": current_time_range,
                    "current_index": result["current_index"],
                    "total_ranges": result["total_ranges"],
                    "tasks_collected": result["tasks_collected"]
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"답변 처리 실패: {str(e)}")


class SelectMainTasksRequest(BaseModel):
    """금일 진행 업무 선택 요청"""
    owner: str = Field(..., description="작성자")
    target_date: date = Field(..., description="보고서 날짜")
    main_tasks: List[Dict[str, Any]] = Field(
        ...,
        description="선택된 금일 진행 업무 리스트"
    )
    append: bool = Field(
        default=False,
        description="True면 기존 업무에 추가, False면 덮어쓰기"
    )


class SelectMainTasksResponse(BaseModel):
    """금일 진행 업무 선택 응답"""
    success: bool
    message: str
    saved_count: int


@router.post("/select_main_tasks", response_model=SelectMainTasksResponse)
async def select_main_tasks(
    request: SelectMainTasksRequest,
    db: Session = Depends(get_db)
):
    """
    금일 진행 업무 선택 및 저장
    
    사용자가 TodayPlan Chain에서 플래닝받은 업무 중 
    실제로 수행할 업무를 선택하여 저장합니다.
    
    저장된 업무는:
    1. 메모리에 임시 저장 (FSM 시작 시 사용)
    2. PostgreSQL에 부분 저장 (금일 진행 업무만, status="in_progress")
    """
    try:
        if not request.main_tasks:
            raise HTTPException(
                status_code=400,
                detail="최소 1개 이상의 업무를 선택해주세요."
            )
        
        # 1. 메모리 저장 (FSM용)
        store = get_main_tasks_store()
        store.save(
            owner=request.owner,
            target_date=request.target_date,
            main_tasks=request.main_tasks,
            append=request.append
        )
        
        # 2. PostgreSQL에 부분 저장 (금일 진행 업무만)
        try:
            # 기존 보고서 확인
            existing_report = DailyReportRepository.get_by_owner_and_date(
                db, request.owner, request.target_date
            )
            
            # CanonicalReport 구조로 부분 저장
            from app.domain.report.core.canonical_models import CanonicalReport, CanonicalDaily
            from app.domain.report.daily.daily_builder import generate_report_id
            
            new_plan_titles = [task.get("title", "") for task in request.main_tasks if task.get("title")]
            
            if existing_report:
                # 기존 보고서가 있으면 CanonicalReport 구조 내에서 업데이트
                existing_json = existing_report.report_json.copy()
                
                try:
                    existing_canonical = CanonicalReport(**existing_json)
                except Exception:
                    # 기존 데이터가 형식이 안 맞으면 새로 생성
                    existing_canonical = None
                
                if existing_canonical and existing_canonical.daily:
                    # 기존 daily 구조 유지하고 summary_tasks만 업데이트
                    updated_daily = existing_canonical.daily.model_copy(deep=True)
                    
                    if request.append:
                        # 기존 summary_tasks에 추가
                        existing_summary = updated_daily.summary_tasks.copy()
                        updated_daily.summary_tasks = existing_summary + new_plan_titles
                    else:
                        # 덮어쓰기
                        updated_daily.summary_tasks = new_plan_titles
                    
                    updated_report = CanonicalReport(
                        report_id=existing_canonical.report_id,
                        report_type=existing_canonical.report_type,
                        owner=existing_canonical.owner,
                        period_start=existing_canonical.period_start,
                        period_end=existing_canonical.period_end,
                        daily=updated_daily
                    )
                else:
                    # 기존 데이터가 없거나 형식이 안 맞으면 새로 생성
                    report_id = generate_report_id(request.owner, request.target_date)
                    updated_daily = CanonicalDaily(
                        header={
                            "작성일자": request.target_date.isoformat(),
                            "성명": request.owner
                        },
                        summary_tasks=new_plan_titles,
                        detail_tasks=[],
                        pending=[],
                        plans=[],
                        notes=""
                    )
                    updated_report = CanonicalReport(
                        report_id=report_id,
                        report_type="daily",
                        owner=request.owner,
                        period_start=request.target_date,
                        period_end=request.target_date,
                        daily=updated_daily
                    )
                
                from app.domain.report.daily.schemas import DailyReportUpdate
                DailyReportRepository.update(
                    db,
                    existing_report,
                    DailyReportUpdate(report_json=updated_report.model_dump(mode='json'))
                )
                print(f"💾 금일 진행 업무 업데이트 완료: {request.owner} - {request.target_date}")
            else:
                # 새로운 부분 보고서 생성 (CanonicalReport 구조)
                report_id = generate_report_id(request.owner, request.target_date)
                partial_daily = CanonicalDaily(
                    header={
                        "작성일자": request.target_date.isoformat(),
                        "성명": request.owner
                    },
                    summary_tasks=new_plan_titles,
                    detail_tasks=[],
                    pending=[],
                    plans=[],
                    notes=""
                )
                partial_report = CanonicalReport(
                    report_id=report_id,
                    report_type="daily",
                    owner=request.owner,
                    period_start=request.target_date,
                    period_end=request.target_date,
                    daily=partial_daily
                )
                
                DailyReportRepository.create(
                    db,
                    DailyReportCreate(
                        owner=request.owner,
                        report_date=request.target_date,
                        report_json=partial_report.model_dump(mode='json')
                    )
                )
                print(f"💾 금일 진행 업무 생성 완료: {request.owner} - {request.target_date}")
        
        except Exception as db_error:
            print(f"⚠️  PostgreSQL 저장 실패 (메모리 저장은 성공): {str(db_error)}")
            # DB 저장 실패해도 메모리 저장은 성공했으므로 계속 진행
        
        return SelectMainTasksResponse(
            success=True,
            message="금일 진행 업무가 저장되었습니다.",
            saved_count=len(request.main_tasks)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"업무 저장 실패: {str(e)}"
        )


class GetMainTasksRequest(BaseModel):
    """금일 진행 업무 조회 요청"""
    owner: str = Field(..., description="작성자")
    target_date: date = Field(..., description="보고서 날짜")


class GetMainTasksResponse(BaseModel):
    """금일 진행 업무 조회 응답"""
    success: bool
    main_tasks: List[Dict[str, Any]]
    count: int


@router.post("/get_main_tasks", response_model=GetMainTasksResponse)
async def get_main_tasks(request: GetMainTasksRequest):
    """
    저장된 금일 진행 업무 조회
    """
    try:
        store = get_main_tasks_store()
        main_tasks = store.get(
            owner=request.owner,
            target_date=request.target_date
        )
        
        if main_tasks is None:
            main_tasks = []
        
        return GetMainTasksResponse(
            success=True,
            main_tasks=main_tasks,
            count=len(main_tasks)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"업무 조회 실패: {str(e)}"
        )


class UpdateMainTasksRequest(BaseModel):
    """금일 진행 업무 수정 요청"""
    owner: str = Field(..., description="작성자")
    target_date: date = Field(..., description="보고서 날짜")
    main_tasks: List[Dict[str, Any]] = Field(
        ...,
        description="수정된 금일 진행 업무 리스트"
    )


class UpdateMainTasksResponse(BaseModel):
    """금일 진행 업무 수정 응답"""
    success: bool
    message: str
    updated_count: int


@router.put("/update_main_tasks", response_model=UpdateMainTasksResponse)
async def update_main_tasks(
    request: UpdateMainTasksRequest,
    db: Session = Depends(get_db)
):
    """
    금일 진행 업무 수정
    
    저장된 금일 진행 업무를 수정합니다.
    - 메모리 (MainTasksStore) 업데이트
    - PostgreSQL 업데이트 (tasks 필드만)
    """
    try:
        if not request.main_tasks:
            raise HTTPException(
                status_code=400,
                detail="최소 1개 이상의 업무가 필요합니다."
            )
        
        # 1. 메모리 업데이트
        store = get_main_tasks_store()
        store.save(
            owner=request.owner,
            target_date=request.target_date,
            main_tasks=request.main_tasks,
            append=False  # 덮어쓰기
        )
        
        # 2. PostgreSQL 업데이트
        try:
            existing_report = DailyReportRepository.get_by_owner_and_date(
                db, request.owner, request.target_date
            )
            
            # CanonicalReport 구조로 업데이트
            from app.domain.report.core.canonical_models import CanonicalReport, CanonicalDaily
            from app.domain.report.daily.daily_builder import generate_report_id
            
            summary_tasks = [task.get("title", "") for task in request.main_tasks if task.get("title")]
            
            if existing_report:
                # 기존 보고서가 있으면 CanonicalReport 구조 내에서 업데이트
                existing_json = existing_report.report_json.copy()
                
                try:
                    existing_canonical = CanonicalReport(**existing_json)
                except Exception:
                    # 기존 데이터가 형식이 안 맞으면 새로 생성
                    existing_canonical = None
                
                if existing_canonical and existing_canonical.daily:
                    # 기존 daily 구조 유지하고 summary_tasks만 업데이트
                    updated_daily = existing_canonical.daily.model_copy(deep=True)
                    updated_daily.summary_tasks = summary_tasks
                    
                    updated_report = CanonicalReport(
                        report_id=existing_canonical.report_id,
                        report_type=existing_canonical.report_type,
                        owner=existing_canonical.owner,
                        period_start=existing_canonical.period_start,
                        period_end=existing_canonical.period_end,
                        daily=updated_daily
                    )
                else:
                    # 기존 데이터가 없거나 형식이 안 맞으면 새로 생성
                    report_id = generate_report_id(request.owner, request.target_date)
                    updated_daily = CanonicalDaily(
                        header={
                            "작성일자": request.target_date.isoformat(),
                            "성명": request.owner
                        },
                        summary_tasks=summary_tasks,
                        detail_tasks=[],
                        pending=[],
                        plans=[],
                        notes=""
                    )
                    updated_report = CanonicalReport(
                        report_id=report_id,
                        report_type="daily",
                        owner=request.owner,
                        period_start=request.target_date,
                        period_end=request.target_date,
                        daily=updated_daily
                    )
                
                from app.domain.report.daily.schemas import DailyReportUpdate
                DailyReportRepository.update(
                    db,
                    existing_report,
                    DailyReportUpdate(report_json=updated_report.model_dump(mode='json'))
                )
                print(f"💾 금일 진행 업무 수정 완료 (DB): {request.owner} - {request.target_date}")
            else:
                # 보고서가 없으면 새로 생성 (CanonicalReport 구조)
                report_id = generate_report_id(request.owner, request.target_date)
                partial_daily = CanonicalDaily(
                    header={
                        "작성일자": request.target_date.isoformat(),
                        "성명": request.owner
                    },
                    summary_tasks=summary_tasks,
                    detail_tasks=[],
                    pending=[],
                    plans=[],
                    notes=""
                )
                partial_report = CanonicalReport(
                    report_id=report_id,
                    report_type="daily",
                    owner=request.owner,
                    period_start=request.target_date,
                    period_end=request.target_date,
                    daily=partial_daily
                )
                
                DailyReportRepository.create(
                    db,
                    DailyReportCreate(
                        owner=request.owner,
                        report_date=request.target_date,
                        report_json=partial_report.model_dump(mode='json')
                    )
                )
                print(f"💾 금일 진행 업무 생성 완료 (DB): {request.owner} - {request.target_date}")
        
        except Exception as db_error:
            print(f"⚠️  PostgreSQL 업데이트 실패 (메모리는 성공): {str(db_error)}")
            # DB 실패해도 메모리는 성공했으므로 계속 진행
        
        return UpdateMainTasksResponse(
            success=True,
            message="금일 진행 업무가 수정되었습니다.",
            updated_count=len(request.main_tasks)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"업무 수정 실패: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "service": "daily"}

