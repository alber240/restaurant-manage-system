from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView  # <-- ADD THIS

from restaurant.views import customer, staff, auth as auth_views_custom, api, payments

urlpatterns = [
    # Main Pages
    path('', customer.home_view, name='home'),
    path('about/', customer.about_view, name='about'),
    path('contact/', customer.contact_view, name='contact'),

    # Authentication
    path('accounts/register/', auth_views_custom.register, name='register'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Menu and Cart
    path('menu/', customer.menu_view, name='menu'),
    path('add-to-cart/<int:item_id>/', customer.add_to_cart, name='add_to_cart'),
    path('cart/', customer.view_cart, name='view_cart'),
    path('remove-from-cart/<int:item_id>/', customer.remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:item_id>/', customer.update_cart, name='update_cart'),
    path('cart-count/', customer.cart_count, name='cart-count'),

    # Checkout and Orders
    path('checkout/', customer.checkout, name='checkout'),
    path('process-payment/', payments.process_payment, name='process_payment'),
    path('orders/', customer.order_history, name='order_history'),
    path('order/<int:order_id>/confirmation/', customer.order_confirmation, name='order_confirmation'),
    path('order/<int:order_id>/payment/', customer.order_payment, name='order_payment'),
    path('order/<int:order_id>/3d-secure/', customer.verify_3d_secure, name='verify_3d_secure'),

    # Staff Views
    path('kitchen/', staff.kitchen_dashboard, name='kitchen'),
    path('waiter/', staff.waiter_dashboard, name='waiter'),
    path('update-status/<int:order_id>/', staff.update_order_status, name='update_order_status'),
    path('sales-report/', staff.sales_report, name='sales_report'),

    # Reservations
    path('reservation/', customer.create_reservation, name='reservation'),
    path('reservation/success/', customer.reservation_success, name='reservation_success'),

    # API endpoints
    path('api/protected-endpoint/', api.ProtectedView.as_view(), name='protected-endpoint'),
    path('api/staff-dashboard/', api.StaffOnlyView.as_view(), name='api_staff_dashboard'),
    path('api/logout/', api.LogoutView.as_view(), name='api_logout'),

    # JWT tokens
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('payment/callback/', payments.payment_callback, name='payment_callback'),
    # Debug
    path('debug-menu/', customer.debug_menu, name='debug_menu'),
    
    #inventory
    path('staff/inventory/', staff.inventory_dashboard, name='inventory_dashboard'),
    
    #manage dashboard url
    path('staff/manager/', staff.manager_dashboard, name='manager_dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)