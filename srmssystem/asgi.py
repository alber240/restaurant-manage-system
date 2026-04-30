import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from restaurant.consumers import KitchenConsumer, WaiterConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'srmssystem.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path('ws/kitchen/', KitchenConsumer.as_asgi()),
            path('ws/waiter/', WaiterConsumer.as_asgi()),
        ])
    ),
})