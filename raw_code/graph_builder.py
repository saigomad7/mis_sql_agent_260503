"""
graph_builder.py — LangGraph 워크플로우 구성
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

노드 순서:
  domain → schema_rag → sql_gen → sql_valid
       → human_review → sql_exec → formatter → feedback → END

조건부 엣지:
  sql_valid   → (error ≥ 3회) → error_node → END
              → (재시도)       → sql_gen
              → (통과)         → human_review
  human_review→ (미승인)       → error_node → END
              → (승인)         → sql_exec
  sql_exec    → (실행 오류)    → error_node → END
              → (성공)         → formatter
"""

from langgraph.graph import StateGraph, END

from agent_state import GraphState
from node_domain      import domain_node
from node_schema_rag  import schema_rag_node
from node_sql_gen     import sql_generator_node
from node_sql_valid   import sql_validation_node
from node_human_review import human_review_node
from node_sql_exec    import sql_execution_node
from node_formatter   import formatter_node
from node_feedback    import feedback_node
from node_error       import error_node


# ── 조건부 엣지 함수 ────────────────────────────────────────────

def _after_validation(state: GraphState) -> str:
    if state.get("status") == "error":
        return "error"
    if state.get("validation_error"):
        return "retry"
    return "ok"


def _after_human_review(state: GraphState) -> str:
    if state.get("human_approved"):
        return "approved"
    return "rejected"


def _after_execution(state: GraphState) -> str:
    if state.get("execution_error"):
        return "error"
    return "ok"


# ── 그래프 빌더 ─────────────────────────────────────────────────

def build_graph():
    g = StateGraph(GraphState)

    # 노드 등록
    g.add_node("domain",       domain_node)
    g.add_node("schema_rag",   schema_rag_node)
    g.add_node("sql_gen",      sql_generator_node)
    g.add_node("sql_valid",    sql_validation_node)
    g.add_node("human_review", human_review_node)
    g.add_node("sql_exec",     sql_execution_node)
    g.add_node("formatter",    formatter_node)
    g.add_node("feedback",     feedback_node)
    g.add_node("error",        error_node)

    # 진입점
    g.set_entry_point("domain")

    # 고정 엣지
    g.add_edge("domain",    "schema_rag")
    g.add_edge("schema_rag","sql_gen")
    g.add_edge("formatter", "feedback")
    g.add_edge("feedback",  END)
    g.add_edge("error",     END)

    # 조건부 엣지
    g.add_conditional_edges(
        "sql_valid",
        _after_validation,
        {"ok": "human_review", "retry": "sql_gen", "error": "error"},
    )
    g.add_conditional_edges(
        "human_review",
        _after_human_review,
        {"approved": "sql_exec", "rejected": "error"},
    )
    g.add_conditional_edges(
        "sql_exec",
        _after_execution,
        {"ok": "formatter", "error": "error"},
    )

    # sql_gen → sql_valid 고정 엣지 (조건 분기 후 재진입 포함)
    g.add_edge("sql_gen", "sql_valid")

    return g.compile()


graph = build_graph()
