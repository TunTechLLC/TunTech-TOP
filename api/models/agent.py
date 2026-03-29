from pydantic import BaseModel
from typing import Optional


class AgentRunResponse(BaseModel):
    """Shape of agent run data returned to the frontend."""
    run_id:          str
    engagement_id:   str
    agent_name:      str
    model_used:      Optional[str] = None
    run_date:        Optional[str] = None
    prompt_version:  Optional[str] = None
    output_summary:  Optional[str] = None
    output_doc_link: Optional[str] = None
    accepted:        int
    created_date:    str


class AgentRegistryEntry(BaseModel):
    """Shape of a single agent entry from the registry."""
    name:                  str
    sequence:              int
    domain:                str
    required_prior_agents: list[str]