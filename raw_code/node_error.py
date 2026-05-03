"""
node_error.py — 에러 처리 노드
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
역할: SQL 재시도 최대 횟수 초과 시 에러 응답을 조립한다.
"""

from agent_state import GraphState


def error_handler_node(state: GraphState) -> dict:
    val_err   = state.get("validation_error", "알 수 없는 오류")
    retry_cnt = state.get("retry_count", 0)

    response = {
        "status": "error",
        "answer": f"'{state.get('user_query','')}' 에 대한 SQL을 생성하지 못했습니다. 질문을 더 구체적으로 입력해 주세요.",
        "sql":    state.get("generated_sql", ""),
        "result": [],
        "metadata": {
            "row_count": 0, "execution_time_ms": 0,
            "retry_count": retry_cnt, "team_id": state.get("team_id", ""),
            "error_detail": val_err,
        },
    }
    return {
        "response":      response,
        "status":        "error",
        "error_message": f"{retry_cnt}회 시도 실패: {val_err}",
    }
