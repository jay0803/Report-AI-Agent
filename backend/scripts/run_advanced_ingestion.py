"""
일일보고서 고급 Ingestion 실행 스크립트
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from ingestion.ingest_daily_advanced import ingest_daily_reports_advanced
import argparse


def main():
    parser = argparse.ArgumentParser(description="일일보고서 고급 Ingestion")
    parser.add_argument("--api-key", type=str, help="OpenAI API 키")
    parser.add_argument("--model-type", type=str, choices=["openai", "hf"], default="openai", help="임베딩 모델 타입")
    parser.add_argument("--no-llm-refine", action="store_true", help="LLM 재정제 비활성화")
    
    args = parser.parse_args()
    
    ingest_daily_reports_advanced(
        api_key=args.api_key,
        model_type=args.model_type,
        use_llm_refine=not args.no_llm_refine
    )


if __name__ == "__main__":
    main()

