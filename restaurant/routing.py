from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/kitchen/$', consumers.KitchenConsumer.as_asgi()),
    re_path(r'ws/waiter/$', consumers.WaiterConsumer.as_asgi()),
    # You can add more routes for other roles if needed
]