from flask import request, has_request_context
from app.extensions import db
from app.models import AuditLog
from app.decorators import get_current_user

SENSITIVE_KEYS = {"password", "password_hash", "secret", "token", "csrf_token", "confirm_password"}


def sanitize_details(details: str) -> str:
    """Ensure passwords or secret tokens are never written to audit logs."""
    if not details:
        return ""
    lower = details.lower()
    for key in SENSITIVE_KEYS:
        if f"{key}=" in lower or f'"{key}"' in lower:
            return "[REDACTED SENSITIVE PAYLOAD]"
    return details


def log_audit(
    action: str,
    entity_type: str,
    entity_id=None,
    details: str = "",
    actor=None,
    is_demo: bool = False,
    commit: bool = False,
) -> AuditLog:
    """Record an administrative or security-sensitive action in the audit log."""
    if actor is None and has_request_context():
        actor = get_current_user()

    actor_id = actor.id if actor else None
    actor_username = actor.username if actor else "system"
    ip_addr = request.remote_addr if has_request_context() else "127.0.0.1"

    entry = AuditLog(
        actor_id=actor_id,
        actor_username=actor_username,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=sanitize_details(details),
        ip_address=ip_addr,
        is_demo=is_demo,
    )
    db.session.add(entry)
    if commit:
        db.session.commit()
    return entry
