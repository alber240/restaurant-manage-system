from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from restaurant.services import order as order_service
from restaurant.models import MenuItem, Order  # <-- added import

@staff_member_required
def kitchen_dashboard(request):
    orders = order_service.get_kitchen_orders()
    return render(request, 'restaurant/kitchen/orders.html', {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES
    })

@staff_member_required
def waiter_dashboard(request):
    orders = order_service.get_waiter_orders()
    return render(request, 'restaurant/staff/waiter.html', {'orders': orders})

@staff_member_required
@require_POST
def update_order_status(request, order_id):
    new_status = request.POST.get('status')
    order = order_service.update_order_status(order_id, new_status)
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
    except ImportError:
        pass
    messages.success(request, f"Order #{order.id} updated to {order.get_status_display()}")
    return redirect('kitchen')

@staff_member_required
def sales_report(request):
    return render(request, 'reports/sales.html')

from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from restaurant.services import inventory

@staff_member_required
def inventory_dashboard(request):
    items = MenuItem.objects.all().order_by('category', 'name')
    low_stock_items = [item for item in items if item.stock <= item.low_stock_threshold]
    return render(request, 'restaurant/staff/inventory.html', {
        'items': items,
        'low_stock_items': low_stock_items
    })
  
#Manager Dashboard View  
from restaurant.services import dashboard

@staff_member_required
def manager_dashboard(request):
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