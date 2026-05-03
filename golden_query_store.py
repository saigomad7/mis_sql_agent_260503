""" 
golden_query_store.py — FAISS 기반 Golden Query 저장소
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
설계:
  ┌────────────────────────────────────────────────┐
  │  golden_{team_id}.json  ← 원본 메타데이터     │
  │  faiss_db/golden_{team_id}/  ← 유사도 검색용  │
  └────────────────────────────────────────────────┘

- JSON : 추가·삭제·목록 조회 (source of truth)
- FAISS: 유사 질문 벡터 검색용 (JSON과 항상 동기화)

FAISS는 삭제 연산이 없으므로 JSON 변경 시 인덱스 재빌드.
"""
import os
os.chdir("C:\\Users\\USER\\Documents\\agent\\sql_agent\\mis_sql_agent_v3")

import os
import json
import uuid
from datetime import datetime
from langchain_community.vectorstores import FAISS
from vector_store import get_embeddings, golden_path, faiss_exists, FAISS_DIR


# ── JSON 메타 파일 경로 ────────────────────────────────────────

def _json_path(team_id: str) -> str:
    os.makedirs(FAISS_DIR, exist_ok=True)
    return os.path.join(FAISS_DIR, f"golden_{team_id}.json")


def _load_all(team_id: str) -> list:
    path = _json_path(team_id)
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_all(team_id: str, records: list):
    with open(_json_path(team_id), "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


# ── FAISS 인덱스 재빌드 ───────────────────────────────────────

def _rebuild_index(team_id: str, records: list):
    path = golden_path(team_id)
    os.makedirs(path, exist_ok=True)

    if not records:
        # 비어있으면 더미 인덱스 생성 (검색 시 early-return)
        return

    texts  = [r["question"] for r in records]
    metas  = [{"id": r["id"], "sql": r["sql"], "description": r.get("description", "")}
              for r in records]
    emb    = get_embeddings()
    vs     = FAISS.from_texts(texts, emb, metadatas=metas)
    vs.save_local(path)


# ── 저장 ──────────────────────────────────────────────────────

def save_golden_query(
    team_id: str,
    question: str,
    sql: str,
    description: str = "",
) -> str:
    """검증된 쿼리 저장. 반환: 쿼리 ID"""
    records = _load_all(team_id)
    qid     = str(uuid.uuid4())
    records.append({
        "id":          qid,
        "question":    question,
        "sql":         sql,
        "description": description,
        "created_at":  datetime.now().isoformat(),
    })
    _save_all(team_id, records)
    _rebuild_index(team_id, records)
    return qid


# ── 검색 ──────────────────────────────────────────────────────

def search_golden_queries(
    team_id: str,
    user_query: str,
    n_results: int = 3,
    distance_threshold: float = 1.2,
) -> list:
    """
    FAISS로 유사 질문 검색.
    distance_threshold: L2 거리 초과 시 제외 (값이 클수록 느슨).
    """
    path = golden_path(team_id)
    if not faiss_exists(path):
        return []

    records = _load_all(team_id)
    if not records:
        return []

    emb   = get_embeddings()
    vs    = FAISS.load_local(path, emb, allow_dangerous_deserialization=True)
    k     = min(n_results, len(records))
    pairs = vs.similarity_search_with_score(user_query, k=k)

    results = []
    for doc, score in pairs:
        if score <= distance_threshold:
            results.append({
                "question":    doc.page_content,
                "sql":         doc.metadata.get("sql", ""),
                "description": doc.metadata.get("description", ""),
                "score":       round(float(score), 4),
            })
    return results


# ── 목록 ──────────────────────────────────────────────────────

def list_golden_queries(team_id: str) -> list:
    """저장된 모든 Golden Query 반환"""
    return _load_all(team_id)


# ── 삭제 ──────────────────────────────────────────────────────

def delete_golden_query(team_id: str, query_id: str) -> bool:
    records  = _load_all(team_id)
    filtered = [r for r in records if r["id"] != query_id]
    if len(filtered) == len(records):
        return False
    _save_all(team_id, filtered)
    _rebuild_index(team_id, filtered)
    return True


# ── 시드 (초기 데이터) ────────────────────────────────────────

def seed_golden_queries(team_id: str, examples: list) -> int:
    """
    초기 예시 쿼리 일괄 삽입.
    examples: [{"question": ..., "sql": ..., "description": ...}]
    """
    count = 0
    for ex in examples:
        save_golden_query(team_id, ex["question"], ex["sql"],
                          ex.get("description", ""))
        count += 1
    return count
