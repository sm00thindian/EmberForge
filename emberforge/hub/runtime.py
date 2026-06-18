"""Hub composition root — wires settings, layout, personas, and converse for one tenant."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from emberforge.hub.deployment import DeploymentProfile
from emberforge.hub.layout import ProjectLayout
from emberforge.hub.storage.factory import HubStores, build_hub_stores, get_process_security_store
from emberforge.services.converse import ConverseService
from emberforge.services.personas import Persona
from emberforge.settings import Settings, get_settings


@dataclass(frozen=True)
class HubRuntime:
    """One logical EmberForge hub (single tenant today, cloud-ready seams)."""

    settings: Settings
    deployment: DeploymentProfile
    layout: ProjectLayout
    stores: HubStores
    personas: dict[str, Persona]
    converse: ConverseService

    @property
    def tenant_key(self) -> str:
        return self.layout.tenant_key

    def as_capabilities(self) -> dict[str, object]:
        """Expose deployment facts to /device/v1/capabilities and setup status."""
        return {
            "deployment": self.deployment.value,
            "tenant_mode": "single" if not self.tenant_key else "isolated",
            "state_backend": self.deployment.state_backend,
            "conversation_backend": self.deployment.conversation_backend,
            "setup_env_file_writes": self.deployment.allows_env_file_writes,
        }


def build_hub(
    settings: Settings | None = None,
    *,
    tenant_key: str = "",
) -> HubRuntime:
    """Construct a hub runtime from settings (maker-local by default)."""
    resolved = settings or get_settings()
    deployment = resolved.deployment_profile
    layout = ProjectLayout.from_settings(resolved, tenant_key=tenant_key)
    security_store = get_process_security_store() if settings is None else None
    stores = build_hub_stores(
        resolved,
        layout,
        deployment,
        security_store=security_store,
    )
    personas = stores.personas.load()
    converse = ConverseService(
        resolved,
        personas,
        history_store=stores.conversation,
    )
    return HubRuntime(
        settings=resolved,
        deployment=deployment,
        layout=layout,
        stores=stores,
        personas=personas,
        converse=converse,
    )


@lru_cache
def get_hub() -> HubRuntime:
    """Process-wide default hub for CLI and uvicorn entrypoints."""
    return build_hub()