from django import template
import os
from django.conf import settings

register = template.Library()

@register.filter
def file_exists(filepath):
    if not filepath:
        return False
    return os.path.exists(os.path.join(settings.MEDIA_ROOT, filepath.split('/media/')[-1]))