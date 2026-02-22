from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from restaurant.forms import ReservationForm
from restaurant.models import Order
from restaurant.services import cart as cart_service
from restaurant.services import order as order_service
from restaurant.services import reservation as reservation_service

def home_view(request):
    return render(request, 'restaurant/home.html')

def about_view(request):
    return render(request, 'restaurant/aboutus.html')

def contact_view(request):
    return render(request, 'restaurant/contactus.html')

def menu_view(request):
    from restaurant.models import MenuCategory
    categories = MenuCategory.objects.prefetch_related('menu_items').all()
    return render(request, 'restaurant/customer/menu.html', {'categories': categories})

@login_required
def add_to_cart(request, item_id):
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        try:
            cart_service.add_item_to_cart(request.user, item_id, quantity)
            cart = cart_service.get_cart(request.user)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'cart_total': str(cart.total),
                    'item_count': cart.item_count
                })
            messages.success(request, "Item added to cart")
        except Exception as e:
            messages.error(request, str(e))
        return redirect('menu')

@login_required
def view_cart(request):
    cart = cart_service.get_cart(request.user)
    return render(request, 'restaurant/customer/cart.html', {
        'cart': cart,
        'cart_items': cart.items.all()
    })

@login_required
def remove_from_cart(request, item_id):
    cart_service.remove_item_from_cart(request.user, item_id)
    messages.success(request, "Item removed from cart")
    return redirect('view_cart')

@login_required
def update_cart(request, item_id):
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        cart_service.update_cart_item_quantity(request.user, item_id, quantity)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            cart = cart_service.get_cart(request.user)
            return JsonResponse({
                'success': True,
                'cart_total': str(cart.total),
                'item_count': cart.item_count
            })
    return redirect('view_cart')

@login_required
def order_history(request):
    orders = order_service.get_orders_for_user(request.user)
    return render(request, 'restaurant/customer/order_history.html', {'orders': orders})

def cart_count(request):
    count = 0
    if request.user.is_authenticated:
        count = cart_service.get_cart_item_count(request.user)
    return JsonResponse({'count': count})

@login_required
def checkout(request):
    cart = cart_service.get_cart(request.user)
    return render(request, 'restaurant/customer/checkout.html', {
        'cart': cart,
        'cart_items': cart.items.all()
    })

@login_required
def order_confirmation(request, order_id):
    order = order_service.get_order_by_id(order_id, user=request.user)
    return render(request, 'restaurant/customer/order_confirmation.html', {'order': order})

@login_required
def order_payment(request, order_id):
    order = order_service.get_order_by_id(order_id, user=request.user)
    return render(request, 'restaurant/customer/order_payment.html', {'order': order})

def verify_3d_secure(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    if request.method == 'POST':
        if request.POST.get('secure_code') == '1234':
            order.payment_status = 'completed'
            order.save()
            from restaurant.signals import send_payment_receipt
            send_payment_receipt(order)
            messages.success(request, "3D Secure verification successful")
            return redirect('order_payment', order_id=order.id)
        else:
            messages.error(request, "Invalid verification code")
    return render(request, 'restaurant/customer/3d_secure.html', {'order_id': order_id})

def create_reservation(request):
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            data = {
                'name': form.cleaned_data['name'],
                'email': form.cleaned_data.get('email', ''),
                'phone': form.cleaned_data['phone'],
                'date': form.cleaned_data['date'],
                'time': form.cleaned_data['time'],
                'guests': form.cleaned_data['guests'],
                'table': form.cleaned_data['table'],
                'special_requests': form.cleaned_data.get('special_requests', ''),
            }
            reservation_service.create_reservation(data, user=request.user)
            messages.success(request, "Reservation created successfully!")
            return redirect('reservation_success')
    else:
        form = ReservationForm()
    return render(request, 'restaurant/reservation_form.html', {'form': form})

@login_required
def reservation_success(request):
    return render(request, 'restaurant/reservation_success.html')

def debug_menu(request):
    html = """
    <!DOCTYPE html>
    <html>
    <body style="padding: 20px; font-family: Arial;">
        <h1>Image Debug Test</h1>
        <div style="border: 5px solid red; padding: 20px; margin: 20px 0;">
            <h2>Direct Image Test</h2>
            <img src="/media/menu_images/cookingw.jpeg" 
                 style="max-width: 300px; border: 2px solid blue;">
            <p>If you see the image above, the problem is in your template.</p>
            <p>If not, there's a server configuration issue.</p>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)