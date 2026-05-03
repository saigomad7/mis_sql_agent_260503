"""
node_feedback.py — Golden Query 피드백 + 멀티턴 히스토리 관리 노드
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
역할:
  1. conversation_history 에 이번 턴 추가 (멀티턴)
  2. 사용자에게 Golden Query 저장 여부 확인 후 저장

오류 상태에서는 히스토리만 갱신하고 저장 질문은 건너뜀.
"""

from agent_state import GraphState
from golden_query_store import save_golden_query


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip().lower()
    except EOFError:
        return "n"


def feedback_node(state: GraphState) -> dict:
    status  = state.get("status", "")
    sql     = state.get("generated_sql", "")
    query   = state.get("user_query", "")
    team_id = state.get("team_id", "")

    # ── 멀티턴: 대화 히스토리 갱신 ──────────────────────────
    history   = list(state.get("conversation_history", []))
    resp      = state.get("response", {})
    summary   = str(resp.get("answer", ""))[:120] if resp else ""
    row_count = len(state.get("query_result", []))

    history.append({
        "user_query": query,
        "sql":        sql,
        "summary":    summary,
        "row_count":  row_count,
    })
    history = history[-10:]        # 최근 10턴만 보관

    # ── Golden Query 저장 ────────────────────────────────────
    if status not in ("error", "cancelled", "needs_clarification") and sql:
        print("\n" + "-" * 50)
        print(f"  💬 쿼리 성공  (결과 {row_count}행)")
        ans = _ask("  이 쿼리를 Golden Query로 저장할까요? (y / n): ")
        if ans == "y":
            desc = _ask("  설명 입력 (Enter 스킵): ")
            qid  = save_golden_query(team_id, query, sql, desc)
            print(f"  💾 저장 완료  ID={qid[:8]}...\n")
        else:
            print("  ⏭  저장 건너뜀.\n")

    return {
        "conversation_history": history,
        "turn_count":           state.get("turn_count", 0) + 1,
    }
