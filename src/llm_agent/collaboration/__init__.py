"""
LLM Agent Framework - 协作层

支持多个LLM Agent之间的智能协作。
"""

from llm_agent.collaboration.protocol import CollaborationProtocol, AgentMessage
from llm_agent.collaboration.team import LLMAgentTeam, TeamConfig
from llm_agent.collaboration.negotiation import Negotiation, NegotiationResult

__all__ = [
    "CollaborationProtocol",
    "AgentMessage",
    "LLMAgentTeam",
    "TeamConfig",
    "Negotiation",
    "NegotiationResult"
]
