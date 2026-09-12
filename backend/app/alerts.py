"""Alerting on health-state transitions, via Resend.

Same fallback pattern as NFL_Confidence's email_service: if RESEND_API_KEY
isn't set, alerts are logged instead of sent -- local/dev never needs real
credentials. No PagerDuty-class tooling; this is a single-user dashboard.
"""

from __future__ import annotations

import logging

import httpx

from .config import Settings

logger = logging.getLogger("aisaac.alerts")


def send_transition_alert(
    settings: Settings, app_name: str, from_state: str, to_state: str
) -> None:
    if to_state in ("down", "degraded") and from_state not in ("down", "degraded"):
        subject = f"[AIsaac] {app_name} is now {to_state}"
    elif to_state == "up" and from_state in ("down", "degraded"):
        subject = f"[AIsaac] {app_name} has recovered"
    else:
        return

    body = f"{app_name} transitioned from '{from_state}' to '{to_state}'."

    if not settings.resend_api_key or not settings.alert_to_email:
        logger.warning("ALERT (not sent, no Resend config): %s -- %s", subject, body)
        return

    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.alert_from_email,
                "to": [settings.alert_to_email],
                "subject": subject,
                "text": body,
            },
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Failed to send transition alert via Resend: %s", subject)
