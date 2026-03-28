"""Async notification dispatcher with multiple channels and retry logic."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
from typing import Optional


class Channel(Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class Priority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Notification:
    recipient_id: str
    channel: Channel
    subject: str
    body: str
    priority: Priority = Priority.NORMAL
    scheduled_at: Optional[datetime] = None


@dataclass
class DeliveryResult:
    notification: Notification
    success: bool
    attempts: int
    error: Optional[str] = None
    delivered_at: Optional[datetime] = None


class NotificationDispatcher:
    """Dispatches notifications across channels with retry and quiet hours."""

    QUIET_HOURS_START = time(22, 0)  # 10 PM
    QUIET_HOURS_END = time(7, 0)  # 7 AM
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]  # seconds

    def __init__(self, email_client, sms_client, push_client):
        self.email_client = email_client
        self.sms_client = sms_client
        self.push_client = push_client
        self._rate_limits: dict[str, list[datetime]] = {}

    def _is_quiet_hours(self, now: Optional[datetime] = None) -> bool:
        """Check if current time falls within quiet hours."""
        current_time = (now or datetime.utcnow()).time()
        if self.QUIET_HOURS_START > self.QUIET_HOURS_END:
            # Crosses midnight
            return current_time >= self.QUIET_HOURS_START or current_time < self.QUIET_HOURS_END
        return self.QUIET_HOURS_START <= current_time < self.QUIET_HOURS_END

    def _check_rate_limit(self, recipient_id: str, max_per_minute: int = 5) -> bool:
        """Check if recipient has exceeded rate limit."""
        now = datetime.utcnow()
        if recipient_id not in self._rate_limits:
            self._rate_limits[recipient_id] = []

        # Remove entries older than 1 minute
        self._rate_limits[recipient_id] = [
            t for t in self._rate_limits[recipient_id] if (now - t).total_seconds() < 60
        ]

        if len(self._rate_limits[recipient_id]) >= max_per_minute:
            return False

        self._rate_limits[recipient_id].append(now)
        return True

    async def send(self, notification: Notification) -> DeliveryResult:
        """Send a notification with retry logic.

        Respects quiet hours for non-critical notifications.
        Applies rate limiting per recipient.
        Retries with exponential backoff on failure.

        Returns DeliveryResult with success status and attempt count.
        """
        # Quiet hours check (critical notifications bypass)
        if notification.priority != Priority.CRITICAL and self._is_quiet_hours():
            return DeliveryResult(
                notification=notification,
                success=False,
                attempts=0,
                error="Blocked by quiet hours policy",
            )

        # Rate limit check
        if not self._check_rate_limit(notification.recipient_id):
            return DeliveryResult(
                notification=notification,
                success=False,
                attempts=0,
                error="Rate limit exceeded",
            )

        # Dispatch with retry
        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                await self._dispatch(notification)
                return DeliveryResult(
                    notification=notification,
                    success=True,
                    attempts=attempt,
                    delivered_at=datetime.utcnow(),
                )
            except Exception as e:
                last_error = str(e)
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(self.RETRY_DELAYS[attempt - 1])

        return DeliveryResult(
            notification=notification,
            success=False,
            attempts=self.MAX_RETRIES,
            error=f"Failed after {self.MAX_RETRIES} attempts: {last_error}",
        )

    async def _dispatch(self, notification: Notification) -> None:
        """Route to the appropriate channel client."""
        if notification.channel == Channel.EMAIL:
            await self.email_client.send(
                to=notification.recipient_id,
                subject=notification.subject,
                body=notification.body,
            )
        elif notification.channel == Channel.SMS:
            await self.sms_client.send(
                to=notification.recipient_id,
                message=notification.body,
            )
        elif notification.channel == Channel.PUSH:
            await self.push_client.send(
                device_id=notification.recipient_id,
                title=notification.subject,
                body=notification.body,
            )
        else:
            raise ValueError(f"Unknown channel: {notification.channel}")

    async def send_batch(self, notifications: list[Notification]) -> list[DeliveryResult]:
        """Send multiple notifications concurrently."""
        return await asyncio.gather(*(self.send(n) for n in notifications))
