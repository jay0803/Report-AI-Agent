"""
금일 진행 업무 선택 Flow API 엔드포인트 테스트

FastAPI 서버가 실행된 상태에서 테스트합니다.

Usage:
    1. 백엔드 서버 실행: uvicorn app.main:app --reload
    2. 이 스크립트 실행: python test_api_endpoints.py

Author: AI Assistant
Created: 2025-11-19
"""
import requests
from datetime import date


API_BASE_URL = "http://localhost:8000/api/v1"


def test_today_plan():
    """POST /plan/today 테스트"""
    print("=" * 60)
    print("POST /plan/today 테스트")
    print("=" * 60)
    
    url = f"{API_BASE_URL}/plan/today"
    payload = {
        "owner": "김보험",
        "target_date": str(date.today())
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 성공!")
            print(f"   요약: {data.get('summary', 'N/A')}")
            print(f"   추천 업무 수: {len(data.get('tasks', []))}")
            
            for i, task in enumerate(data.get('tasks', []), 1):
                print(f"\n   [{i}] {task.get('title', 'N/A')}")
                print(f"       설명: {task.get('description', 'N/A')}")
                print(f"       우선순위: {task.get('priority', 'N/A')}")
                print(f"       예상 시간: {task.get('expected_time', 'N/A')}")
                print(f"       카테고리: {task.get('category', 'N/A')}")
            
            return data.get('tasks', [])
        else:
            print(f"❌ 실패: {response.text}")
            return []
    
    except Exception as e:
        print(f"❌ 오류: {e}")
        return []


def test_select_main_tasks(tasks):
    """POST /daily/select_main_tasks 테스트"""
    print("\n" + "=" * 60)
    print("POST /daily/select_main_tasks 테스트")
    print("=" * 60)
    
    if not tasks:
        print("⚠️  추천 업무가 없어서 스킵합니다.")
        return False
    
    # 첫 3개 업무 선택
    selected_tasks = tasks[:3]
    
    url = f"{API_BASE_URL}/daily/select_main_tasks"
    payload = {
        "owner": "김보험",
        "target_date": str(date.today()),
        "main_tasks": selected_tasks
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 성공!")
            print(f"   메시지: {data.get('message', 'N/A')}")
            print(f"   저장된 업무 수: {data.get('saved_count', 0)}")
            
            for i, task in enumerate(selected_tasks, 1):
                print(f"   [{i}] {task.get('title', 'N/A')}")
            
            return True
        else:
            print(f"❌ 실패: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def test_daily_start():
    """POST /daily/start 테스트 (자동 로딩)"""
    print("\n" + "=" * 60)
    print("POST /daily/start 테스트 (main_tasks 자동 로딩)")
    print("=" * 60)
    
    url = f"{API_BASE_URL}/daily/start"
    payload = {
        "owner": "김보험",
        "target_date": str(date.today())
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 성공!")
            print(f"   세션 ID: {data.get('session_id', 'N/A')}")
            print(f"   질문: {data.get('question', 'N/A')}")
            print(f"   현재 인덱스: {data.get('current_index', 0)}")
            print(f"   전체 시간대: {data.get('total_ranges', 0)}")
            print(f"   완료 여부: {data.get('finished', False)}")
            
            print("\n✅ main_tasks가 자동으로 로딩되었습니다!")
            return True
        else:
            print(f"❌ 실패: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def test_health_check():
    """Health check 테스트"""
    print("\n" + "=" * 60)
    print("Health Check")
    print("=" * 60)
    
    endpoints = [
        "/plan/health",
        "/daily/health"
    ]
    
    for endpoint in endpoints:
        try:
            url = f"{API_BASE_URL}{endpoint}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {endpoint}: {data.get('status', 'unknown')}")
            else:
                print(f"❌ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("금일 진행 업무 선택 Flow - API 엔드포인트 테스트")
    print("=" * 70)
    print("\n⚠️  백엔드 서버가 실행 중이어야 합니다!")
    print("   실행 명령: cd backend && uvicorn app.main:app --reload")
    print("\n")
    
    # Health check
    test_health_check()
    
    # Step 1: TodayPlan API 호출
    tasks = test_today_plan()
    
    # Step 2: 선택한 업무 저장
    if tasks:
        success = test_select_main_tasks(tasks)
        
        # Step 3: /daily/start로 자동 로딩 확인
        if success:
            test_daily_start()
    
    print("\n" + "=" * 70)
    print("✅ 전체 테스트 완료!")
    print("=" * 70)

