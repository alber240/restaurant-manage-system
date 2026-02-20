from django import template

register = template.Library()

@register.filter
def status_color(status):
    colors = {
        'received': 'warning',
        'preparing': 'info',
        'ready': 'success',
        'delivered': 'secondary',
        'cancelled': 'danger'
    }
    return colors.get(status.lower(), 'primary')