# payments/gateways.py (New file)
class MTNMoMoGateway:
    def process_payment(self, amount, phone):
        # Will implement actual API call later
        return {"status": "TEST_SUCCESS"}

class StripeGateway:
    def process_payment(self, card_details):
        # Placeholder for Stripe logic
        return {"status": "TEST_SUCCESS"}