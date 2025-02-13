from flask import Flask, render_template, request, jsonify
import os
import requests
import json
import logging
from datetime import datetime

# Configure logging to console and file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sms_sender.log'),
        logging.StreamHandler()
    ]
)

# Create Flask app
app = Flask(__name__)
app.debug = True

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'xlsx', 'xls'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create reports directory if it doesn't exist
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)

# Import config after app creation
try:
    from config import SMS_API_CONFIG
    logging.info("Successfully loaded SMS_API_CONFIG")
except ImportError as e:
    logging.error(f"Failed to load config: {e}")
    SMS_API_CONFIG = {
        'API_URL': 'https://yurticisms1.com/sms_api',
        'USERNAME': 'user',
        'PASSWORD': 'Tr**ys^4e',
        'DATACODING': 'turkish'
    }

def validate_phone_number(number):
    # Remove any non-digit characters
    clean_number = ''.join(filter(str.isdigit, number))
    
    # Check if the cleaned number is valid
    if len(clean_number) < 10 or len(clean_number) > 12:
        return False, f"Geçersiz numara uzunluğu: {number}"
    
    return True, clean_number

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_numbers_from_file(file):
    invalid_numbers = []
    valid_numbers = []
    
    try:
        if file.filename.endswith('.txt'):
            # Read TXT file
            numbers = file.read().decode('utf-8').splitlines()
            for num in numbers:
                num = num.strip()
                if num:
                    is_valid, result = validate_phone_number(num)
                    if is_valid:
                        valid_numbers.append(result)
                    else:
                        invalid_numbers.append(result)
        elif file.filename.endswith(('.xlsx', '.xls')):
            try:
                import pandas as pd
                logging.info("Successfully imported pandas")
                
                # Save the uploaded file temporarily
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp.xlsx')
                file.save(temp_path)
                logging.info(f"Saved temp file to {temp_path}")
                
                try:
                    # Read Excel file with explicit engine
                    df = pd.read_excel(temp_path, engine='openpyxl')
                    logging.info("Successfully read Excel file")
                    
                    # Get numbers from the first column
                    numbers = df.iloc[:, 0].astype(str).tolist()
                    
                    for num in numbers:
                        num = str(num).strip()
                        if num and num.lower() != 'nan' and num.lower() != 'telefon':
                            is_valid, result = validate_phone_number(num)
                            if is_valid:
                                valid_numbers.append(result)
                            else:
                                invalid_numbers.append(result)
                finally:
                    # Always try to remove the temp file
                    try:
                        os.remove(temp_path)
                        logging.info("Removed temp file")
                    except Exception as e:
                        logging.error(f"Error removing temp file: {e}")
                
            except ImportError as e:
                logging.error(f"Pandas import error: {e}")
                raise Exception("Excel dosyalarını okumak için pandas kütüphanesi gerekli.")
            except Exception as e:
                logging.error(f"Excel reading error: {e}")
                raise Exception(f"Excel dosyası okuma hatası: {str(e)}")
    except Exception as e:
        logging.error(f"File reading error: {e}")
        raise
    
    return valid_numbers, invalid_numbers

def format_phone_number(number):
    # Remove any non-digit characters
    number = ''.join(filter(str.isdigit, number))
    
    # If number starts with 0, remove it
    if number.startswith('0'):
        number = number[1:]
    
    # If number doesn't start with 90, add it
    if not number.startswith('90'):
        number = '90' + number
    
    return number

def send_sms_batch(numbers, message):
    # Format phone numbers
    formatted_numbers = [format_phone_number(num) for num in numbers]
    
    payload = {
        "Username": SMS_API_CONFIG['USERNAME'],
        "Password": SMS_API_CONFIG['PASSWORD'],
        "DataCoding": SMS_API_CONFIG['DATACODING'],
        "Text": message,
        "To": formatted_numbers
    }
    
    try:
        logging.info(f"Sending SMS request to {SMS_API_CONFIG['API_URL']}")
        response = requests.post(
            SMS_API_CONFIG['API_URL'],
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        # Log the request and response
        logging.info(f"SMS Request - Numbers: {formatted_numbers}, Message: {message}")
        logging.info(f"API Response: {response.text}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"API Error: {str(e)}")
        return {"Status": "Error", "Message": str(e)}

def get_sms_report(message_id):
    payload = {
        "Username": SMS_API_CONFIG['USERNAME'],
        "Password": SMS_API_CONFIG['PASSWORD'],
        "MessageId": message_id
    }
    
    try:
        response = requests.post(
            f"{SMS_API_CONFIG['API_URL']}/report",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Report API Error: {str(e)}")
        return {"Status": "Error", "Message": str(e)}

def save_report(message_id, numbers, message, report=None):
    """Save a report to the reports directory"""
    report_data = {
        'message_id': message_id,
        'numbers': numbers,
        'message': message,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'statuses': report['Response']['Report']['List'] if report and 'Response' in report else []
    }
    
    report_file = os.path.join(REPORTS_DIR, f'{message_id}.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

def get_previous_reports(limit=50):
    """Get previous reports from the reports directory"""
    reports = []
    try:
        report_files = sorted(
            [f for f in os.listdir(REPORTS_DIR) if f.endswith('.json')],
            key=lambda x: os.path.getmtime(os.path.join(REPORTS_DIR, x)),
            reverse=True
        )[:limit]
        
        for report_file in report_files:
            try:
                with open(os.path.join(REPORTS_DIR, report_file), 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                    reports.append(report_data)
            except Exception as e:
                logging.error(f"Error reading report file {report_file}: {e}")
                continue
    except Exception as e:
        logging.error(f"Error listing report files: {e}")
    
    return reports

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_sms', methods=['POST'])
def send_sms():
    message = request.form.get('message', '')
    file = request.files.get('number_file')
    manual_numbers = request.form.get('manual_numbers', '')
    
    if not message:
        return jsonify({
            'status': 'error',
            'message': 'Mesaj boş olamaz'
        })
    
    try:
        numbers = []
        invalid_numbers = []

        # Process manual numbers if provided
        if manual_numbers:
            manual_numbers_list = [num.strip() for num in manual_numbers.split('\n') if num.strip()]
            for num in manual_numbers_list:
                is_valid, result = validate_phone_number(num)
                if is_valid:
                    numbers.append(result)
                else:
                    invalid_numbers.append(result)
        
        # Process file if provided
        if file and allowed_file(file.filename):
            file_numbers, file_invalid = read_numbers_from_file(file)
            numbers.extend(file_numbers)
            invalid_numbers.extend(file_invalid)
        
        if not numbers and not manual_numbers and not file:
            return jsonify({
                'status': 'error',
                'message': 'Lütfen en az bir telefon numarası girin veya dosya yükleyin'
            })
        
        if not numbers:
            return jsonify({
                'status': 'error',
                'message': 'Geçerli telefon numarası bulunamadı'
            })
        
        # Remove duplicates while preserving order
        numbers = list(dict.fromkeys(numbers))
        
        # Log the attempt
        logging.info(f"Sending SMS - Valid Numbers: {len(numbers)}, Invalid Numbers: {len(invalid_numbers)}")
        
        # Send SMS
        result = send_sms_batch(numbers, message)
        
        if result.get('Status') == 'OK':
            message_id = result.get('MessageId')
            # Save the report
            save_report(message_id, numbers, message, result.get('report'))
            
            return jsonify({
                'status': 'success',
                'message_id': message_id,
                'numbers': numbers,
                'message': message,
                'report': result.get('report', {}),
                'invalid_numbers': invalid_numbers
            })
        else:
            error_msg = result.get('Message', 'SMS gönderilemedi')
            logging.error(f"SMS sending failed: {error_msg}")
            return jsonify({
                'status': 'error',
                'message': error_msg
            })
            
    except Exception as e:
        logging.error(f"Error in send_sms: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Bir hata oluştu: {str(e)}'
        })

@app.route('/get_previous_reports', methods=['GET'])
def get_reports():
    """Endpoint to get previous SMS reports"""
    try:
        reports = get_previous_reports()
        return jsonify({
            'status': 'success',
            'reports': reports
        })
    except Exception as e:
        logging.error(f"Error getting previous reports: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/check_status/<message_id>')
def check_status(message_id):
    try:
        report = get_sms_report(message_id)
        
        # Update stored report with new status
        report_file = os.path.join(REPORTS_DIR, f'{message_id}.json')
        if os.path.exists(report_file):
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    stored_report = json.load(f)
                stored_report['statuses'] = report['Response']['Report']['List']
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(stored_report, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logging.error(f"Error updating report file {message_id}: {e}")
        
        return jsonify(report)
    except Exception as e:
        logging.error(f"Error checking status: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    logging.info("Starting Flask application...")
    app.run(debug=True, use_reloader=True) 