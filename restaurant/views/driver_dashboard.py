from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from restaurant.models import Order, Driver
from django.utils import timezone

@login_required
def driver_dashboard(request):
    """Driver dashboard - only shows assigned orders"""
    if not hasattr(request.user, 'driver_profile'):
        messages.error(request, "You are not authorized as a driver")
        return redirect('home')
    
    driver = request.user.driver_profile
    
    # Only get orders assigned to this driver (not all available)
    assigned_orders = Order.objects.filter(
        driver=driver,
        delivery_status__in=['assigned', 'accepted', 'picked_up', 'en_route']
    ).order_by('-created_at')
    
    # Delivery history
    delivery_history = Order.objects.filter(
        driver=driver,
        delivery_status='delivered'
    ).order_by('-delivered_at')[:20]
    
    context = {
        'driver': driver,
        'assigned_orders': assigned_orders,
        'delivery_history': delivery_history,
    }
    return render(request, 'restaurant/driver/dashboard.html', context)


@login_required
def driver_accept_order(request, order_id):
    """Driver accepts the assigned delivery"""
    driver = request.user.driver_profile
    order = get_object_or_404(Order, id=order_id, driver=driver, delivery_status='assigned')
    
    order.delivery_status = 'accepted'
    order.save()
    
    messages.success(request, f'You accepted Order #{order.id}')
    return redirect('driver_dashboard')


@login_required
def driver_pickup_order(request, order_id):
    """Driver marks order as picked up"""
    driver = request.user.driver_profile
    order = get_object_or_404(Order, id=order_id, driver=driver, delivery_status='accepted')
    
    order.delivery_status = 'picked_up'
    order.picked_up_at = timezone.now()
    order.save()
    
    messages.success(request, f'Order #{order.id} marked as picked up')
    return redirect('driver_dashboard')


@login_required
def driver_deliver_order(request, order_id):
    """Driver marks order as delivered and becomes available again"""
    driver = request.user.driver_profile
    order = get_object_or_404(Order, id=order_id, driver=driver, delivery_status='picked_up')
    
    order.delivery_status = 'delivered'
    order.status = 'delivered'
    order.delivered_at = timezone.now()
    order.save()
    
    # Update driver earnings
    driver.total_deliveries += 1
    driver.total_earnings += order.delivery_fee
    if order.delivery_tip:
        driver.total_earnings += order.delivery_tip
    
    # IMPORTANT: Set driver status back to AVAILABLE
    driver.status = 'available'
    driver.save()
    
    messages.success(request, f'✅ Order #{order.id} delivered! You are now available for new deliveries.')
    return redirect('driver_dashboard')


@login_required
def driver_update_status(request, order_id):
    """Driver updates delivery status (GET method for simplicity)"""
    if not hasattr(request.user, 'driver_profile'):
        messages.error(request, "Not authorized as a driver")
        return redirect('home')
    
    order = get_object_or_404(Order, id=order_id, driver=request.user.driver_profile)
    new_status = request.GET.get('status')
    
    if new_status in ['picked_up', 'en_route', 'delivered']:
        order.delivery_status = new_status
        
        if new_status == 'picked_up':
            order.picked_up_at = timezone.now()
            messages.success(request, f"Order #{order.id} marked as Picked Up")
        elif new_status == 'en_route':
            messages.success(request, f"Order #{order.id} marked as En Route")
        elif new_status == 'delivered':
            order.delivered_at = timezone.now()
            # Update driver earnings
            driver = request.user.driver_profile
            driver.total_deliveries += 1
            driver.total_earnings += order.delivery_fee
            if order.delivery_tip:
                driver.total_earnings += order.delivery_tip
            driver.status = 'available'
            driver.save()
            messages.success(request, f"✅ Order #{order.id} delivered! You earned ${order.delivery_fee}")
        
        order.save()
    
    return redirect('driver_dashboard')


@login_required
def driver_update_location(request):
    """API endpoint for driver to update current location"""
    if not hasattr(request.user, 'driver_profile'):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        driver = request.user.driver_profile
        driver.current_latitude = latitude
        driver.current_longitude = longitude
        driver.save()
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Invalid method'}, status=400)

@login_required
def driver_make_available(request):
    """Driver manually marks themselves as available"""
    driver = request.user.driver_profile
    driver.status = 'available'
    driver.save()
    messages.success(request, "You are now available for new deliveries!")
    return redirect('driver_dashboard')