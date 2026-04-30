"""
Admin Settings Views for Restaurant Management System
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import HttpResponse
from restaurant.models import RestaurantSettings, QRCodeTable, Table
from restaurant.utils import manager_required
import qrcode
from io import BytesIO
import base64


@manager_required
def settings_dashboard(request):
    """Main settings dashboard"""
    settings = RestaurantSettings.objects.first()
    if not settings:
        settings = RestaurantSettings.objects.create()
    
    context = {
        'settings': settings,
    }
    return render(request, 'restaurant/admin/settings/dashboard.html', context)


@manager_required
def general_settings(request):
    """Update general restaurant settings"""
    settings = RestaurantSettings.objects.first()
    if not settings:
        settings = RestaurantSettings.objects.create()
    
    if request.method == 'POST':
        settings.restaurant_name = request.POST.get('restaurant_name')
        settings.restaurant_phone = request.POST.get('restaurant_phone')
        settings.restaurant_email = request.POST.get('restaurant_email')
        settings.restaurant_address = request.POST.get('restaurant_address')
        settings.currency_symbol = request.POST.get('currency_symbol')
        settings.currency_code = request.POST.get('currency_code')
        settings.opening_time = request.POST.get('opening_time')
        settings.closing_time = request.POST.get('closing_time')
        settings.save()
        
        messages.success(request, 'General settings updated successfully!')
        return redirect('settings_general')
    
    context = {'settings': settings}
    return render(request, 'restaurant/admin/settings/general.html', context)


@manager_required
def delivery_settings(request):
    """Update delivery settings"""
    settings = RestaurantSettings.objects.first()
    if not settings:
        settings = RestaurantSettings.objects.create()
    
    if request.method == 'POST':
        settings.enable_delivery = request.POST.get('enable_delivery') == 'on'
        settings.delivery_radius_km = request.POST.get('delivery_radius_km')
        settings.min_order_for_delivery = request.POST.get('min_order_for_delivery')
        settings.delivery_fee_type = request.POST.get('delivery_fee_type')
        settings.delivery_fee_amount = request.POST.get('delivery_fee_amount')
        settings.delivery_fee_per_km = request.POST.get('delivery_fee_per_km')
        settings.free_delivery_minimum = request.POST.get('free_delivery_minimum')
        settings.estimated_delivery_time = request.POST.get('estimated_delivery_time')
        settings.save()
        
        messages.success(request, 'Delivery settings updated successfully!')
        return redirect('settings_delivery')
    
    context = {'settings': settings}
    return render(request, 'restaurant/admin/settings/delivery.html', context)


@manager_required
def payment_settings(request):
    """Update payment settings"""
    settings = RestaurantSettings.objects.first()
    if not settings:
        settings = RestaurantSettings.objects.create()
    
    if request.method == 'POST':
        settings.enable_card_payment = request.POST.get('enable_card_payment') == 'on'
        settings.enable_mobile_money = request.POST.get('enable_mobile_money') == 'on'
        settings.enable_cash_on_delivery = request.POST.get('enable_cash_on_delivery') == 'on'
        settings.enable_cash_dine_in = request.POST.get('enable_cash_dine_in') == 'on'
        settings.tax_rate = request.POST.get('tax_rate')
        settings.service_charge = request.POST.get('service_charge')
        settings.save()
        
        messages.success(request, 'Payment settings updated successfully!')
        return redirect('settings_payment')
    
    context = {'settings': settings}
    return render(request, 'restaurant/admin/settings/payment.html', context)


@manager_required
def tip_settings(request):
    """Update tip settings"""
    settings = RestaurantSettings.objects.first()
    if not settings:
        settings = RestaurantSettings.objects.create()
    
    if request.method == 'POST':
        settings.enable_tips = request.POST.get('enable_tips') == 'on'
        settings.tip_distribution_method = request.POST.get('tip_distribution_method')
        
        # Parse suggested tip percentages
        tip_percentages = request.POST.getlist('tip_percentages')
        settings.suggested_tip_percentages = [int(p) for p in tip_percentages if p]
        settings.save()
        
        messages.success(request, 'Tip settings updated successfully!')
        return redirect('settings_tip')
    
    context = {'settings': settings}
    return render(request, 'restaurant/admin/settings/tip.html', context)


@manager_required
def qr_code_management(request):
    """Manage QR codes for tables"""
    qr_codes = QRCodeTable.objects.all()
    tables = Table.objects.all()
    
    # Get existing table numbers that have QR codes
    existing_tables = [q.table_number for q in qr_codes]
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'generate':
            table_number = request.POST.get('table_number')
            
            if QRCodeTable.objects.filter(table_number=table_number).exists():
                messages.error(request, f'QR code for Table {table_number} already exists!')
            else:
                qr_code = QRCodeTable.objects.create(table_number=table_number)
                
                # Generate QR code image
                import qrcode
                from PIL import Image
                
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(qr_code.get_qr_url())
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Save to bytes
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                
                # Convert to base64 for displaying
                qr_base64 = base64.b64encode(buffer.getvalue()).decode()
                
                messages.success(request, f'QR code for Table {table_number} generated successfully!')
                
                return render(request, 'restaurant/admin/settings/qr_code_preview.html', {
                    'qr_code': qr_code,
                    'qr_image': qr_base64,
                })
        
        elif action == 'delete':
            qr_id = request.POST.get('qr_id')
            qr_code = get_object_or_404(QRCodeTable, id=qr_id)
            table_number = qr_code.table_number
            qr_code.delete()
            messages.success(request, f'QR code for Table {table_number} deleted!')
            return redirect('settings_qr_codes')
        
        elif action == 'bulk_generate':
            # Generate QR codes for all tables that don't have them
            created_count = 0
            for table in tables:
                if not QRCodeTable.objects.filter(table_number=table.number).exists():
                    QRCodeTable.objects.create(table_number=table.number)
                    created_count += 1
            
            messages.success(request, f'Generated {created_count} new QR codes!')
            return redirect('settings_qr_codes')
    
    context = {
        'qr_codes': qr_codes,
        'tables': tables,
        'existing_tables': existing_tables,
    }
    return render(request, 'restaurant/admin/settings/qr_codes.html', context)


@manager_required
def download_qr_code(request, qr_id):
    """Download QR code as PNG image"""
    qr_code = get_object_or_404(QRCodeTable, id=qr_id)
    
    # Generate QR code image
    import qrcode
    from PIL import Image
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_code.get_qr_url())
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Create HTTP response with PNG image
    response = HttpResponse(content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="table_{qr_code.table_number}_qr.png"'
    img.save(response, 'PNG')
    
    return response