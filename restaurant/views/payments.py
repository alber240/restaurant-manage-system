"""
Payment processing views for the restaurant system.
Handles Paystack integration and payment callbacks.
"""

import logging
import re
from django.shortcuts import redirect, render
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
from restaurant.models import Order
from restaurant.services import cart as cart_service
from restaurant.services import order as order_service
from restaurant.services import paystack

logger = logging.getLogger(__name__)


def format_phone_for_paystack(phone, method):
    """
    Convert local phone number to international format for Paystack.
    E.g., 078xxxxxxx -> 25078xxxxxxx
    """
    phone = re.sub(r'\s+', '', phone)  # remove spaces
    if phone.startswith('0') and len(phone) == 10:
        # Local format, add Rwanda country code
        return '250' + phone[1:]
    return phone  # assume already international


@login_required
@require_POST
def process_payment(request):
    """
    Step 1: Create an order from the user's cart and redirect to Paystack.
    """
    logger.info(f"🔥 process_payment called for user {request.user.username}")
    logger.info(f"User email: {request.user.email}")

    # Ensure user has an email address
    if not request.user.email:
        logger.error("❌ No email, redirecting to checkout")
        messages.error(request, "You must have an email address to pay online.")
        return redirect('checkout')

    # Check if cart is empty
    cart = cart_service.get_cart(request.user)
    if cart.items.count() == 0:
        logger.error("❌ Cart is empty, redirecting to cart")
        messages.error(request, "Your cart is empty.")
        return redirect('view_cart')

    payment_method = request.POST.get('payment_method')
    logger.info(f"Payment method: {payment_method}")

    # Create order from cart (this clears the cart)
    try:
        order = order_service.create_order_from_cart(request.user, payment_method)
        logger.info(f"✅ Order {order.id} created")
    except ValueError as e:
        logger.error(f"❌ Order creation failed: {e}")
        messages.error(request, str(e))
        return redirect('view_cart')

    # Prepare Paystack initialization
    email = request.user.email
    phone = None
    if payment_method in ['mtn', 'airtel']:
        raw_phone = request.POST.get(f'{payment_method}_phone', '').strip()
        if not raw_phone:
            messages.error(request, "Phone number is required for mobile money.")
            return redirect('checkout')
        phone = format_phone_for_paystack(raw_phone, payment_method)
        logger.info(f"Formatted phone for Paystack: {phone}")

    result = paystack.initialize_payment(
        order=order,
        email=email,
        amount=order.total,
        payment_method=payment_method,
        phone=phone
    )

    if result['success']:
        logger.info(f"✅ Paystack init successful, redirecting to {result['authorization_url']}")
        return redirect(result['authorization_url'])
    else:
        logger.error(f"❌ Paystack init failed: {result.get('message')}")
        messages.error(request, result.get('message', 'Payment failed'))
        return redirect('checkout')


def payment_callback(request):
    """
    Step 2: Handle the callback from Paystack after payment.
    Verifies the transaction and updates the order status.
    """
    reference = request.GET.get('reference')
    if not reference:
        logger.error("❌ No payment reference provided in callback")
        messages.error(request, "No payment reference provided.")
        return redirect('home')

    logger.info(f"📞 Payment callback received with reference: {reference}")
    result = paystack.verify_payment(reference)

    if not result['success']:
        logger.error(f"❌ Payment verification failed: {result.get('message')}")
        messages.error(request, "Payment verification failed. Please contact support.")
        return redirect('home')

    # Extract order ID from reference (format: order_{id}_timestamp)
    try:
        parts = reference.split('_')
        if len(parts) < 2 or parts[0] != 'order':
            raise ValueError("Invalid reference format")
        order_id = int(parts[1])
    except (IndexError, ValueError) as e:
        logger.error(f"❌ Could not extract order ID from reference {reference}: {e}")
        messages.error(request, "Invalid payment reference. Please contact support.")
        return redirect('home')

    # Retrieve the order
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        logger.error(f"❌ Order {order_id} not found for reference {reference}")
        messages.error(request, "Order not found. Please contact support.")
        return redirect('home')

    # Mark order as completed
    order.payment_status = 'completed'
    order.save()
    logger.info(f"✅ Order {order_id} marked as completed")

    # Send payment receipt email
    from restaurant.signals import send_payment_receipt
    try:
        send_payment_receipt(order)
    except Exception as e:
        logger.error(f"❌ Failed to send payment receipt for order {order_id}: {e}")

    messages.success(request, "Payment successful!")
    return redirect('order_confirmation', order_id=order.id)