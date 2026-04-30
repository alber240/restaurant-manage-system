# Restaurant Utilities
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def get_user_role(user):
    if user.is_authenticated and hasattr(user, 'profile'):
        return user.profile.role
    return 'customer'

def is_manager(user):
    return user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'manager')

def is_kitchen_staff(user):
    return user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'kitchen')

def is_waiter(user):
    return user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'waiter')

def manager_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login')
            return redirect('login')
        if not is_manager(request.user):
            messages.error(request, 'Permission denied')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper

def kitchen_staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login')
            return redirect('login')
        if not (is_kitchen_staff(request.user) or is_manager(request.user)):
            messages.error(request, 'Kitchen staff only')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper

def waiter_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login')
            return redirect('login')
        if not (is_waiter(request.user) or is_manager(request.user)):
            messages.error(request, 'Waiter only')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper
