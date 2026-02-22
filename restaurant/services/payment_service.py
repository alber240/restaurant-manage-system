import logging
from django.shortcuts import redirect, render
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
from restaurant.services import order as order_service
from restaurant.services import paystack

logger = logging.getLogger(__name__)

@login_required
@require_POST
def process_payment(request):
    payment_method = request.POST.get('payment_method')
    try:
        order = order_service.create_order_from_cart(request.user, payment_method)
        logger.info(f"Order {order.id} created for user {request.user.id}")
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('cart')

    email = request.user.email
    if not email:
        messages.error(request, "You must have an email address to pay online.")
        return redirect('checkout')

    phone = None
    if payment_method in ['mtn', 'airtel']:
        phone = request.POST.get(f'{payment_method}_phone', '').strip()
        if not phone:
            messages.error(request, "Phone number is required for mobile money.")
            return redirect('checkout')

    result = paystack.initialize_payment(
        order=order,
        email=email,
        amount=order.total,
        payment_method=payment_method,
        phone=phone
    )

    if result['success']:
        logger.info(f"Paystack init successful for order {order.id}, ref: {result['reference']}")
        return redirect(result['authorization_url'])
    else:
        logger.error(f"Paystack init failed for order {order.id}: {result.get('message')}")
        messages.error(request, result.get('message', 'Payment failed'))
        return redirect('checkout')


def payment_callback(request):
    reference = request.GET.get('reference')
    if not reference:
        messages.error(request, "No payment reference provided.")
        return redirect('home')

    logger.info(f"Payment callback received with reference: {reference}")
    result = paystack.verify_payment(reference)

    if result['success']:
        # Try to extract order ID from reference (format: order_{id}_timestamp)
        try:
            parts = reference.split('_')
            if len(parts) >= 2 and parts[0] == 'order':
                order_id = int(parts[1])
                order = order_service.get_order_by_id(order_id, user=request.user)
                order.payment_status = 'completed'
                order.save()
                from restaurant.signals import send_payment_receipt
                send_payment_receipt(order)
                messages.success(request, "Payment successful!")
                logger.info(f"Order {order_id} marked as completed")
                return redirect('order_confirmation', order_id=order.id)
            else:
                raise ValueError("Invalid reference format")
        except (IndexError, ValueError, order_service.Order.DoesNotExist) as e:
            logger.error(f"Could not find order for reference {reference}: {e}")
            messages.error(request, "Order not found. Please contact support.")
    else:
        logger.error(f"Payment verification failed for reference {reference}: {result.get('message')}")
        messages.error(request, "Payment verification failed. Please contact support.")

    return redirect('home')