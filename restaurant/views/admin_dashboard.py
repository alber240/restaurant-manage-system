"""
Admin Dashboard Views for Restaurant Management System
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, timedelta
from decimal import Decimal
import csv
import json

from restaurant.models import (
    Order, MenuItem, MenuCategory, Reservation, 
    Table, Cart, CartItem, OrderItem, Inventory
)
from restaurant.forms import MenuItemForm, MenuCategoryForm, ReservationForm

User = get_user_model()

# ==================================================
# DASHBOARD HOME - MAIN OVERVIEW
# ==================================================

@staff_member_required
def admin_dashboard_home(request):
    """Main admin dashboard with overview statistics"""
    
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    
    # Order statistics
    total_orders = Order.objects.count()
    today_orders = Order.objects.filter(created_at__date=today).count()
    pending_orders = Order.objects.filter(status='received').count()
    preparing_orders = Order.objects.filter(status='preparing').count()
    ready_orders = Order.objects.filter(status='ready').count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    cancelled_orders = Order.objects.filter(status='cancelled').count()
    
    # Revenue calculations
    today_revenue = Order.objects.filter(
        created_at__date=today, 
        payment_status='completed'
    ).aggregate(total=Sum('total'))['total'] or Decimal(0)
    
    week_revenue = Order.objects.filter(
        created_at__date__gte=start_of_week,
        payment_status='completed'
    ).aggregate(total=Sum('total'))['total'] or Decimal(0)
    
    month_revenue = Order.objects.filter(
        created_at__date__gte=start_of_month,
        payment_status='completed'
    ).aggregate(total=Sum('total'))['total'] or Decimal(0)
    
    # User statistics
    total_users = User.objects.count()
    staff_count = User.objects.filter(is_staff=True).count()
    customer_count = User.objects.filter(is_staff=False).count()
    
    # Menu statistics
    total_menu_items = MenuItem.objects.count()
    low_stock_items = MenuItem.objects.filter(stock__lte=F('low_stock_threshold'))
    low_stock_count = low_stock_items.count()
    out_of_stock = MenuItem.objects.filter(stock=0).count()
    
    # Reservation statistics
    today_reservations = Reservation.objects.filter(date=today).count()
    upcoming_reservations = Reservation.objects.filter(date__gte=today).count()
    
    # Recent data
    recent_orders = Order.objects.all().order_by('-created_at')[:10]
    recent_reservations = Reservation.objects.all().order_by('-created_at')[:5]
    popular_items = OrderItem.objects.values('item__name').annotate(
        total_ordered=Sum('quantity')
    ).order_by('-total_ordered')[:5]
    
    context = {
        'total_orders': total_orders,
        'today_orders': today_orders,
        'pending_orders': pending_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
        'delivered_orders': delivered_orders,
        'cancelled_orders': cancelled_orders,
        'today_revenue': today_revenue,
        'week_revenue': week_revenue,
        'month_revenue': month_revenue,
        'total_users': total_users,
        'staff_count': staff_count,
        'customer_count': customer_count,
        'total_menu_items': total_menu_items,
        'low_stock_count': low_stock_count,
        'out_of_stock': out_of_stock,
        'low_stock_items': low_stock_items[:5],
        'today_reservations': today_reservations,
        'upcoming_reservations': upcoming_reservations,
        'recent_orders': recent_orders,
        'recent_reservations': recent_reservations,
        'popular_items': popular_items,
        'today': today,
    }
    
    return render(request, 'restaurant/admin/dashboard.html', context)

# ==================================================
# USER MANAGEMENT
# ==================================================

@staff_member_required
def admin_users(request):
    """View and manage all users"""
    users = User.objects.all().order_by('-date_joined')
    
    role = request.GET.get('role', '')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    if role == 'staff':
        users = users.filter(is_staff=True)
    elif role == 'customer':
        users = users.filter(is_staff=False)
    
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    
    if search:
        users = users.filter(
            Q(username__icontains=search) | 
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    context = {
        'users': users,
        'role_filter': role,
        'status_filter': status,
        'search_query': search,
        'staff_count': users.filter(is_staff=True).count(),
        'customer_count': users.filter(is_staff=False).count(),
        'total_users': users.count(),
    }
    return render(request, 'restaurant/admin/users.html', context)


@staff_member_required
def admin_create_user(request):
    """Create new user (customer, staff, or driver)"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        role = request.POST.get('role', 'customer')
        
        errors = []
        if not username:
            errors.append("Username is required")
        if not email:
            errors.append("Email is required")
        if not password:
            errors.append("Password is required")
        if password != confirm_password:
            errors.append("Passwords do not match")
        if User.objects.filter(username=username).exists():
            errors.append("Username already exists")
        if User.objects.filter(email=email).exists():
            errors.append("Email already exists")
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Create the user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Create UserProfile for role
            from restaurant.models import UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.save()
            
            # Set staff status and create driver profile if needed
            if role in ['manager', 'kitchen', 'waiter']:
                user.is_staff = True
            else:
                user.is_staff = False
            
            user.save()
            
            # Create Driver profile if role is driver
            if role == 'driver':
                from restaurant.models import Driver
                Driver.objects.create(
                    user=user,
                    phone=email,  # Use email as phone temporarily, can be updated later
                    vehicle_type='motorcycle',  # Default vehicle type
                    status='available'
                )
                messages.success(request, f'🚚 Driver account "{username}" created successfully!')
            elif role == 'kitchen':
                messages.success(request, f'🍳 Kitchen staff account "{username}" created successfully!')
            elif role == 'waiter':
                messages.success(request, f'🍽️ Waiter account "{username}" created successfully!')
            elif role == 'manager':
                messages.success(request, f'📊 Manager account "{username}" created successfully!')
            else:
                messages.success(request, f'👤 Customer account "{username}" created successfully!')
            
            return redirect('admin_users')
    
    # For GET request, render the form with role options
    return render(request, 'restaurant/admin/create_user.html')
@staff_member_required
def admin_edit_user(request, user_id):
    """Edit user details and role"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.is_staff = request.POST.get('is_staff') == 'on'
        user.is_active = request.POST.get('is_active') == 'on'
        
        new_password = request.POST.get('new_password')
        if new_password:
            user.set_password(new_password)
            messages.warning(request, f'Password changed for {user.username}')
        
        user.save()
        messages.success(request, f'User "{user.username}" updated successfully!')
        return redirect('admin_users')
    
    context = {'edit_user': user}
    return render(request, 'restaurant/admin/edit_user.html', context)


@staff_member_required
def admin_delete_user(request, user_id):
    """Delete user"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User "{username}" deleted successfully!')
        return redirect('admin_users')
    
    context = {'user_to_delete': user}
    return render(request, 'restaurant/admin/delete_user.html', context)

# ==================================================
# ORDER MANAGEMENT
# ==================================================

@staff_member_required
def admin_orders(request):
    """View all orders with filters"""
    orders = Order.objects.all().select_related('user').prefetch_related('items').order_by('-created_at')
    
    status = request.GET.get('status', '')
    payment_status = request.GET.get('payment_status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search = request.GET.get('search', '')
    
    if status:
        orders = orders.filter(status=status)
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    if search:
        orders = orders.filter(
            Q(id__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    total_amount = orders.aggregate(total=Sum('total'))['total'] or Decimal(0)
    completed_amount = orders.filter(payment_status='completed').aggregate(total=Sum('total'))['total'] or Decimal(0)
    
    context = {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
        'payment_status_choices': Order.PAYMENT_STATUS_CHOICES,
        'current_status': status,
        'current_payment_status': payment_status,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search,
        'total_amount': total_amount,
        'completed_amount': completed_amount,
        'total_orders': orders.count(),
    }
    return render(request, 'restaurant/admin/orders.html', context)


@staff_member_required
def admin_order_detail(request, order_id):
    """View and update order details"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_status':
            new_status = request.POST.get('status')
            if new_status:
                old_status = order.status
                order.status = new_status
                order.save()
                messages.success(request, f'Order #{order.id} status updated to {order.get_status_display()}')
        
        elif action == 'update_payment':
            new_payment_status = request.POST.get('payment_status')
            if new_payment_status:
                order.payment_status = new_payment_status
                order.save()
                messages.success(request, f'Order #{order.id} payment status updated')
        
        elif action == 'add_note':
            note = request.POST.get('note', '')
            if note:
                current_notes = order.notes or ''
                order.notes = f"{current_notes}\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {note}"
                order.save()
                messages.success(request, 'Note added to order')
        
        return redirect('admin_order_detail', order_id=order.id)
    
    context = {
        'order': order,
        'status_choices': Order.STATUS_CHOICES,
        'payment_status_choices': Order.PAYMENT_STATUS_CHOICES,
    }
    return render(request, 'restaurant/admin/order_detail.html', context)


@staff_member_required
def admin_export_orders(request):
    """Export orders to CSV"""
    orders = Order.objects.all().order_by('-created_at')
    
    status = request.GET.get('status', '')
    payment_status = request.GET.get('payment_status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if status:
        orders = orders.filter(status=status)
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Customer', 'Email', 'Total', 'Status', 'Payment Status', 'Payment Method', 'Created Date', 'Items'])
    
    for order in orders:
        items_summary = ", ".join([f"{item.quantity}x {item.item.name}" for item in order.items.all()])
        
        writer.writerow([
            order.id,
            order.user.get_full_name() or order.user.username,
            order.user.email,
            f"${order.total}",
            order.get_status_display(),
            order.get_payment_status_display(),
            order.get_payment_method_display() if order.payment_method else 'N/A',
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            items_summary[:200]
        ])
    
    messages.success(request, f'Exported {orders.count()} orders to CSV')
    return response

# ==================================================
# MENU MANAGEMENT
# ==================================================

@staff_member_required
def admin_menu(request):
    """Manage menu items and categories"""
    categories = MenuCategory.objects.all().prefetch_related('menu_items')
    
    context = {
        'categories': categories,
        'total_items': MenuItem.objects.count(),
        'total_categories': categories.count(),
        'available_items': MenuItem.objects.filter(stock__gt=0).count(),
    }
    return render(request, 'restaurant/admin/menu.html', context)


@staff_member_required
def admin_add_menu_item(request):
    """Add new menu item"""
    categories = MenuCategory.objects.all().order_by('name')  # Make sure this line exists
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        category_id = request.POST.get('category')
        stock = request.POST.get('stock', 0)
        low_stock_threshold = request.POST.get('low_stock_threshold', 5)
        image = request.FILES.get('image')
        
        # Validate category exists
        if not category_id:
            messages.error(request, 'Please select a category')
            return render(request, 'restaurant/admin/add_menu_item.html', {'categories': categories})
        
        try:
            category = MenuCategory.objects.get(id=category_id)
            menu_item = MenuItem.objects.create(
                name=name,
                description=description,
                price=price,
                category=category,
                stock=stock,
                low_stock_threshold=low_stock_threshold,
                image=image
            )
            messages.success(request, f'Menu item "{name}" added successfully!')
            return redirect('admin_menu')
        except MenuCategory.DoesNotExist:
            messages.error(request, 'Selected category does not exist')
        except Exception as e:
            messages.error(request, f'Error adding menu item: {str(e)}')
    
    # Important: Always pass categories to the template
    return render(request, 'restaurant/admin/add_menu_item.html', {'categories': categories})


@staff_member_required
def admin_edit_menu_item(request, item_id):
    """Edit menu item"""
    item = get_object_or_404(MenuItem, id=item_id)
    categories = MenuCategory.objects.all().order_by('name')  # Get all categories
    
    if request.method == 'POST':
        item.name = request.POST.get('name')
        item.description = request.POST.get('description')
        item.price = request.POST.get('price')
        item.category_id = request.POST.get('category')
        item.stock = request.POST.get('stock', 0)
        item.low_stock_threshold = request.POST.get('low_stock_threshold', 5)
        
        if request.FILES.get('image'):
            item.image = request.FILES.get('image')
        
        item.save()
        messages.success(request, f'Menu item "{item.name}" updated successfully!')
        return redirect('admin_menu')
    
    context = {
        'item': item,
        'categories': categories  # Pass categories to template
    }
    return render(request, 'restaurant/admin/edit_menu_item.html', context)


@staff_member_required
def admin_delete_menu_item(request, item_id):
    """Delete menu item"""
    item = get_object_or_404(MenuItem, id=item_id)
    
    if request.method == 'POST':
        item_name = item.name
        item.delete()
        messages.success(request, f'Menu item "{item_name}" deleted successfully!')
        return redirect('admin_menu')
    
    context = {'item': item}
    return render(request, 'restaurant/admin/delete_menu_item.html', context)


@staff_member_required
def admin_add_category(request):
    """Add new menu category"""
    if request.method == 'POST':
        form = MenuCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{form.cleaned_data["name"]}" created successfully!')
        else:
            for error in form.errors.values():
                messages.error(request, error)
        return redirect('admin_menu')
    
    return render(request, 'restaurant/admin/add_category.html', {'form': MenuCategoryForm()})


@staff_member_required
def admin_bulk_update_stock(request):
    """Update stock for multiple items at once"""
    if request.method == 'POST':
        updates = 0
        for key, value in request.POST.items():
            if key.startswith('stock_'):
                item_id = key.replace('stock_', '')
                try:
                    item = MenuItem.objects.get(id=item_id)
                    item.stock = int(value)
                    item.save()
                    updates += 1
                except:
                    pass
        
        messages.success(request, f'Updated stock for {updates} items')
        return redirect('admin_menu')
    
    items = MenuItem.objects.all().order_by('category__name', 'name')
    return render(request, 'restaurant/admin/bulk_stock_update.html', {'items': items})

# ==================================================
# RESERVATION MANAGEMENT
# ==================================================

@staff_member_required
def admin_reservations(request):
    """View all reservations"""
    reservations = Reservation.objects.all().select_related('table').order_by('-date', '-created_at')
    
    date_filter = request.GET.get('date', '')
    if date_filter:
        reservations = reservations.filter(date=date_filter)
    
    context = {
        'reservations': reservations,
        'tables': Table.objects.all(),
        'date_filter': date_filter,
        'total_reservations': reservations.count(),
    }
    return render(request, 'restaurant/admin/reservations.html', context)


@staff_member_required
def admin_cancel_reservation(request, reservation_id):
    """Cancel a reservation"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if request.method == 'POST':
        customer_name = reservation.name
        reservation.delete()
        messages.success(request, f'Reservation for "{customer_name}" cancelled successfully!')
        return redirect('admin_reservations')
    
    context = {'reservation': reservation}
    return render(request, 'restaurant/admin/cancel_reservation.html', context)


@staff_member_required
def admin_reports(request):
    """View sales reports and analytics"""
    # Get date range
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    # Daily sales data for chart
    daily_sales = []
    for i in range(min(days, 30)):  # Limit to 30 days for performance
        date = start_date + timedelta(days=i)
        daily_total = Order.objects.filter(
            created_at__date=date,
            payment_status='completed'
        ).aggregate(total=Sum('total'))['total'] or Decimal(0)
        
        daily_sales.append({
            'date': date.strftime('%Y-%m-%d'),
            'total': float(daily_total)
        })
    
    # Category sales breakdown
    category_sales = []
    categories = MenuCategory.objects.all()
    for category in categories:
        total = 0
        for item in category.menu_items.all():
            item_total = OrderItem.objects.filter(
                item=item,
                order__payment_status='completed'
            ).aggregate(total=Sum('price'))['total'] or Decimal(0)
            total += item_total
        
        if total > 0:
            category_sales.append({
                'name': category.name,
                'total': float(total)
            })
    
    # Payment method breakdown
    payment_methods = []
    for method in Order.PAYMENT_METHOD_CHOICES:
        count = Order.objects.filter(payment_method=method[0]).count()
        total = Order.objects.filter(payment_method=method[0], payment_status='completed').aggregate(total=Sum('total'))['total'] or Decimal(0)
        
        if count > 0 or total > 0:
            payment_methods.append({
                'name': method[1],
                'count': count,
                'total': float(total)
            })
    
    # Popular items
    popular_items = OrderItem.objects.values('item__name', 'item__price').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')[:10]
    
    context = {
        'days': days,
        'daily_sales': json.dumps(daily_sales),
        'category_sales': category_sales,
        'payment_methods': payment_methods,
        'popular_items': popular_items,
    }
    return render(request, 'restaurant/admin/reports.html', context)


@staff_member_required
def admin_categories(request):
    """Manage menu categories"""
    categories = MenuCategory.objects.all().order_by('name')
    
    context = {
        'categories': categories,
        'total_categories': categories.count(),
    }
    return render(request, 'restaurant/admin/categories.html', context)


@staff_member_required
def admin_add_category(request):
    """Add new menu category"""
    if request.method == 'POST':
        name = request.POST.get('name')
        slug = request.POST.get('slug', name.lower().replace(' ', '-'))
        
        if MenuCategory.objects.filter(name__iexact=name).exists():
            messages.error(request, f'Category "{name}" already exists!')
        else:
            try:
                category = MenuCategory.objects.create(name=name, slug=slug)
                messages.success(request, f'Category "{name}" created successfully!')
                return redirect('admin_categories')
            except Exception as e:
                messages.error(request, f'Error creating category: {str(e)}')
    
    return render(request, 'restaurant/admin/add_category.html')


@staff_member_required
def admin_edit_category(request, category_id):
    """Edit menu category"""
    category = get_object_or_404(MenuCategory, id=category_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        slug = request.POST.get('slug', name.lower().replace(' ', '-'))
        
        if MenuCategory.objects.filter(name__iexact=name).exclude(id=category_id).exists():
            messages.error(request, f'Category "{name}" already exists!')
        else:
            category.name = name
            category.slug = slug
            category.save()
            messages.success(request, f'Category "{name}" updated successfully!')
            return redirect('admin_categories')
    
    context = {'category': category}
    return render(request, 'restaurant/admin/edit_category.html', context)


@staff_member_required
def admin_delete_category(request, category_id):
    """Delete menu category"""
    category = get_object_or_404(MenuCategory, id=category_id)
    
    if request.method == 'POST':
        category_name = category.name
        # Check if category has items
        if category.menu_items.count() > 0:
            messages.error(request, f'Cannot delete "{category_name}" because it has {category.menu_items.count()} menu items. Move or delete items first.')
        else:
            category.delete()
            messages.success(request, f'Category "{category_name}" deleted successfully!')
            return redirect('admin_categories')
    
    context = {'category': category}
    return render(request, 'restaurant/admin/delete_category.html', context)

from restaurant.models import Driver

@staff_member_required
def admin_delivery_orders(request):
    """View pending delivery orders for admin to assign drivers"""
    # Get orders ready for driver assignment (confirmed by kitchen, not yet assigned)
    pending_deliveries = Order.objects.filter(
        order_type='delivery',
        status='confirmed',
        delivery_status='pending',
        driver__isnull=True
    ).order_by('-created_at')
    
    # Get available drivers
    available_drivers = Driver.objects.filter(status='available')
    
    context = {
        'pending_deliveries': pending_deliveries,
        'available_drivers': available_drivers,
    }
    return render(request, 'restaurant/admin/delivery_orders.html', context)


@staff_member_required
def admin_assign_driver(request, order_id):
    """Admin assigns a driver to an order"""
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        driver_id = request.POST.get('driver_id')
        
        if driver_id:
            driver = get_object_or_404(Driver, id=driver_id)
            order.driver = driver
            order.delivery_status = 'assigned'
            driver.status = 'busy'
            driver.save()
            order.save()
            messages.success(request, f'Driver {driver.user.username} assigned to Order #{order.id}')
            
            # TODO: Send notification to driver
        else:
            messages.error(request, 'Please select a driver')
    
    return redirect('admin_delivery_orders')