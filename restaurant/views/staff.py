from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from restaurant.services import order as order_service
from restaurant.models import MenuItem, Order
from restaurant.utils import kitchen_staff_required, waiter_required, manager_required

# Remove @staff_member_required, use kitchen_staff_required instead
@kitchen_staff_required
def kitchen_dashboard(request):
    orders = order_service.get_kitchen_orders()
    
    # Add table number to each order for dine-in
    for order in orders:
        if order.order_type == 'dine_in' and order.notes:
            # Extract table number from notes
            import re
            match = re.search(r'Table: (\d+)', order.notes)
            if match:
                order.table_number = match.group(1)
            else:
                order.table_number = 'N/A'
        else:
            order.table_number = None
    
    return render(request, 'restaurant/kitchen/orders.html', {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES
    })
# Remove @staff_member_required, use waiter_required instead
@waiter_required
def waiter_dashboard(request):
    orders = order_service.get_waiter_orders()
    return render(request, 'restaurant/staff/waiter.html', {'orders': orders})

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@require_POST
@kitchen_staff_required
def update_order_status(request, order_id):
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

@manager_required
def sales_report(request):
    return render(request, 'reports/sales.html')

@manager_required
def inventory_dashboard(request):
    items = MenuItem.objects.all().order_by('category', 'name')
    low_stock_items = [item for item in items if item.stock <= item.low_stock_threshold]
    return render(request, 'restaurant/staff/inventory.html', {
        'items': items,
        'low_stock_items': low_stock_items
    })

@manager_required
def manager_dashboard(request):
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


@kitchen_staff_required
def kitchen_confirm_order(request, order_id):
    """Kitchen confirms an order (checks stock availability)"""
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
            
            messages.success(request, f'Order #{order.id} confirmed!')
            
        elif action == 'reject':
            reason = request.POST.get('rejection_reason', '')
            order.status = 'rejected'
            order.rejection_reason = reason
            order.save()
            messages.warning(request, f'Order #{order.id} rejected: {reason}')
    
    return redirect('kitchen')