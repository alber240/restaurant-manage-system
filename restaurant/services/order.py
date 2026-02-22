# restaurant/services/order.py
from restaurant.models import Order, OrderItem, Cart
from restaurant.services import inventory

def create_order_from_cart(user, payment_method=None, notes=""):
    """Create an order from the user's cart."""
    cart = Cart.objects.get(user=user)
    if cart.items.count() == 0:
        raise ValueError("Cart is empty")
    
    # First, check stock for all items
    for cart_item in cart.items.all():
        if cart_item.item.stock < cart_item.quantity:
            raise ValueError(f"Insufficient stock for {cart_item.item.name}. Only {cart_item.item.stock} left.")

    order = Order.objects.create(
        user=user,
        status='received',
        total=cart.total,
        notes=notes,
        payment_method=payment_method,
        payment_status='pending'
    )

    for cart_item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            item=cart_item.item,
            quantity=cart_item.quantity,
            price=cart_item.item.price
        )
        #dedut stock
        inventory.deduct_stock(cart_item.item.id, cart_item.quantity)

    # Clear the cart
    cart.items.all().delete()
    return order

def update_order_status(order_id, new_status):
    """Update order status and trigger notifications."""
    order = Order.objects.get(pk=order_id)
    order.status = new_status
    order.save()
    return order

def get_orders_for_user(user):
    """Get all orders for a user."""
    return Order.objects.filter(user=user).order_by('-created_at')

def get_kitchen_orders():
    """Get orders for kitchen display (received or preparing)."""
    return Order.objects.filter(status__in=['received', 'preparing']).order_by('-created_at')

def get_waiter_orders():
    """Get orders for waiter display (preparing or ready)."""
    return Order.objects.filter(status__in=['preparing', 'ready']).order_by('-created_at')

def get_order_by_id(order_id, user=None):
    """
    Get an order by its ID.
    If user is provided, ensure the order belongs to that user.
    """
    queryset = Order.objects.all()
    if user:
        queryset = queryset.filter(user=user)
    return queryset.get(pk=order_id)