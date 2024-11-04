from flask import Flask, request, jsonify, send_from_directory, render_template
import requests
import logging
import os
from PIL import Image, ImageEnhance
from io import BytesIO
from datetime import datetime, timedelta
import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature
from bs4 import BeautifulSoup
from image_generator import generate_image_from_text, generate_image_from_url  

app = Flask(__name__)

# Configuration
ID_AKUN = 'id-akun-cloudflaremu'  # Replace with your actual account ID
app.config['SECRET_KEY'] = 'YourSecretKey'  # Replace with a strong secret key
AI_MODEL_URL = f'https://api.cloudflare.com/client/v4/accounts/{ID_AKUN}/ai/run/@cf/stabilityai/stable-diffusion-xl-base-1.0'
WORKERS_API_TOKEN = 'ypur-workers-api-token'
IMAGE_FOLDER = './static/images'
TOKEN_EXPIRATION = 3600  # Token expiration time in seconds (1 hour)
password_hash = bcrypt.hashpw(b'password', bcrypt.gensalt())  # Replace with a secure password
os.makedirs(IMAGE_FOLDER, exist_ok=True)  # Ensure image folder exists

# Setup logging
logging.basicConfig(level=logging.INFO)

# Helper Functions
@app.route('/images')
def images():
    image_files = [f for f in os.listdir(IMAGE_FOLDER) if f.endswith('.jpg')]
    return jsonify(image_files)

def generate_token(username):
    """Generate a timed token for the given user."""
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    expiration_time = datetime.utcnow() + timedelta(seconds=TOKEN_EXPIRATION)
    token_data = {'username': username, 'exp': expiration_time.isoformat()}
    return s.dumps(token_data)

def verify_token(token):
    """Verify the provided token."""
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        data = s.loads(token)
        expiration_time = datetime.fromisoformat(data['exp'])
        if datetime.utcnow() > expiration_time:
            return None  # Token has expired
    except (BadSignature, KeyError, ValueError):
        return None  # Invalid or incorrect format
    return data['username']

def check_password(password):
    """Verify if provided password matches the stored hash."""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash)

def run_ai_model(prompt):
    """Call the AI model API with the provided prompt."""
    api_url = f'https://api.cloudflare.com/client/v4/accounts/{ID_AKUN}/ai/run/@cf/meta/llama-2-7b-chat-fp16'
    
    headers = {
        'Authorization': f'Bearer {WORKERS_API_TOKEN}',
        'Content-Type': 'application/json',
    }
    payload = {'prompt': prompt}
    
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        if 'result' in data:
            return data['result']
        else:
            logging.error("Invalid response format: 'result' key missing")
            return None
    except requests.RequestException as e:
        logging.error(f'Request error: {str(e)}')
        raise RuntimeError(f'Request error: {str(e)}')

def google_search(query):
    """Perform a Google search and return the results."""
    search_url = f"https://www.google.com/search?q={query}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        for g in soup.find_all('div', class_='tF2Cxc'):
            link = g.find('a')['href']
            title = g.find('h3').text if g.find('h3') else 'No title'
            results.append({'title': title, 'link': link})

        if not results:
            logging.debug(f"No results found for query: {query}")
            raise ValueError("No results found")

        return results
    except requests.RequestException as e:
        logging.error(f"Request error: {str(e)}")
        raise RuntimeError(f"Request error: {str(e)}")

@app.route('/login', methods=['POST'])
def login():
    """Endpoint for user authentication."""
    password = request.form.get('password')  # Retrieve password from the request
    if not check_password(password):
        return jsonify({'error': 'Invalid password'}), 401
    return jsonify({'success': True})  # Indicate success

@app.route('/dorking', methods=['POST'])
def dorking():
    """Endpoint for Google search."""
    query = request.form.get('query')
    if not query:
        return jsonify({'error': 'Missing query'}), 400

    try:
        search_results = google_search(query)
        return jsonify({'search_results': search_results})
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Endpoint to send a query to the AI model and get a response."""
    query = request.form.get('query')
    if not query:
        return jsonify({'error': 'Missing query'}), 400

    try:
        ai_response = run_ai_model(query)
        return jsonify({'ai_response': ai_response})

    except Exception as e:
        logging.error(f"Error in /chat endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/images/<filename>')
def get_image(filename):
    """Serve images from the static folder."""
    return send_from_directory(IMAGE_FOLDER, filename)

@app.route('/generate', methods=['POST'])
def generate():
    """Generate image based on text prompt."""
    password = request.form.get('password')  # Retrieve password from the request
    if not check_password(password):
        return jsonify({'error': 'Invalid password'}), 401

    prompt = request.form.get('query')
    if not prompt:
        return jsonify({"error": "Query is required."}), 400
    try:
        # Placeholder for an image generation function
        image = generate_image_from_text(prompt)  # Implement this function
        if image:
            image_path = os.path.join(IMAGE_FOLDER, f"{datetime.now():%Y%m%d_%H%M%S}_image.jpg")
            image.save(image_path)
            return jsonify({'image_path': image_path})
        else:
            return jsonify({"error": "Failed to generate image."}), 500
    except Exception as e:
        logging.error(f"Image generation failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/sharpen_image', methods=['POST'])
def sharpen_image():
    """Sharpen an image provided via URL."""
    token = request.headers.get('Authorization')
    if not token or not verify_token(token):
        return jsonify({'error': 'Invalid or expired token'}), 403

    image_url = request.form.get('image_url')
    if not image_url:
        return jsonify({'error': 'No image URL provided'}), 400

    try:
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(2.0)  # Increase sharpness
        img_path = os.path.join(IMAGE_FOLDER, f'sharpened_{datetime.now():%Y%m%d_%H%M%S}.jpg')
        img.save(img_path)
        
        return jsonify({'sharpened_image_url': f'static/images/{os.path.basename(img_path)}'})
    except Exception as e:
        logging.error(f"Error sharpening image: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """Render the main index page."""
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)