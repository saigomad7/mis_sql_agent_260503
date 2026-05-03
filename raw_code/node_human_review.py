"""
node_human_review.py — 신뢰도 기반 Human-in-the-loop 노드
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
신뢰도에 따른 3단계 분기:
  HIGH   (≥ 0.80) : 자동 실행
  MEDIUM (≥ 0.50) : SQL 표시 후 사용자 확인 요청 (y/n)
  LOW    (< 0.50) : 질문 재작성 권고 후 중단

Spyder / 터미널 양쪽에서 input()으로 동작.
비대화형 환경(EOFError)에서는 자동 승인(y) 처리.
"""

from agent_state import GraphState

HIGH_THRESHOLD   = 0.80
MEDIUM_THRESHOLD = 0.50


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip().lower()
    except EOFError:
        return "y"


def human_review_node(state: GraphState) -> dict:
    confidence = state.get("confidence_score", 0.5)
    reason     = state.get("confidence_reason", "")
    sql        = state.get("generated_sql", "")
    tables     = state.get("relevant_tables", [])

    bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))

    print("\n" + "=" * 62)
    print("  🤖  SQL 생성 결과")
    print("=" * 62)
    if tables:
        print(f"  📋 사용 테이블 : {', '.join(tables)}")
    print(f"\n  💡 생성된 SQL :\n")
    for line in sql.splitlines():
        print(f"     {line}")
    print(f"\n  📊 신뢰도     : [{bar}] {confidence:.0%}")
    print(f"  📝 근거       : {reason}")
    print("=" * 62)

    # ── HIGH ────────────────────────────────────────────────
    if confidence >= HIGH_THRESHOLD:
        print("  ✅ 높은 신뢰도 — 자동 실행합니다.\n")
        return {"human_approved": True}

    # ── MEDIUM ───────────────────────────────────────────────
    if confidence >= MEDIUM_THRESHOLD:
        print("  ⚠️  중간 신뢰도 — SQL을 확인해 주세요.")
        ans = _ask("  이 SQL을 실행하시겠습니까? (y / n): ")
        if ans == "y":
            print("  ✅ 승인됨 — 실행합니다.\n")
            return {"human_approved": True}
        print("  🚫 취소됨.\n")
        return {
            "human_approved": False,
            "status":         "cancelled",
            "error_message":  "사용자가 SQL 실행을 취소했습니다.",
        }

    # ── LOW ─────────────────────────────────────────────────
    print("  🔴 낮은 신뢰도 — 질문을 더 구체적으로 작성해 주세요.\n")
    return {
        "human_approved": False,
        "status":         "needs_clarification",
        "error_message":  f"신뢰도 부족 ({confidence:.0%}): {reason}",
    }
