from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.plan import router as plan_router
from app.api.v1.endpoints.daily import router as daily_router
from app.api.v1.endpoints.daily_report import router as daily_report_router
from app.api.v1.endpoints.weekly_report import router as weekly_report_router
from app.api.v1.endpoints.monthly_report import router as monthly_report_router
from app.api.v1.endpoints.pdf_export import router as pdf_export_router
from app.api.v1.endpoints.chatbot import router as chatbot_router
from app.api.v1.endpoints.report_chat import router as report_chat_router

api_router = APIRouter()

# Auth 엔드포인트
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"]
)

# Users 엔드포인트
api_router.include_router(
    users_router,
    prefix="/users",
    tags=["Users"]
)

# Reports 엔드포인트
api_router.include_router(
    reports_router,
    tags=["Reports"]
)

# Plan 엔드포인트
api_router.include_router(
    plan_router,
    tags=["Plan"]
)

# Daily 엔드포인트
api_router.include_router(
    daily_router,
    tags=["Daily"]
)

# Daily Report (운영 DB) 엔드포인트
api_router.include_router(
    daily_report_router,
    tags=["Daily Report"]
)

# Weekly Report (주간 보고서) 엔드포인트
api_router.include_router(
    weekly_report_router,
    tags=["Weekly Report"]
)

# Monthly Report (월간 보고서) 엔드포인트
api_router.include_router(
    monthly_report_router,
    tags=["Monthly Report"]
)

# PDF Export (PDF 다운로드) 엔드포인트
api_router.include_router(
    pdf_export_router,
    tags=["PDF Export"]
)

# Chatbot 엔드포인트
api_router.include_router(
    chatbot_router,
    prefix="/chatbot",
    tags=["Chatbot"]
)

# Report Chat (일일보고서 RAG 챗봇) 엔드포인트
api_router.include_router(
    report_chat_router,
    tags=["Report Chat"]
)
