"""
node_sql_exec.py — SQL 실행 노드
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
수정 대상:
  - 최대 반환 행 수 변경 시 MAX_ROWS 수정

역할: 검증된 SQL을 DB에서 실행하고 결과를 반환한다.
"""

import time
from agent_state import GraphState
from db_config import get_dict_conn, get_dict_conn_by

MAX_ROWS = 500


def sql_executor_node(state: GraphState) -> dict:
    conn, cursor = None, None
    db_config    = state.get("db_config")
    try:
        conn, cursor = get_dict_conn_by(db_config) if db_config else get_dict_conn()
        t0 = time.time()
        cursor.execute(state.get("generated_sql", ""))
        elapsed = round((time.time() - t0) * 1000, 2)
        rows    = [dict(r) for r in cursor.fetchmany(MAX_ROWS)]
        return {
            "query_result":    rows,
            "execution_error": None,
            "exec_time_ms":    elapsed,
        }
    except Exception as e:
        return {
            "query_result":    [],
            "execution_error": str(e),
            "exec_time_ms":    0.0,
        }
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()
