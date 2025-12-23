# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import Message
from asgiref.sync import sync_to_async


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
