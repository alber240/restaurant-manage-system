from datetime import timezone
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from restaurant.services import order as order_service
from restaurant.models import MenuItem, Order, OrderItem
from restaurant.utils import kitchen_staff_required, waiter_required, manager_required


# ==================================================
# KITCHEN STAFF VIEWS
# ==================================================

@kitchen_staff_required
def kitchen_dashboard(request):
    """Kitchen dashboard - shows all pending and active orders"""
    
    # Get all orders that need kitchen attention
    # This includes pending (new from waiter) and confirmed orders
    orders = Order.objects.filter(
        status__in=['pending', 'confirmed', 'preparing', 'ready']
    ).order_by('-created_at')
    
    # Extract table number for display
    for order in orders:
        if order.table:
            order.display_info = f"Table {order.table.number}"
        elif order.order_type == 'delivery':
            order.display_info = "🚚 Delivery"
        else:
            order.display_info = "Dine In"
        
        # Add waiter info if available
        if order.waiter:
            order.waiter_name = order.waiter.username
    
    return render(request, 'restaurant/kitchen/orders.html', {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES
    })


@kitchen_staff_required
def kitchen_confirm_order(request, order_id):
    """Kitchen confirms an order (checks stock availability) - Kitchen only"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirm':
            # Check stock for all items
            out_of_stock = []
            for item in order.items.all():
                if item.item.stock < item.quantity:
                    out_of_stock.append(item.item.name)
            
            if out_of_stock:
                messages.error(request, f'Out of stock: {", ".join(out_of_stock)}')
                return redirect('kitchen')
            
            # Reduce stock
            for item in order.items.all():
                item.item.stock -= item.quantity
                item.item.save()
            
            order.status = 'confirmed'
            order.confirmed_at = timezone.now()
            order.save()
            
            # Send WebSocket notification
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "kitchen",
                    {
                        'type': 'order_update',
                        'order_id': order.id,
                        'new_status': order.get_status_display(),
                    }
                )
            except Exception as e:
                print(f"WebSocket error: {e}")
            
            messages.success(request, f'Order #{order.id} confirmed!')
            
        elif action == 'reject':
            reason = request.POST.get('rejection_reason', '')
            order.status = 'rejected'
            order.rejection_reason = reason
            order.save()
            messages.warning(request, f'Order #{order.id} rejected: {reason}')
    
    return redirect('kitchen')


@require_POST
@kitchen_staff_required
def update_order_status(request, order_id):
    """Update order status - Kitchen staff and managers only"""
    new_status = request.POST.get('status')
    order = order_service.update_order_status(order_id, new_status)
    
    try:
        channel_layer = get_channel_layer()
        
        # Send to kitchen group
        async_to_sync(channel_layer.group_send)(
            "kitchen",
            {
                'type': 'order_update',
                'order_id': order.id,
                'new_status': order.get_status_display(),
                'order_data': {
                    'id': order.id,
                    'status': order.get_status_display()
                }
            }
        )
        
        # Send to waiter group
        async_to_sync(channel_layer.group_send)(
            "waiter",
            {
                'type': 'order_update',
                'order_id': order.id,
                'new_status': order.get_status_display()
            }
        )
        print(f"✅ WebSocket status update sent for Order #{order.id}")
    except Exception as e:
        print(f"⚠️ WebSocket error: {e}")
    
    messages.success(request, f"Order #{order.id} updated to {order.get_status_display()}")
    return redirect('kitchen')


# ==================================================
# WAITER VIEWS
# ==================================================

from django.db.models import Q, Sum
from django.utils import timezone

@waiter_required
def waiter_dashboard(request):
    """Waiter dashboard - shows only orders assigned to this waiter"""
    
    from django.db.models import Sum
    from django.utils import timezone
    from datetime import timedelta
    
    # Get the current waiter's profile
    waiter = request.user
    
    # Orders assigned to THIS waiter only (not yet delivered)
    my_active_orders = Order.objects.filter(
        waiter=waiter,
        status__in=['confirmed', 'preparing', 'ready']
    ).order_by('-created_at')
    
    # Orders ready to be served (assigned to this waiter)
    ready_to_serve = Order.objects.filter(
        waiter=waiter,
        status='ready'
    ).order_by('created_at')
    
    # Orders that need payment processing (served but not paid)
    pending_payment = Order.objects.filter(
        waiter=waiter,
        status='delivered',
        payment_status='pending'
    ).order_by('-created_at')
    
    # Today's completed orders for this waiter (use created_at instead of updated_at)
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = Order.objects.filter(
        waiter=waiter,
        status='delivered',
        payment_status='completed',
        created_at__gte=today_start
    ).count()
    
    # Today's earnings for this waiter (tips only)
    tips_today = Order.objects.filter(
        waiter=waiter,
        status='delivered',
        dine_in_tip__gt=0,
        created_at__gte=today_start
    ).aggregate(total=Sum('dine_in_tip'))['total'] or 0
    
    # Extract table numbers for display
    for order in ready_to_serve:
        if order.table:
            order.table_display = f"Table {order.table.number}"
        elif order.notes and 'Table:' in order.notes:
            import re
            match = re.search(r'Table:\s*(\d+)', order.notes)
            if match:
                order.table_display = f"Table {match.group(1)}"
            else:
                order.table_display = "Dine In"
        else:
            order.table_display = "Dine In"
    
    for order in pending_payment:
        if order.table:
            order.table_display = f"Table {order.table.number}"
        elif order.notes and 'Table:' in order.notes:
            import re
            match = re.search(r'Table:\s*(\d+)', order.notes)
            if match:
                order.table_display = f"Table {match.group(1)}"
            else:
                order.table_display = "Dine In"
        else:
            order.table_display = "Dine In"
    
    context = {
        'my_active_orders': my_active_orders,
        'ready_to_serve': ready_to_serve,
        'pending_payment': pending_payment,
        'completed_today': completed_today,
        'tips_today': tips_today,
    }
    return render(request, 'restaurant/staff/waiter.html', context)


# ==================================================
# MANAGER VIEWS
# ==================================================

@manager_required
def sales_report(request):
    """Sales report - managers only"""
    return render(request, 'reports/sales.html')


@manager_required
def inventory_dashboard(request):
    """Inventory dashboard - managers only"""
    items = MenuItem.objects.all().order_by('category', 'name')
    low_stock_items = [item for item in items if item.stock <= item.low_stock_threshold]
    return render(request, 'restaurant/staff/inventory.html', {
        'items': items,
        'low_stock_items': low_stock_items
    })


@manager_required
def manager_dashboard(request):
    """Manager dashboard - managers only"""
    from restaurant.services import dashboard
    daily_sales = dashboard.get_daily_sales()
    popular_items = dashboard.get_popular_items()
    revenue = dashboard.get_revenue_summary()
    recent_orders = dashboard.get_recent_orders()

    context = {
        'daily_sales': daily_sales,
        'popular_items': popular_items,
        'revenue': revenue,
        'recent_orders': recent_orders,
    }
    return render(request, 'restaurant/staff/manager_dashboard.html', context)

from restaurant.models import MenuCategory, Cart, CartItem, Table

from decimal import Decimal
from django.http import JsonResponse
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from restaurant.models import Table, MenuItem, Order, OrderItem

@waiter_required
def waiter_create_order(request):
    """Waiter creates an order on behalf of a customer"""
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})
        
        table_id = data.get('table_id')
        items_data = data.get('items', [])
        notes = data.get('notes', '')
        
        # Validate table exists
        try:
            table = Table.objects.get(id=table_id)
        except Table.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Table not found'})
        
        if not items_data:
            return JsonResponse({'success': False, 'error': 'No items in order'})
        
        # Calculate total
        total = Decimal('0.00')
        order_items = []
        
        for item_data in items_data:
            try:
                menu_item = MenuItem.objects.get(id=item_data['id'])
                quantity = int(item_data['quantity'])
                subtotal = menu_item.price * quantity
                total += subtotal
                order_items.append({
                    'item': menu_item,
                    'quantity': quantity,
                    'price': menu_item.price
                })
            except MenuItem.DoesNotExist:
                return JsonResponse({'success': False, 'error': f'Item {item_data.get("id")} not found'})
        
        # Create order
        order = Order.objects.create(
            user=None,
            total=total,
            status='pending',
            payment_status='pending',
            payment_method=None,
            order_type='dine_in',
            order_source='waiter',
            waiter=request.user,
            table=table,
            assigned_at=timezone.now(),
            notes=f"Waiter: {request.user.username}\nTable: {table.number}\nCustomer notes: {notes}"
        )
        
        # Add order items
        for item_data in order_items:
            OrderItem.objects.create(
                order=order,
                item=item_data['item'],
                quantity=item_data['quantity'],
                price=item_data['item'].price
            )
        
        # Send WebSocket notification to kitchen
        try:
            channel_layer = get_channel_layer()
            
            # Prepare order data for kitchen
            order_data = {
                'id': order.id,
                'table_number': table.number,
                'waiter': request.user.username,
                'items': [f"{item['quantity']}x {item['item'].name}" for item in order_items],
                'total': str(total),
                'status': 'pending',
                'order_type': 'dine_in',
                'created_at': timezone.now().strftime('%H:%M')
            }
            
            # Send to kitchen group
            async_to_sync(channel_layer.group_send)(
                "kitchen",
                {
                    'type': 'new_order',
                    'order_data': order_data
                }
            )
            print(f"✅ WebSocket notification sent to kitchen for Order #{order.id}")
        except Exception as e:
            print(f"⚠️ WebSocket error: {e}")
        
        return JsonResponse({'success': True, 'order_id': order.id})
    
    # GET request - show order creation form
    tables = Table.objects.all().order_by('number')
    categories = MenuCategory.objects.prefetch_related('menu_items').all()
    
    context = {
        'tables': tables,
        'categories': categories,
    }
    return render(request, 'restaurant/staff/waiter_create_order.html', context)


@waiter_required
def waiter_mark_delivered(request, order_id):
    """Waiter marks order as delivered (food served)"""
    order = get_object_or_404(Order, id=order_id, waiter=request.user)
    order.status = 'delivered'
    order.served_at = timezone.now()
    order.save()
    
    # Send WebSocket notification
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "kitchen",
            {
                'type': 'order_update',
                'order_id': order.id,
                'new_status': 'Delivered'
            }
        )
    except Exception as e:
        print(f"WebSocket error: {e}")
    
    return JsonResponse({'success': True})


@waiter_required
def waiter_process_payment(request, order_id):
    """Waiter processes payment at table"""
    import json
    from decimal import Decimal
    
    try:
        data = json.loads(request.body)
    except:
        return JsonResponse({'success': False, 'error': 'Invalid request body'})
    
    order = get_object_or_404(Order, id=order_id, waiter=request.user)
    
    payment_method = data.get('payment_method')
    tip = Decimal(str(data.get('tip', '0')))
    
    valid_methods = ['cash', 'card', 'mtn', 'airtel']
    if payment_method not in valid_methods:
        return JsonResponse({'success': False, 'error': 'Invalid payment method'})
    
    order.payment_method = payment_method
    order.payment_status = 'completed'
    order.dine_in_tip = tip
    order.payment_processed_at = timezone.now()
    order.save()
    
    return JsonResponse({'success': True})