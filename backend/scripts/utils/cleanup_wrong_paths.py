"""
잘못된 경로에 생성된 파일/폴더 정리

backend/backend/output 같은 중복 경로를 삭제합니다.

실행 방법:
    python -m debug.cleanup_wrong_paths
"""
import sys
from pathlib import Path
import shutil

# 프로젝트 루트
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def cleanup_wrong_paths():
    """잘못된 경로 정리"""
    print("=" * 80)
    print("🧹 잘못된 경로 정리")
    print("=" * 80)
    print()
    
    # 잘못된 경로 목록
    wrong_paths = [
        project_root / "backend" / "output",  # backend/backend/output
        project_root / "Data" / "chroma",  # 혹시 있을 수 있는 루트 레벨 Data
        project_root / "backend" / "output" / "report_result" / "daily" / "output",  # 중복 경로
        project_root / "backend" / "output" / "report_result" / "weekly" / "output",  # 중복 경로
        project_root / "backend" / "output" / "report_result" / "monthly" / "output",  # 중복 경로
    ]
    
    removed_count = 0
    
    for wrong_path in wrong_paths:
        if wrong_path.exists():
            try:
                if wrong_path.is_dir():
                    shutil.rmtree(wrong_path)
                    print(f"✅ 디렉토리 삭제: {wrong_path.relative_to(project_root)}")
                else:
                    wrong_path.unlink()
                    print(f"✅ 파일 삭제: {wrong_path.relative_to(project_root)}")
                removed_count += 1
            except Exception as e:
                print(f"❌ 삭제 실패 ({wrong_path.relative_to(project_root)}): {e}")
        else:
            print(f"ℹ️  경로 없음: {wrong_path.relative_to(project_root)}")
    
    print()
    print("=" * 80)
    if removed_count > 0:
        print(f"✅ {removed_count}개 항목 정리 완료")
    else:
        print("ℹ️  정리할 항목 없음")
    print("=" * 80)
    print()
    
    # 올바른 경로 확인
    print("📂 올바른 경로 확인:")
    correct_output_dir = project_root / "backend" / "output" / "report_result"
    if correct_output_dir.exists():
        print(f"   ✅ {correct_output_dir.relative_to(project_root)} (존재)")
    else:
        print(f"   ℹ️  {correct_output_dir.relative_to(project_root)} (아직 없음)")
    print()


if __name__ == "__main__":
    cleanup_wrong_paths()

