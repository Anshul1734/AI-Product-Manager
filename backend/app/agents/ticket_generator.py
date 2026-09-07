"""Ticket generator: decomposes the plan into buildable work."""
from __future__ import annotations

from typing import List, Optional

from ..schemas.artifacts import PRD, ScoredFeature, SystemArchitecture, Tickets
from .base import BaseAgent
from .digests import architecture_digest, features_digest, prd_digest


class TicketGeneratorAgent(BaseAgent[Tickets]):
    name = "ticket_generator"
    label = "Delivery backlog"
    output_model = Tickets
    tool_names = ()
    temperature = 0.35
    max_tokens = 2600
    # Mechanical decomposition of decisions already made upstream, so the
    # smaller model is sufficient -- and it keeps the primary bucket free.
    model_role = "fast"

    def system_prompt(self) -> str:
        return (
            "You are a tech lead breaking a product plan into a backlog a team can "
            "start on Monday.\n\n"
            "Your standards:\n"
            "- Sequence a walking skeleton first: the thinnest end-to-end slice that "
            "proves the architecture, before breadth of features.\n"
            "- Every story is independently shippable and testable, with falsifiable "
            "Given/When/Then acceptance criteria.\n"
            "- Story points use the Fibonacci scale and reflect relative complexity, not "
            "hours. Anything above 8 points should have been split.\n"
            "- Tasks are concrete engineering steps with honest hour estimates. "
            "'Implement backend' is not a task; 'Add shipments table + migration with "
            "composite index on (tenant_id, sla_due_at)' is.\n"
            "- Epic priority follows the prioritized feature list, adjusted for "
            "technical dependencies -- auth and schema work usually precede the features "
            "that scored highest.\n\n"
            "Cover the endpoints and tables the architecture defines. Do not invent work "
            "for components that do not exist in the design."
        )

    def build_task(
        self,
        *,
        prd: PRD,
        architecture: SystemArchitecture,
        features: Optional[List[ScoredFeature]] = None,
        **_: object,
    ) -> str:
        sections = ["## Task\n\nProduce the delivery backlog for this plan."]

        priorities = features_digest(features, limit=8)
        if priorities:
            sections.append(priorities)

        sections.append(f"### Requirements\n\n{prd_digest(prd)}")
        sections.append(f"### Architecture\n\n{architecture_digest(architecture)}")
        sections.append(
            "Produce 3-5 epics ordered so the riskiest integration is proven earliest, "
            "starting with a walking skeleton. Cover the endpoints and tables listed "
            "above. Set delivery_sequence to the epic names in build order."
        )
        return "\n\n".join(sections)
