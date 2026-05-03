"""
domain_team_a.py — Team A 도메인 설정
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
수정 대상: 새 팀 적용 시 이 파일을 복사해 내용을 교체한다.
  cp domain_team_a.py domain_team_b.py
  → domain_team_b.py 내용 수정
  → main.py 상단에서 import 대상만 변경
 
LLM이 DB를 이해하기 위한 5가지 정보:
  1. TABLE_DEFINITIONS   : 테이블·컬럼 비즈니스 설명
  2. TABLE_RELATIONSHIPS : JOIN 경로
  3. GLOSSARY            : 자연어 단어 → SQL 표현
  4. BUSINESS_RULES      : 암묵적 집계 규칙
  5. QUERY_EXAMPLES      : 자주 묻는 질문 패턴
"""

TEAM_ID          = "team_a"
TEAM_NAME        = "이커머스 운영팀"
TEAM_DESCRIPTION = "온라인 쇼핑몰 주문·상품·고객 데이터를 관리하는 팀"

# ── 1. 테이블 정의 ────────────────────────────────────────────
TABLE_DEFINITIONS = {
    "categories": {
        "description":      "상품 카테고리 분류 테이블",
        "business_meaning": "전자제품·의류·식품 등 상품을 분류하는 기준 코드 테이블",
        "primary_key":      "category_id",
        "columns": {
            "category_id":   "카테고리 고유 식별자 (PK, 자동증가)",
            "category_name": "카테고리 명칭 — 전자제품 / 의류 / 식품 / 도서 / 스포츠용품",
            "description":   "카테고리 상세 설명 (분석 쿼리에서 거의 사용 안 함)",
        },
        "notes": "마스터 데이터, 변경 빈도 낮음.",
    },
    "products": {
        "description":      "판매 상품 정보 테이블",
        "business_meaning": "현재 판매 중인 모든 상품의 기본 정보 (정가·재고 포함)",
        "primary_key":      "product_id",
        "columns": {
            "product_id":   "상품 고유 식별자 (PK)",
            "category_id":  "카테고리 FK → categories.category_id",
            "product_name": "상품 이름",
            "price":        "정가 (원 단위). 실제 판매가는 order_items.unit_price 사용",
            "stock":        "현재 재고 수량. 0이면 품절",
        },
        "notes": "매출 계산 시 products.price가 아닌 order_items.unit_price를 반드시 사용.",
    },
    "customers": {
        "description":      "고객 정보 테이블",
        "business_meaning": "쇼핑몰 가입 고객의 기본 정보 및 등급",
        "primary_key":      "customer_id",
        "columns": {
            "customer_id": "고객 고유 식별자 (PK)",
            "name":        "고객 실명",
            "email":       "고객 이메일 (UNIQUE)",
            "city":        "거주 도시 — 서울 / 부산 / 대구 / 인천 / 광주 / 대전",
            "grade":       "고객 등급 — NORMAL / VIP / VVIP (대문자 필수)",
            "join_date":   "가입일 (DATE, YYYY-MM-DD)",
        },
        "notes": "grade 비교 시 반드시 대문자 사용 ('VIP', 'VVIP', 'NORMAL').",
    },
    "orders": {
        "description":      "주문 헤더 테이블",
        "business_meaning": "고객이 생성한 주문 건과 처리 상태 관리",
        "primary_key":      "order_id",
        "columns": {
            "order_id":     "주문 고유 식별자 (PK)",
            "customer_id":  "주문 고객 FK → customers.customer_id",
            "order_date":   "주문 생성일 (DATE)",
            "status":       "주문 상태 — completed(완료) / pending(처리중) / cancelled(취소)",
            "total_amount": "주문 총액 요약값 (참고용). 정확한 집계는 order_items에서 직접 계산",
        },
        "notes": "total_amount는 참고용. 정확한 매출은 order_items.unit_price * quantity SUM.",
    },
    "order_items": {
        "description":      "주문 상세 항목 테이블",
        "business_meaning": "주문에 포함된 개별 상품 라인. 매출·수량 집계의 핵심 테이블",
        "primary_key":      "item_id",
        "columns": {
            "item_id":    "주문 항목 고유 식별자 (PK)",
            "order_id":   "소속 주문 FK → orders.order_id",
            "product_id": "구매 상품 FK → products.product_id",
            "quantity":   "구매 수량",
            "unit_price": "실제 구매 단가 (원). 할인·프로모션 반영된 실거래가",
        },
        "notes": "매출 = SUM(unit_price * quantity). 취소 주문 항목도 남으므로 status='completed' 필터 필수.",
    },
}

# ── 2. 테이블 관계 ────────────────────────────────────────────
TABLE_RELATIONSHIPS = [
    "customers.customer_id  = orders.customer_id         (고객 → 주문)",
    "orders.order_id        = order_items.order_id       (주문 → 주문항목)",
    "order_items.product_id = products.product_id        (주문항목 → 상품)",
    "products.category_id   = categories.category_id     (상품 → 카테고리)",
]

FULL_JOIN_PATH = """
FROM customers   c
JOIN orders      o   ON c.customer_id  = o.customer_id
JOIN order_items oi  ON o.order_id     = oi.order_id
JOIN products    p   ON oi.product_id  = p.product_id
JOIN categories  cat ON p.category_id  = cat.category_id
""".strip()

# ── 3. 도메인 용어 사전 ───────────────────────────────────────
GLOSSARY = {
    "매출":         "SUM(oi.unit_price * oi.quantity) — 완료 주문 기준",
    "주문금액":     "SUM(oi.unit_price * oi.quantity)",
    "구매금액":     "SUM(oi.unit_price * oi.quantity)",
    "총매출":       "SUM(oi.unit_price * oi.quantity) — 완료 주문 기준",
    "평균주문금액": "AVG(oi.unit_price * oi.quantity)",
    "판매량":       "SUM(oi.quantity)",
    "유효주문":     "orders.status = 'completed'",
    "완료주문":     "orders.status = 'completed'",
    "취소주문":     "orders.status = 'cancelled'",
    "대기주문":     "orders.status = 'pending'",
    "우수고객":     "customers.grade IN ('VIP', 'VVIP')",
    "일반고객":     "customers.grade = 'NORMAL'",
    "최우수고객":   "customers.grade = 'VVIP'",
    "재고":         "products.stock",
    "정가":         "products.price",
    "실거래가":     "order_items.unit_price",
}

# ── 4. 비즈니스 규칙 ──────────────────────────────────────────
BUSINESS_RULES = [
    "매출·판매량 집계 시 status='cancelled' 주문은 반드시 제외한다.",
    "실제 판매가는 order_items.unit_price를 사용한다. products.price(정가)로 매출 계산 금지.",
    "고객 등급 순서: NORMAL < VIP < VVIP. '상위 등급'은 VIP와 VVIP를 포함한다.",
    "한 주문(order_id)에 여러 상품(order_items)이 포함될 수 있다.",
    "날짜 필터는 orders.order_date 기준으로 한다.",
]

# ── 5. 예시 쿼리 (Few-shot) ───────────────────────────────────
QUERY_EXAMPLES = [
    {
        "question": "고객별 총 구매금액을 높은 순으로",
        "sql": (
            "SELECT c.name AS 고객명, SUM(oi.unit_price * oi.quantity) AS 총구매금액\n"
            "FROM customers c\n"
            "JOIN orders o ON c.customer_id = o.customer_id\n"
            "JOIN order_items oi ON o.order_id = oi.order_id\n"
            "WHERE o.status = 'completed'\n"
            "GROUP BY c.name ORDER BY 총구매금액 DESC;"
        ),
    },
    {
        "question": "카테고리별 매출 합계",
        "sql": (
            "SELECT cat.category_name AS 카테고리, SUM(oi.unit_price * oi.quantity) AS 총매출\n"
            "FROM categories cat\n"
            "JOIN products p ON cat.category_id = p.category_id\n"
            "JOIN order_items oi ON p.product_id = oi.product_id\n"
            "JOIN orders o ON oi.order_id = o.order_id\n"
            "WHERE o.status = 'completed'\n"
            "GROUP BY cat.category_name ORDER BY 총매출 DESC;"
        ),
    },
    {
        "question": "VIP 이상 고객이 구매한 상품과 카테고리",
        "sql": (
            "SELECT c.name AS 고객명, c.grade AS 등급, p.product_name AS 상품명,\n"
            "       cat.category_name AS 카테고리, oi.quantity AS 수량\n"
            "FROM customers c\n"
            "JOIN orders o ON c.customer_id = o.customer_id\n"
            "JOIN order_items oi ON o.order_id = oi.order_id\n"
            "JOIN products p ON oi.product_id = p.product_id\n"
            "JOIN categories cat ON p.category_id = cat.category_id\n"
            "WHERE c.grade IN ('VIP','VVIP') AND o.status = 'completed'\n"
            "ORDER BY c.grade DESC, c.name;"
        ),
    },
]
