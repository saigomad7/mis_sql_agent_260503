"""
setup_rag.py — Schema RAG + Golden Query 초기화 (1회 실행)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
실행 방법:
  python setup_rag.py          # Spyder 셀 실행 또는 터미널
  python setup_rag.py --reset  # 기존 인덱스 초기화 후 재빌드

수행 작업:
  1. faiss_db/schema_team_a/  — 테이블 설명 FAISS 인덱스 빌드
  2. faiss_db/golden_team_a/  — QUERY_EXAMPLES를 Golden Query로 시드
"""

import argparse
import shutil
import os

from schema_embedder   import build_schema_index
from golden_query_store import seed_golden_queries
from vector_store      import FAISS_DIR, schema_path, golden_path
from domain_team_a     import (
    TEAM_ID,
    TABLE_DEFINITIONS,
    QUERY_EXAMPLES,
)


def reset_indices(team_id: str):
    for p in [schema_path(team_id), golden_path(team_id)]:
        if os.path.isdir(p):
            shutil.rmtree(p)
            print(f"  🗑  삭제: {p}")

    # JSON 파일도 초기화
    json_file = os.path.join(FAISS_DIR, f"golden_{team_id}.json")
    if os.path.isfile(json_file):
        os.remove(json_file)
        print(f"  🗑  삭제: {json_file}")


def main(reset: bool = False):
    print("=" * 56)
    print("  RAG 초기화 시작")
    print("=" * 56)

    if reset:
        print("\n[0] 기존 인덱스 초기화...")
        reset_indices(TEAM_ID)

    # ── 1. Schema RAG ─────────────────────────────────────────
    print(f"\n[1] Schema RAG 인덱스 빌드 (team_id={TEAM_ID})")
    n = build_schema_index(TEAM_ID, TABLE_DEFINITIONS)
    print(f"    ✅ 테이블 {n}개 인덱싱 완료")

    # ── 2. Golden Query 시드 ─────────────────────────────────
    print(f"\n[2] Golden Query 시드 삽입 (team_id={TEAM_ID})")
    c = seed_golden_queries(
        TEAM_ID,
        [{"question": e["question"], "sql": e["sql"], "description": e.get("description", "")}
         for e in QUERY_EXAMPLES],
    )
    print(f"    ✅ {c}개 예시 쿼리 저장 완료")

    print("\n" + "=" * 56)
    print("  초기화 완료 ─ 이제 main.py를 실행할 수 있습니다.")
    print("=" * 56)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="기존 인덱스 삭제 후 재빌드")
    args = parser.parse_args()
    main(reset=args.reset)
