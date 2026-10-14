import logging

from django.conf import settings


logger = logging.getLogger(__name__)


def send_topic_notification(*, topic, title, body, data):
    """Send a Firebase topic message; keep the API usable when FCM is unconfigured."""
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        if not firebase_admin._apps:
            credentials_path = getattr(settings, "FIREBASE_ADMIN_CREDENTIALS", "")
            if credentials_path:
                firebase_admin.initialize_app(credentials.Certificate(credentials_path))
            else:
                firebase_admin.initialize_app()
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={key: str(value) for key, value in data.items()},
            topic=topic,
        )
        return messaging.send(message)
    except Exception:
        logger.exception("Could not send Firebase notification to topic %s.", topic)
        return None
