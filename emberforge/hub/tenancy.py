"""Tenant scoping helpers — default single-tenant for maker hubs."""

from __future__ import annotations

DEFAULT_TENANT = ""


def scoped_session_id(tenant_key: str, session_id: str) -> str:
    """
    Namespace conversation memory by tenant when multi-tenancy is enabled.

    Maker hubs pass an empty tenant key, preserving today's session_id behavior.
    """
    tenant = tenant_key.strip()
    session = session_id.strip()
    if not tenant:
        return session
    if not session:
        return tenant
    return f"{tenant}:{session}"