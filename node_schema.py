"""
node_schema.py — DB 스키마 추출 유틸 (node_schema_rag에서 호출)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
v3에서는 독립 노드가 아닌 build_schema_text() 함수만 제공.
node_schema_rag 가 테이블을 선택한 뒤 이 함수를 호출한다.
"""

from db_config import get_conn, get_conn_by


def _get_tables(cur) -> list:
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_type='BASE TABLE'
        ORDER BY table_name
    """)
    return [r[0] for r in cur.fetchall()]


def _get_columns(cur, table: str) -> list:
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        ORDER BY ordinal_position
    """, (table,))
    return cur.fetchall()


def _get_pks(cur, table: str) -> set:
    cur.execute("""
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema
        WHERE tc.constraint_type='PRIMARY KEY' AND tc.table_name=%s
    """, (table,))
    return {r[0] for r in cur.fetchall()}


def _get_fks(cur, table: str) -> dict:
    cur.execute("""
        SELECT kcu.column_name, ccu.table_name, ccu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name=tc.constraint_name AND ccu.table_schema=tc.table_schema
        WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_name=%s
    """, (table,))
    return {r[0]: (r[1], r[2]) for r in cur.fetchall()}


def build_schema_text(table_definitions: dict, db_config: dict = None) -> str:
    """
    선택된 테이블만 information_schema에서 조회해 LLM용 스키마 텍스트 반환.
    table_definitions가 비어있으면 DB의 모든 테이블을 사용.
    """
    conn = get_conn_by(db_config) if db_config else get_conn()
    cur  = conn.cursor()

    db_tables  = set(_get_tables(cur))
    target     = set(table_definitions.keys()) & db_tables if table_definitions else db_tables

    lines = ["[데이터베이스 스키마]", ""]
    for table in sorted(target):
        columns = _get_columns(cur, table)
        pks     = _get_pks(cur, table)
        fks     = _get_fks(cur, table)
        tbl_def = table_definitions.get(table, {})

        desc = tbl_def.get("description", "")
        lines.append(f"▶ {table}" + (f"  # {desc}" if desc else ""))

        biz = tbl_def.get("business_meaning", "")
        if biz:
            lines.append(f"  비즈니스 의미: {biz}")

        col_defs = tbl_def.get("columns", {})
        for col_name, data_type, nullable in columns:
            markers  = []
            if col_name in pks:
                markers.append("PK")
            if col_name in fks:
                rt, rc = fks[col_name]
                markers.append(f"FK→{rt}.{rc}")
            m_str    = f" [{', '.join(markers)}]" if markers else ""
            null_str = "" if nullable == "YES" else " NOT NULL"
            c_desc   = col_defs.get(col_name, "")
            d_str    = f"  # {c_desc}" if c_desc else ""
            lines.append(f"  - {col_name}{m_str}: {data_type.upper()}{null_str}{d_str}")

        notes = tbl_def.get("notes", "")
        if notes:
            lines.append(f"  ※ 주의: {notes}")
        lines.append("")

    cur.close()
    conn.close()
    return "\n".join(lines)
