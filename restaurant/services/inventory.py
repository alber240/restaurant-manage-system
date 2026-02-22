from restaurant import models
from restaurant.models import MenuItem

def deduct_stock(item_id, quantity):
    """Reduce stock for a menu item. Raises ValueError if insufficient stock."""
    try:
        item = MenuItem.objects.get(pk=item_id)
    except MenuItem.DoesNotExist:
        raise ValueError(f"Item {item_id} not found")

    if item.stock < quantity:
        raise ValueError(f"Insufficient stock for {item.name}. Available: {item.stock}, requested: {quantity}")

    item.stock -= quantity
    item.save()
    return item.stock

def check_low_stock(item):
    """Return True if item stock is below threshold."""
    return item.stock <= item.low_stock_threshold

def get_low_stock_items():
    """Return all items with stock below threshold."""
    return MenuItem.objects.filter(stock__lte=models.F('low_stock_threshold'))

def get_inventory_status():
    """Return all items with stock info for dashboard."""
    return MenuItem.objects.all().values('id', 'name', 'stock', 'low_stock_threshold')