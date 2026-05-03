""" 
vector_store.py — FAISS 벡터 스토어 공통 설정 
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
저장 구조:
  ./faiss_db/
    schema_{team_id}/   — 테이블 설명 인덱스 (Schema RAG)
    golden_{team_id}/   — 검증된 쿼리 인덱스 (Golden Query)

사용 패키지: faiss-cpu, langchain-community, langchain-openai
"""
import os
os.chdir("C:\\Users\\USER\\Documents\\agent\\sql_agent\\mis_sql_agent_v3")

import os
from langchain_openai import OpenAIEmbeddings

try:
    FAISS_DIR = os.path.join(os.path.dirname(__file__), "faiss_db")
except NameError:
    FAISS_DIR = os.path.join(os.getcwd(), "faiss_db")

print(f"FAISS Directory: {FAISS_DIR}")


def get_embeddings() -> OpenAIEmbeddings:
    """text-embedding-3-small 임베딩 함수 반환"""
    return OpenAIEmbeddings(model="text-embedding-3-small")


def schema_path(team_id: str) -> str:
    return os.path.join(FAISS_DIR, f"schema_{team_id}")


def golden_path(team_id: str) -> str:
    return os.path.join(FAISS_DIR, f"golden_{team_id}")


def faiss_exists(path: str) -> bool:
    return os.path.isfile(os.path.join(path, "index.faiss"))
