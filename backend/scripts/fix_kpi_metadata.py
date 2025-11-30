"""
KPI 청크의 keywords를 리스트에서 문자열로 변환
"""
import sys
import codecs
import json
from pathlib import Path

# Windows CMD에서 UTF-8 출력 설정
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# 프로젝트 루트를 기준으로 경로 설정
backend_dir = Path(__file__).resolve().parent.parent
kpi_chunks_path = backend_dir / "output" / "KPI 자료_kpi_chunks.json"

print(f"📂 파일 로드 중: {kpi_chunks_path}")

# 청크 로드
with open(kpi_chunks_path, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"✅ {len(chunks)}개 청크 로드 완료")

# keywords를 리스트에서 문자열로 변환
fixed_count = 0
for chunk in chunks:
    metadata = chunk.get("metadata", {})
    keywords = metadata.get("keywords", "")
    
    if isinstance(keywords, list):
        # 리스트를 문자열로 변환
        metadata["keywords"] = ", ".join(keywords)
        fixed_count += 1

print(f"🔧 {fixed_count}개 청크의 keywords 수정됨")

# 저장
with open(kpi_chunks_path, "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

print(f"✅ 파일 저장 완료: {kpi_chunks_path}")
print()
print("이제 다시 업로드를 시도하세요:")
print("  python test_ingestion_pipeline.py")

