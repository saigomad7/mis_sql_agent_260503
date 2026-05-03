"""
display_utils.py — Spyder 출력 유틸리티
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
수정 대상: 출력 형식 변경 시 이 파일만 수정

역할: response dict를 pandas DataFrame + 터미널 출력으로 보기 좋게 변환.
      Spyder Variable Explorer에서 DataFrame을 클릭해 확인 가능.
"""
import pandas as pd

def response_to_df(response: dict) -> pd.DataFrame:
    """query_result 리스트를 pandas DataFrame으로 변환한다."""
    # 'result' -> 'query_result'로 수정
    rows = response.get("query_result", [])
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)

def print_response(response: dict, query: str = "") -> None:
    """response를 터미널에 보기 좋게 출력한다."""
    sep    = "=" * 65
    status = response.get("status", "unknown").upper()

    print(f"\n{sep}")
    # 인자로 받은 query가 없다면 dict 내의 'user_query'를 사용하도록 보완
    actual_query = query if query else response.get("user_query", "")
    if actual_query:
        print(f"[질문] {actual_query}")
    print(f"[상태] {status}")
    print(sep)

    # answer가 response['response']['answer'] 에 위치함
    inner_response = response.get("response", {})
    print(f"\n[답변]\n{inner_response.get('answer', '')}")
    
    # sql이 'generated_sql' 이라는 키로 존재함
    print(f"\n[실행된 SQL]\n{response.get('generated_sql', '')}")

    # 메타데이터가 묶여있지 않고 바깥에 나와있으므로 개별적으로 가져옴
    exec_time = response.get("exec_time_ms", 0)
    # 결과행수는 query_result 리스트의 길이로 계산
    row_count = len(response.get("query_result", [])) 
    retry_count = response.get("retry_count", 0)
    team_id = response.get("team_id", "unknown")

    print(
        f"\n[메타]  실행시간: {exec_time}ms  |  "
        f"결과: {row_count}행  |  재시도: {retry_count}회  |  "
        f"팀: {team_id}"
    )
    print(sep)
    
def build_summary_df(all_responses: list) -> pd.DataFrame:
    """여러 질의의 실행 요약을 DataFrame으로 반환한다."""
    rows = []
    for item in all_responses:
        # 기존처럼 metadata 딕셔너리를 찾지 않고, item(최상단)에서 직접 값을 가져옵니다.
        rows.append({
            "질문":           item.get("user_query", ""),           # '_query' -> 'user_query'로 변경
            "상태":           item.get("status", ""),
            "결과행수":       len(item.get("query_result", [])),    # 'query_result' 리스트의 길이로 계산
            "실행시간(ms)":   item.get("exec_time_ms", 0.0),        # 'execution_time_ms' -> 'exec_time_ms'로 변경
            "재시도":         item.get("retry_count", 0),
        })
    return pd.DataFrame(rows)