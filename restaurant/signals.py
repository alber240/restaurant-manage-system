from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from restaurant.services import inventory
from .models import Order, User
from .utils.email import send_email  # Your custom email utility

@receiver(post_save, sender=Order)
def handle_order_notifications(sender, instance, created, **kwargs):
    """
    Unified signal handler for all order-related notifications.
    """
    if created:
        send_order_confirmation(instance)
        # If order was already marked completed (e.g., prepaid online)
        if instance.payment_status == 'completed':
            send_payment_receipt(instance)
    else:
        # Status change to 'ready'
        if hasattr(instance, 'tracker') and instance.tracker.has_changed('status') and instance.status == 'ready':
            send_order_ready_email(instance)
        # Payment status changed to 'completed' after creation
        if hasattr(instance, 'tracker') and instance.tracker.has_changed('payment_status') and instance.payment_status == 'completed':
            send_payment_receipt(instance)
            
            for order_item in instance.items.all():
               if inventory.check_low_stock(order_item.item):
                send_low_stock_alert(order_item.item)
            
        
            
    


def send_order_confirmation(order):
    """Send order confirmation email."""
    if not order.user.email:
        return
    context = {
        'order': order,
        'user': order.user,
        'SITE_NAME': 'Your Restaurant'
    }
    send_email(
        subject=f"Order Confirmation #{order.id}",
        to_email=order.user.email,
        template_name='restaurant/emails/payment_receipt.html',
        context=context
    )


def send_order_ready_email(order):
    """Notify customer that order is ready for pickup."""
    if not order.user.email:
        return
    subject = f"🛎 Order #{order.id} Ready for Pickup!"
    html_message = render_to_string('restaurant/emails/order_ready.html', {
        'order': order,
        'user': order.user
    })
    # Use send_mail as fallback or enhance send_email to handle HTML
    send_email(
        subject=subject,
        to_email=order.user.email,
        template_name='restaurant/emails/order_ready.html',
        context={'order': order, 'user': order.user}
    )


def send_payment_receipt(order):
    """Send payment receipt after successful payment."""
    if not order.user.email:
        return
    subject = f"📝 Payment Receipt for Order #{order.id}"
    context = {
        'order': order,
        'items': order.items.all(),
        'user': order.user
    }
    send_email(
        subject=subject,
        to_email=order.user.email,
        template_name='restaurant/emails/payment_receipt.html',
        context=context
    )
    
def send_low_stock_alert(item):
    subject = f"⚠️ Low Stock Alert: {item.name}"
    context = {'item': item}
    # Send to staff emails (you need a list of staff emails)
    staff_emails = User.objects.filter(is_staff=True).values_list('email', flat=True)
    for email in staff_emails:
        send_email(subject, email, 'restaurant/emails/low_stock_alert.html', context)