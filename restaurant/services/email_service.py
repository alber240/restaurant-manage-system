from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_order_confirmation(order, customer_email, customer_name):
    """Send order confirmation email to customer"""
    subject = f'Order Confirmation #{order.id} - Gourmet House'
    
    html_message = render_to_string('restaurant/emails/order_confirmation.html', {
        'order': order,
        'customer_name': customer_name,
    })
    
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer_email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Order confirmation email sent to {customer_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def send_order_status_update(order, customer_email, customer_name):
    """Send email when order status changes"""
    subject = f'Order #{order.id} Status Update - {order.get_status_display()}'
    
    message = f"""
    Dear {customer_name},
    
    Your order #{order.id} status has been updated to: {order.get_status_display()}
    
    {get_status_message(order.status)}
    
    You can track your order at: {settings.SITE_URL}/orders/
    
    Thank you for dining with us!
    
    Gourmet House Restaurant
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer_email],
            fail_silently=False,
        )
        print(f"✅ Status update email sent to {customer_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def get_status_message(status):
    messages = {
        'pending': 'Your order has been received and is awaiting confirmation.',
        'confirmed': 'Your order has been confirmed and will be prepared shortly.',
        'preparing': 'Your order is now being prepared by our kitchen team.',
        'ready': 'Your order is ready for pickup/delivery!',
        'delivered': 'Your order has been delivered. Enjoy your meal!',
        'cancelled': 'Your order has been cancelled.',
    }
    return messages.get(status, 'Your order status has been updated.')