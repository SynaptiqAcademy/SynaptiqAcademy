"""Dashboard Engine — personalized adaptive dashboard per user role."""
from __future__ import annotations

from .models import DashboardConfig, DashboardWidget, UserRole

# ── Widget definitions per role ────────────────────────────────────────────────

_ROLE_WIDGETS: dict[str, list[dict]] = {
    UserRole.STUDENT.value: [
        {"widget_type": "research_progress",  "title": "Research Progress",    "data_source": "workflow",       "position": {"x": 0, "y": 0, "w": 8, "h": 3}},
        {"widget_type": "ai_assistant",        "title": "AI Assistant",         "data_source": "copilot",        "position": {"x": 8, "y": 0, "w": 4, "h": 3}},
        {"widget_type": "deadline_tracker",    "title": "Upcoming Deadlines",   "data_source": "notifications",  "position": {"x": 0, "y": 3, "w": 6, "h": 2}},
        {"widget_type": "learning_resources",  "title": "Learning Resources",   "data_source": "knowledge_graph","position": {"x": 6, "y": 3, "w": 6, "h": 2}},
        {"widget_type": "activity_feed",       "title": "Recent Activity",      "data_source": "timeline",       "position": {"x": 0, "y": 5, "w": 12,"h": 3}},
    ],
    UserRole.MASTER_STUDENT.value: [
        {"widget_type": "research_progress",   "title": "Thesis Progress",      "data_source": "workflow",       "position": {"x": 0, "y": 0, "w": 8, "h": 3}},
        {"widget_type": "ai_assistant",        "title": "Copilot",              "data_source": "copilot",        "position": {"x": 8, "y": 0, "w": 4, "h": 3}},
        {"widget_type": "literature_map",      "title": "Literature Map",       "data_source": "knowledge_graph","position": {"x": 0, "y": 3, "w": 6, "h": 3}},
        {"widget_type": "deadline_tracker",    "title": "Deadlines",            "data_source": "notifications",  "position": {"x": 6, "y": 3, "w": 6, "h": 3}},
        {"widget_type": "activity_feed",       "title": "Activity",             "data_source": "timeline",       "position": {"x": 0, "y": 6, "w": 12,"h": 2}},
    ],
    UserRole.PHD_CANDIDATE.value: [
        {"widget_type": "research_progress",   "title": "PhD Progress",         "data_source": "workflow",       "position": {"x": 0, "y": 0, "w": 6, "h": 3}},
        {"widget_type": "publication_pipeline","title": "Publication Pipeline",  "data_source": "project_center", "position": {"x": 6, "y": 0, "w": 6, "h": 3}},
        {"widget_type": "literature_map",      "title": "Literature Map",       "data_source": "knowledge_graph","position": {"x": 0, "y": 3, "w": 4, "h": 3}},
        {"widget_type": "citation_tracker",    "title": "Citations",            "data_source": "citation_monitoring","position": {"x": 4, "y": 3, "w": 4, "h": 3}},
        {"widget_type": "ai_assistant",        "title": "Research Copilot",     "data_source": "copilot",        "position": {"x": 8, "y": 3, "w": 4, "h": 3}},
        {"widget_type": "deadline_tracker",    "title": "Deadlines",            "data_source": "notifications",  "position": {"x": 0, "y": 6, "w": 6, "h": 2}},
        {"widget_type": "activity_feed",       "title": "Activity",             "data_source": "timeline",       "position": {"x": 6, "y": 6, "w": 6, "h": 2}},
    ],
    UserRole.RESEARCHER.value: [
        {"widget_type": "research_impact",     "title": "Research Impact",       "data_source": "research_impact","position": {"x": 0, "y": 0, "w": 6, "h": 3}},
        {"widget_type": "grant_pipeline",      "title": "Grant Pipeline",        "data_source": "grant_predictor","position": {"x": 6, "y": 0, "w": 6, "h": 3}},
        {"widget_type": "publication_analytics","title":"Publication Analytics", "data_source": "analytics",      "position": {"x": 0, "y": 3, "w": 4, "h": 3}},
        {"widget_type": "collaboration_network","title":"Collaboration Network", "data_source": "collaboration",  "position": {"x": 4, "y": 3, "w": 4, "h": 3}},
        {"widget_type": "prediction_insights", "title": "Predictions",          "data_source": "prediction",     "position": {"x": 8, "y": 3, "w": 4, "h": 3}},
        {"widget_type": "ai_assistant",        "title": "Research Copilot",     "data_source": "copilot",        "position": {"x": 0, "y": 6, "w": 6, "h": 3}},
        {"widget_type": "activity_feed",       "title": "Activity",             "data_source": "timeline",       "position": {"x": 6, "y": 6, "w": 6, "h": 3}},
    ],
    UserRole.PROFESSOR.value: [
        {"widget_type": "research_impact",     "title": "Research Impact",       "data_source": "research_impact","position": {"x": 0, "y": 0, "w": 4, "h": 3}},
        {"widget_type": "reputation_score",    "title": "Reputation Score",      "data_source": "reputation",     "position": {"x": 4, "y": 0, "w": 4, "h": 3}},
        {"widget_type": "teaching_analytics",  "title": "Teaching Analytics",    "data_source": "teaching",       "position": {"x": 8, "y": 0, "w": 4, "h": 3}},
        {"widget_type": "student_progress",    "title": "Student Progress",      "data_source": "collaboration",  "position": {"x": 0, "y": 3, "w": 6, "h": 3}},
        {"widget_type": "grant_pipeline",      "title": "Grant Pipeline",        "data_source": "grant_predictor","position": {"x": 6, "y": 3, "w": 6, "h": 3}},
        {"widget_type": "collaboration_network","title":"Collaboration Network", "data_source": "collaboration",  "position": {"x": 0, "y": 6, "w": 6, "h": 3}},
        {"widget_type": "activity_feed",       "title": "Activity",             "data_source": "timeline",       "position": {"x": 6, "y": 6, "w": 6, "h": 3}},
    ],
    UserRole.INSTITUTION.value: [
        {"widget_type": "institution_analytics","title":"Institution Analytics", "data_source": "institution",    "position": {"x": 0, "y": 0, "w": 6, "h": 3}},
        {"widget_type": "benchmarking",         "title": "Benchmarking",         "data_source": "institution",    "position": {"x": 6, "y": 0, "w": 6, "h": 3}},
        {"widget_type": "department_analytics", "title": "Departments",          "data_source": "institution",    "position": {"x": 0, "y": 3, "w": 4, "h": 3}},
        {"widget_type": "compliance",           "title": "Compliance",           "data_source": "verification",   "position": {"x": 4, "y": 3, "w": 4, "h": 3}},
        {"widget_type": "grant_pipeline",       "title": "Grant Portfolio",      "data_source": "grant_predictor","position": {"x": 8, "y": 3, "w": 4, "h": 3}},
        {"widget_type": "activity_feed",        "title": "Institution Activity", "data_source": "timeline",       "position": {"x": 0, "y": 6, "w": 12,"h": 3}},
    ],
    UserRole.ADMINISTRATOR.value: [
        {"widget_type": "platform_health",      "title": "Platform Health",      "data_source": "self_improvement","position": {"x": 0, "y": 0, "w": 6, "h": 3}},
        {"widget_type": "user_analytics",       "title": "User Analytics",       "data_source": "admin",          "position": {"x": 6, "y": 0, "w": 6, "h": 3}},
        {"widget_type": "ai_performance",       "title": "AI Performance",       "data_source": "self_improvement","position": {"x": 0, "y": 3, "w": 4, "h": 3}},
        {"widget_type": "security_center",      "title": "Security",             "data_source": "security",       "position": {"x": 4, "y": 3, "w": 4, "h": 3}},
        {"widget_type": "billing_overview",     "title": "Billing",              "data_source": "billing",        "position": {"x": 8, "y": 3, "w": 4, "h": 3}},
        {"widget_type": "activity_feed",        "title": "Platform Activity",    "data_source": "timeline",       "position": {"x": 0, "y": 6, "w": 12,"h": 3}},
    ],
}


def _build_widgets(role: str) -> list[DashboardWidget]:
    templates = _ROLE_WIDGETS.get(role, _ROLE_WIDGETS[UserRole.RESEARCHER.value])
    return [
        DashboardWidget(
            widget_type=t["widget_type"],
            title=t["title"],
            data_source=t["data_source"],
            position=t["position"],
        )
        for t in templates
    ]


def get_dashboard(user_role: str, metrics: dict | None = None) -> DashboardConfig:
    if user_role not in [r.value for r in UserRole]:
        user_role = UserRole.RESEARCHER.value

    widgets = _build_widgets(user_role)

    personalization: dict = {}
    if metrics:
        personalization["adapted_for"] = metrics.get("career_stage", user_role)
        if metrics.get("active_grants", 0) > 2:
            personalization["grant_widgets_expanded"] = True
        if metrics.get("publications_per_year", 0) > 5:
            personalization["publication_focus"] = True

    return DashboardConfig(
        user_role=user_role,
        widgets=widgets,
        personalization=personalization,
    )


def get_available_roles() -> list[str]:
    return [r.value for r in UserRole]
