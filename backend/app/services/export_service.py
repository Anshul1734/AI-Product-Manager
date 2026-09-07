"""
Export a generated plan to Markdown, Jira-ready CSV, or JSON.

Dependency-free by design. The previous implementation pulled in reportlab for
PDF generation -- a native dependency that was never declared in
requirements.txt, so importing this module crashed the app at startup and forced
a duplicate serverless entrypoint to exist. PDF output is now handled by the
browser's own print-to-PDF against a print-styled view, which needs no server
dependency and renders the same document the user is looking at.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _bullets(items: Optional[List[Any]], empty: str = "_None specified._") -> str:
    if not items:
        return empty
    return "\n".join(f"- {item}" for item in items)


def _safe(value: Any, fallback: str = "") -> str:
    return str(value).strip() if value not in (None, "") else fallback


class ExportService:
    """Renders a plan payload into downloadable documents."""

    def prd_markdown(self, payload: Dict[str, Any], idea: Optional[str] = None) -> bytes:
        plan = payload.get("plan") or {}
        prd = payload.get("prd") or {}
        architecture = payload.get("architecture") or {}
        features = payload.get("features_detailed") or []
        quality = payload.get("quality") or {}
        citations = payload.get("citations") or []

        product = _safe(plan.get("product_name"), "Untitled Product")
        lines: List[str] = [
            f"# {product}",
            "",
            "> Product Requirements Document",
            f"> Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
        ]

        if idea:
            lines += ["## Original idea", "", f"> {idea}", ""]

        lines += [
            "## Problem",
            "",
            _safe(prd.get("problem_statement") or plan.get("problem_statement"), "_Not specified._"),
            "",
        ]

        if plan.get("value_proposition"):
            lines += ["## Value proposition", "", _safe(plan["value_proposition"]), ""]

        lines += [
            "## Target users",
            "",
            _bullets(prd.get("target_users") or plan.get("target_users")),
            "",
            "## Goals",
            "",
            _bullets(plan.get("core_goals")),
            "",
            "## Non-goals",
            "",
            _bullets(plan.get("non_goals") or prd.get("non_goals")),
            "",
        ]

        if plan.get("jobs_to_be_done"):
            lines += ["## Jobs to be done", ""]
            for job in plan["jobs_to_be_done"]:
                lines.append(
                    f"- When {_safe(job.get('situation'))}, "
                    f"I want to {_safe(job.get('motivation'))}, "
                    f"so I can {_safe(job.get('outcome'))}."
                )
            lines.append("")

        if prd.get("user_personas"):
            lines += ["## Personas", ""]
            for persona in prd["user_personas"]:
                lines += [f"### {_safe(persona.get('name'), 'Persona')}", "", _safe(persona.get("description")), ""]
                if persona.get("current_workaround"):
                    lines += [f"**Today they:** {_safe(persona['current_workaround'])}", ""]
                lines += ["**Pain points**", "", _bullets(persona.get("pain_points")), ""]

        if prd.get("user_stories"):
            lines += ["## User stories", ""]
            for index, story in enumerate(prd["user_stories"], start=1):
                lines += [
                    f"### {index}. {_safe(story.get('title'), 'Story')}",
                    "",
                    f"As a **{_safe(story.get('as_a'))}**, I want to **{_safe(story.get('i_want_to'))}** "
                    f"so that **{_safe(story.get('so_that'))}**.",
                    "",
                ]
                if story.get("acceptance_criteria"):
                    lines += ["**Acceptance criteria**", "", _bullets(story["acceptance_criteria"]), ""]

        if features:
            lines += [
                "## Prioritized features (RICE)",
                "",
                "| # | Feature | Reach | Impact | Confidence | Effort | Score | MoSCoW |",
                "|---|---------|-------|--------|------------|--------|-------|--------|",
            ]
            for index, feature in enumerate(features, start=1):
                rice = feature.get("rice") or {}
                lines.append(
                    f"| {index} | {_safe(feature.get('name'))} | {rice.get('reach', '')} | "
                    f"{rice.get('impact', '')} | {rice.get('confidence', '')}% | "
                    f"{rice.get('effort', '')} | **{rice.get('score', '')}** | "
                    f"{_safe(feature.get('moscow'))} |"
                )
            lines.append("")
            if payload.get("sequencing_rationale"):
                lines += ["**Sequencing rationale**", "", _safe(payload["sequencing_rationale"]), ""]

        if prd.get("success_metrics"):
            lines += ["## Success metrics", "", "| Metric | Type | Target | Description |", "|---|---|---|---|"]
            for metric in prd["success_metrics"]:
                lines.append(
                    f"| {_safe(metric.get('name'))} | {_safe(metric.get('metric_type'))} | "
                    f"{_safe(metric.get('target'))} | {_safe(metric.get('description'))} |"
                )
            lines.append("")

        if architecture:
            lines += ["## Architecture", "", _safe(architecture.get("system_design")), ""]
            if architecture.get("architecture_pattern"):
                lines += [f"**Pattern:** {_safe(architecture['architecture_pattern'])}", ""]
            if architecture.get("tech_stack"):
                lines += ["### Tech stack", "", "| Layer | Choice |", "|---|---|"]
                for layer, choice in architecture["tech_stack"].items():
                    lines.append(f"| {_safe(layer)} | {_safe(choice)} |")
                lines.append("")
            if architecture.get("api_endpoints"):
                lines += ["### API endpoints", "", "| Method | Path | Purpose |", "|---|---|---|"]
                for endpoint in architecture["api_endpoints"]:
                    lines.append(
                        f"| `{_safe(endpoint.get('method'), 'GET')}` | `{_safe(endpoint.get('endpoint'))}` | "
                        f"{_safe(endpoint.get('description'))} |"
                    )
                lines.append("")
            if architecture.get("database_schema"):
                lines += ["### Data model", ""]
                for table in architecture["database_schema"]:
                    lines += [f"**{_safe(table.get('table_name'))}**", "", "| Field | Type | Constraints |", "|---|---|---|"]
                    for column in table.get("fields") or []:
                        lines.append(
                            f"| {_safe(column.get('name'))} | {_safe(column.get('type'))} | "
                            f"{_safe(column.get('constraints'))} |"
                        )
                    lines.append("")
            if architecture.get("key_decisions"):
                lines += ["### Key decisions", ""]
                for decision in architecture["key_decisions"]:
                    lines += [
                        f"**{_safe(decision.get('decision'))}**",
                        "",
                        f"- Rationale: {_safe(decision.get('rationale'))}",
                    ]
                    if decision.get("alternatives_considered"):
                        lines.append(f"- Alternatives: {', '.join(decision['alternatives_considered'])}")
                    if decision.get("tradeoffs"):
                        lines.append(f"- Tradeoff accepted: {_safe(decision['tradeoffs'])}")
                    lines.append("")
            if architecture.get("non_functional_requirements"):
                lines += ["### Non-functional requirements", "", _bullets(architecture["non_functional_requirements"]), ""]

        if prd.get("risks"):
            lines += ["## Risks", "", _bullets(prd["risks"]), ""]
        if plan.get("assumptions"):
            lines += ["## Assumptions to validate", "", _bullets(plan["assumptions"]), ""]
        if prd.get("open_questions"):
            lines += ["## Open questions", "", _bullets(prd["open_questions"]), ""]

        if quality:
            lines += [
                "## Quality review",
                "",
                f"**Overall: {quality.get('overall', 'n/a')}/10 ({_safe(quality.get('grade'))})**",
                "",
                _safe(quality.get("assessment")),
                "",
            ]
            if quality.get("blocking_issues"):
                lines += ["**Blocking issues**", "", _bullets(quality["blocking_issues"]), ""]

        if citations:
            lines += ["## Sources consulted", ""]
            for citation in citations:
                heading = _safe(citation.get("heading"))
                suffix = f" — {heading}" if heading else ""
                lines.append(f"- [{_safe(citation.get('marker'))}] {_safe(citation.get('title'))}{suffix}")
            lines.append("")

        return "\n".join(lines).encode("utf-8")

    def tickets_csv(self, payload: Dict[str, Any]) -> bytes:
        """Jira-importable CSV: one row per epic, story, and task."""
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(
            ["Issue Type", "Summary", "Description", "Priority", "Status", "Epic Link", "Story Points", "Estimate (h)"]
        )

        tickets = payload.get("tickets") or {}
        for epic in tickets.get("epics") or []:
            epic_name = _safe(epic.get("epic_name"), "Untitled Epic")
            writer.writerow(
                ["Epic", epic_name, _safe(epic.get("description")), _safe(epic.get("priority"), "Medium"), "To Do", "", "", ""]
            )
            for story in epic.get("stories") or []:
                criteria = story.get("acceptance_criteria") or []
                description = _safe(story.get("description"))
                if criteria:
                    description = (description + "\n\nAcceptance criteria:\n" + "\n".join(f"- {c}" for c in criteria)).strip()
                writer.writerow(
                    [
                        "Story",
                        _safe(story.get("story_title"), "Untitled Story"),
                        description,
                        "Medium",
                        "To Do",
                        epic_name,
                        story.get("story_points") or "",
                        "",
                    ]
                )
                for task in story.get("tasks") or []:
                    writer.writerow(
                        [
                            "Task",
                            _safe(task.get("title"), "Untitled Task"),
                            _safe(task.get("description")),
                            "Low",
                            "To Do",
                            epic_name,
                            "",
                            task.get("estimated_hours") or "",
                        ]
                    )

        return buffer.getvalue().encode("utf-8")

    def full_json(self, payload: Dict[str, Any], idea: Optional[str] = None) -> bytes:
        document = {
            "export_metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "export_version": "2.0",
                "product_idea": idea,
            },
            "plan": payload,
        }
        return json.dumps(document, indent=2, default=str, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def filename(payload: Dict[str, Any], kind: str, extension: str) -> str:
        product = _safe((payload.get("plan") or {}).get("product_name"), "product-plan")
        slug = "".join(char if char.isalnum() else "-" for char in product.lower()).strip("-")[:48] or "product-plan"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
        return f"{slug}-{kind}-{stamp}.{extension}"
