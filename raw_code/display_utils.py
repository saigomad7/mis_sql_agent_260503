"""
display_utils.py — Spyder 출력 유틸리티
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
수정 대상: 출력 형식 변경 시 이 파일만 수정

역할: response dict를 pandas DataFrame + 터미널 출력으로 보기 좋게 변환.
      Spyder Variable Explorer에서 DataFrame을 클릭해 확인 가능.
"""

import pandas as pd


def response_to_df(response: dict) -> pd.DataFrame:
    """result 리스트를 pandas DataFrame으로 변환한다."""
    rows = response.get("result", [])
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def print_response(response: dict, query: str = "") -> None:
    """response를 터미널에 보기 좋게 출력한다."""
    sep    = "=" * 65
    status = response.get("status", "unknown").upper()

    print(f"\n{sep}")
    if query:
        print(f"[질문] {query}")
    print(f"[상태] {status}")
    print(sep)

    print(f"\n[답변]\n{response.get('answer','')}")
    print(f"\n[실행된 SQL]\n{response.get('sql','')}")

    meta = response.get("metadata", {})
    print(
        f"\n[메타]  실행시간: {meta.get('execution_time_ms')}ms  |  "
        f"결과: {meta.get('row_count')}행  |  재시도: {meta.get('retry_count')}회  |  "
        f"팀: {meta.get('team_id')}"
    )
    print(sep)


def build_summary_df(all_responses: list) -> pd.DataFrame:
    """여러 질의의 실행 요약을 DataFrame으로 반환한다."""
    rows = []
    for item in all_responses:
        meta = item.get("metadata", {})
        rows.append({
            "질문":           item.get("_query", ""),
            "상태":           item.get("status", ""),
            "결과행수":       meta.get("row_count", 0),
            "실행시간(ms)":   meta.get("execution_time_ms", 0),
            "재시도":         meta.get("retry_count", 0),
        })
    return pd.DataFrame(rows)
