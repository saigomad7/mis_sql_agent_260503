"""
db_config.py — DB 연결 설정
━━━━━━━━━━━━━━━━━━━━━━━━━━━
팀 공통 기본 연결 + 팀별 DB 설정을 모두 지원한다.
다른 파일에서:
  from db_config import get_conn           (기본 DB)
  from db_config import get_conn_by        (팀별 DB config dict 전달)
"""

import os
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

load_dotenv()

# ── 기본 DB (Team A) ──────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "sql_agent_db"),
    "user":     os.getenv("DB_USER", "jj"),
    "password": os.getenv("DB_PASSWORD", ""),
}


# ── 기본 연결 함수 (Team A 전용) ──────────────────────────────
def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def get_dict_conn():
    conn   = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return conn, cursor


# ── 팀별 연결 함수 (팀 설정 dict를 받아 연결) ─────────────────
def get_conn_by(cfg: dict):
    """state["db_config"]를 받아 해당 팀 DB에 연결한다."""
    return psycopg2.connect(
        host     = cfg.get("host", "localhost"),
        port     = cfg.get("port", 5432),
        dbname   = cfg.get("dbname"),
        user     = cfg.get("user"),
        password = cfg.get("password", ""),
    )

def get_dict_conn_by(cfg: dict):
    """RealDictCursor 커넥션을 팀별 DB 설정으로 반환한다."""
    conn   = get_conn_by(cfg)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return conn, cursor


# ── 연결 테스트 ───────────────────────────────────────────────
def test_connection(cfg: dict = None) -> bool:
    """DB 연결 상태와 테이블 목록을 출력한다. cfg 없으면 기본 DB 사용."""
    target = cfg or DB_CONFIG
    try:
        conn = get_conn_by(target) if cfg else get_conn()
        cur  = conn.cursor()
        cur.execute("""
            SELECT table_name,
                   (SELECT COUNT(*) FROM information_schema.columns
                    WHERE table_name = t.table_name AND table_schema = 'public') AS col_count
            FROM information_schema.tables t
            WHERE table_schema = 'public' ORDER BY table_name
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        print(f"✅ DB 연결 성공: {target['user']}@{target['host']}/{target['dbname']}\n")
        print(f"  {'테이블':<25} {'컬럼수':>5}")
        print("  " + "-" * 31)
        for table, cols in rows:
            print(f"  {table:<25} {cols:>5}")
        return True
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        return False
