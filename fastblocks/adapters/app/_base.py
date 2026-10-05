from __future__ import annotations

import typing as t
from typing import Literal

# Pydantic imports
from pydantic import BaseModel, Field
# Oneiric imports
from oneiric.core.config import OneiricSettings
from starlette.routing import Router
from fastblocks.core.validators import DEFAULT_STYLE, StyleName


# ---------------------------------------------------------------------------
# Observability v6 spec settings (Δ9/Δ11/Δ18/Δ20/Δ41).
#
# Per oneiric 0.26.4, OneiricSettings enforces ``extra="forbid"`` — fields
# loaded from app.yml that are not declared on the model are rejected.
# These classes declare the v6 spec defaults so the settings in app.yml
# (``observability.cardinality_mode`` etc.) are accepted, and so the
# v6 spec tests can construct ``AppSettings()`` without a ValidationError.
# ---------------------------------------------------------------------------


class MetricsSettings(BaseModel):
    """Per Δ9: ``accept_dispatch`` controls the /metrics endpoint's
    Accept-header dispatch behaviour (OpenMetrics vs text/plain)."""

    accept_dispatch: bool = True


class TracesSettings(BaseModel):
    """Per Δ10/Δ18: ``shutdown_on_lifespan_exit`` controls whether the
    OTel SDK tracer provider is flushed on app shutdown."""

    shutdown_on_lifespan_exit: bool = True


class SentrySettings(BaseModel):
    """Per Δ11/Δ20: Sentry SDK bridge configuration.

    ``disabled_on_import_error`` controls loud-fail vs silent-swallow on
    Sentry import errors. ``profiling_enabled`` is alpha-locked (Δ20)
    and raises RuntimeError if True."""

    disabled_on_import_error: bool = False
    profiling_enabled: bool = False


class ObservabilitySettings(BaseModel):
    """Per Δ41: ``cardinality_mode`` escalation order is
    off < audit < warn < enforce."""

    cardinality_mode: Literal["off", "audit", "warn", "enforce"] = "enforce"
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    traces: TracesSettings = Field(default_factory=TracesSettings)
    sentry: SentrySettings = Field(default_factory=SentrySettings)


class AppBaseSettings(OneiricSettings):  # type: ignore[misc]
    """App base settings using OneiricSettings.

    The ``v6_observability`` field holds the fastblocks v6 observability
    behavior spec (Δ9/Δ11/Δ18/Δ20/Δ41: cardinality_mode, metrics, traces,
    sentry). It is intentionally NOT named ``observability`` because
    oneiric 0.26.4's ``OneiricSettings.observability`` field is typed as
    ``OTelStorageSettings`` (pgvector/embeddings) and uses
    ``extra="forbid"``; reusing the field name would conflict with
    oneiric's storage settings. Using a distinct field name lets both
    oneiric's storage settings and fastblocks's behavior settings
    coexist on the same AppSettings model.
    """

    name: str = "fastblocks"
    style: StyleName = DEFAULT_STYLE
    theme: str = "light"
    title: str = ""
    domain: str = ""
    description: str = ""
    version: str = ""
    v6_observability: ObservabilitySettings = Field(
        default_factory=ObservabilitySettings,
    )


class AppProtocol(t.Protocol):
    def __init__(self) -> None: ...

    async def lifespan(self) -> t.AsyncIterator[None]: ...


class AppBase:
    """App base adapter using Oneiric."""

    router: Router | None

    def __init__(self) -> None:
        self.router = None
