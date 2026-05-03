"""
node_formatter.py — 쿼리 결과 포맷팅 노드
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
멀티턴 컨텍스트를 포함하여 최종 응답을 생성.
오류 상태에서는 에러 메시지를 그대로 반환.
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agent_state import GraphState

LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def _history_summary(history: list) -> str:
    if not history:
        return ""
    lines = ["이전 대화 요약:"]
    for i, turn in enumerate(history[-3:], 1):
        lines.append(f"  [{i}] Q: {turn.get('user_query','')[:60]}")
        lines.append(f"       결과: {turn.get('row_count', 0)}행")
    return "\n".join(lines)


def formatter_node(state: GraphState) -> dict:
    status = state.get("status", "")

    # ── 오류 / 취소 상태 ─────────────────────────────────────
    if status in ("error", "cancelled", "needs_clarification"):
        msg = state.get("error_message", "알 수 없는 오류가 발생했습니다.")
        return {"response": {"answer": msg, "status": status}}

    # ── 정상 결과 포맷팅 ─────────────────────────────────────
    query        = state.get("user_query", "")
    sql          = state.get("generated_sql", "")
    rows         = state.get("query_result", [])
    exec_ms      = state.get("exec_time_ms", 0)
    history      = state.get("conversation_history", [])
    domain       = state.get("domain_context", {})
    team_name    = domain.get("team_name", "")

    history_ctx = _history_summary(history)

    system_prompt = (
        f"당신은 {team_name} 팀의 데이터 분석 결과를 설명하는 어시스턴트입니다.\n"
        "SQL 결과를 비즈니스 관점에서 간결하게 3~5문장으로 요약하세요.\n"
        "숫자는 구체적으로 언급하고, 인사이트를 1줄 추가하세요.\n"
        + (f"\n{history_ctx}" if history_ctx else "")
    )

    rows_preview = rows[:10]
    user_msg = (
        f"질문: {query}\n\n"
        f"SQL:\n{sql}\n\n"
        f"결과 ({len(rows)}행, {exec_ms:.0f}ms):\n{rows_preview}"
    )

    try:
        resp = LLM.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg),
        ])
        answer = resp.content.strip()
    except Exception as e:
        answer = f"결과 요약 생성 실패: {e}"

    return {
        "response": {
            "answer":    answer,
            "row_count": len(rows),
            "exec_ms":   exec_ms,
            "sql":       sql,
            "status":    "ok",
        }
    }
