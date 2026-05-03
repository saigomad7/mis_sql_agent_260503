"""
node_domain.py — 도메인 컨텍스트 주입 노드 (v3 · Team A 단일팀)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
확장: 새 팀 추가 시 TEAM_REGISTRY에 한 줄만 추가
"""

from agent_state import GraphState
import domain_team_a

TEAM_REGISTRY = {
    "team_a": domain_team_a,
    # "team_b": domain_team_b,  ← 확장 시 추가
}


def domain_context_node(state: GraphState) -> dict:
    team_id = state.get("team_id", "")

    if team_id not in TEAM_REGISTRY:
        return {
            "status":        "error",
            "error_message": f"미등록 team_id='{team_id}'. 등록된 팀: {list(TEAM_REGISTRY.keys())}",
        }

    cfg = TEAM_REGISTRY[team_id]
    return {
        "domain_context": {
            "team_name":           cfg.TEAM_NAME,
            "team_description":    cfg.TEAM_DESCRIPTION,
            "table_definitions":   cfg.TABLE_DEFINITIONS,
            "table_relationships": cfg.TABLE_RELATIONSHIPS,
            "full_join_path":      cfg.FULL_JOIN_PATH,
            "glossary":            cfg.GLOSSARY,
            "business_rules":      cfg.BUSINESS_RULES,
            "query_examples":      cfg.QUERY_EXAMPLES,
        },
        "db_config": cfg.DB_CONFIG if hasattr(cfg, "DB_CONFIG") else {},
    }
