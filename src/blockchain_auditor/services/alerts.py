from __future__ import annotations

import logging
from dataclasses import dataclass

LOGGER = logging.getLogger("blockchain_auditor.alerts")


@dataclass
class Alert:
    code: str
    level: str
    message: str
    context: dict


class AlertService:
    """Unified local alert boundary; enterprise transports can implement this interface."""
    def publish(self, alert: Alert) -> None:
        getattr(LOGGER, alert.level if alert.level in {"info", "warning", "error"} else "info")(
            "%s: %s context=%s", alert.code, alert.message, alert.context
        )


alerts = AlertService()
