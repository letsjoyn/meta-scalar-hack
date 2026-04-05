"""Disaster Response Coordination environment with deterministic graders.

Implements the OpenEnv Environment interface with typed actions, observations,
resource-budget tracking, anti-gaming penalties, and per-ticket composite scoring.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional
from uuid import uuid4

try:
    from openenv.core.env_server.interfaces import Environment
except ImportError:
    from openenv_core.env_server.interfaces import Environment

try:
    from ..models import SupportOpsAction, SupportOpsObservation, SupportOpsState
    from ..tasks import TASKS, Difficulty, TaskSpec, TicketSpec
except ImportError:
    from models import SupportOpsAction, SupportOpsObservation, SupportOpsState
    from tasks import TASKS, Difficulty, TaskSpec, TicketSpec


_PRIORITY_RANK = {"low": 0, "medium": 1, "high": 2, "urgent": 3}
_TEAM_COST = {
    "rescue": 4,
    "medical": 5,
    "utilities": 3,
    "shelter": 2,
    "logistics": 2,
    "general": 1,
}
_BUDGET_BY_TASK = {
    "easy": 40,
    "medium": 48,
    "hard": 55,
}

# Valid action types that an agent may submit
_VALID_ACTION_TYPES = [
    "classify",
    "set_priority",
    "draft_reply",
    "submit_ticket",
    "next_ticket",
    "finish_episode",
    "noop",
]


class SupportOpsEnvironment(Environment):
    """Disaster response coordination environment with deterministic graders."""

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self, task_name: Difficulty = "easy"):
        self._task_name: Difficulty = task_name
        self._task_spec: TaskSpec = TASKS[task_name]
        self._state = SupportOpsState(
            episode_id=str(uuid4()),
            step_count=0,
            task_name=task_name,
            cursor=0,
            solved_tickets=0,
            total_tickets=len(self._task_spec.tickets),
            invalid_actions=0,
            loop_penalties=0,
            route_changes=0,
            budget_overflows=0,
            cumulative_reward=0.0,
        )
        self._last_action_error: Optional[str] = None
        self._history: List[str] = []
        self._tickets_runtime: Dict[str, Dict[str, Any]] = {}
        self._episode_done: bool = False
        self._max_steps = self._task_spec.max_steps
        self._resource_budget = _BUDGET_BY_TASK[self._task_name]
        self._resource_used = 0
        self._submit_step: Dict[str, int] = {}  # ticket_id -> step when submitted
        self._init_ticket_runtime()

    @property
    def state(self) -> SupportOpsState:
        return self._state

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_name: Optional[Difficulty] = None,
        **kwargs: Any,
    ) -> SupportOpsObservation:
        if task_name is not None and task_name in TASKS:
            self._task_name = task_name

        self._task_spec = TASKS[self._task_name]
        self._state = SupportOpsState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_name=self._task_name,
            cursor=0,
            solved_tickets=0,
            total_tickets=len(self._task_spec.tickets),
            invalid_actions=0,
            loop_penalties=0,
            route_changes=0,
            budget_overflows=0,
            cumulative_reward=0.0,
        )
        self._max_steps = self._task_spec.max_steps
        self._resource_budget = _BUDGET_BY_TASK[self._task_name]
        self._resource_used = 0
        self._history = []
        self._last_action_error = None
        self._episode_done = False
        self._submit_step = {}
        self._init_ticket_runtime()
        return self._build_observation(reward=0.0, done=False)

    def step(self, action: SupportOpsAction) -> SupportOpsObservation:  # type: ignore[override]
        if self._episode_done:
            return self._build_observation(reward=0.0, done=True)

        self._state.step_count += 1
        self._last_action_error = None

        reward = 0.0
        at = action.action_type

        if at == "classify":
            reward = self._handle_classify(action)
        elif at == "set_priority":
            reward = self._handle_priority(action)
        elif at == "draft_reply":
            reward = self._handle_draft(action)
        elif at == "submit_ticket":
            reward = self._handle_submit(action)
        elif at == "next_ticket":
            reward = self._handle_next_ticket()
        elif at == "finish_episode":
            self._episode_done = True
            reward = self._score_overall_task() * 0.15
        elif at == "noop":
            self._state.loop_penalties += 1
            reward = 0.0
        else:
            self._register_invalid(f"Unsupported action_type: {at}")

        self._history.append(self._format_action(action))
        done = self._episode_done or self._state.step_count >= self._max_steps

        if self._state.solved_tickets >= self._state.total_tickets:
            done = True

        self._episode_done = done
        self._state.cumulative_reward = self._score_overall_task()

        return self._build_observation(reward=self._clip01(reward), done=done)

    # ------------------------------------------------------------------
    # Ticket runtime helpers
    # ------------------------------------------------------------------

    def _init_ticket_runtime(self) -> None:
        self._tickets_runtime = {}
        for ticket in self._task_spec.tickets:
            self._tickets_runtime[ticket.ticket_id] = {
                "ticket": deepcopy(ticket.__dict__),
                "predicted_team": None,
                "predicted_priority": None,
                "reply_text": "",
                "submitted": False,
                "ticket_score": 0.0,
            }

    def _current_ticket(self) -> TicketSpec:
        idx = min(self._state.cursor, len(self._task_spec.tickets) - 1)
        return self._task_spec.tickets[idx]

    def _resolve_ticket(self, ticket_id: Optional[str]) -> TicketSpec:
        if ticket_id and ticket_id in self._tickets_runtime:
            for t in self._task_spec.tickets:
                if t.ticket_id == ticket_id:
                    return t
        return self._current_ticket()

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _handle_classify(self, action: SupportOpsAction) -> float:
        ticket = self._resolve_ticket(action.ticket_id)
        rt = self._tickets_runtime[ticket.ticket_id]
        prev_team = rt.get("predicted_team")
        if rt["submitted"]:
            self._register_invalid("Cannot classify a submitted ticket.")
            return 0.0
        if not action.predicted_team:
            self._register_invalid("classify requires predicted_team.")
            return 0.0

        rt["predicted_team"] = action.predicted_team
        if prev_team and prev_team != action.predicted_team:
            self._state.route_changes += 1

        base = 0.35 if action.predicted_team == ticket.gold_team else 0.05
        if prev_team and prev_team != action.predicted_team:
            base = max(base - 0.08, 0.0)
        return base

    def _handle_priority(self, action: SupportOpsAction) -> float:
        ticket = self._resolve_ticket(action.ticket_id)
        rt = self._tickets_runtime[ticket.ticket_id]
        if rt["submitted"]:
            self._register_invalid("Cannot reprioritize a submitted ticket.")
            return 0.0
        if not action.predicted_priority:
            self._register_invalid("set_priority requires predicted_priority.")
            return 0.0

        rt["predicted_priority"] = action.predicted_priority
        gold = _PRIORITY_RANK[ticket.gold_priority]
        got = _PRIORITY_RANK[action.predicted_priority]
        distance = abs(gold - got)
        if distance == 0:
            return 0.3
        if distance == 1:
            return 0.12
        return 0.02

    def _handle_draft(self, action: SupportOpsAction) -> float:
        ticket = self._resolve_ticket(action.ticket_id)
        rt = self._tickets_runtime[ticket.ticket_id]
        if rt["submitted"]:
            self._register_invalid("Cannot edit draft after submit.")
            return 0.0
        text = (action.reply_text or "").strip()
        if not text:
            self._register_invalid("draft_reply requires reply_text.")
            return 0.0

        rt["reply_text"] = text
        return self._grade_reply_partial(ticket, text)

    def _handle_submit(self, action: SupportOpsAction) -> float:
        ticket = self._resolve_ticket(action.ticket_id)
        rt = self._tickets_runtime[ticket.ticket_id]
        if rt["submitted"]:
            self._register_invalid("Ticket already submitted.")
            return 0.0

        if not rt["predicted_team"] or not rt["predicted_priority"] or not rt["reply_text"]:
            self._register_invalid("submit_ticket requires classify, set_priority, and draft_reply first.")
            return 0.0

        ticket_score = self._grade_ticket(ticket, rt)

        budget_cost = self._estimate_resource_cost(rt)
        self._resource_used += budget_cost
        if self._resource_used > self._resource_budget:
            self._state.budget_overflows += 1
            ticket_score *= 0.75

        rt["ticket_score"] = ticket_score
        rt["submitted"] = True
        self._submit_step[ticket.ticket_id] = self._state.step_count
        self._state.solved_tickets += 1

        if self._state.solved_tickets < self._state.total_tickets:
            self._advance_to_next_unsolved()

        return self._clip01(0.2 + 0.8 * ticket_score)

    def _handle_next_ticket(self) -> float:
        moved = self._advance_to_next_unsolved()
        if not moved:
            self._state.loop_penalties += 1
            return 0.0
        return 0.03

    def _advance_to_next_unsolved(self) -> bool:
        total = len(self._task_spec.tickets)
        start = self._state.cursor

        for offset in range(1, total + 1):
            idx = (start + offset) % total
            ticket = self._task_spec.tickets[idx]
            if not self._tickets_runtime[ticket.ticket_id]["submitted"]:
                self._state.cursor = idx
                return True
        return False

    # ------------------------------------------------------------------
    # Grading helpers
    # ------------------------------------------------------------------

    def _grade_reply_partial(self, ticket: TicketSpec, text: str) -> float:
        if not text.strip():
            return 0.0

        lower = text.lower()
        kw_hits = sum(1 for kw in ticket.required_reply_keywords if kw in lower)
        keyword_ratio = kw_hits / max(len(ticket.required_reply_keywords), 1)

        polite = any(p in lower for p in ["thanks", "thank you", "sorry", "appreciate"])
        has_next_step = any(p in lower for p in ["next", "within", "update", "follow up", "eta", "dispatch"])

        score = 0.45 * keyword_ratio
        score += 0.15 if polite else 0.0
        score += 0.15 if has_next_step else 0.0
        score += 0.1 if len(text) >= 60 else 0.02

        # Penalize unsafe/dismissive language
        if "ignore" in lower or "not our issue" in lower:
            score *= 0.4
        if "panic" in lower or "everyone move now" in lower:
            score *= 0.85

        return self._clip01(score)

    def _grade_ticket(self, ticket: TicketSpec, rt: Dict[str, Any]) -> float:
        breakdown = self._ticket_breakdown(ticket, rt)
        composite = breakdown["composite"]

        # Hard mode: rescue incidents require explicit evacuation language
        if self._task_name == "hard" and ticket.gold_team == "rescue":
            text = (rt.get("reply_text") or "").lower()
            if "evac" not in text and "staging" not in text and "perimeter" not in text:
                composite *= 0.75

        # Hard mode: urgent tickets solved late get a time-pressure penalty
        if self._task_name == "hard" and ticket.gold_priority == "urgent":
            submit_step = self._submit_step.get(ticket.ticket_id, self._max_steps)
            urgency_deadline = self._max_steps * 0.6
            if submit_step > urgency_deadline:
                delay_fraction = (submit_step - urgency_deadline) / (self._max_steps - urgency_deadline + 1)
                composite *= max(1.0 - 0.2 * delay_fraction, 0.7)

        return self._clip01(composite)

    def _ticket_breakdown(self, ticket: TicketSpec, rt: Dict[str, Any]) -> Dict[str, float]:
        team_score = 1.0 if rt["predicted_team"] == ticket.gold_team else 0.0

        pr = rt["predicted_priority"]
        if pr is None:
            priority_score = 0.0
        else:
            distance = abs(_PRIORITY_RANK[ticket.gold_priority] - _PRIORITY_RANK[pr])
            if distance == 0:
                priority_score = 1.0
            elif distance == 1:
                priority_score = 0.45
            else:
                priority_score = 0.1

        reply_score = self._grade_reply_partial(ticket, rt.get("reply_text", ""))
        composite = 0.4 * team_score + 0.3 * priority_score + 0.3 * reply_score
        return {
            "team_score": team_score,
            "priority_score": priority_score,
            "reply_score": reply_score,
            "composite": composite,
        }

    def _score_overall_task(self) -> float:
        if self._state.total_tickets == 0:
            return 0.0

        ticket_scores = [self._tickets_runtime[t.ticket_id]["ticket_score"] for t in self._task_spec.tickets]
        avg_ticket_score = sum(ticket_scores) / self._state.total_tickets

        invalid_penalty = min(self._state.invalid_actions * 0.03, 0.15)
        loop_penalty = min(self._state.loop_penalties * 0.015, 0.1)
        reroute_penalty = min(self._state.route_changes * 0.02, 0.12)
        budget_penalty = min(self._state.budget_overflows * 0.06, 0.18)
        step_efficiency_penalty = 0.0
        if self._state.step_count > self._max_steps * 0.8:
            step_efficiency_penalty = 0.05

        final_score = (
            avg_ticket_score
            - invalid_penalty
            - loop_penalty
            - reroute_penalty
            - budget_penalty
            - step_efficiency_penalty
        )
        return self._clip01(final_score)

    def _estimate_resource_cost(self, rt: Dict[str, Any]) -> int:
        team = rt.get("predicted_team") or "general"
        priority = rt.get("predicted_priority") or "low"
        return _TEAM_COST.get(team, 1) + (_PRIORITY_RANK.get(priority, 0) + 1)

    # ------------------------------------------------------------------
    # Valid-action helper (exposed via observation metadata)
    # ------------------------------------------------------------------

    def _get_valid_actions(self) -> List[str]:
        """Return the subset of action types that are currently valid."""
        if self._episode_done:
            return []

        current = self._current_ticket()
        rt = self._tickets_runtime[current.ticket_id]
        valid: List[str] = []

        if not rt["submitted"]:
            if rt["predicted_team"] is None:
                valid.append("classify")
            else:
                valid.append("classify")  # re-classify allowed (but penalized)
            if rt["predicted_team"] is not None and rt["predicted_priority"] is None:
                valid.append("set_priority")
            elif rt["predicted_priority"] is not None:
                valid.append("set_priority")  # re-prioritize allowed
            if rt["predicted_team"] is not None and rt["predicted_priority"] is not None:
                valid.append("draft_reply")
            if rt["predicted_team"] and rt["predicted_priority"] and rt["reply_text"]:
                valid.append("submit_ticket")

        # Can always move to next ticket or finish
        has_unsolved = any(
            not self._tickets_runtime[t.ticket_id]["submitted"]
            for t in self._task_spec.tickets
            if t.ticket_id != current.ticket_id
        )
        if has_unsolved:
            valid.append("next_ticket")
        valid.append("finish_episode")

        return valid

    # ------------------------------------------------------------------
    # Observation builder
    # ------------------------------------------------------------------

    def _register_invalid(self, error: str) -> None:
        self._last_action_error = error
        self._state.invalid_actions += 1

    def _build_observation(self, reward: float, done: bool) -> SupportOpsObservation:
        current = self._current_ticket()
        task_score = self._score_overall_task()

        inbox_snapshot: List[Dict[str, Any]] = []
        for ticket in self._task_spec.tickets:
            rt = self._tickets_runtime[ticket.ticket_id]
            breakdown = self._ticket_breakdown(ticket, rt)
            inbox_snapshot.append(
                {
                    "ticket_id": ticket.ticket_id,
                    "submitted": rt["submitted"],
                    "predicted_team": rt["predicted_team"],
                    "predicted_priority": rt["predicted_priority"],
                    "ticket_score": rt["ticket_score"],
                    "resource_cost_estimate": self._estimate_resource_cost(rt),
                    "reward_breakdown": breakdown,
                }
            )

        current_rt = self._tickets_runtime[current.ticket_id]
        current_breakdown = self._ticket_breakdown(current, current_rt)

        return SupportOpsObservation(
            task_name=self._task_name,
            objective=self._task_spec.objective,
            current_ticket_id=current.ticket_id,
            current_ticket_message=current.customer_message,
            current_ticket_customer_tier=current.customer_tier,
            inbox_snapshot=inbox_snapshot,
            action_history=self._history[-8:],
            task_score=task_score,
            last_action_error=self._last_action_error,
            done=done,
            reward=self._clip01(reward),
            metadata={
                "max_steps": self._max_steps,
                "step_count": self._state.step_count,
                "solved_tickets": self._state.solved_tickets,
                "total_tickets": self._state.total_tickets,
                "resource_budget": self._resource_budget,
                "resource_used": self._resource_used,
                "budget_overflows": self._state.budget_overflows,
                "route_changes": self._state.route_changes,
                "current_reward_breakdown": current_breakdown,
                "valid_actions": self._get_valid_actions(),
                "anti_gaming_checks": {
                    "require_complete_workflow_before_submit": True,
                    "reroute_penalty_enabled": True,
                    "resource_budget_penalty_enabled": True,
                    "time_pressure_penalty_enabled": self._task_name == "hard",
                },
            },
        )

    def _format_action(self, action: SupportOpsAction) -> str:
        parts = [f"action_type={action.action_type}"]
        if action.ticket_id:
            parts.append(f"ticket_id={action.ticket_id}")
        if action.predicted_team:
            parts.append(f"predicted_team={action.predicted_team}")
        if action.predicted_priority:
            parts.append(f"predicted_priority={action.predicted_priority}")
        if action.reply_text:
            parts.append(f"reply_text_len={len(action.reply_text)}")
        return " ".join(parts)

    @staticmethod
    def _clip01(value: float) -> float:
        return min(max(value, 0.0), 1.0)
