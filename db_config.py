""" 
db_config.py — DB 연결 설정
━━━━━━━━━━━━━━━━━━━━━━━━━━━
팀 공통 기본 연결 + 팀별 DB 설정을 모두 지원한다.
다른 파일에서:
  from db_config import get_conn           (기본 DB)
  from db_config import get_conn_by        (팀별 DB config dict 전달)
"""
import os
os.chdir("C:\\Users\\USER\\Documents\\agent\\sql_agent\\mis_sql_agent_v3")

import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

# ── 기본 DB (Team A) ──────────────────────────────────────────
DB_CONFIG = {
    "host":       os.getenv("DB_HOST", "localhost"),
    "port":       int(os.getenv("DB_PORT", 3306)),
    "database":   os.getenv("DB_NAME", "my_local_db"),
    "user":       os.getenv("DB_USER", "root"),
    "password":   os.getenv("DB_PASSWORD", "gjf850510!"),
    "charset":    "utf8mb4"  # MySQL 한글 깨짐 방지
}


# ── 기본 연결 함수 ──────────────────────────────────────────────
def get_conn():
    return pymysql.connect(**DB_CONFIG)

def get_dict_conn():
    conn   = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    return conn, cursor


# ── 팀별 연결 함수 ─────────────────────────────────────────
def get_conn_by(cfg: dict):
    """state["db_config"]를 받아 해당 팀 DB에 연결한다."""
    # DB_CONFIG와 pymysql의 매개변수 이름을 호환하도록 처리
    config_dict = {
        "host":     cfg.get("host", "localhost"),
        "port":     int(cfg.get("port", 3306)),
        "database": cfg.get("database", cfg.get("dbname", "my_local_db")),
        "user":     cfg.get("user", "root"),
        "password": cfg.get("password", "gjf850510!"),
        "charset":  "utf8mb4"
    }
    return pymysql.connect(**config_dict)

def get_dict_conn_by(cfg: dict):
    """DictCursor 커넥션을 팀별 DB 설정으로 반환한다."""
    conn   = get_conn_by(cfg)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    return conn, cursor


# ── 연결 테스트 ───────────────────────────────────────────────
def test_connection(cfg: dict = None) -> bool:
    """DB 연결 상태와 테이블 목록을 출력한다. cfg 없으면 기본 DB 사용."""
    target = cfg or DB_CONFIG
    try:
        conn = get_conn_by(target) if cfg else get_conn()
        cur  = conn.cursor()
        
        # MySQL 환경에 맞는 테이블 정보 조회 쿼리
        cur.execute("""
            SELECT table_name, 
                   (SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_name = t.table_name AND table_schema = DATABASE()) AS col_count
            FROM information_schema.tables t
            WHERE table_schema = DATABASE()
            ORDER BY table_name
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        db_name = target.get("database") or target.get("dbname")
        print(f"✅ DB 연결 성공: {target['user']}@{target['host']}/{db_name}\n")
        print(f"  {'테이블':<25} {'컬럼수':>5}")
        print("  " + "-" * 31)
        for table, cols in rows:
            print(f"  {table:<25} {cols:>5}")
        return True
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        return False


