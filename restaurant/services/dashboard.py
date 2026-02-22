# restaurant/services/dashboard.py
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from restaurant.models import Order, OrderItem

def get_daily_sales(days=7):
    """Return sales totals per day for the last `days` days."""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days-1)
    daily = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        total = Order.objects.filter(
            created_at__date=day,
            payment_status='completed'
        ).aggregate(total=Sum('total'))['total'] or 0
        daily.append({
            'date': day.strftime('%Y-%m-%d'),
            'total': float(total)
        })
    return daily

def get_popular_items(limit=5):
    """Return top `limit` most ordered items."""
    return OrderItem.objects.filter(
        order__payment_status='completed'
    ).values('item__name').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')[:limit]

def get_revenue_summary():
    """Return revenue for today, this week, this month."""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    today_rev = Order.objects.filter(
        created_at__date=today,
        payment_status='completed'
    ).aggregate(Sum('total'))['total__sum'] or 0

    week_rev = Order.objects.filter(
        created_at__date__gte=week_ago,
        payment_status='completed'
    ).aggregate(Sum('total'))['total__sum'] or 0

    month_rev = Order.objects.filter(
        created_at__date__gte=month_ago,
        payment_status='completed'
    ).aggregate(Sum('total'))['total__sum'] or 0

    return {
        'today': float(today_rev),
        'week': float(week_rev),
        'month': float(month_rev)
    }

def get_recent_orders(limit=5):
    """Return the most recent orders."""
    return Order.objects.filter(
        payment_status='completed'
    ).select_related('user').order_by('-created_at')[:limit]