from restaurant.models import Cart, CartItem, MenuItem

def get_or_create_cart(user):
    """Get or create a cart for the user."""
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart

def add_item_to_cart(user, item_id, quantity=1):
    """Add a menu item to the user's cart."""
    item = MenuItem.objects.get(pk=item_id)
    cart = get_or_create_cart(user)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        item=item,
        defaults={'quantity': quantity}
    )
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    return cart_item

def remove_item_from_cart(user, item_id):
    """Remove a menu item from the user's cart."""
    cart = Cart.objects.get(user=user)
    CartItem.objects.filter(cart=cart, item_id=item_id).delete()

def update_cart_item_quantity(user, item_id, quantity):
    """Update quantity of a cart item."""
    cart = Cart.objects.get(user=user)
    cart_item = CartItem.objects.get(cart=cart, item_id=item_id)
    if quantity <= 0:
        cart_item.delete()
    else:
        cart_item.quantity = quantity
        cart_item.save()
    return cart_item

def get_cart(user):
    """Get user's cart."""
    return Cart.objects.get(user=user)

def get_cart_total(user):
    """Get total price of user's cart."""
    return get_cart(user).total

def get_cart_item_count(user):
    """Get number of items in cart."""
    return get_cart(user).items.count()

def clear_cart(user):
    """Delete all items from cart."""
    cart = get_cart(user)
    cart.items.all().delete()