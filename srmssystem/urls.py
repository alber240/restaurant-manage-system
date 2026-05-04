from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from restaurant import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from restaurant.views import driver_dashboard, staff
from restaurant.views import admin_dashboard, admin_settings, customer
from restaurant.views import auth as auth_views
from django.contrib.auth.views import LogoutView
urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),

    # Optional: Django Jet admin theme (uncomment if using Jet)
    # path('jet/', include('jet.urls', 'jet')),

    # Django built-in authentication URLs (login, logout, password reset)
    path('accounts/', include('django.contrib.auth.urls')),

    # All restaurant app URLs (menu, cart, orders, reservations, etc.)
    path('', include('restaurant.urls')),

    # 3D Secure verification for test payments
    path('order/<int:order_id>/3d-secure/', views.verify_3d_secure, name='verify_3d_secure'),

    # JWT authentication endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
   # Admin Dashboard URLS
    
    
    # ==================================================
    # ADMIN DASHBOARD URLs (For Restaurant Managers)
    # ==================================================
    
    # Dashboard Home
    path('admin-dashboard/', admin_dashboard.admin_dashboard_home, name='admin_dashboard'),
    
    # User Management
    path('admin-dashboard/users/', admin_dashboard.admin_users, name='admin_users'),
    path('admin-dashboard/users/create/', admin_dashboard.admin_create_user, name='admin_create_user'),
    path('admin-dashboard/users/<int:user_id>/edit/', admin_dashboard.admin_edit_user, name='admin_edit_user'),
    path('admin-dashboard/users/<int:user_id>/delete/', admin_dashboard.admin_delete_user, name='admin_delete_user'),
    
    # Order Management
    path('admin-dashboard/orders/', admin_dashboard.admin_orders, name='admin_orders'),
    path('admin-dashboard/orders/<int:order_id>/', admin_dashboard.admin_order_detail, name='admin_order_detail'),
    path('admin-dashboard/orders/export/', admin_dashboard.admin_export_orders, name='admin_export_orders'),
    
    # Menu Management
    path('admin-dashboard/menu/', admin_dashboard.admin_menu, name='admin_menu'),
    path('admin-dashboard/menu/add/', admin_dashboard.admin_add_menu_item, name='admin_add_menu_item'),
    path('admin-dashboard/menu/<int:item_id>/edit/', admin_dashboard.admin_edit_menu_item, name='admin_edit_menu_item'),
    path('admin-dashboard/menu/<int:item_id>/delete/', admin_dashboard.admin_delete_menu_item, name='admin_delete_menu_item'),
    path('admin-dashboard/menu/category/add/', admin_dashboard.admin_add_category, name='admin_add_category'),
    path('admin-dashboard/menu/bulk-stock/', admin_dashboard.admin_bulk_update_stock, name='admin_bulk_stock'),
    
    # Reservation Management
    path('admin-dashboard/reservations/', admin_dashboard.admin_reservations, name='admin_reservations'),
    path('admin-dashboard/reservations/<int:reservation_id>/cancel/', admin_dashboard.admin_cancel_reservation, name='admin_cancel_reservation'),
    
    # Reports
    path('admin-dashboard/reports/', admin_dashboard.admin_reports, name='admin_reports'),
    path('accounts/register/', auth_views.register, name='register'),
    
    # Add these to urlpatterns:
path('admin-dashboard/categories/', admin_dashboard.admin_categories, name='admin_categories'),
path('admin-dashboard/categories/add/', admin_dashboard.admin_add_category, name='admin_add_category'),
path('admin-dashboard/categories/<int:category_id>/edit/', admin_dashboard.admin_edit_category, name='admin_edit_category'),
path('admin-dashboard/categories/<int:category_id>/delete/', admin_dashboard.admin_delete_category, name='admin_delete_category'),


# Add to the existing urlpatterns in srmssystem/urls.py

# Settings URLs
path('settings/', admin_settings.settings_dashboard, name='settings_dashboard'),
path('settings/general/', admin_settings.general_settings, name='settings_general'),
path('settings/delivery/', admin_settings.delivery_settings, name='settings_delivery'),
path('settings/payment/', admin_settings.payment_settings, name='settings_payment'),
path('settings/tip/', admin_settings.tip_settings, name='settings_tip'),
path('settings/qr-codes/', admin_settings.qr_code_management, name='settings_qr_codes'),
path('settings/qr-code/download/<int:qr_id>/', admin_settings.download_qr_code, name='download_qr_code'),

# QR Code Ordering URLs - Add these to urlpatterns
path('table/order/<str:token>/', customer.table_order, name='table_order'),
path('table/order/<str:token>/add/<int:item_id>/', customer.table_add_to_cart, name='table_add_to_cart'),
path('table/order/<str:token>/cart/', customer.table_cart, name='table_cart'),
path('table/order/<str:token>/checkout/', customer.table_checkout, name='table_checkout'),
path('table/order/<str:token>/success/<int:order_id>/', customer.table_order_success, name='table_order_success'), 

    # Driver URLs
    path('driver/', driver_dashboard.driver_dashboard, name='driver_dashboard'),
    path('driver/accept/<int:order_id>/', driver_dashboard.driver_accept_order, name='driver_accept_order'),
    path('driver/update-status/<int:order_id>/', driver_dashboard.driver_update_status, name='driver_update_status'),
    path('driver/update-location/', driver_dashboard.driver_update_location, name='driver_update_location'),
      
   
   # Order tracking
path('order/track/<int:order_id>/', customer.order_tracking, name='order_tracking'),
# Driver location API
path('driver/location/<int:driver_id>/', customer.driver_location, name='driver_location'),

# Admin delivery management
path('admin-dashboard/delivery-orders/', admin_dashboard.admin_delivery_orders, name='admin_delivery_orders'),
path('admin-dashboard/assign-driver/<int:order_id>/', admin_dashboard.admin_assign_driver, name='admin_assign_driver'),

# Kitchen confirmation
path('kitchen/confirm/<int:order_id>/', staff.kitchen_confirm_order, name='kitchen_confirm_order'),

# Driver updates
path('driver/accept/<int:order_id>/', driver_dashboard.driver_accept_order, name='driver_accept_order'),
path('driver/pickup/<int:order_id>/', driver_dashboard.driver_pickup_order, name='driver_pickup_order'),
path('driver/deliver/<int:order_id>/', driver_dashboard.driver_deliver_order, name='driver_deliver_order'),
   
   
   
path('setup/', customer.setup_database, name='setup'),

path('accounts/logout/', LogoutView.as_view(next_page='/'), name='logout'),

path('guest-order-confirmation/', customer.guest_order_confirmation, name='guest_order_confirmation'),


#admin report
path('admin-dashboard/reports/', admin_dashboard.reports_dashboard, name='reports_dashboard'),
#gust
path('guest-order-confirmation/', customer.guest_order_confirmation, name='guest_order_confirmation')

]

# Serve static and media files during development only
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    
    