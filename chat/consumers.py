# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import Message
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.utils import timezone
import datetime


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)

        message_text = data.get("message", "")
        recipient_id = data.get("recipient")
        file = data.get("file")

        recipient = await self.get_user_by_id(recipient_id)

        msg = await self.save_message(
            sender=self.user,
            recipient=recipient,
            message=message_text,
            file=file
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "id": msg.id,
                "sender": self.user.id,
                "recipient": recipient.id,
                "message": msg.message,
                "file": msg.file.url if msg.file else None,
                "created_at": msg.created_at.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    # ---------------- DB HELPERS ---------------- #

    @sync_to_async
    def get_user_by_id(self, user_id):
        return User.objects.get(id=user_id)

    @sync_to_async
    def save_message(self, sender, recipient, message, file=None):
        return Message.objects.create(
            sender=sender,
            recipient=recipient,
            message=message,
            file=file if file else None
        )

    # ---------------- DB HELPERS ---------------- #

    @sync_to_async
    def get_user_by_id(self, user_id):
        return User.objects.get(id=user_id)


    @sync_to_async
    def save_message(self, sender, recipient, message, file=None):
        return Message.objects.create(
            sender=sender,
            recipient=recipient,
            message=message,
            file=file if file else None
        )

ONLINE_KEY = "online_users"
TIMEOUT_SECONDS = 10

class PresenceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close()
            return

        self.user = user
        await self.accept()

        await self.channel_layer.group_add("presence", self.channel_name)

        await self.mark_alive()
        await self.broadcast()

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get("type") == "ping":
            await self.mark_alive()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("presence", self.channel_name)

    async def mark_alive(self):
        users = cache.get(ONLINE_KEY, {})
        users[str(self.user.id)] = {
            "username": self.user.username,
            "last_seen": timezone.now().isoformat()
        }
        cache.set(ONLINE_KEY, users)

    async def broadcast(self):
        users = cache.get(ONLINE_KEY, {})
        now = timezone.now()

        online = []
        for uid, info in users.items():
            last_seen = timezone.datetime.fromisoformat(info["last_seen"])
            if (now - last_seen).total_seconds() < TIMEOUT_SECONDS:
                online.append({
                    "userId": uid,
                    "username": info["username"]
                })

        await self.channel_layer.group_send(
            "presence",
            {
                "type": "presence.update",
                "online": online
            }
        )

    async def presence_update(self, event):
        await self.send(text_data=json.dumps({
            "online": event["online"]
        }))