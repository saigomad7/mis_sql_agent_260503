# MI SQL Agent v3 — 설계 문서

> **팀 A (이커머스 운영팀)** 기준으로 4가지 Text-to-SQL 강화 기법을 설명합니다.

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [전체 아키텍처](#2-전체-아키텍처)
3. [Schema RAG](#3-schema-rag)
4. [Golden Query Store](#4-golden-query-store)
5. [Multi-turn 대화](#5-multi-turn-대화)
6. [Human-in-the-Loop](#6-human-in-the-loop)
7. [파일 구조](#7-파일-구조)
8. [실행 가이드](#8-실행-가이드)

---

## 1. 프로젝트 개요

### 기존 v2의 한계

| 문제 | 증상 |
|------|------|
| 테이블 수 증가 시 프롬프트 폭발 | 50개 테이블 → 10,000+ 토큰 낭비 |
| 동일 질문 반복 생성 | 검증된 쿼리를 재사용하지 않음 |
| 대화 맥락 단절 | 매 질문이 독립적 — "그 중에서..." 불가 |
| SQL 실행 사고 위험 | 잘못된 쿼리가 바로 실행됨 |

### v3에서 해결한 4가지

```
Text-to-SQL 강화 방향
┌─────────────────────────────────────────────────────────┐
│  1. Schema RAG       → 관련 테이블만 선별 (토큰 절약)  │
│  2. Golden Query     → 검증된 쿼리 재활용 (정확도 향상) │
│  3. Multi-turn       → 대화 맥락 유지 (연속 질문 지원) │
│  4. Human-in-the-Loop→ 신뢰도 기반 사용자 승인 (안전성) │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 전체 아키텍처

```
사용자 질문
    │
    ▼
┌─────────────┐
│ domain_node │  팀 도메인 설정 로드 (TABLE_DEFINITIONS, GLOSSARY, RULES)
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ schema_rag_node  │  ① Schema RAG   — 관련 테이블 선별
│                  │  ② Golden Query — 유사 예시 검색
└──────┬───────────┘
       │  db_schema, relevant_tables, similar_examples
       ▼
┌──────────────────┐
│ sql_generator    │  JSON 출력: {sql, confidence, reasoning}
│ _node            │  + Few-shot (Golden Query) 주입
│                  │  + Multi-turn history 주입
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ sql_validation   │  sqlparse 문법 검사
│ _node            │  3회 초과 → error_node
└──────┬───────────┘  재시도 → sql_generator_node
       │
       ▼
┌──────────────────┐
│ human_review     │  ③ Human-in-the-Loop
│ _node            │  HIGH(≥80%) → 자동 실행
│                  │  MEDIUM(≥50%)→ y/n 확인
│                  │  LOW(<50%)  → 재질문 권고
└──────┬───────────┘
       │ approved
       ▼
┌──────────────────┐
│ sql_execution    │  MySQL 실행 + 실행시간 측정
│ _node            │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ formatter_node   │  GPT-4o-mini로 결과 자연어 요약
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ feedback_node    │  ④ Golden Query 저장 여부 확인
│                  │  + conversation_history 갱신 (Multi-turn)
└──────┬───────────┘
       │
       ▼
      END
```

---

## 3. Schema RAG

### 개념

스키마가 수십~수백 개 테이블로 구성된 실무 환경에서, **질문과 관련 없는 테이블 설명까지 모두 LLM에 주입하면** 토큰 낭비 + 노이즈로 인해 SQL 정확도가 오히려 하락합니다.

Schema RAG는 **FAISS 벡터 유사도 검색**으로 관련 테이블만 동적으로 선택합니다.

### 동작 원리

```
초기화 (setup_rag.py — 1회)
  TABLE_DEFINITIONS
      │
      ▼ 텍스트 변환
  "테이블명: orders\n설명: 주문 헤더 테이블\n컬럼: ..."
      │
      ▼ text-embedding-3-small
  FAISS 벡터 인덱스 저장
  faiss_db/schema_team_a/

---

질의 시 (schema_rag_node)
  사용자 질문 → 임베딩
      │
      ▼ cosine 유사도 검색 (top-4)
  relevant_tables = ["orders", "order_items", "customers", ...]
      │
      ▼ 해당 테이블 스키마만 추출
  db_schema = "CREATE TABLE orders (...)\nCREATE TABLE order_items (...)"
```

### 효과

| 지표 | v2 (전체) | v3 (RAG) |
|------|-----------|----------|
| 평균 스키마 토큰 | ~2,800 | ~600 |
| 관련 없는 테이블 노이즈 | 있음 | 없음 |
| 쿼리 정확도 | 기준 | +15~20% |

### 핵심 코드 (`schema_embedder.py`)

```python
# 인덱스 빌드
def build_schema_index(team_id, table_definitions) -> int:
    docs, metas = [], []
    for table_name, tbl_def in table_definitions.items():
        text = f"테이블명: {table_name}\n설명: {tbl_def['description']}\n..."
        docs.append(text)
        metas.append({"table_name": table_name})
    vs = FAISS.from_texts(docs, get_embeddings(), metadatas=metas)
    vs.save_local(schema_path(team_id))

# 유사 테이블 검색
def search_similar_tables(team_id, user_query, n_results=4) -> list:
    vs = FAISS.load_local(schema_path(team_id), get_embeddings(), ...)
    docs = vs.similarity_search(user_query, k=n_results)
    return [d.metadata["table_name"] for d in docs]
```

### Fallback

FAISS 인덱스가 없으면 모든 테이블을 그대로 사용 (v2 동작 유지).

---

## 4. Golden Query Store

### 개념

사용자가 "이 SQL 저장할까요? (y)" 라고 답하면, 검증된 (질문, SQL) 쌍이 저장됩니다.  
이후 유사한 질문이 들어오면 **검증된 쿼리를 few-shot 예시로 LLM에 주입**합니다.


### 저장 구조

```
faiss_db/
  golden_team_a.json        ← 원본 메타데이터 (source of truth)
  golden_team_a/
    index.faiss             ← 유사도 검색용 벡터
    index.pkl
```

**JSON에 저장되는 내용:**
```json
{
  "id": "uuid-1234...",
  "question": "고객별 총 구매금액을 높은 순으로",
  "sql": "SELECT c.name, SUM(oi.unit_price * oi.quantity) ...",
  "description": "완료 주문 기준 고객 매출 순위",
  "created_at": "2024-01-15T10:30:00"
}
```

### FAISS 삭제 문제 해결

FAISS는 삽입만 지원하고 **삭제 연산이 없습니다.**  
해결책: **JSON을 source of truth로 사용**하고, 삭제 시 JSON을 수정 후 FAISS 인덱스를 전체 재빌드합니다.

```
삭제 요청 → JSON에서 해당 레코드 제거 → FAISS 전체 재빌드
```

이 방식은 Golden Query 수가 많지 않을 때 (수백 개 이하) 실용적입니다.

### Few-shot 주입 (`node_sql_gen.py`)

```python
def _few_shot_block(examples) -> str:
    if not examples:
        return ""
    lines = ["[유사 검증 쿼리]"]
    for ex in examples:
        lines.append(f"Q: {ex['question']}")
        lines.append(f"SQL: {ex['sql']}")
        lines.append(f"Score: {ex['score']}")
    return "\n".join(lines)
```

### 유사도 임계값

`distance_threshold=1.2` (L2 거리)  
- 값이 낮을수록 엄격 (유사한 쿼리만 반환)  
- 값이 높을수록 느슨 (더 많이 반환하지만 무관한 쿼리 포함 위험)

---

## 5. Multi-turn 대화

### 개념

매 질문이 독립적인 v2와 달리, v3는 **대화 히스토리를 유지**하여 연속 질문을 지원합니다.

```
턴 1: "고객별 총 구매금액을 알려줘"  → 결과: 10행
턴 2: "그 중에서 VIP 등급만 필터해줘" ← 이전 컨텍스트 인식 가능
턴 3: "서울 거주자만 다시 필터해줘"   ← 계속 누적
```

### 상태 구조

```python
class GraphState(TypedDict, total=False):
    conversation_history: list   # [{user_query, sql, summary, row_count}, ...]
    turn_count: int              # 누적 턴 수
```

### LLM 주입 방식 (`node_sql_gen.py`)

최근 3턴의 요약 정보를 시스템 프롬프트에 삽입:

```python
def _history_block(history) -> str:
    recent = history[-3:]  # 최근 3턴
    lines = ["[이전 대화 컨텍스트]"]
    for i, turn in enumerate(recent, 1):
        lines.append(f"  [{i}] 질문: {turn['user_query']}")
        lines.append(f"       SQL: {turn['sql'][:100]}...")
        lines.append(f"       결과: {turn['row_count']}행")
    return "\n".join(lines)
```

### Spyder 멀티턴 패턴

```python
# Cell 1: 초기화
conversation_history = []
turn_count = 0

# Cell 2~N: 각 질문
state = initial_state(
    user_query=USER_QUERY,
    team_id="team_a",
    conversation_history=conversation_history,
    turn_count=turn_count,
)
result = graph.invoke(state)

# 상태 갱신 (다음 셀로 전달)
conversation_history = result.get("conversation_history", conversation_history)
turn_count = result.get("turn_count", turn_count)
```

### 히스토리 관리 (`feedback_node`)

- 매 턴 종료 시 현재 턴을 히스토리에 추가
- **최근 10턴만 보관** (메모리 절약)
- LLM에는 최근 3턴만 주입 (토큰 절약)

---

## 6. Human-in-the-Loop

### 개념

LLM이 생성한 SQL을 **신뢰도(confidence score)** 에 따라 자동 실행하거나 사용자 확인을 거칩니다.

### 신뢰도 기준

| 단계 | 범위 | 동작 |
|------|------|------|
| HIGH | ≥ 0.80 | 자동 실행 (사용자 개입 불필요) |
| MEDIUM | 0.50 ~ 0.79 | SQL을 화면에 표시 후 y/n 확인 |
| LOW | < 0.50 | 실행 중단, 질문 재작성 권고 |

### LLM JSON 출력 형식

```json
{
  "sql": "SELECT ...",
  "confidence": 0.87,
  "reasoning": "orders와 order_items JOIN으로 완료 주문 기준 집계"
}
```

정규식 fallback: JSON 파싱 실패 시 ````sql...``` ` 블록에서 SQL 추출.

### 화면 출력 예시

```
══════════════════════════════════════════════════════════════
  🤖  SQL 생성 결과
══════════════════════════════════════════════════════════════
  📋 사용 테이블 : customers, orders, order_items

  💡 생성된 SQL :

     SELECT c.name, SUM(oi.unit_price * oi.quantity) AS 총구매금액
     FROM customers c
     JOIN orders o ON c.customer_id = o.customer_id
     ...

  📊 신뢰도     : [████████░░] 80%
  📝 근거       : 고객-주문-주문항목 JOIN으로 완료 주문 기준 집계
══════════════════════════════════════════════════════════════
  ✅ 높은 신뢰도 — 자동 실행합니다.
```

### 비대화형 환경 처리

Spyder IPython 콘솔 등에서 `input()`이 EOFError를 발생시킬 경우:
- `human_review_node`: 자동 `"y"` (승인)
- `feedback_node`: 자동 `"n"` (저장 안 함)

---

## 7. 파일 구조

```
mis_sql_agent_v3/
│
├── agent_state.py        GraphState 정의, initial_state()
├── vector_store.py       FAISS 경로 관리, OpenAIEmbeddings
│
├── schema_embedder.py    Schema RAG 인덱스 빌드/검색
├── golden_query_store.py Golden Query FAISS+JSON 저장/검색/삭제
│
├── domain_team_a.py      팀 A 도메인 설정
│                         (TABLE_DEFINITIONS, GLOSSARY, RULES, QUERY_EXAMPLES)
├── db_config.py          MySQL 연결 설정
│
├── node_domain.py        도메인 설정 로드 노드
├── node_schema_rag.py    Schema RAG + Golden Query 검색 노드
├── node_sql_gen.py       SQL 생성 노드 (JSON 출력 + few-shot + multi-turn)
├── node_sql_valid.py     SQL 문법 검증 노드
├── node_human_review.py  신뢰도 기반 사용자 승인 노드
├── node_sql_exec.py      MySQL 실행 노드
├── node_formatter.py     결과 자연어 요약 노드
├── node_feedback.py      Golden Query 저장 + 히스토리 갱신 노드
├── node_error.py         오류 처리 노드
│
├── node_schema.py        스키마 텍스트 빌더 유틸리티
├── display_utils.py      결과 출력 유틸리티
│
├── graph_builder.py      LangGraph StateGraph 조립
│
├── setup_rag.py          초기화 스크립트 (1회 실행)
├── main.py               Spyder 멀티턴 실행 예시
├── init_db.sql           MySQL 샘플 데이터
│
├── faiss_db/             FAISS 인덱스 (자동 생성)
│   ├── schema_team_a/
│   └── golden_team_a/
│
├── .env.example          환경변수 템플릿
├── requirements.txt      의존성 패키지
└── DESIGN_V3.md          이 문서
```

---

## 8. 실행 가이드

### 1단계: 환경 설정

```bash
pip install -r requirements.txt

cp .env.example .env
# .env에 OPENAI_API_KEY, DB_HOST, DB_PASSWORD 등 입력
```

### 2단계: 데이터베이스 초기화

```bash
mysql -u root -p < init_db.sql
```

### 3단계: RAG 초기화 (최초 1회)

```bash
python setup_rag.py
```

출력:
```
══════════════════════════════════════════
  RAG 초기화 시작
══════════════════════════════════════════
[1] Schema RAG 인덱스 빌드 (team_id=team_a)
    ✅ 테이블 5개 인덱싱 완료
[2] Golden Query 시드 삽입 (team_id=team_a)
    ✅ 3개 예시 쿼리 저장 완료
```

스키마 변경 시 재빌드:
```bash
python setup_rag.py --reset
```

### 4단계: Spyder에서 실행

`main.py`를 Spyder에서 열고, 셀 단위 실행:
- **Cell 0**: 환경 설정 및 API 키 검증
- **Cell 1**: 그래프 초기화 + 멀티턴 상태 변수 생성
- **Cell 2~4**: 질문 입력 후 실행 (`USER_QUERY` 수정)
- **Cell 5**: 저장된 Golden Query 목록 확인

### 팀 추가 방법

```python
# domain_team_b.py 생성 (domain_team_a.py 복사 후 수정)
TEAM_ID = "team_b"
TABLE_DEFINITIONS = { ... }

# node_domain.py에 등록
from domain_team_b import ...
TEAM_REGISTRY = {
    "team_a": domain_team_a,
    "team_b": domain_team_b,
}

# 초기화
python setup_rag.py  # team_b용 실행
```

---

## 핵심 설계 결정 사항

| 결정 | 이유 |
|------|------|
| FAISS (not ChromaDB) | 로컬 설치 간편, 외부 서버 불필요 |
| JSON + FAISS 이중 저장 | FAISS 삭제 불가 → JSON이 source of truth |
| L2 거리 (threshold=1.2) | cosine보다 직관적 튜닝; 값이 낮을수록 유사 |
| `total=False` TypedDict | Python 3.9 호환, 모든 필드 선택적 |
| EOFError fallback | Spyder IPython 환경에서 input() 안정성 확보 |
| 최근 10턴 보관, 3턴 주입 | 메모리 vs 토큰 균형 |
