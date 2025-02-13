from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import pandas as pd
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import os

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def send_sms_via_web(message, numbers):
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Initialize Chrome driver with webdriver-manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    wait = WebDriverWait(driver, 20)
    
    try:
        # Go to login page
        logger.info("Navigating to login page")
        driver.get('https://yurticisms1.com/login')
        
        # Login
        logger.info("Attempting to login")
        username = wait.until(EC.presence_of_element_located((By.NAME, 'username')))
        password = wait.until(EC.presence_of_element_located((By.NAME, 'password')))
        submit = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[type="submit"]')))
        
        username.send_keys('user')
        password.send_keys('Tr**ys^4e')
        submit.click()
        
        # Wait for login to complete and navigate to SMS page
        time.sleep(2)
        logger.info("Navigating to SMS page")
        driver.get('https://yurticisms1.com/sms/send')
        
        # Fill in SMS form
        logger.info("Filling SMS form")
        message_field = wait.until(EC.presence_of_element_located((By.NAME, 'message')))
        numbers_field = wait.until(EC.presence_of_element_located((By.NAME, 'numbers')))
        
        message_field.send_keys(message)
        numbers_field.send_keys('\n'.join(numbers))
        
        # Try to select Turkish encoding if available
        try:
            encoding = wait.until(EC.presence_of_element_located((By.NAME, 'encoding')))
            encoding.send_keys('turkish')
        except:
            logger.warning("Could not set Turkish encoding")
        
        # Submit form
        logger.info("Submitting form")
        submit = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[type="submit"]')))
        submit.click()
        
        # Wait for response
        time.sleep(2)
        
        # Check for success/error messages
        try:
            success = driver.find_element(By.CLASS_NAME, 'alert-success')
            if success:
                logger.info(f"Success: {success.text}")
                return {"success": True, "message": success.text}
        except:
            pass
            
        try:
            error = driver.find_element(By.CLASS_NAME, 'alert-danger')
            if error:
                logger.error(f"Error: {error.text}")
                return {"success": False, "error": error.text}
        except:
            pass
        
        logger.info("SMS sent successfully")
        return {"success": True, "message": "SMS sent successfully"}
        
    except Exception as e:
        logger.error(f"Error in web automation: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        driver.quit()

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
        
        # Send SMS using web automation
        result = send_sms_via_web(message, formatted_numbers)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
