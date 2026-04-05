from typing import Any, Dict

try:
    from openenv.core.client_types import StepResult
    from openenv.core.env_client import EnvClient
    from openenv.core.env_server.types import State
except ImportError:
    from openenv_core.client_types import StepResult
    from openenv_core.env_client import EnvClient
    from openenv_core.env_server.types import State

try:
    from .models import SupportOpsAction, SupportOpsObservation, SupportOpsState
except ImportError:
    from models import SupportOpsAction, SupportOpsObservation, SupportOpsState


class SupportOpsEnv(EnvClient[SupportOpsAction, SupportOpsObservation, SupportOpsState]):
    """Typed OpenEnv client for support operations environment."""

    def _step_payload(self, action: SupportOpsAction) -> Dict[str, Any]:
        return action.model_dump(exclude_none=True)

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[SupportOpsObservation]:
        obs_data = payload.get("observation", {})
        observation = SupportOpsObservation(
            task_name=obs_data.get("task_name", "easy"),
            objective=obs_data.get("objective", ""),
            current_ticket_id=obs_data.get("current_ticket_id"),
            current_ticket_message=obs_data.get("current_ticket_message", ""),
            current_ticket_customer_tier=obs_data.get("current_ticket_customer_tier", "standard"),
            inbox_snapshot=obs_data.get("inbox_snapshot", []),
            action_history=obs_data.get("action_history", []),
            task_score=obs_data.get("task_score", 0.0),
            last_action_error=obs_data.get("last_action_error"),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )
        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
            info=payload.get("info", {}),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> SupportOpsState:
        return SupportOpsState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            task_name=payload.get("task_name", "easy"),
            cursor=payload.get("cursor", 0),
            solved_tickets=payload.get("solved_tickets", 0),
            total_tickets=payload.get("total_tickets", 0),
            invalid_actions=payload.get("invalid_actions", 0),
            loop_penalties=payload.get("loop_penalties", 0),
            route_changes=payload.get("route_changes", 0),
            budget_overflows=payload.get("budget_overflows", 0),
            cumulative_reward=payload.get("cumulative_reward", 0.0),
        )
