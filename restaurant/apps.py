from django.apps import AppConfig


class RestaurantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'restaurant'

    def ready(self):
        """
        Import signals when the app is ready.
        """
        from . import signals  # noqa