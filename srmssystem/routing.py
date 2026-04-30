from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from restaurant.consumers import KitchenConsumer, WaiterConsumer

websocket_urlpatterns = [
    path('ws/kitchen/', KitchenConsumer.as_asgi()),
    path('ws/waiter/', WaiterConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})