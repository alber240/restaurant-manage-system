"""
Signals for Restaurant Management System
Handles email notifications and order status updates
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from restaurant.models import Order

def send_payment_receipt(order):
    """
    Send payment receipt email to customer after successful payment
    """
    try:
        subject = f'Payment Receipt - Order #{order.id}'
        
        # Create HTML email content
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Payment Receipt</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #c52e2e; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .total {{ font-size: 24px; font-weight: bold; color: #c52e2e; }}
                .footer {{ text-align: center; padding: 20px; color: #666; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Payment Receipt</h2>
                    <p>Order #{order.id}</p>
                </div>
                <div class="content">
                    <p>Dear {order.user.get_full_name() or order.user.username},</p>
                    <p>Thank you for your payment! Your order has been confirmed and will be prepared shortly.</p>
                    
                    <h3>Order Summary:</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Item</th>
                                <th>Quantity</th>
                                <th>Price</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for item in order.items.all():
            html_message += f"""
                            <tr>
                                <td>{item.item.name}</td>
                                <td>{item.quantity}</td>
                                <td>${item.price}</td>
                            </tr>
            """
        
        html_message += f"""
                        </tbody>
                        <tfoot>
                            <tr>
                                <th colspan="2">Total:</th>
                                <th class="total">${order.total}</th>
                            </tr>
                        </tfoot>
                    </table>
                    
                    <p><strong>Payment Method:</strong> {order.get_payment_method_display()}</p>
                    <p><strong>Payment Status:</strong> <span style="color: green;">Completed</span></p>
                    <p><strong>Order Status:</strong> {order.get_status_display()}</p>
                    
                    <p>You can track your order at: <a href="{settings.SITE_URL}/orders/">{settings.SITE_URL}/orders/</a></p>
                    
                    <p>Thank you for choosing Gourmet House!</p>
                </div>
                <div class="footer">
                    <p>Gourmet House Restaurant<br>
                    123 Restaurant Ave, Food City<br>
                    Phone: (555) 123-4567</p>
                    <p>© 2025 Gourmet House. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"Payment receipt sent to {order.user.email}")
        
    except Exception as e:
        print(f"Error sending payment receipt: {e}")


def send_order_status_email(order, old_status, new_status):
    """
    Send email notification when order status changes
    """
    try:
        subject = f'Order #{order.id} Status Update - {new_status}'
        
        message = f"""
        Dear {order.user.get_full_name() or order.user.username},
        
        Your order #{order.id} status has been updated from {old_status} to {new_status}.
        
        Status Details:
        - Received: We have received your order
        - Preparing: Our kitchen is preparing your food
        - Ready: Your order is ready for pickup/delivery
        - Delivered: Your order has been delivered
        
        You can track your order at: {settings.SITE_URL}/orders/
        
        Thank you for dining with us!
        
        Gourmet House Restaurant
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
        print(f"Status update email sent to {order.user.email}")
        
    except Exception as e:
        print(f"Error sending status email: {e}")


@receiver(post_save, sender=Order)
def order_status_changed(sender, instance, created, **kwargs):
    """
    Signal to send email when order status changes
    """
    if not created and hasattr(instance, 'tracker'):
        # Check if status changed
        if hasattr(instance.tracker, 'previous'):
            old_status = instance.tracker.previous('status')
            new_status = instance.status
            
            if old_status and old_status != new_status:
                send_order_status_email(instance, 
                                       dict(Order.STATUS_CHOICES).get(old_status, old_status),
                                       dict(Order.STATUS_CHOICES).get(new_status, new_status))