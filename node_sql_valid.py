"""
node_sql_valid.py — SQL 검증 노드
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
수정 대상:
  - 금지 키워드 추가 시 FORBIDDEN_KEYWORDS 수정
  - 검증 단계 추가 시 sql_validator_node() 내에 단계 추가

역할: 생성된 SQL을 2단계로 검증한다.
  1단계 — 안전성: SELECT 문 확인, 금지 키워드 차단
  2단계 — 문법:   EXPLAIN으로 PostgreSQL 파서 검사 (실제 실행 없음)
"""

import psycopg2
from agent_state import GraphState
from db_config import get_conn, get_conn_by

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE",
    "ALTER", "CREATE", "REPLACE", "MERGE", "EXEC",
]


def _safety_check(sql: str):
    sql_upper = sql.upper()
    if not sql_upper.lstrip().startswith("SELECT"):
        return "SELECT 문으로 시작하지 않습니다."
    for kw in FORBIDDEN_KEYWORDS:
        if kw in sql_upper:
            return f"허용되지 않는 키워드 포함: {kw}"
    return None


def _syntax_check(sql: str, db_config: dict = None):
    conn = None
    try:
        conn = get_conn_by(db_config) if db_config else get_conn()
        cur  = conn.cursor()
        cur.execute(f"EXPLAIN {sql}")
        cur.close()
        return None
    except psycopg2.Error as e:
        return f"SQL 문법 오류: {e.pgerror or str(e)}"
    finally:
        if conn:
            conn.close()


def sql_validator_node(state: GraphState) -> dict:
    sql       = state.get("generated_sql", "")
    db_config = state.get("db_config")

    error = _safety_check(sql)
    if error:
        return {"validation_error": error}

    error = _syntax_check(sql, db_config)
    if error:
        return {"validation_error": error}

    return {"validation_error": None}
