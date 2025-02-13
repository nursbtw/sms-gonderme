from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import json
import logging
import traceback
import urllib3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# SMS API Configuration
SMS_API_CONFIG = {
    'API_URL': 'https://yurticisms1.com/sms_api',
    'USERNAME': 'user',
    'PASSWORD': 'Tr**ys^4e',
    'DATACODING': 'turkish'
}

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    return webdriver.Chrome(options=chrome_options)

def send_sms_via_selenium(message, numbers):
    try:
        driver = setup_driver()
        logger.info("Selenium driver initialized")
        
        # Navigate to the login page
        driver.get('https://yurticisms1.com/')
        logger.info("Navigated to website")
        
        # Login
        try:
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_field = driver.find_element(By.NAME, "password")
            
            username_field.send_keys(SMS_API_CONFIG['USERNAME'])
            password_field.send_keys(SMS_API_CONFIG['PASSWORD'])
            password_field.submit()
            logger.info("Login form submitted")
            
            # Wait for login to complete
            time.sleep(2)
            
            # Navigate to SMS sending page
            driver.get('https://yurticisms1.com/sms_api')
            logger.info("Navigated to SMS API page")
            
            # Fill in the SMS form
            message_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "message"))
            )
            numbers_field = driver.find_element(By.NAME, "numbers")
            
            message_field.send_keys(message)
            numbers_field.send_keys(numbers)
            
            # Submit the form
            message_field.submit()
            logger.info("SMS form submitted")
            
            # Wait for response
            time.sleep(2)
            
            # Get response
            response_text = driver.page_source
            logger.info(f"Response received: {response_text}")
            
            return {"success": True, "message": "SMS sent successfully"}
            
        except Exception as e:
            logger.error(f"Error during Selenium operation: {str(e)}")
            logger.error(traceback.format_exc())
            return {"error": str(e)}
            
        finally:
            driver.quit()
            logger.info("Selenium driver closed")
            
    except Exception as e:
        logger.error(f"Error setting up Selenium: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

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
        
        # Send SMS using Selenium
        result = send_sms_via_selenium(message, numbers_str)
        
        if "error" in result:
            return jsonify({"error": "SMS gönderimi başarısız", "details": result["error"]}), 500
        
        return jsonify(result), 200
            
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
