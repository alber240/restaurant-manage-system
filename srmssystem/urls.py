from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from restaurant import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

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
]

# Serve static and media files during development only
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)