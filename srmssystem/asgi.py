"""
ASGI config for srmssystem project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from restaurant.routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'srmssystem.settings')

# The ASGI application that handles both HTTP and WebSocket connections
application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # Handles traditional HTTP requests
    "websocket": AuthMiddlewareStack(  # Adds authentication to WebSocket
        URLRouter(websocket_urlpatterns)
    ),
})