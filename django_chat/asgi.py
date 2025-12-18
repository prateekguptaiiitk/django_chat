"""
ASGI config for django_chat project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from chat import routing

from chat.middleware import JwtCookieAuthMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_chat.settings')

# Initialize ASGI application

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JwtCookieAuthMiddleware(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})
