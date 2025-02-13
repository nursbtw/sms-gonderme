from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import logging
import pandas as pd
import json
import cloudscraper
import time
import os

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return jsonify({
            "error": "Sayfa yüklenirken bir hata oluştu",
            "details": str(e)
        }), 500

def send_sms(message, numbers):
    try:
        # Create a cloudscraper session
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        
        # First get the login page to get any necessary cookies
        logger.info("Getting login page")
        login_url = 'https://yurticisms1.com/login'
        login_response = scraper.get(login_url)
        
        if login_response.status_code != 200:
            logger.error(f"Failed to get login page: {login_response.status_code}")
            return {"success": False, "error": "Could not access login page"}
            
        # Login to the system
        logger.info("Attempting to login")
        login_data = {
            'username': 'user',
            'password': 'Tr**ys^4e'
        }
        
        login_result = scraper.post(login_url, data=login_data)
        
        if login_result.status_code != 200:
            logger.error(f"Login failed: {login_result.status_code}")
            return {"success": False, "error": "Login failed"}
            
        # Send SMS
        logger.info("Sending SMS")
        sms_url = 'https://yurticisms1.com/sms_api/json'
        
        sms_data = {
            'user': {
                'name': 'user',
                'pass': 'Tr**ys^4e'
            },
            'msgBaslik': 'APITEST',
            'msgData': message,
            'msgNumbers': ','.join(numbers),
            'msgEncoding': 'turkish',
            'msgSaveReport': '1',
            'msgTime': '',
            'msgTimeZone': '+0300'
        }
        
        # Add headers to mimic browser
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/json',
            'Origin': 'https://yurticisms1.com',
            'Referer': 'https://yurticisms1.com/',
        }
        
        response = scraper.post(sms_url, json=sms_data, headers=headers)
        
        logger.info(f"SMS API Response Status: {response.status_code}")
        logger.info(f"SMS API Response Content: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                return {"success": True, "message": "SMS sent successfully", "api_response": result}
            except json.JSONDecodeError:
                if "success" in response.text.lower():
                    return {"success": True, "message": "SMS sent successfully"}
                return {"success": False, "error": "Invalid JSON response", "response": response.text}
        else:
            return {
                "success": False,
                "error": "SMS API error",
                "status": response.status_code,
                "details": response.text
            }
            
    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.route('/send_sms', methods=['POST'])
def handle_sms():
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
        
        # Format numbers to match requirements
        formatted_numbers = []
        for num in numbers:
            num = num.strip().replace(' ', '')
            if num.startswith('+90'):
                num = num[1:]
            elif not num.startswith('90'):
                num = '90' + num.lstrip('0')
            formatted_numbers.append(num)
            
        logger.info(f"Formatted numbers: {','.join(formatted_numbers)}")
        
        # Send SMS
        result = send_sms(message, formatted_numbers)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
