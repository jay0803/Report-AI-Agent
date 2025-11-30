"""
Daily Report 파일 미리보기

bulk_daily_ingest.py를 실행하기 전에 어떤 파일들이 처리될지 미리 확인하는 스크립트
"""
import sys
import os
from pathlib import Path

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# backend 경로를 Python path에 추가
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.insert(0, str(backend_dir))

# find_all_txt_files와 read_json_objects_from_file를 직접 구현 (DB 연결 없이)
import json
import re


def find_all_txt_files(base_dir: Path):
    """base_dir 하위의 모든 txt 파일 찾기"""
    return sorted(base_dir.rglob("*.txt"))


def read_json_objects_from_file(file_path: Path):
    """txt 파일에서 여러 JSON 객체를 읽어서 리스트로 반환"""
    json_objects = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 빈 줄로 분리된 JSON 객체들을 추출
        json_texts = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
        
        for json_text in json_texts:
            try:
                obj = json.loads(json_text)
                json_objects.append(obj)
            except json.JSONDecodeError:
                continue
    
    except Exception as e:
        print(f"파일 읽기 오류 ({file_path}): {e}")
    
    return json_objects


def preview_files():
    """파일 미리보기"""
    print("=" * 70)
    print("👀 Daily Report 파일 미리보기")
    print("=" * 70)
    
    # 1. 기본 경로 설정
    base_dir = backend_dir / "Data" / "mock_reports" / "daily"
    
    if not base_dir.exists():
        print(f"❌ 디렉토리가 존재하지 않습니다: {base_dir}")
        return
    
    print(f"\n📁 대상 디렉토리: {base_dir}")
    
    # 2. 모든 txt 파일 찾기
    txt_files = find_all_txt_files(base_dir)
    print(f"📄 발견된 txt 파일: {len(txt_files)}개\n")
    
    if not txt_files:
        print("⚠️  txt 파일이 없습니다.")
        return
    
    # 3. 각 폴더별 파일 통계
    folder_stats = {}
    total_json_count = 0
    
    for file_path in txt_files:
        folder_name = file_path.parent.name
        
        # JSON 객체 수 확인
        json_objects = read_json_objects_from_file(file_path)
        json_count = len(json_objects)
        total_json_count += json_count
        
        if folder_name not in folder_stats:
            folder_stats[folder_name] = {
                "files": [],
                "total_json": 0
            }
        
        folder_stats[folder_name]["files"].append({
            "name": file_path.name,
            "json_count": json_count
        })
        folder_stats[folder_name]["total_json"] += json_count
    
    # 4. 폴더별 출력
    print("📂 폴더별 파일 목록:\n")
    
    for folder_name in sorted(folder_stats.keys()):
        stats = folder_stats[folder_name]
        print(f"📁 {folder_name}")
        print(f"   ├─ 파일 수: {len(stats['files'])}개")
        print(f"   ├─ 보고서 수: {stats['total_json']}개")
        print(f"   └─ 파일 목록:")
        
        for file_info in stats["files"]:
            print(f"      ├─ {file_info['name']} ({file_info['json_count']}개)")
        
        print()
    
    # 5. 전체 통계
    print("=" * 70)
    print("📊 전체 통계:")
    print(f"   ├─ 폴더 수: {len(folder_stats)}개")
    print(f"   ├─ 파일 수: {len(txt_files)}개")
    print(f"   └─ 총 보고서 수: {total_json_count}개")
    print("=" * 70)
    
    # 6. 샘플 미리보기
    print("\n📖 첫 번째 파일 샘플 미리보기:\n")
    
    if txt_files:
        first_file = txt_files[0]
        json_objects = read_json_objects_from_file(first_file)
        
        if json_objects:
            first_json = json_objects[0]
            print(f"파일: {first_file.name}")
            print(f"작성일자: {first_json.get('상단정보', {}).get('작성일자', 'N/A')}")
            print(f"성명: {first_json.get('상단정보', {}).get('성명', 'N/A')}")
            print(f"세부업무 수: {len(first_json.get('세부업무', []))}개")
            print(f"금일 진행 업무: {first_json.get('금일_진행_업무', 'N/A')[:50]}...")
    
    print("\n" + "=" * 70)
    print("✅ 미리보기 완료!")
    print("\n실행하려면:")
    print("  python backend/tools/bulk_daily_ingest.py")
    print("=" * 70)


if __name__ == "__main__":
    preview_files()

