"""Notification engine - sends alerts via multiple channels."""

import re
from datetime import datetime, timedelta
from typing import Any


class NotificationEngine:
    """Handles sending notifications across email, SMS, and push channels."""

    def __init__(self, email_client, sms_client, push_client, db, logger):
        self.email_client = email_client
        self.sms_client = sms_client
        self.push_client = push_client
        self.db = db
        self.logger = logger
        self._rate_limits = {}
        self._templates = {}

    def send_notification(
        self, user_id: str, notification_type: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Send a notification to a user through appropriate channels."""
        user = self.db.find("users", {"user_id": user_id})
        if not user:
            return {"success": False, "error": "User not found"}

        prefs = user.get("notification_preferences", {})
        channels = prefs.get("channels", ["email"])
        quiet_start = prefs.get("quiet_hours_start")
        quiet_end = prefs.get("quiet_hours_end")

        now = datetime.now()
        if quiet_start and quiet_end:
            current_hour = now.hour
            if quiet_start <= quiet_end:
                if quiet_start <= current_hour < quiet_end:
                    if notification_type != "critical":
                        self.db.insert(
                            "deferred_notifications",
                            {
                                "user_id": user_id,
                                "type": notification_type,
                                "data": data,
                                "defer_until": now.replace(hour=quiet_end, minute=0).isoformat(),
                            },
                        )
                        return {
                            "success": True,
                            "deferred": True,
                            "reason": "quiet hours",
                        }
            else:
                if current_hour >= quiet_start or current_hour < quiet_end:
                    if notification_type != "critical":
                        self.db.insert(
                            "deferred_notifications",
                            {
                                "user_id": user_id,
                                "type": notification_type,
                                "data": data,
                                "defer_until": now.replace(hour=quiet_end, minute=0).isoformat(),
                            },
                        )
                        return {
                            "success": True,
                            "deferred": True,
                            "reason": "quiet hours",
                        }

        rate_key = f"{user_id}:{notification_type}"
        if rate_key in self._rate_limits:
            last_sent, count = self._rate_limits[rate_key]
            if (now - last_sent).total_seconds() < 3600:
                if count >= 5:
                    self.logger.warning(f"Rate limit exceeded for {user_id} on {notification_type}")
                    return {
                        "success": False,
                        "error": "Rate limit exceeded",
                    }
                self._rate_limits[rate_key] = (last_sent, count + 1)
            else:
                self._rate_limits[rate_key] = (now, 1)
        else:
            self._rate_limits[rate_key] = (now, 1)

        template = self._templates.get(notification_type)
        if not template:
            template = self.db.find("notification_templates", {"type": notification_type})
            if template:
                self._templates[notification_type] = template

        if not template:
            return {
                "success": False,
                "error": f"No template for {notification_type}",
            }

        subject = template.get("subject", "Notification")
        body = template.get("body", "")
        for key, value in data.items():
            subject = subject.replace(f"{{{{{key}}}}}", str(value))
            body = body.replace(f"{{{{{key}}}}}", str(value))

        results = {}
        if "email" in channels:
            email = user.get("email")
            if email and re.match(r"[^@]+@[^@]+\.[^@]+", email):
                try:
                    self.email_client.send(to=email, subject=subject, body=body)
                    results["email"] = "sent"
                except Exception as e:
                    results["email"] = f"failed: {e}"
                    self.logger.error(f"Email failed for {user_id}: {e}")
            else:
                results["email"] = "invalid_address"

        if "sms" in channels:
            phone = user.get("phone")
            if phone:
                clean_phone = re.sub(r"[^\d+]", "", phone)
                if len(clean_phone) >= 10:
                    try:
                        sms_body = body[:160]
                        self.sms_client.send(to=clean_phone, message=sms_body)
                        results["sms"] = "sent"
                    except Exception as e:
                        results["sms"] = f"failed: {e}"
                        self.logger.error(f"SMS failed for {user_id}: {e}")
                else:
                    results["sms"] = "invalid_phone"
            else:
                results["sms"] = "no_phone"

        if "push" in channels:
            device_tokens = user.get("device_tokens", [])
            if device_tokens:
                push_results = []
                for token in device_tokens:
                    try:
                        self.push_client.send(
                            token=token,
                            title=subject,
                            body=body[:256],
                            data=data,
                        )
                        push_results.append("sent")
                    except Exception as e:
                        push_results.append(f"failed: {e}")
                        self.logger.error(f"Push failed for {user_id} token {token}: {e}")
                results["push"] = push_results
            else:
                results["push"] = "no_devices"

        self.db.insert(
            "notification_log",
            {
                "user_id": user_id,
                "type": notification_type,
                "channels": results,
                "sent_at": now.isoformat(),
                "data": data,
            },
        )

        any_sent = any(
            v == "sent" or (isinstance(v, list) and "sent" in v) for v in results.values()
        )
        return {"success": any_sent, "channels": results}

    def send_bulk(
        self,
        user_ids: list[str],
        notification_type: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Send the same notification to multiple users."""
        results = {}
        succeeded = 0
        failed = 0
        deferred = 0
        for uid in user_ids:
            result = self.send_notification(uid, notification_type, data)
            results[uid] = result
            if result.get("success"):
                if result.get("deferred"):
                    deferred += 1
                else:
                    succeeded += 1
            else:
                failed += 1
        return {
            "total": len(user_ids),
            "succeeded": succeeded,
            "failed": failed,
            "deferred": deferred,
            "details": results,
        }

    def get_notification_history(
        self,
        user_id: str,
        limit: int = 50,
        notification_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get notification history for a user."""
        query: dict[str, Any] = {"user_id": user_id}
        if notification_type:
            query["type"] = notification_type
        logs = self.db.find_many("notification_log", query, limit=limit)
        return logs

    def retry_failed(self, hours: int = 24) -> dict[str, Any]:
        """Retry notifications that failed in the last N hours."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        logs = self.db.find_many(
            "notification_log",
            {"sent_at": {"$gte": cutoff}},
        )
        retried = 0
        succeeded = 0
        for log in logs:
            channels = log.get("channels", {})
            has_failure = False
            for _channel, status in channels.items():
                if isinstance(status, str) and "failed" in status:
                    has_failure = True
                    break
                if isinstance(status, list):
                    for s in status:
                        if "failed" in s:
                            has_failure = True
                            break
            if has_failure:
                result = self.send_notification(log["user_id"], log["type"], log.get("data", {}))
                retried += 1
                if result.get("success"):
                    succeeded += 1
        return {
            "retried": retried,
            "succeeded": succeeded,
            "still_failing": retried - succeeded,
        }
