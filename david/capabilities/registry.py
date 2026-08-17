from __future__ import annotations

CAPABILITY_GROUPS = {
    "core_ai": [
        "natural_conversation",
        "long_context",
        "memory",
        "personality",
        "multilingual",
        "voice",
        "vision",
        "document_understanding",
    ],
    "knowledge": [
        "web_search",
        "deep_research",
        "citations",
        "fact_checking",
        "report_generation",
    ],
    "reasoning": [
        "planning",
        "goal_decomposition",
        "problem_solving",
        "self_evaluation",
        "retry_failed_tasks",
    ],
    "development": [
        "code_generation",
        "debugging",
        "refactoring",
        "api_builder",
        "website_builder",
        "app_builder",
        "deployment_assistance",
    ],
    "media": [
        "image_generation",
        "image_editing",
        "ocr",
        "video_workflows",
        "audio_workflows",
    ],
    "productivity": [
        "calendar",
        "email",
        "notes",
        "tasks",
        "reminders",
    ],
    "business": [
        "crm",
        "sales_reports",
        "inventory",
        "invoicing",
        "market_analysis",
    ],
    "automation": [
        "workflows",
        "background_jobs",
        "webhooks",
        "integrations",
    ],
    "platform": [
        "plugins",
        "deployment",
        "monitoring",
        "metrics",
        "audit_logs",
        "rate_limiting",
    ],
    "future_suite": [
        "social_media_management",
        "website_publishing",
        "domain_management",
        "model_switching",
        "automatic_model_selection",
        "knowledge_graph",
        "offline_mode",
    ],
}

def list_capabilities() -> dict:
    return CAPABILITY_GROUPS
