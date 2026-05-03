"""
node_schema_rag.py — Schema RAG + Golden Query 통합 검색 노드
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
역할:
  1. Schema RAG  : 질의와 관련된 테이블만 벡터 검색으로 선택
  2. Golden Query: 유사한 검증된 예시 쿼리 검색
  3. 선택된 테이블만으로 스키마 텍스트 생성 (컨텍스트 절감)

ChromaDB 미초기화 시 자동 fallback → 전체 테이블 사용
"""

from agent_state import GraphState
from schema_embedder import search_similar_tables
from golden_query_store import search_golden_queries
from node_schema import build_schema_text   # v2에서 재사용


def schema_rag_node(state: GraphState) -> dict:
    team_id    = state.get("team_id", "")
    user_query = state.get("user_query", "")
    table_defs = state.get("domain_context", {}).get("table_definitions", {})
    db_config  = state.get("db_config", {})

    # ── 1. Schema RAG: 관련 테이블 벡터 검색 ───────────────────
    try:
        relevant = search_similar_tables(team_id, user_query, n_results=4)
    except Exception:
        relevant = []

    if not relevant:                        # fallback: 전체 테이블
        relevant = list(table_defs.keys())
        rag_used = False
    else:
        rag_used = True

    # ── 2. Golden Query: 유사 예시 검색 ────────────────────────
    try:
        examples = search_golden_queries(team_id, user_query, n_results=3)
    except Exception:
        examples = []

    # ── 3. 선택된 테이블만으로 스키마 텍스트 생성 ───────────────
    filtered = {t: table_defs[t] for t in relevant if t in table_defs}
    try:
        schema_text = build_schema_text(filtered, db_config)
    except Exception as e:
        return {"status": "error", "error_message": f"스키마 로드 실패: {e}"}

    # RAG 결과 요약 출력 (Spyder 확인용)
    print(f"[Schema RAG] 선택 테이블({len(relevant)}): {relevant}  |  "
          f"RAG={'ON' if rag_used else 'fallback'}  |  "
          f"Golden 예시: {len(examples)}건")

    return {
        "db_schema":       schema_text,
        "relevant_tables": relevant,
        "similar_examples": examples,
    }
