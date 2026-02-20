from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.template.loader import get_template
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.conf import settings
import random

from .forms import ReservationForm
from restaurant.utils.email import send_email
from .models import MenuCategory, MenuItem, Cart, CartItem, Order, Reservation
from restaurant.signals import send_payment_receipt

# ========================
# CUSTOMER-FACING VIEWS
# ========================

def home_view(request):
    """Home page view"""
    return render(request, 'restaurant/home.html')

def about_view(request):
    """About Us page view"""
    return render(request, 'restaurant/aboutus.html')

def contact_view(request):
    """Contact Us page view"""
    return render(request, 'restaurant/contactus.html')

def menu_view(request):
    """Display menu grouped by categories"""
    categories = MenuCategory.objects.prefetch_related('menu_items').all()
    return render(request, 'restaurant/customer/menu.html', {'categories': categories})

@login_required
def add_to_cart(request, item_id):
    """Add item to cart with AJAX support"""
    if request.method == 'POST':
        item = get_object_or_404(MenuItem, pk=item_id)
        quantity = int(request.POST.get('quantity', 1))
        cart, _ = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            item=item,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_total': str(cart.total),
                'item_count': cart.item_count
            })

        messages.success(request, f"{quantity} x {item.name} added to cart")
        return redirect('menu')

@login_required
def view_cart(request):
    """Display user's cart"""
    cart = get_object_or_404(Cart, user=request.user)
    return render(request, 'restaurant/customer/cart.html', {
        'cart': cart,
        'cart_items': cart.items.all()
    })

@login_required
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    item = get_object_or_404(MenuItem, pk=item_id)
    cart = get_object_or_404(Cart, user=request.user)
    CartItem.objects.filter(cart=cart, item=item).delete()
    messages.success(request, f"{item.name} removed from cart")
    return redirect('view_cart')

@login_required
def update_cart(request, item_id):
    """Update cart item quantity"""
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        item = get_object_or_404(MenuItem, pk=item_id)
        cart = get_object_or_404(Cart, user=request.user)

        # Get all cart items matching this cart and item
        cart_items = CartItem.objects.filter(cart=cart, item=item)

        if cart_items.exists():
            if cart_items.count() > 1:
                # Sum all quantities and delete duplicates
                total_quantity = sum(ci.quantity for ci in cart_items)
                cart_items.delete()
                CartItem.objects.create(
                    cart=cart,
                    item=item,
                    quantity=total_quantity
                )
            else:
                cart_item = cart_items.first()
                cart_item.quantity = quantity
                cart_item.save()
        else:
            CartItem.objects.create(
                cart=cart,
                item=item,
                quantity=quantity
            )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_total': str(cart.total),
                'item_count': cart.item_count
            })

    return redirect('view_cart')

@login_required
def order_history(request):
    """Display user's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'restaurant/customer/order_history.html', {'orders': orders})

def cart_count(request):
    """AJAX endpoint for cart item count"""
    count = CartItem.objects.filter(cart__user=request.user).count() if request.user.is_authenticated else 0
    return JsonResponse({'count': count})

# ========================
# AUTHENTICATION VIEWS
# ========================

def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

def debug_template(request):
    """Template debugging utility"""
    template = get_template('registration/login.html')
    return HttpResponse(template.render())

# ========================
# STAFF-ONLY VIEWS
# ========================

@staff_member_required
def kitchen_dashboard(request):
    """Kitchen order management view"""
    orders = Order.objects.filter(status__in=['received', 'preparing']).order_by('-created_at')
    return render(request, 'restaurant/kitchen/orders.html', {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES
    })

@staff_member_required
def waiter_dashboard(request):
    """Waiter order management view"""
    active_orders = Order.objects.filter(status__in=['preparing', 'ready'])
    return render(request, 'restaurant/staff/waiter.html', {'orders': active_orders})

@staff_member_required
@require_POST
def update_order_status(request, order_id):
    """Update order status with WebSocket support"""
    order = get_object_or_404(Order, pk=order_id)
    new_status = request.POST.get('status')

    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        order.save()

        # WebSocket notification (requires Django Channels)
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "orders",
                {
                    'type': 'order_update',
                    'order_id': order.id,
                    'new_status': order.get_status_display()
                }
            )
        except (ImportError, Exception):
            pass  # Channels not installed or not configured

        messages.success(request, f"Order #{order.id} updated to {order.get_status_display()}")

    return redirect('kitchen')

# ========================
# RESERVATION VIEWS
# ========================

def create_reservation(request):
    """Handle reservation creation for both logged-in and anonymous users."""
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            if request.user.is_authenticated:
                reservation.customer = request.user
                # Use user's email if not provided in form
                if not reservation.email:
                    reservation.email = request.user.email
            else:
                # For anonymous users, email is required (enforced in form)
                pass
            reservation.save()
            messages.success(request, "Reservation created successfully!")

            # Send confirmation email if email is present
            if reservation.email:
                send_email(
                    subject="Reservation Confirmation",
                    to_email=reservation.email,
                    template_name='restaurant/emails/reservation_confirm.html',
                    context={'reservation': reservation}
                )
            return redirect('reservation_success')
    else:
        form = ReservationForm()

    return render(request, 'restaurant/reservation_form.html', {'form': form})

def reservation_confirm(request):
    """Legacy view, kept for compatibility; consider merging with reservation_success."""
    return render(request, 'restaurant/reservation_confirm.html')

@login_required
def reservation_success(request):
    """Reservation confirmation page"""
    return render(request, 'restaurant/reservation_success.html')

# ========================
# CHECKOUT & ORDER VIEWS
# ========================

@login_required
def checkout(request):
    """Display checkout page with cart summary."""
    cart = get_object_or_404(Cart, user=request.user)
    return render(request, 'restaurant/customer/checkout.html', {
        'cart': cart,
        'cart_items': cart.items.all()
    })

@login_required
@require_POST
def process_payment(request):
    """Process payment, create order, and handle different payment methods."""
    if not request.user.is_authenticated:
        return redirect('login')

    payment_method = request.POST.get('payment_method')
    cart = request.user.cart

    # Create order first
    order = Order.objects.create(
        user=request.user,
        status='received',
        total=cart.total,
        payment_status='pending'
    )

    # Move cart items to order
    for cart_item in cart.items.all():
        order.items.create(
            item=cart_item.item,
            quantity=cart_item.quantity,
            price=cart_item.item.price
        )

    # Process payment based on method
    if payment_method == 'card':
        return handle_card_payment(request, order)
    elif payment_method == 'mtn':
        return handle_mtn_payment(request, order)
    elif payment_method == 'airtel':
        return handle_airtel_payment(request, order)

    messages.error(request, "Invalid payment method.")
    return redirect('checkout')

def handle_card_payment(request, order):
    """Mock card payment processing with test card simulation."""
    # In test mode, simulate successful payment 80% of the time
    if random.random() < 0.8:  # 80% success rate
        order.payment_status = 'completed'
        order.save()
        send_payment_receipt(order)
        messages.success(request, "Card payment processed successfully!")
        return redirect('order_confirmation', order_id=order.id)
    else:
        order.payment_status = 'failed'
        order.save()
        messages.error(request, "Card payment failed. Please try another method.")
        return redirect('checkout')

def handle_mtn_payment(request, order):
    """Mock MTN MoMo payment handler with Rwanda number validation."""
    phone = request.POST.get('mtn_phone', '').strip()

    # Validate Rwanda MTN number
    if not (phone.startswith(('078', '072')) and len(phone) == 10 and phone.isdigit()):
        messages.error(request, "Invalid MTN Rwanda number (must start with 078 or 072)")
        return redirect('checkout')

    # Simulate different scenarios
    if phone.endswith('1111'):
        order.payment_status = 'failed'
        order.save()
        messages.error(request, "Mobile payment failed (test: ends with 1111)")
    elif phone.endswith('2222'):
        order.payment_status = 'pending'
        order.save()
        messages.info(request, "Payment pending - requires user confirmation")
    else:
        order.payment_status = 'completed'
        order.save()
        send_payment_receipt(order)
        messages.success(request, "MTN MoMo payment successful (test mode)")

    return redirect('order_payment', order_id=order.id)

def handle_airtel_payment(request, order):
    """Mock Airtel Money payment handler with Rwanda number validation."""
    phone = request.POST.get('airtel_phone', '').strip()

    # Validate Rwanda Airtel number
    if not (phone.startswith(('073', '075')) and len(phone) == 10 and phone.isdigit()):
        messages.error(request, "Invalid Airtel Rwanda number (must start with 073 or 075)")
        return redirect('checkout')

    # Simulate different scenarios
    if phone.endswith('1111'):
        order.payment_status = 'failed'
        order.save()
        messages.error(request, "Mobile payment failed (test: ends with 1111)")
    elif phone.endswith('2222'):
        order.payment_status = 'pending'
        order.save()
        messages.info(request, "Payment pending - requires user confirmation")
    else:
        order.payment_status = 'completed'
        order.save()
        send_payment_receipt(order)
        messages.success(request, "Airtel Money payment successful (test mode)")

    return redirect('order_payment', order_id=order.id)

@login_required
def order_confirmation(request, order_id):
    """Display order confirmation after successful payment."""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'restaurant/customer/order_confirmation.html', {
        'order': order
    })

@login_required
def order_payment(request, order_id):
    """Display payment status page."""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'restaurant/customer/order_payment.html', {
        'order': order
    })

def verify_3d_secure(request, order_id):
    """Handle 3D Secure verification for an order (test mode)."""
    order = get_object_or_404(Order, pk=order_id, user=request.user)

    if request.method == 'POST':
        if request.POST.get('secure_code') == '1234':  # Test code
            order.payment_status = 'completed'
            order.save()
            send_payment_receipt(order)
            messages.success(request, "3D Secure verification successful")
            return redirect('order_payment', order_id=order.id)
        else:
            messages.error(request, "Invalid verification code")

    return render(request, 'restaurant/customer/3d_secure.html', {'order_id': order_id})

# ========================
# API VIEWS (JWT Protected)
# ========================

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken

class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "message": "This is a protected endpoint!",
            "user": request.user.username
        })

class StaffOnlyView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        return Response({
            "message": "Staff-only data",
            "secret_data": "Sensitive operational metrics"
        })

class LogoutView(APIView):
    def post(self, request):
        refresh = request.data.get('refresh')
        token = RefreshToken(refresh)
        token.blacklist()
        return Response({"message": "Logged out"})

# ========================
# REPORTING VIEWS
# ========================

@staff_member_required
def sales_report(request):
    """Basic sales report (placeholder)."""
    orders = Order.objects.filter(status='delivered')
    return render(request, 'reports/sales.html', {'orders': orders})

# ========================
# DEBUG VIEW (remove in production)
# ========================

def debug_menu(request):
    """Simple image debug helper."""
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