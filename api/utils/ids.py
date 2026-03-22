# TOP Auto-ID Generation
# Never manually increment IDs - always use these functions

from db.connection import execute_query


def next_id(table, id_column, prefix, pad):
    """
    Generic next-ID generator.
    prefix = 'C', 'E', 'EP', etc.
    pad = total digits after prefix (3 for C001, 3 for EP001)
    """
    sql = f"SELECT MAX(CAST(SUBSTR({id_column}, {len(prefix) + 1}) AS INTEGER)) as max_id FROM {table}"
    rows = execute_query(sql)
    current_max = rows[0]['max_id'] or 0
    next_num = current_max + 1
    return f"{prefix}{str(next_num).zfill(pad)}"


def next_client_id():
    return next_id("Clients", "client_id", "C", 3)

def next_engagement_id():
    return next_id("Engagements", "engagement_id", "E", 3)

def next_interview_id():
    return next_id("Interviews", "interview_id", "I", 3)

def next_signal_id():
    return next_id("Signals", "signal_id", "S", 3)

def next_document_id():
    return next_id("Documents", "document_id", "D", 3)

def next_ep_id():
    return next_id("EngagementPatterns", "ep_id", "EP", 3)

def next_agent_run_id():
    return next_id("AgentRuns", "run_id", "AR", 3)

def next_finding_id():
    return next_id("OPDFindings", "finding_id", "F", 3)

def next_roadmap_id():
    return next_id("RoadmapItems", "item_id", "R", 3)

def next_knowledge_id():
    return next_id("KnowledgePromotions", "promotion_id", "KP", 3)