"""ORM models (SAD §4). Import this module to register all tables on `Base.metadata`."""

from backend.app.models.approval import Approval
from backend.app.models.audit_event import AuditEvent
from backend.app.models.base import Base
from backend.app.models.instance import Instance
from backend.app.models.kb_article import KbArticle
from backend.app.models.learned_pattern import LearnedPattern
from backend.app.models.user import User

__all__ = [
    "Approval",
    "AuditEvent",
    "Base",
    "Instance",
    "KbArticle",
    "LearnedPattern",
    "User",
]
