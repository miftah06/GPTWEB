import requests
from PIL import Image
from io import BytesIO

# Cloudflare API configuration
API_URL = 'https://api.cloudflare.com/client/v4/accounts/<id akun>/ai/run/@cf/stabilityai/stable-diffusion-xl-base-1.0'
WORKERS_API_TOKEN = '<api token>'  # Replace with your actual token

def generate_image_from_text(text):
    """Generate an image from a text prompt using Cloudflare's API."""
    if not text:
        return None  # Return None if no text is provided

    headers = {
        'Authorization': f'Bearer {WORKERS_API_TOKEN}',
        'Content-Type': 'application/json'
    }

    payload = {
        'prompt': text
    }

    response = requests.post(API_URL, json=payload, headers=headers)

    if response.status_code == 200:
        image_data = response.content
        return Image.open(BytesIO(image_data))
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def generate_image_from_url(url):
    """Generate an image from a URL using Cloudflare's API."""
    if not url:
        return None  # Return None if no URL is provided

    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    return img
