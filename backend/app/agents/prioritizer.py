"""
Prioritizer: RICE-scores and sequences the feature set.

Scores are always recomputed in Python from the validated estimates, so the
ranking cannot drift from the arithmetic even if the model asserts a different
number.
"""
from __future__ import annotations

from typing import Any, Dict

from ..schemas.artifacts import FeaturePriorities, ProductVision, RiceInputs
from .base import BaseAgent
from .digests import vision_digest


class PrioritizerAgent(BaseAgent[FeaturePriorities]):
    name = "prioritizer"
    label = "Feature prioritization"
    output_model = FeaturePriorities
    tool_names = ("score_features_rice",)
    temperature = 0.3
    max_tokens = 2800
    # Runs concurrently with the analyst, so it sits on a different model --
    # and therefore a different token bucket -- which is what makes that
    # parallelism buy wall-clock time instead of contending for one budget.
    # Measured choice: gpt-oss-20b repeatedly failed validation on this nested
    # features[].rice{} schema, while this model produced it correctly.
    model_role = "alt"

    def system_prompt(self) -> str:
        return (
            "You are a product manager prioritizing a feature set for a first release.\n\n"
            "Your standards:\n"
            "- Estimate RICE inputs honestly. Reach is users affected per quarter, "
            "grounded in the stated audience size, not an aspiration. Impact uses the "
            "canonical scale (3 massive, 2 high, 1 medium, 0.5 low, 0.25 minimal). "
            "Confidence is evidence-based: 100% needs real data, 80% needs a strong "
            "analogue, 50% is an informed guess. Effort is person-months.\n"
            "- You must call score_features_rice to compute and rank the scores. Never "
            "do the arithmetic yourself.\n"
            "- Justify each estimate in one or two lines. An unjustified number is noise.\n"
            "- MoSCoW labels must be disciplined: Must-haves are what makes the release "
            "coherent at all, and should stay well under half the total effort.\n"
            "- Sequencing is not just score order. Call out dependencies and the "
            "riskiest assumption you want to test first.\n\n"
            "Fabricated precision is the failure mode here. Wide, honest estimates beat "
            "confident invented ones."
        )

    def build_task(self, *, vision: ProductVision, **_: object) -> str:
        return (
            "## Task\n\n"
            "Prioritize the feature set implied by this product vision.\n\n"
            f"{vision_digest(vision)}\n\n"
            "Expand the candidate features into concrete, buildable capabilities "
            "(aim for 5-8). Estimate reach, impact, confidence and effort for each, "
            "then call score_features_rice to rank them. Report the tool's computed "
            "scores exactly as returned."
        )

    def postprocess(self, output: FeaturePriorities, tool_data: Dict[str, Any]) -> FeaturePriorities:
        computed = {
            str(item.get("name", "")).strip().lower(): item
            for item in tool_data.get("features_detailed") or []
        }

        for feature in output.features_detailed:
            match = computed.get(feature.name.strip().lower())
            if match and isinstance(match.get("rice"), dict):
                feature.rice = RiceInputs.model_validate(match["rice"])
            # Recompute unconditionally: the score is a function of the inputs.
            feature.rice.score = feature.rice.compute_score()

        output.features_detailed.sort(key=lambda item: item.rice.score, reverse=True)
        return output
