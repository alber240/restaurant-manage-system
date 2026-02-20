from PIL import Image, ImageDraw, ImageFont
import os

# Ensure the static/images folder exists
os.makedirs('static/images', exist_ok=True)

# List of images with filename, size, and optional text
images = [
    ('logo.png', (200, 80), 'LOGO'),
    ('hero-bg.jpg', (1920, 600), 'Hero Banner'),
    ('restaurant-interior.jpg', (800, 600), 'Restaurant Interior'),
    ('delivery-service.jpg', (800, 600), 'Delivery Service'),
    ('chef1.jpg', (400, 400), 'Chef 1'),
    ('chef2.jpg', (400, 400), 'Chef 2'),
    ('manager.jpg', (400, 400), 'Manager'),
    ('cookingw.jpeg', (400, 300), 'Cooking'),
]

for filename, size, text in images:
    # Create a gray image
    img = Image.new('RGB', size, color='#cccccc')
    draw = ImageDraw.Draw(img)
    
    # Optionally add text in the center
    # You can skip this if you just want a plain color
    # But text helps identify the placeholder
    try:
        font = ImageFont.load_default()
        # Get text bounding box to center it
        bbox = draw.textbbox((0,0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((size[0] - text_width)//2, (size[1] - text_height)//2)
        draw.text(position, text, fill='#333333', font=font)
    except:
        pass  # If text fails, just plain color
    
    img.save(f'static/images/{filename}')
    print(f'Created static/images/{filename}')

print("All placeholder images created!")