"""Architect: designs a system proportionate to the requirements."""
from __future__ import annotations

from ..schemas.artifacts import PRD, SystemArchitecture
from .base import BaseAgent
from .digests import prd_digest


class ArchitectAgent(BaseAgent[SystemArchitecture]):
    name = "architect"
    label = "System architecture"
    output_model = SystemArchitecture
    tool_names = ("search_pm_knowledge",)
    temperature = 0.35
    # The largest schema in the pipeline: endpoints, tables with nested columns,
    # and decision records. Needs headroom, since a truncated object costs a
    # full repair round.
    max_tokens = 3200
    # Stays on the primary model despite the bucket pressure. Smaller models
    # reliably produce malformed JSON at this schema's size, and a repair round
    # costs more tokens than the larger model does.
    model_role = "primary"

    def system_prompt(self) -> str:
        return (
            "You are a staff engineer designing the first architecture for a new "
            "product.\n\n"
            "Your standards:\n"
            "- Design for the team and traffic that actually exist. A greenfield product "
            "with a small team gets a modular monolith; proposing microservices without "
            "the operational maturity to run them is a design error, not ambition.\n"
            "- Justify the pattern you choose and name what you gave up. Every "
            "key decision records alternatives considered and the tradeoff accepted.\n"
            "- REST endpoints use correct verbs and resource-shaped paths. Include the "
            "status codes that matter, and idempotency where a retry could double-charge "
            "or double-create.\n"
            "- The data model must support the PRD's actual access patterns. State the "
            "indexes the hot queries need.\n"
            "- Non-functional requirements are concrete: a latency budget, an "
            "availability target, a data-retention rule -- not 'must be scalable'.\n"
            "- Prefer boring, well-understood technology. Novelty is a cost paid by "
            "whoever is on call.\n\n"
            "Ground the design in the PRD's requirements. Do not add infrastructure no "
            "user story needs."
        )

    def build_task(self, *, prd: PRD, **_: object) -> str:
        return (
            "## Task\n\n"
            "Design the system architecture that satisfies this PRD.\n\n"
            f"{prd_digest(prd)}\n\n"
            "Assume a small founding team (3-5 engineers) unless the requirements "
            "clearly demand otherwise. Choose the pattern that team size justifies, "
            "then design only the components, endpoints, and tables the user stories "
            "above actually require."
        )
