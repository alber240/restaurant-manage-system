import json
from channels.generic.websocket import AsyncWebsocketConsumer


class KitchenConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for kitchen staff.
    Listens to the 'kitchen' group for order updates.
    """

    async def connect(self):
        await self.channel_layer.group_add("kitchen", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("kitchen", self.channel_name)

    async def order_update(self, event):
        """
        Receive order update from the 'kitchen' group and send to WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'order_id': event['order_id'],
            'new_status': event['new_status'],
            'order_data': event.get('order_data', {})
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