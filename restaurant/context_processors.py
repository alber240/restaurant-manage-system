from .models import Cart

def cart_context(request):
    """
    Adds cart item count to the template context for all requests.
    """
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.items.count()
    else:
        cart_count = 0
    return {'cart_count': cart_count}