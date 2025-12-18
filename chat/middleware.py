from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async

User = get_user_model()


@database_sync_to_async
def get_user_from_jwt(token):
    try:
        access = AccessToken(token)
        return User.objects.get(id=access["user_id"])
    except Exception:
        return AnonymousUser()


class JwtCookieAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        headers = dict(scope["headers"])
        scope["user"] = AnonymousUser()

        if b"cookie" in headers:
            cookies = headers[b"cookie"].decode()
            for cookie in cookies.split(";"):
                name, _, value = cookie.strip().partition("=")
                if name == "access":
                    scope["user"] = await get_user_from_jwt(value)

        return await self.inner(scope, receive, send)
