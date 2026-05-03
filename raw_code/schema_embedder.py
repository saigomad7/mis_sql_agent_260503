"""
schema_embedder.py — FAISS 기반 Schema RAG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
초기화 : setup_rag.py 에서 1회 실행
검색   : node_schema_rag.py 에서 질의마다 호출
"""

import os
from langchain_community.vectorstores import FAISS
from vector_store import get_embeddings, schema_path, faiss_exists


# ── 인덱스 구축 ───────────────────────────────────────────────

def build_schema_index(team_id: str, table_definitions: dict) -> int:
    """
    TABLE_DEFINITIONS를 FAISS에 임베딩 저장.
    기존 인덱스를 덮어쓰므로 스키마 변경 시 재실행.
    반환: 저장된 테이블 수
    """
    docs, metas = [], []
    for table_name, tbl_def in table_definitions.items():
        col_lines = "\n".join(
            f"  - {col}: {desc}"
            for col, desc in tbl_def.get("columns", {}).items()
        )
        text = (
            f"테이블명: {table_name}\n"
            f"설명: {tbl_def.get('description', '')}\n"
            f"비즈니스의미: {tbl_def.get('business_meaning', '')}\n"
            f"컬럼:\n{col_lines}\n"
            f"주의: {tbl_def.get('notes', '')}"
        )
        docs.append(text)
        metas.append({"table_name": table_name, "team_id": team_id})

    emb  = get_embeddings()
    vs   = FAISS.from_texts(docs, emb, metadatas=metas)
    path = schema_path(team_id)
    os.makedirs(path, exist_ok=True)
    vs.save_local(path)
    return len(docs)


# ── 관련 테이블 검색 ──────────────────────────────────────────

def search_similar_tables(
    team_id: str,
    user_query: str,
    n_results: int = 4,
) -> list:
    """
    질의와 cosine 유사도가 높은 테이블 이름 목록 반환.
    인덱스 미존재 시 빈 리스트 반환 (호출부에서 fallback 처리).
    """
    path = schema_path(team_id)
    if not faiss_exists(path):
        return []

    emb  = get_embeddings()
    vs   = FAISS.load_local(path, emb, allow_dangerous_deserialization=True)
    docs = vs.similarity_search(user_query, k=n_results)
    return [d.metadata["table_name"] for d in docs]
