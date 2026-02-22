import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY
PAYSTACK_PUBLIC_KEY = settings.PAYSTACK_PUBLIC_KEY
PAYSTACK_INITIALIZE_URL = 'https://api.paystack.co/transaction/initialize'
PAYSTACK_VERIFY_URL = 'https://api.paystack.co/transaction/verify/'

def initialize_payment(order, email, amount, payment_method='card', phone=None):
    """
    Initialize a Paystack transaction.
    payment_method: 'card', 'mtn', 'airtel'
    """
    headers = {
        'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }

    amount_kobo = int(amount * 100)  # Paystack uses smallest currency unit (kobo for NGN)
    reference = f'order_{order.id}_{int(order.created_at.timestamp())}'

    # Base payload with explicit currency (NGN for test mode)
    payload = {
        'email': email,
        'amount': amount_kobo,
        'currency': 'NGN',  # Explicitly set currency
        'reference': reference,
        'callback_url': f"{settings.SITE_URL}/payment/callback/",
    }

    # Set channels based on payment method
    if payment_method == 'card':
        # For card, do NOT restrict channels – let Paystack decide
        pass
    elif payment_method in ['mtn', 'airtel']:
        # For mobile money, specify channel and provider
        payload['channels'] = ['mobile_money']
        payload['mobile_money'] = {
            'phone': phone,
            'provider': payment_method.upper()  # MTN or AIRTEL
        }
    else:
        # Default: no channel restriction
        pass

    logger.info(f"Paystack initialize payload: {payload}")
    print("🚀 Sending to Paystack:", payload)  # temporary for debugging

    try:
        response = requests.post(PAYSTACK_INITIALIZE_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Paystack initialize response: {data}")
        print("📦 Paystack response:", data)

        if data['status']:
            return {
                'success': True,
                'authorization_url': data['data']['authorization_url'],
                'reference': data['data']['reference']
            }
        else:
            logger.error(f"Paystack initialization failed: {data}")
            return {'success': False, 'message': data.get('message', 'Unknown error')}
    except requests.exceptions.RequestException as e:
        logger.error(f"Paystack HTTP error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                logger.error(f"Paystack error response: {error_data}")
                print("🔥 Error details:", error_data)
            except:
                logger.error(f"Paystack error text: {e.response.text}")
        return {'success': False, 'message': 'Network error. Please try again.'}
    except Exception as e:
        logger.error(f"Unexpected error during Paystack init: {e}")
        return {'success': False, 'message': 'An unexpected error occurred.'}


def verify_payment(reference):
    """Verify a Paystack transaction."""
    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
    url = f"{PAYSTACK_VERIFY_URL}{reference}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Paystack verify response: {data}")
        if data['status'] and data['data']['status'] == 'success':
            return {'success': True, 'data': data['data']}
        else:
            logger.error(f"Paystack verification failed: {data}")
            return {'success': False, 'message': data.get('message', 'Verification failed')}
    except requests.exceptions.RequestException as e:
        logger.error(f"Paystack verify HTTP error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                logger.error(f"Paystack error response: {error_data}")
            except:
                logger.error(f"Paystack error text: {e.response.text}")
        return {'success': False, 'message': 'Network error during verification.'}
    except Exception as e:
        logger.error(f"Unexpected error during verify: {e}")
        return {'success': False, 'message': 'Unexpected error.'}