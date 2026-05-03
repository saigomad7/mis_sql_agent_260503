""" 
main.py — MI SQL Agent v3  (Spyder 셀 실행)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 
사전 준비:
  1. .env 파일에 OPENAI_API_KEY 설정
  2. init_db.sql 실행 (MySQL 샘플 데이터)
  3. setup_rag.py 실행 (FAISS 인덱스 초기화 — 1회)

멀티턴 구조:
  conversation_history / turn_count 는 세션 전체에서 누적된다.
  각 셀은 initial_state()에 이 값을 전달하여 이전 대화를 LLM에 주입한다.
"""

import os
os.chdir("C:\\Users\\USER\\Documents\\agent\\sql_agent\\mis_sql_agent_v3")

# %%  Cell 0: 환경 설정
import os
from dotenv import load_dotenv

load_dotenv()

assert os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY가 설정되지 않았습니다."

# %%  Cell 1: 그래프 임포트 및 멀티턴 상태 초기화
from graph_builder import graph
from agent_state   import initial_state
from display_utils import response_to_df, print_response, build_summary_df

conversation_history = []   # 세션 전체에서 누적
turn_count           = 0

print("✅ SQL Agent v3 준비 완료")

# %%  Cell 2: 첫 번째 질문
USER_QUERY = "고객별 총 구매금액을 높은 순으로 알려줘"

state = initial_state(
    user_query           = USER_QUERY,
    team_id              = "team_a",
    conversation_history = conversation_history,
    turn_count           = turn_count,
)

result = graph.invoke(state)

# 멀티턴 상태 갱신
conversation_history = result.get("conversation_history", conversation_history)
turn_count           = result.get("turn_count", turn_count)

#response_to_df(result)
#display_result(result)

# %%  Cell 3: 두 번째 질문 (이전 결과 컨텍스트 유지)
USER_QUERY = "그 중에서 VIP 등급 고객만 따로 보여줘"

state = initial_state(
    user_query           = USER_QUERY,
    team_id              = "team_a",
    conversation_history = conversation_history,
    turn_count           = turn_count,
)

result = graph.invoke(state)

conversation_history = result.get("conversation_history", conversation_history)
turn_count           = result.get("turn_count", turn_count)

response_to_df(result)
print_response(result)



# %%  Cell 4: 자유 질문 — 원하는 질문으로 교체
USER_QUERY = "카테고리별 매출 합계를 내림차순으로"

state = initial_state(
    user_query           = USER_QUERY,
    team_id              = "team_a",
    conversation_history = conversation_history,
    turn_count           = turn_count,
)

result = graph.invoke(state)

conversation_history = result.get("conversation_history", conversation_history)
turn_count           = result.get("turn_count", turn_count)

response_to_df(result)
print_response(result)

# %%  Cell 5: Golden Query 목록 확인
from golden_query_store import list_golden_queries

print("=" * 50)
print("  저장된 Golden Query 목록")
print("=" * 50)
for q in list_golden_queries("team_a"):
    print(f"\n  [{q['id'][:8]}] {q['question']}")
    print(f"   SQL: {q['sql'][:80]}...")
    print(f"   설명: {q.get('description','—')}")
