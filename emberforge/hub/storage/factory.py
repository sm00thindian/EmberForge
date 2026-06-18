"""Construct hub storage backends from deployment profile and layout."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from emberforge.hub.deployment import DeploymentProfile
from emberforge.hub.layout import ProjectLayout
from emberforge.hub.storage.local import (
    LocalConfigStore,
    LocalPersonaCatalog,
    LocalSecurityStore,
    build_local_security_store,
)
from emberforge.hub.storage.protocols import (
    ConfigStore,
    ConversationStore,
    PersonaCatalog,
    SecurityStore,
)
from emberforge.services.history import ConversationHistoryStore
from emberforge.settings import Settings, get_settings


@dataclass(frozen=True)
class HubStores:
    """Injectable storage layer for one hub instance."""

    config: ConfigStore
    security: SecurityStore
    conversation: ConversationStore
    personas: PersonaCatalog


def build_conversation_store(settings: Settings) -> ConversationHistoryStore:
    return ConversationHistoryStore(
        max_turns=settings.conversation_max_turns,
        ttl_seconds=settings.conversation_session_ttl_seconds,
    )


def build_hub_stores(
    settings: Settings,
    layout: ProjectLayout,
    deployment: DeploymentProfile,
    *,
    security_store: SecurityStore | None = None,
) -> HubStores:
    """
    Wire storage backends for a hub instance.

    Maker profiles use filesystem + in-memory implementations. Cloud profile
    uses the same local classes today; AWS-backed implementations plug in here
    without changing device or converse APIs.
    """
    return HubStores(
        config=LocalConfigStore(
            layout.env_file,
            allows_writes=deployment.allows_env_file_writes,
        ),
        security=security_store
        or build_local_security_store(settings, layout.security_state_dir),
        conversation=build_conversation_store(settings),
        personas=LocalPersonaCatalog(settings),
    )


@lru_cache
def get_process_security_store() -> LocalSecurityStore:
    """Process-wide security store for default settings (CLI / uvicorn)."""
    settings = get_settings()
    layout = ProjectLayout.from_settings(settings)
    return build_local_security_store(settings, layout.security_state_dir)


def clear_process_security_store() -> None:
    get_process_security_store.cache_clear()