import json
import asyncio
import firebase_admin
import logging
from datetime import datetime
from asgiref.sync import sync_to_async
from firebase_admin import credentials, messaging
from django.conf import settings
from dataclasses import dataclass, asdict, field

import firebase_admin._messaging_utils
from bookingsystem.models import CustomUser, FCMToken, UserNotification
from booking_system.settings import Path, BASE_DIR


@dataclass
class FirebaseNotificationPayload:
    title: str
    body: str
    icon: str = None
    sound: str = None
    click_action: str = field(default=None, repr=False, init=False)
    badge: str = None
    data: dict = None

    def to_dict(self):
        return asdict(self)

    def to_args(self):
        return {
            "title": self.title,
            "body": self.body,
            "image": self.icon,
        }

    @property
    def notification_data(self):
        base_dict = {}
        if self.data:
            base_dict.update(self.data)

        base_dict["app_url"] = settings.APP_URL
        if self.click_action:
            base_dict["click_action"] = self.click_action

        return {
            key: (
                json.dumps(value)
                if isinstance(value, dict)
                else str(value) if value is not None else ""
            )
            for key, value in base_dict.items()
        }


class FCMNotification:
    _is_initialized = False
    payload: FirebaseNotificationPayload

    def __init__(self, payload: FirebaseNotificationPayload):
        self.payload = payload

    @staticmethod
    def initialize():
        if not FCMNotification._is_initialized:
            try:
                cred = credentials.Certificate(
                    Path.joinpath(
                        BASE_DIR,
                        "bookingsystem/config/firebase",
                        "service-account.json",
                    )
                )
                firebase_admin.initialize_app(cred)
                FCMNotification._is_initialized = True
            except ValueError:
                FCMNotification._is_initialized = True

    def is_initialized(self):
        if not self._is_initialized:
            raise ValueError("FCMNotification is not initialized.")

    def send(self, users: list[CustomUser]):
        for user in users:
            self.multi_push(
                list(user.fcm_tokens.all().values_list("token", flat=True).distinct())
            )
            UserNotification.objects.create(user=user, payload=self.payload.to_dict(), fcm_sent_at=datetime.now())

    def single_push(self, token: str):
        self.is_initialized()
        try:
            message = messaging.Message(
                notification=messaging.Notification(**self.payload.to_args()),
                data=self.payload.notification_data,
                webpush=messaging.WebpushConfig(
                    fcm_options=(
                        messaging.WebpushFCMOptions(link=self.payload.click_action)
                        if self.payload.click_action
                        else None
                    )
                ),
                token=token,
            )
            return messaging.send(message)
        except firebase_admin._messaging_utils.UnregisteredError:
            FCMToken.objects.filter(token=token).delete()
            return "Unregistered"
        except Exception as e:
            logging.error(f"Error sending notification: {e}", e)
            return None

    async def async_single_push(self, token: str):
        try:
            return messaging.send(
                messaging.Message(
                    notification=messaging.Notification(**self.payload.to_args()),
                    data=self.payload.notification_data,
                    webpush=messaging.WebpushConfig(
                        fcm_options=(
                            messaging.WebpushFCMOptions(link=self.payload.click_action)
                            if self.payload.click_action
                            else None
                        )
                    ),
                    token=token,
                )
            )
        except firebase_admin._messaging_utils.UnregisteredError:
            delete_token = sync_to_async(FCMToken.objects.filter(token=token).delete)
            await delete_token()
            return "Unregistered"
        except Exception as e:
            logging.error(f"Error sending notification: {e}", e)
            return None

    def multi_push(self, tokens: list[str]):
        self.is_initialized()

        async def run_async():
            tasks = [self.async_single_push(token) for token in tokens]
            await asyncio.gather(*tasks)

        asyncio.run(run_async())
