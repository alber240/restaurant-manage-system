from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test

def manager_required(view_func):
    """Decorator for manager-only views"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied
        if not (request.user.is_superuser or request.user.role == 'manager'):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper

def kitchen_staff_required(view_func):
    """Decorator for kitchen staff only"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied
        if not (request.user.is_superuser or request.user.role == 'kitchen' or request.user.role == 'manager'):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper

def waiter_required(view_func):
    """Decorator for waiter only"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied
        if not (request.user.is_superuser or request.user.role == 'waiter' or request.user.role == 'manager'):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper