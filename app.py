from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import json
import logging

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
    return render_template('index.html')

@app.route('/send_sms', methods=['POST'])
def send_sms():
    try:
        # Get form data
        message = request.form.get('message', '')
        file = request.files.get('number_file')
        manual_numbers = request.form.get('manual_numbers', '')
        
        numbers = []
        
        # Process manual numbers
        if manual_numbers:
            numbers.extend([num.strip() for num in manual_numbers.split('\n') if num.strip()])
        
        # Process file if uploaded
        if file:
            if file.filename.endswith('.txt'):
                numbers.extend([num.strip() for num in file.read().decode('utf-8').splitlines() if num.strip()])
            elif file.filename.endswith(('.xlsx', '.xls')):
                import pandas as pd
                df = pd.read_excel(file)
                numbers.extend([str(num).strip() for num in df.iloc[:, 0].tolist() if str(num).strip()])
        
        if not numbers:
            return jsonify({"error": "No valid phone numbers provided"}), 400

        # Format phone numbers
        formatted_numbers = []
        for num in numbers:
            # Remove any non-digit characters
            num = ''.join(filter(str.isdigit, num))
            # If number starts with 0, remove it
            if num.startswith('0'):
                num = num[1:]
            # If number doesn't start with 90, add it
            if not num.startswith('90'):
                num = '90' + num
            formatted_numbers.append(num)

        # Convert to comma-separated string
        numbers_str = ','.join(formatted_numbers)
        
        # Prepare form data exactly as the API expects
        data = {
            'username': SMS_API_CONFIG['USERNAME'],
            'password': SMS_API_CONFIG['PASSWORD'],
            'message': message,
            'numbers': numbers_str,
            'datacoding': 'turkish'
        }
        
        # Make the request with minimal headers
        response = requests.post(
            SMS_API_CONFIG['API_URL'],
            data=data,
            timeout=30
        )
        
        print(f"Request URL: {SMS_API_CONFIG['API_URL']}")
        print(f"Request Data: {data}")
        print(f"Response Status: {response.status_code}")
        print(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            try:
                return jsonify(response.json()), 200
            except json.JSONDecodeError:
                return jsonify({"success": True, "message": response.text}), 200
        else:
            return jsonify({
                "error": "SMS API error",
                "status": response.status_code,
                "details": response.text
            }), response.status_code
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
