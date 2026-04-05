"""Typed Pydantic models for the Disaster Response Coordination OpenEnv."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import ConfigDict, Field

try:
    from openenv.core.env_server.types import Action, Observation, State
except ImportError:
    from openenv_core.env_server.types import Action, Observation, State


ActionType = Literal[
    "classify",
    "set_priority",
    "draft_reply",
    "submit_ticket",
    "next_ticket",
    "finish_episode",
    "noop",
]

SupportTeam = Literal["rescue", "medical", "utilities", "shelter", "logistics", "general"]
Priority = Literal["low", "medium", "high", "urgent"]
Difficulty = Literal["easy", "medium", "hard"]


class SupportOpsAction(Action):
    """Action for operating on disaster-response incident requests."""

    model_config = ConfigDict(extra="ignore")

    action_type: ActionType = Field(..., description="The action type to execute.")
    ticket_id: Optional[str] = Field(
        default=None,
        description="Incident id to operate on. If omitted, environment uses active incident.",
    )
    predicted_team: Optional[SupportTeam] = Field(
        default=None,
        description="Predicted routing team for classification actions.",
    )
    predicted_priority: Optional[Priority] = Field(
        default=None,
        description="Predicted urgency for set_priority actions.",
    )
    reply_text: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Drafted responder handoff note for draft_reply actions.",
    )


class SupportOpsObservation(Observation):
    """Observation returned after each disaster coordination step."""

    model_config = ConfigDict(extra="ignore")

    task_name: Difficulty = Field(..., description="Current task difficulty.")
    objective: str = Field(default="", description="Current task objective.")
    current_ticket_id: Optional[str] = Field(default=None, description="Active ticket id.")
    current_ticket_message: str = Field(
        default="", description="Incident details for the active case."
    )
    current_ticket_customer_tier: str = Field(
        default="district", description="Affected region criticality tier for active incident."
    )
    inbox_snapshot: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Compact per-incident snapshot with completion status.",
    )
    action_history: List[str] = Field(
        default_factory=list,
        description="Recent action history for trajectory-aware planning.",
    )
    task_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Current normalized task score in [0, 1].",
    )
    last_action_error: Optional[str] = Field(
        default=None,
        description="Error message for invalid action or failed operation.",
    )


class SupportOpsState(State):
    """Server-side state with task progress for support operations."""

    model_config = ConfigDict(extra="ignore")

    task_name: Difficulty = Field(default="easy", description="Current task name.")
    cursor: int = Field(default=0, ge=0, description="Current ticket cursor index.")
    solved_tickets: int = Field(default=0, ge=0, description="Submitted ticket count.")
    total_tickets: int = Field(default=0, ge=0, description="Total tickets in the episode.")
    invalid_actions: int = Field(default=0, ge=0, description="Invalid action count.")
    loop_penalties: int = Field(default=0, ge=0, description="Loop/no-op penalty count.")
    route_changes: int = Field(default=0, ge=0, description="Count of repeated rerouting actions.")
    budget_overflows: int = Field(default=0, ge=0, description="Count of resource budget overflow events.")
    cumulative_reward: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Normalized cumulative task score in [0, 1].",
    )
