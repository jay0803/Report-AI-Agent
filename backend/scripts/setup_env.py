"""
.env 파일 설정 도우미 스크립트

사용법:
    python setup_env.py
"""

import os
from pathlib import Path

def setup_env():
    """
    .env 파일이 없으면 env.example을 복사하여 생성
    """
    backend_dir = Path(__file__).resolve().parent.parent
    env_file = backend_dir / ".env"
    env_example = backend_dir.parent / "env.example"
    
    # .env 파일이 이미 있으면 종료
    if env_file.exists():
        print(f"[OK] .env file already exists: {env_file}")
        print("\n[INFO] Check LangSmith configuration:")
        print("   - LANGSMITH_API_KEY: Get from https://smith.langchain.com")
        print("   - LANGSMITH_PROJECT: Project name (default: virtual-assistant-rag)")
        print("   - LANGSMITH_TRACING: true (enable tracing)")
        return
    
    # env.example 파일이 없으면 에러
    if not env_example.exists():
        print(f"[ERROR] env.example file not found: {env_example}")
        return
    
    # env.example을 .env로 복사
    try:
        content = env_example.read_text(encoding="utf-8")
        env_file.write_text(content, encoding="utf-8")
        print(f"[OK] .env file created: {env_file}")
        print("\n[WARNING] Please update the following settings:")
        print("   1. OPENAI_API_KEY: OpenAI API key")
        print("   2. LANGSMITH_API_KEY: LangSmith API key (optional)")
        print("   3. DATABASE_URL: Database connection string")
        print("   4. SECRET_KEY: JWT secret key")
        print("   5. OAuth settings (Google, Kakao, Naver)")
        print("\n[INFO] See LANGSMITH_SETUP.md for details.")
    except Exception as e:
        print(f"[ERROR] Failed to create .env file: {e}")

if __name__ == "__main__":
    setup_env()

