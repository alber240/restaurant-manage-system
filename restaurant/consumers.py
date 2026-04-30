import json
from channels.generic.websocket import AsyncWebsocketConsumer


import json
from channels.generic.websocket import AsyncWebsocketConsumer

class KitchenConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print(f"🔌 Kitchen WebSocket attempting to connect...")
        await self.channel_layer.group_add("kitchen", self.channel_name)
        await self.accept()
        print(f"✅ Kitchen WebSocket connected successfully")

    async def disconnect(self, close_code):
        print(f"❌ Kitchen WebSocket disconnected with code: {close_code}")
        await self.channel_layer.group_discard("kitchen", self.channel_name)

    async def receive(self, text_data):
        print(f"📨 Received message: {text_data}")
        # Handle incoming messages if needed

    async def new_order(self, event):
        print(f"🆕 New order event received: {event}")
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'order_data': event['order_data']
        }))

    async def order_update(self, event):
        print(f"🔄 Order update event received: {event}")
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'order_id': event['order_id'],
            'new_status': event['new_status']
        }))


class WaiterConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for waitstaff.
    Listens to the 'waiter' group for order updates.
    """

    async def connect(self):
        await self.channel_layer.group_add("waiter", self.channel_name)
        await self.accept()
        print("✅ Waiter WebSocket connected")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("waiter", self.channel_name)
        print("❌ Waiter WebSocket disconnected")

    async def new_order(self, event):
        """
        Receive new order from the 'waiter' group and send to WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'order_data': event['order_data']
        }))

    async def order_update(self, event):
        """
        Receive order update from the 'waiter' group and send to WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'order_id': event['order_id'],
            'new_status': event['new_status']
        }))


class WaiterConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for waitstaff.
    Listens to the 'waiter' group for order updates.
    """

    async def connect(self):
        await self.channel_layer.group_add("waiter", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("waiter", self.channel_name)

    async def order_update(self, event):
        """
        Receive order update from the 'waiter' group and send to WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'order_id': event['order_id'],
            'new_status': event['new_status'],
            'order_data': event.get('order_data', {})
        }))