import africastalking
from django.conf import settings

# Initialize Africa's Talking
username = "sandbox"  # Use 'sandbox' for test environment
api_key = "your_api_key"  # Get from Africa's Talking dashboard

africastalking.initialize(username, api_key)
sms = africastalking.SMS

def send_order_sms(phone_number, customer_name, order_id, status):
    """Send SMS notification to customer"""
    
    messages = {
        'confirmed': f"Hi {customer_name}, your order #{order_id} has been confirmed and will be prepared shortly.",
        'preparing': f"Hi {customer_name}, your order #{order_id} is now being prepared!",
        'ready': f"Hi {customer_name}, your order #{order_id} is ready for pickup/delivery!",
        'delivered': f"Hi {customer_name}, your order #{order_id} has been delivered. Enjoy your meal!",
    }
    
    message = messages.get(status, f"Hi {customer_name}, your order #{order_id} status: {status}")
    
    try:
        response = sms.send(message, [phone_number])
        print(f"✅ SMS sent to {phone_number}: {response}")
        return True
    except Exception as e:
        print(f"❌ Failed to send SMS: {e}")
        return False

def send_delivery_sms(phone_number, driver_name, order_id, estimated_time):
    """Send SMS to customer when driver is assigned"""
    
    message = f"Hi! Your order #{order_id} has been assigned to {driver_name}. Estimated delivery: {estimated_time}. Track your order on our website."
    
    try:
        response = sms.send(message, [phone_number])
        print(f"✅ Delivery SMS sent to {phone_number}")
        return True
    except Exception as e:
        print(f"❌ Failed to send SMS: {e}")
        return False