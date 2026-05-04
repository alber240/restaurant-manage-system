from decimal import Decimal
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from restaurant.forms import ReservationForm
from restaurant.models import Order, Cart, CartItem, OrderItem, MenuCategory, RestaurantSettings, QRCodeTable, Table
from restaurant.services import cart as cart_service
from restaurant.services import order as order_service
from restaurant.services import reservation as reservation_service
from restaurant.services.email_service import send_order_confirmation
from django.utils import timezone
import re


# ==================================================
# PUBLIC PAGES (No login required)
# ==================================================

def home_view(request):
    return render(request, 'restaurant/home.html')

def about_view(request):
    return render(request, 'restaurant/aboutus.html')

def contact_view(request):
    return render(request, 'restaurant/contactus.html')

def menu_view(request):
    categories = MenuCategory.objects.prefetch_related('menu_items').all()
    return render(request, 'restaurant/customer/menu.html', {'categories': categories})


# ==================================================
# CART FUNCTIONS - NO LOGIN REQUIRED (Guest users allowed)
# ==================================================

def add_to_cart(request, item_id):
    """Add item to cart - Guest users can also add items"""
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        # Get or create cart for guest or logged-in user
        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            cart, created = Cart.objects.get_or_create(session_key=session_key, user__isnull=True)
        
        # Add item to cart
        try:
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                item_id=item_id,
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
            messages.success(request, "Item added to cart")
        except Exception as e:
            messages.error(request, str(e))
        
        return redirect('menu')


def view_cart(request):
    """View cart - Guest users can also view cart"""
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    
    return render(request, 'restaurant/customer/cart.html', {
        'cart': cart,
        'cart_items': cart.items.all() if cart else []
    })


def remove_from_cart(request, item_id):
    """Remove item from cart - Guest users can also remove"""
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    
    if cart:
        cart.items.filter(item_id=item_id).delete()
        messages.success(request, "Item removed from cart")
    
    return redirect('view_cart')


def update_cart(request, item_id):
    """Update cart item quantity - Guest users can also update"""
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
        
        if cart:
            cart_item = cart.items.filter(item_id=item_id).first()
            if cart_item:
                if quantity <= 0:
                    cart_item.delete()
                else:
                    cart_item.quantity = quantity
                    cart_item.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if cart:
                return JsonResponse({
                    'success': True,
                    'cart_total': str(cart.total),
                    'item_count': cart.item_count
                })
    
    return redirect('view_cart')


def cart_count(request):
    """Get cart item count for navbar badge - Guest users also work"""
    count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            count = cart.item_count
    else:
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
            if cart:
                count = cart.item_count
    return JsonResponse({'count': count})


# ==================================================
# CHECKOUT & ORDERS (Guest users allowed - no login required)
# ==================================================

def checkout(request):
    """
    Checkout page - Handles both guest and logged-in users
    Guest info is OPTIONAL - customers can checkout without providing details
    """
    # Get cart based on session (for guests) or user (for logged-in)
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    
    # Check if cart exists and has items
    if not cart or cart.items.count() == 0:
        messages.error(request, "Your cart is empty")
        return redirect('menu')
    
    # GET request - show checkout page
    if request.method == 'GET':
        return render(request, 'restaurant/customer/checkout.html', {
            'cart': cart,
            'cart_items': cart.items.all(),
            'total': cart.total,
            'is_guest': not request.user.is_authenticated
        })
    
    # POST request - process order
    if request.method == 'POST':
        order_type = request.POST.get('order_type', 'dine_in')
        payment_method = request.POST.get('payment_method', 'cash')
        
        # Calculate total
        subtotal = cart.total
        delivery_fee = Decimal('0.00')
        
        # Handle delivery orders
        if order_type == 'delivery':
            delivery_address = request.POST.get('delivery_address', '').strip()
            delivery_phone = request.POST.get('delivery_phone', '').strip()
            delivery_instruction = request.POST.get('delivery_instruction', '').strip()
            latitude = request.POST.get('latitude', '')
            longitude = request.POST.get('longitude', '')
            
            # Validate delivery details
            if not delivery_address:
                messages.error(request, "Please provide delivery address")
                return render(request, 'restaurant/customer/checkout.html', {
                    'cart': cart,
                    'cart_items': cart.items.all(),
                    'total': cart.total,
                    'is_guest': not request.user.is_authenticated
                })
            
            if not delivery_phone:
                messages.error(request, "Please provide phone number for delivery")
                return render(request, 'restaurant/customer/checkout.html', {
                    'cart': cart,
                    'cart_items': cart.items.all(),
                    'total': cart.total,
                    'is_guest': not request.user.is_authenticated
                })
            
            # Calculate delivery fee from settings
            settings = RestaurantSettings.objects.first()
            if settings and settings.enable_delivery:
                try:
                    delivery_fee = Decimal(str(settings.delivery_fee_amount))
                except:
                    delivery_fee = Decimal('3.00')
            else:
                delivery_fee = Decimal('3.00')
        
        total = subtotal + delivery_fee
        
        # Get guest info (OPTIONAL - only for non-authenticated users)
        guest_name = ''
        guest_email = ''
        guest_phone = ''
        guest_notes = ''
        
        if not request.user.is_authenticated:
            guest_name = request.POST.get('guest_name', '').strip()
            guest_email = request.POST.get('guest_email', '').strip()
            guest_phone = request.POST.get('guest_phone', '').strip()
            
            # Build notes from guest info (only if provided)
            if guest_name:
                guest_notes += f"Name: {guest_name}\n"
            if guest_email:
                guest_notes += f"Email: {guest_email}\n"
            if guest_phone:
                guest_notes += f"Phone: {guest_phone}\n"
        
        # Create order
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            total=total,
            payment_method=payment_method,
            status='pending',
            payment_status='pending',
            order_type=order_type,
            notes=guest_notes if guest_notes else f"Order from {order_type}"
        )
        
        # Add order items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                item=cart_item.item,
                quantity=cart_item.quantity,
                price=cart_item.item.price
            )
        
        # Update order with delivery details
        if order_type == 'delivery':
            order.delivery_address = delivery_address
            order.delivery_phone = delivery_phone
            order.delivery_instruction = delivery_instruction
            order.delivery_fee = delivery_fee
            order.delivery_status = 'pending'
            
            # Only set coordinates if they are valid numbers
            if latitude and longitude:
                try:
                    order.delivery_latitude = Decimal(str(latitude))
                    order.delivery_longitude = Decimal(str(longitude))
                except:
                    pass
            
            order.save()
        
        # Clear the cart
        cart.items.all().delete()
        
        # ==================================================
        # SEND EMAIL CONFIRMATION
        # ==================================================
        try:
            # Check if order has a user with email
            if order.user and order.user.email:
                customer_name = order.user.get_full_name() or order.user.username
                send_order_confirmation(order, order.user.email, customer_name)
                print(f"✅ Email sent to {order.user.email}")
            elif order.notes and 'Email:' in order.notes:
                # Extract email from guest notes
                email_match = re.search(r'Email:\s*(\S+@\S+)', order.notes)
                if email_match:
                    name_match = re.search(r'Name:\s*([^\n]+)', order.notes)
                    customer_name = name_match.group(1) if name_match else "Guest"
                    send_order_confirmation(order, email_match.group(1), customer_name)
                    print(f"✅ Email sent to guest: {email_match.group(1)}")
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
        
        messages.success(request, f'Order #{order.id} placed successfully!')
        
        # Redirect based on order type and user type
        if order_type == 'delivery':
            if request.user.is_authenticated:
                return redirect('order_tracking', order_id=order.id)
            else:
                request.session['guest_order_id'] = order.id
                return redirect('guest_order_confirmation')
        else:
            return redirect('order_confirmation', order_id=order.id)


@login_required
def order_history(request):
    """Order history - requires login"""
    orders = order_service.get_orders_for_user(request.user)
    return render(request, 'restaurant/customer/order_history.html', {'orders': orders})


@login_required
def order_confirmation(request, order_id):
    """Order confirmation for logged-in users"""
    order = order_service.get_order_by_id(order_id, user=request.user)
    return render(request, 'restaurant/customer/order_confirmation.html', {'order': order})


@login_required
def order_payment(request, order_id):
    order = order_service.get_order_by_id(order_id, user=request.user)
    return render(request, 'restaurant/customer/order_payment.html', {'order': order})


@login_required
def order_tracking(request, order_id):
    """Order tracking page for delivery orders"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'restaurant/customer/order_tracking.html', {'order': order})


def guest_order_confirmation(request):
    """Order confirmation for guest users with option to create account"""
    order_id = request.session.get('guest_order_id')
    if not order_id:
        return redirect('home')
    
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        # Guest wants to create an account
        password = request.POST.get('password')
        email = request.POST.get('email')
        
        from django.contrib.auth.models import User
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists. Please login.")
            return redirect('login')
        
        # Create user account from guest order
        username = email.split('@')[0]
        # Make username unique
        if User.objects.filter(username=username).exists():
            username = f"{username}{order.id}"
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=request.POST.get('name', '').split()[0] if request.POST.get('name') else '',
            last_name=' '.join(request.POST.get('name', '').split()[1:]) if request.POST.get('name') else ''
        )
        
        # Link order to user
        order.user = user
        order.save()
        
        # Log the user in
        from django.contrib.auth import login
        login(request, user)
        
        messages.success(request, "Account created! You can now track your order history.")
        return redirect('order_tracking', order_id=order.id)
    
    return render(request, 'restaurant/customer/guest_confirmation.html', {'order': order})


# ==================================================
# RESERVATIONS
# ==================================================

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
            reservation_service.create_reservation(data, user=request.user if request.user.is_authenticated else None)
            messages.success(request, "Reservation created successfully!")
            return redirect('reservation_success')
    else:
        form = ReservationForm()
    return render(request, 'restaurant/reservation_form.html', {'form': form})


@login_required
def reservation_success(request):
    return render(request, 'restaurant/reservation_success.html')


# ==================================================
# QR CODE ORDERING (No login required)
# ==================================================

def table_order(request, token):
    """Landing page when customer scans QR code"""
    qr_code = get_object_or_404(QRCodeTable, qr_code_token=token, is_active=True)
    table_number = qr_code.table_number
    
    request.session['dine_in_table'] = table_number
    request.session['order_type'] = 'dine_in'
    
    categories = MenuCategory.objects.prefetch_related('menu_items').all()
    
    if not request.user.is_authenticated:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key, user=None)
    else:
        cart, created = Cart.objects.get_or_create(user=request.user)
    
    context = {
        'categories': categories,
        'table_number': table_number,
        'cart': cart,
        'cart_items': cart.items.all(),
        'qr_token': token,
    }
    return render(request, 'restaurant/table_order.html', context)


def table_add_to_cart(request, token, item_id):
    qr_code = get_object_or_404(QRCodeTable, qr_code_token=token, is_active=True)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        if not request.user.is_authenticated:
            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key
            cart, created = Cart.objects.get_or_create(session_key=session_key, user=None)
        else:
            cart, created = Cart.objects.get_or_create(user=request.user)
        
        try:
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                item_id=item_id,
                defaults={'quantity': quantity}
            )
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            messages.success(request, "Item added to cart")
        except Exception as e:
            messages.error(request, str(e))
        
        return redirect('table_order', token=token)


def table_cart(request, token):
    qr_code = get_object_or_404(QRCodeTable, qr_code_token=token, is_active=True)
    
    if not request.user.is_authenticated:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    else:
        cart = Cart.objects.filter(user=request.user).first()
    
    context = {
        'cart': cart,
        'cart_items': cart.items.all() if cart else [],
        'table_number': qr_code.table_number,
        'qr_token': token,
    }
    return render(request, 'restaurant/table_cart.html', context)


def table_checkout(request, token):
    qr_code = get_object_or_404(QRCodeTable, qr_code_token=token, is_active=True)
    
    if not request.user.is_authenticated:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    else:
        cart = Cart.objects.filter(user=request.user).first()
    
    if not cart or cart.items.count() == 0:
        messages.error(request, "Your cart is empty")
        return redirect('table_order', token=token)
    
    if request.method == 'POST':
        total = cart.total
        
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            total=total,
            status='received',
            payment_status='pending',
            payment_method=None,
            order_type='dine_in',
            notes=f"Table: {qr_code.table_number}\nOrder from QR code"
        )
        
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                item=cart_item.item,
                quantity=cart_item.quantity,
                price=cart_item.item.price
            )
        
        cart.items.all().delete()
        
        # Send WebSocket notification to kitchen
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            
            order_items = []
            for item in order.items.all():
                order_items.append({
                    'name': item.item.name,
                    'quantity': item.quantity,
                    'price': str(item.price)
                })
            
            order_data = {
                'id': order.id,
                'table_number': qr_code.table_number,
                'total': str(order.total),
                'status': order.get_status_display(),
                'created_at': order.created_at.strftime('%H:%M'),
                'items': order_items,
                'order_type': 'dine_in'
            }
            
            async_to_sync(channel_layer.group_send)("kitchen", {'type': 'new_order', 'order_data': order_data})
            async_to_sync(channel_layer.group_send)("waiter", {'type': 'new_order', 'order_data': order_data})
        except Exception as e:
            print(f"WebSocket error: {e}")
        
        request.session['last_order_id'] = order.id
        request.session['table_number'] = qr_code.table_number
        
        messages.success(request, f'Order #{order.id} placed successfully!')
        return redirect('table_order_success', token=token, order_id=order.id)
    
    context = {
        'cart': cart,
        'cart_items': cart.items.all(),
        'table_number': qr_code.table_number,
        'qr_token': token,
        'total': cart.total,
    }
    return render(request, 'restaurant/table_checkout.html', context)


def table_order_success(request, token, order_id):
    order = get_object_or_404(Order, id=order_id)
    context = {
        'order': order,
        'table_number': request.session.get('table_number', 'N/A'),
    }
    return render(request, 'restaurant/table_order_success.html', context)


# ==================================================
# UTILITIES
# ==================================================

def verify_3d_secure(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if request.method == 'POST':
        if request.POST.get('secure_code') == '1234':
            order.payment_status = 'completed'
            order.save()
            messages.success(request, "3D Secure verification successful")
            return redirect('order_payment', order_id=order.id)
        else:
            messages.error(request, "Invalid verification code")
    return render(request, 'restaurant/customer/3d_secure.html', {'order_id': order_id})


def debug_menu(request):
    html = """
    <!DOCTYPE html>
    <html>
    <body style="padding: 20px; font-family: Arial;">
        <h1>Image Debug Test</h1>
        <div style="border: 5px solid red; padding: 20px; margin: 20px 0;">
            <h2>Direct Image Test</h2>
            <img src="/media/menu_images/cookingw.jpeg" style="max-width: 300px; border: 2px solid blue;">
            <p>If you see the image above, the problem is in your template.</p>
            <p>If not, there's a server configuration issue.</p>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)


@login_required
def dashboard_redirect(request):
    """Redirect users to their appropriate dashboard based on role"""
    from restaurant.models import UserProfile
    
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    elif profile.role == 'manager':
        return redirect('admin_dashboard')
    elif profile.role == 'kitchen':
        return redirect('kitchen')
    elif profile.role == 'waiter':
        return redirect('waiter')
    elif profile.role == 'driver':
        return redirect('driver_dashboard')
    else:
        return redirect('menu')


def driver_location(request, driver_id):
    """API endpoint to get driver's current location"""
    from restaurant.models import Driver
    try:
        driver = Driver.objects.get(id=driver_id)
        return JsonResponse({
            'latitude': float(driver.current_latitude) if driver.current_latitude else None,
            'longitude': float(driver.current_longitude) if driver.current_longitude else None,
            'status': driver.status
        })
    except Driver.DoesNotExist:
        return JsonResponse({'error': 'Driver not found'}, status=404)