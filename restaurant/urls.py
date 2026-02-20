from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import ProtectedView, StaffOnlyView 
from . import views
from restaurant import views

urlpatterns = [
    # Main Pages
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    
    # Authentication
    path('accounts/register/', views.register, name='register'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    path('order/<int:order_id>/3d-secure/', views.verify_3d_secure, name='verify_3d_secure'),
    
    # Menu and Cart
    path('menu/', views.menu_view, name='menu'),
    path('add-to-cart/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:item_id>/', views.update_cart, name='update_cart'),
    path('cart-count/', views.cart_count, name='cart-count'),
    
    # Checkout and Orders
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_history, name='order_history'),
    
    # Staff Views
    path('kitchen/', views.kitchen_dashboard, name='kitchen'),
    path('waiter/', views.waiter_dashboard, name='waiter'),
    path('update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    
    # Reservations
    path('reservation/', views.create_reservation, name='reservation'),
    path('reservation/confirm/', views.reservation_success, name='reservation_success'),
    
    # Debug
    path('debug-menu/', views.debug_menu, name='debug_menu'),
    
    path('order/<int:order_id>/payment/', views.order_payment, name='order_payment'),
    
    path('api/protected-endpoint/', ProtectedView.as_view(), name='protected-endpoint'),
    
    # urls.py
   path('api/staff-dashboard/', StaffOnlyView.as_view()),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)