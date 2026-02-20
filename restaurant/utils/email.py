from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import os

def send_email(subject, to_email, template_name, context):
    # Render HTML template
    html_content = render_to_string(f'email/{template_name}', context)
    text_content = strip_tags(html_content)  # Fallback text version
    
    # Create email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=os.getenv('DEFAULT_FROM_EMAIL'),
        to=[to_email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send()