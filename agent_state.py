"""
agent_state.py — GraphState 확장 (v3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
v2 대비 신규 필드:
  Schema RAG  : relevant_tables, similar_examples
  신뢰도      : confidence_score, confidence_reason
  Human-loop  : human_approved
  멀티턴      : conversation_history, turn_count
"""

from typing import TypedDict

  
class GraphState(TypedDict, total=False):
    # ── 입력 ─────────────────────────────────────────────────
    user_query:   str
    team_id:      str

    # ── node_domain 출력 ──────────────────────────────────────
    domain_context: dict   # 테이블정의·용어사전·규칙·예시
    db_config:      dict   # 팀 전용 DB 연결 정보

    # ── node_schema_rag 출력 ──────────────────────────────────
    db_schema:       str   # 선택된 테이블만의 스키마 텍스트
    relevant_tables: list  # RAG가 선택한 테이블 이름 목록
    similar_examples: list # Golden Query 검색 결과

    # ── node_sql_gen 출력 ─────────────────────────────────────
    generated_sql:    str
    retry_count:      int
    confidence_score: float  # 0.0(불확실) ~ 1.0(확실)
    confidence_reason: str   # 신뢰도 근거

    # ── node_sql_valid 출력 ───────────────────────────────────
    validation_error: str  # None = 통과

    # ── node_human_review 출력 ────────────────────────────────
    human_approved: bool   # True = 실행 승인

    # ── node_sql_exec 출력 ────────────────────────────────────
    query_result:    list
    execution_error: str
    exec_time_ms:    float

    # ── node_formatter 출력 ───────────────────────────────────
    response: dict  # 최종 JSON {status, answer, sql, result, metadata}

    # ── node_feedback 출력 (멀티턴) ───────────────────────────
    conversation_history: list  # [{user_query, sql, summary, row_count}]
    turn_count: int

    # ── 흐름 제어 ─────────────────────────────────────────────
    status:        str
    error_message: str


def initial_state(
    user_query: str,
    team_id: str = "team_a",
    conversation_history: list = None,
    turn_count: int = 0,
) -> GraphState:
    return GraphState(
        user_query=user_query,
        team_id=team_id,
        domain_context={},
        db_config={},
        db_schema="",
        relevant_tables=[],
        similar_examples=[],
        generated_sql="",
        retry_count=0,
        confidence_score=0.5,
        confidence_reason="",
        validation_error=None,
        human_approved=False,
        query_result=[],
        execution_error=None,
        exec_time_ms=0.0,
        response={},
        conversation_history=conversation_history or [],
        turn_count=turn_count,
        status="",
        error_message="",
    )
