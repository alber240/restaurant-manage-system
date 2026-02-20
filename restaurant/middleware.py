from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
import re

class StaffRequiredMiddleware:
    """
    Middleware to restrict access to staff-only URLs.
    If a non-staff user tries to access a path starting with any of the staff prefixes,
    they are redirected to the home page with an error message.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Define URL patterns that require staff access
        self.staff_paths = [
            reverse('kitchen'),      # /kitchen/
            reverse('waiter'),       # /waiter/
            reverse('update_order_status', args=[0]).replace('/0/', '/'),  # base pattern for status updates
        ]

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Allow superusers always
        if request.user.is_superuser:
            return None

        # Check if the requested path requires staff access
        current_path = request.path
        for path in self.staff_paths:
            # Remove trailing slash and compare start
            if current_path.startswith(path.rstrip('/')):
                if not request.user.is_staff:
                    messages.error(request, "You need staff privileges to access this page.")
                    return redirect('home')
                break
        return None