"""
node_sql_gen.py — SQL 생성 노드 (v3 강화판)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
v2 대비 신규:
  - Golden Query few-shot 자동 주입
  - 멀티턴 대화 히스토리 주입
  - JSON 출력: {sql, confidence, reasoning}
  - confidence 점수로 human_review 노드 분기
"""

import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from agent_state import GraphState

MODEL_NAME  = "gpt-4o"
TEMPERATURE = 0


# ── 프롬프트 조각 빌더 ────────────────────────────────────────

def _few_shot_block(examples: list) -> str:
    if not examples:
        return ""
    lines = ["\n[Golden Query — 유사 검증 예시]"]
    for i, ex in enumerate(examples, 1):
        lines.append(f"예시 {i}. 질문: {ex['question']}")
        lines.append(f"        SQL: {ex['sql']}")
        if ex.get("description"):
            lines.append(f"        설명: {ex['description']}")
    return "\n".join(lines) + "\n"


def _history_block(history: list) -> str:
    if not history:
        return ""
    recent = history[-3:]          # 최근 3턴만
    lines  = ["\n[이전 대화 맥락]"]
    for turn in recent:
        lines.append(f"Q: {turn.get('user_query', '')}")
        lines.append(f"A: {turn.get('summary', '')}  (행수: {turn.get('row_count', 0)})")
        if turn.get("sql"):
            lines.append(f"SQL: {turn['sql']}")
    return "\n".join(lines) + "\n"


def _rag_info_block(relevant_tables: list) -> str:
    if not relevant_tables:
        return ""
    return f"\n[Schema RAG 선택 테이블: {', '.join(relevant_tables)}]\n"


def _build_system(state: GraphState) -> str:
    domain   = state.get("domain_context", {})
    schema   = state.get("db_schema", "")
    examples = state.get("similar_examples", [])
    history  = state.get("conversation_history", [])
    relevant = state.get("relevant_tables", [])

    glossary_text = "\n".join(
        f"  {k}: {v}" for k, v in domain.get("glossary", {}).items()
    )
    rules_text = "\n".join(
        f"  - {r}" for r in domain.get("business_rules", [])
    )

    return f"""당신은 PostgreSQL SQL 전문가입니다.
팀: {domain.get('team_name', '')} — {domain.get('team_description', '')}

{schema}

[용어사전]
{glossary_text}

[비즈니스 규칙]
{rules_text}
{_few_shot_block(examples)}{_history_block(history)}{_rag_info_block(relevant)}
━━━ 출력 규칙 ━━━
반드시 SELECT 문만 생성하고, 아래 JSON 형식으로만 응답하세요.
마크다운 코드블록(```) 없이 순수 JSON만 출력합니다.

{{
  "sql":        "SELECT ...",
  "confidence": 0.85,
  "reasoning":  "신뢰도 근거 (예: 질의가 명확하고 관련 테이블이 특정됨)"
}}

confidence 기준:
  0.9+ : 질의가 명확하고 테이블·컬럼이 정확히 매칭
  0.7  : 질의는 명확하지만 복잡한 조인이 필요
  0.5  : 질의가 다소 모호하거나 여러 해석 가능
  0.3- : 질의가 불명확하거나 필요 테이블이 불분명
"""


def _parse_json_response(raw: str) -> tuple:
    """LLM 응답에서 sql, confidence, reasoning 추출"""
    text = raw.strip()

    # 코드블록 제거
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$",       "", text)

    try:
        obj = json.loads(text)
        return (
            obj.get("sql", "").strip(),
            float(obj.get("confidence", 0.5)),
            obj.get("reasoning", ""),
        )
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 raw를 SQL로 취급
        sql_match = re.search(r"SELECT[\s\S]+?;", text, re.IGNORECASE)
        sql = sql_match.group(0) if sql_match else text
        return sql, 0.5, "JSON 파싱 실패 — 기본 신뢰도 적용"


# ── 노드 ─────────────────────────────────────────────────────

def sql_generator_node(state: GraphState) -> dict:
    retry           = state.get("retry_count", 0)
    validation_err  = state.get("validation_error")

    system_msg  = _build_system(state)
    human_text  = state.get("user_query", "")
    if retry > 0 and validation_err:
        human_text += f"\n\n[이전 오류]\n{validation_err}\n위 오류를 수정해서 다시 생성해주세요."

    llm      = ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE)
    response = llm.invoke([SystemMessage(system_msg), HumanMessage(human_text)])

    sql, confidence, reasoning = _parse_json_response(response.content)

    return {
        "generated_sql":    sql,
        "confidence_score": confidence,
        "confidence_reason": reasoning,
        "retry_count":      retry,      # 유효성 검사 실패 시 validator가 +1
    }
