#!/bin/bash

# Virtual Desk Assistant - Backend 실행 스크립트

echo "🚀 Starting Virtual Desk Assistant Backend..."

# 프로젝트 루트로 이동
cd "$(dirname "$0")"

# Conda 환경 활성화
source ~/miniforge3/etc/profile.d/conda.sh
conda activate virtual-assistant

# Backend 실행
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
