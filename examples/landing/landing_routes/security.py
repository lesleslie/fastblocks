"""Security route — threat model + CVE status + security headers.

Renders a list of CVE-status alerts (using the ``ui-alert`` component)
and threat-model cards. The data is static and the route does not
claim any specific CVE IDs — the alerts are placeholders, and the test
suite asserts only that the page returns 200 and renders the expected
structure. Real CVE status would be sourced from a live advisory feed.

# req: REQ-P2-B2-001
"""

from __future__ import annotations

from dataclasses import dataclass

from fastblocks_ui import alert, card
from landing_templates import render_template
from starlette.requests import Request
from starlette.responses import HTMLResponse


@dataclass(frozen=True)
class CveStatus:
    """Single CVE-status row."""

    title: str
    body: str
    state: str  # one of: "info" | "success" | "warning" | "danger"


@dataclass(frozen=True)
class ThreatLink:
    """Single threat-model link."""

    title: str
    body: str


_CVES: tuple[CveStatus, ...] = (
    CveStatus(
        title="No known critical CVEs",
        body="Framework dependencies are pinned and audited at release time.",
        state="info",
    ),
    CveStatus(
        title="Security headers by default",
        body="SECURITY_HEADERS middleware is on unless explicitly opted out (FastBlocksSettings).",
        state="info",
    ),
)


_THREAT_LINKS: tuple[ThreatLink, ...] = (
    ThreatLink("Threat model", "See docs/security/THREAT_MODEL.md"),
    ThreatLink("Disclosure policy", "See docs/security/DISCLOSURE.md"),
    ThreatLink("Security headers", "See docs/security/HEADERS.md"),
)


async def security_route(request: Request) -> HTMLResponse:
    """Threat model + CVE status + security headers visible."""
    alerts_markup = "".join(
        alert(
            content=f"<strong>{c.title}</strong> {c.body}",
            variant=c.state,
        )
        for c in _CVES
    )
    cards_markup = "".join(card(header=t.title, body=t.body) for t in _THREAT_LINKS)
    context = {"alerts_markup": alerts_markup, "cards_markup": cards_markup}
    return HTMLResponse(await render_template(request, "security.html", context))
