from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import json
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all origins temporarily for testing

# SMS API Configuration
SMS_API_CONFIG = {
    'API_URL': 'https://yurticisms1.com/sms_api',
    'USERNAME': 'user',  # Replace with your actual username
    'PASSWORD': 'Tr**ys^4e',  # Replace with your actual password
    'DATACODING': 'turkish'
}

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
        
        # Get form data
        message = request.form.get('message', '')
        file = request.files.get('number_file')
        manual_numbers = request.form.get('manual_numbers', '')
        
        logger.debug(f"Message: {message}")
        logger.debug(f"Manual numbers: {manual_numbers}")
        logger.debug(f"File uploaded: {bool(file)}")
        
        numbers = []
        
        # Process manual numbers
        if manual_numbers:
            numbers.extend([num.strip() for num in manual_numbers.split('\n') if num.strip()])
        
        # Process file if uploaded
        if file:
            try:
                if file.filename.endswith('.txt'):
                    numbers.extend([num.strip() for num in file.read().decode('utf-8').splitlines() if num.strip()])
                elif file.filename.endswith(('.xlsx', '.xls')):
                    import pandas as pd
                    df = pd.read_excel(file)
                    numbers.extend([str(num).strip() for num in df.iloc[:, 0].tolist() if str(num).strip()])
            except Exception as e:
                logger.error(f"Error processing file: {str(e)}")
                logger.error(traceback.format_exc())
                return jsonify({
                    "error": "Dosya işlenirken bir hata oluştu",
                    "details": str(e)
                }), 400
        
        if not numbers:
            return jsonify({"error": "Geçerli telefon numarası bulunamadı"}), 400

        logger.info(f"Processing {len(numbers)} numbers")

        # Format phone numbers
        formatted_numbers = []
        for num in numbers:
            try:
                # Remove any non-digit characters
                num = ''.join(filter(str.isdigit, num))
                # If number starts with 0, remove it
                if num.startswith('0'):
                    num = num[1:]
                # If number doesn't start with 90, add it
                if not num.startswith('90'):
                    num = '90' + num
                formatted_numbers.append(num)
            except Exception as e:
                logger.error(f"Error formatting number {num}: {str(e)}")
                continue

        # Convert to comma-separated string
        numbers_str = ','.join(formatted_numbers)
        
        logger.info(f"Formatted numbers: {numbers_str}")
        
        # Prepare form data exactly as the API expects
        data = {
            'username': SMS_API_CONFIG['USERNAME'],
            'password': SMS_API_CONFIG['PASSWORD'],
            'message': message,
            'numbers': numbers_str,
            'datacoding': 'turkish'
        }
        
        logger.info("Sending request to SMS API")
        
        # Make the request with minimal headers
        response = requests.post(
            SMS_API_CONFIG['API_URL'],
            data=data,
            timeout=30
        )
        
        logger.info(f"API Response - Status: {response.status_code}")
        logger.info(f"API Response - Content: {response.text}")
        
        if response.status_code == 200:
            try:
                return jsonify(response.json()), 200
            except json.JSONDecodeError:
                return jsonify({"success": True, "message": response.text}), 200
        else:
            error_msg = {
                "error": "SMS API hatası",
                "status": response.status_code,
                "details": response.text
            }
            logger.error(f"API Error: {error_msg}")
            return jsonify(error_msg), response.status_code
            
    except Exception as e:
        error_msg = {
            "error": "Bir hata oluştu",
            "details": str(e),
            "trace": traceback.format_exc()
        }
        logger.error(f"Unexpected error: {error_msg}")
        return jsonify(error_msg), 500

if __name__ == '__main__':
    app.run(debug=True)
