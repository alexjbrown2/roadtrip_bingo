"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

import bingo.routing  # noqa: E402  (must import after django_asgi_app is initialized)

application = ProtocolTypeRouter(
    {
        'http': django_asgi_app,
        'websocket': URLRouter(bingo.routing.websocket_urlpatterns),
    }
)
