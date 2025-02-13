from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import logging
import requests
import pandas as pd
import json
import time
import traceback
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# SMS API Configuration
SMS_API_CONFIG = {
    'API_URL': 'https://yurticisms1.com/sms_api/json',
    'USERNAME': 'user',
    'PASSWORD': 'Tr**ys^4e'
}

def create_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Origin': 'https://yurticisms1.com',
        'Referer': 'https://yurticisms1.com/',
        'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    })
    return session

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Sayfa yüklenirken bir hata oluştu",
            "details": str(e),
            "trace": traceback.format_exc()
        }), 500

@app.route('/send_sms', methods=['POST'])
def send_sms():
    try:
        logger.info("Received SMS request")
        
        # Get message and numbers from request
        message = request.form.get('message')
        manual_numbers = request.form.get('numbers')
        file = request.files.get('file')
        
        logger.debug(f"Message: {message}")
        logger.debug(f"Manual numbers: {manual_numbers}")
        logger.debug(f"File uploaded: {True if file else False}")
        
        # Process phone numbers
        numbers = []
        if manual_numbers:
            numbers.extend(manual_numbers.split(','))
        if file:
            df = pd.read_excel(file)
            numbers.extend(df['Telefon'].astype(str).tolist())
        
        # Remove duplicates and format numbers
        numbers = list(set(numbers))
        logger.info(f"Processing {len(numbers)} numbers")
        
        # Format numbers to match API requirements (add 90 prefix if needed)
        formatted_numbers = []
        for num in numbers:
            num = num.strip().replace(' ', '')
            if num.startswith('+90'):
                num = num[1:]
            elif not num.startswith('90'):
                num = '90' + num.lstrip('0')
            formatted_numbers.append(num)
            
        logger.info(f"Formatted numbers: {','.join(formatted_numbers)}")
        
        # Prepare API request
        api_url = SMS_API_CONFIG['API_URL']
        
        payload = {
            'user': {
                'name': SMS_API_CONFIG['USERNAME'],
                'pass': SMS_API_CONFIG['PASSWORD']
            },
            'msgBaslik': 'APITEST',
            'msgData': message,
            'msgNumbers': ','.join(formatted_numbers),
            'msgEncoding': 'turkish',
            'msgSaveReport': '1',
            'msgTime': '',
            'msgTimeZone': '+0300'
        }
        
        logger.info("Sending request to SMS API")
        
        # Create a session and send request
        session = create_session()
        
        # First make a GET request to the main page to get Cloudflare cookies
        session.get('https://yurticisms1.com/')
        time.sleep(2)  # Wait for Cloudflare to process
        
        # Now send the actual API request
        response = session.post(api_url, json=payload)
        
        logger.info(f"API Response - Status: {response.status_code}")
        logger.info(f"API Response - Content: {response.text}")
        logger.debug(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                return jsonify(result)
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid JSON response from API', 'response': response.text}), 500
        else:
            return jsonify({
                'error': 'SMS API hatası',
                'status': response.status_code,
                'details': response.text
            }), response.status_code
            
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
