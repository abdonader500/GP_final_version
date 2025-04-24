from flask import Blueprint, request, jsonify, current_app
import os
import pandas as pd
import csv
from werkzeug.utils import secure_filename
from datetime import datetime
import subprocess
import threading
import time
import json
from app.models.database import init_db, insert_data
from app.routes.auth import token_required, admin_required

upload_bp = Blueprint('upload', __name__)

# Initialize process status
process_status = {
    "price_classification": {"status": "pending", "message": ""},
    "profit_optimizer": {"status": "pending", "message": ""},
    "aggregate_historical_demand": {"status": "pending", "message": ""},
    "predict_demand_2025": {"status": "pending", "message": ""}
}

# Required columns for validation
REQUIRED_COLUMNS = [
    'التاريخ', 'باركود', 'اسم الصنف', 'المورد', 'القسم', 
    'سعر المستهلك', 'الكمية', 'الرصيد', 'القيمة', 
    'الخصم', 'الصافي', 'سعر الجملة', 'الربح', 'نسبة الربح'
]

def validate_csv(file_path):
    """Validate CSV file structure against required columns."""
    try:
        # First, detect the delimiter
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            dialect = csv.Sniffer().sniff(csvfile.read(4096))
            delimiter = dialect.delimiter
        
        # Read the CSV file with proper encoding
        df = pd.read_csv(file_path, delimiter=delimiter, encoding='utf-8')
        
        # Check if all required columns are present
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        
        if missing_columns:
            return False, f"الأعمدة التالية مفقودة: {', '.join(missing_columns)}"
        
        # Check if there are any rows in the file
        if len(df) == 0:
            return False, "الملف لا يحتوي على أي بيانات"
        
        # Additional validation can be added here
        
        return True, len(df)
    except Exception as e:
        return False, f"خطأ في التحقق من الملف: {str(e)}"

def run_processing_script(script_name, script_path):
    """Run data processing script and update status."""
    global process_status
    
    # Update status to processing
    process_status[script_name]["status"] = "processing"
    process_status[script_name]["message"] = "جاري المعالجة..."
    
    try:
        # Run the script
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Update status to complete
        process_status[script_name]["status"] = "complete"
        process_status[script_name]["message"] = "تمت المعالجة بنجاح"
        
        # Log output
        print(f"Script {script_name} completed: {result.stdout}")
        
        return True
    except subprocess.CalledProcessError as e:
        # Update status to error
        process_status[script_name]["status"] = "error"
        process_status[script_name]["message"] = f"حدث خطأ: {e.stderr}"
        
        # Log error
        print(f"Error running script {script_name}: {e.stderr}")
        
        return False
    except Exception as e:
        # Update status to error
        process_status[script_name]["status"] = "error"
        process_status[script_name]["message"] = f"حدث خطأ: {str(e)}"
        
        # Log error
        print(f"Exception running script {script_name}: {str(e)}")
        
        return False

def process_data_pipeline():
    """Run the data processing pipeline in sequence."""
    # Get paths to scripts
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scripts = {
        "price_classification": os.path.join(base_path, "models", "price_classification.py"),
        "profit_optimizer": os.path.join(base_path, "models", "profit_optimizer.py"),
        "aggregate_historical_demand": os.path.join(base_path, "models", "aggregate_historical_demand.py"),
        "predict_demand_2025": os.path.join(base_path, "models", "predict_demand_2025.py")
    }
    
    # Process in sequence
    for script_name, script_path in scripts.items():
        success = run_processing_script(script_name, script_path)
        
        # If a script fails, stop the pipeline
        if not success:
            print(f"Pipeline stopped at {script_name} due to errors.")
            break

@upload_bp.route('/admin/upload-data', methods=['POST'])
@token_required
@admin_required
def upload_data():
    """Handle file upload and validate it."""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "message": "لم يتم إرسال أي ملف"
            }), 400
        
        file = request.files['file']
        
        # Check if file is empty
        if file.filename == '':
            return jsonify({
                "success": False,
                "message": "لم يتم اختيار أي ملف"
            }), 400
        
        # Check file extension
        if not file.filename.endswith('.csv'):
            return jsonify({
                "success": False,
                "message": "يجب أن يكون الملف بتنسيق CSV"
            }), 400
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(current_app.root_path, 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        # Save with timestamp to avoid filename conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{secure_filename(file.filename)}"
        file_path = os.path.join(upload_dir, filename)
        
        # Save file
        file.save(file_path)
        
        # Validate CSV structure
        is_valid, validation_result = validate_csv(file_path)
        
        if not is_valid:
            # Remove invalid file
            os.remove(file_path)
            
            return jsonify({
                "success": False,
                "message": validation_result
            }), 400
        
        # If valid, save path to file for processing
        current_app.config['LAST_UPLOADED_FILE'] = file_path
        
        # Save to database (directly into 'sales' collection)
        try:
            # Read data with pandas
            df = pd.read_csv(file_path, encoding='utf-8')
            
            # Convert to list of dictionaries
            records = df.to_dict(orient='records')
            
            # Initialize database
            init_db()
            
            # Insert into 'sales' collection (this will replace existing data)
            insert_data("sales", records)
            
            print(f"✅ Data uploaded to sales collection: {len(records)} records")
        except Exception as e:
            print(f"❌ Error saving data to database: {str(e)}")
            # Continue process even if database insertion fails
        
        # Return success response
        return jsonify({
            "success": True,
            "message": "تم رفع الملف بنجاح والتحقق من صحته",
            "filename": filename,
            "rows_count": validation_result
        }), 200
        
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"حدث خطأ أثناء رفع الملف: {str(e)}"
        }), 500

@upload_bp.route('/admin/process-data', methods=['POST'])
@token_required
@admin_required
def process_data():
    """Start the data processing pipeline."""
    try:
        # Reset process status
        global process_status
        process_status = {
            "price_classification": {"status": "pending", "message": ""},
            "profit_optimizer": {"status": "pending", "message": ""},
            "aggregate_historical_demand": {"status": "pending", "message": ""},
            "predict_demand_2025": {"status": "pending", "message": ""}
        }
        
        # Check if a file was uploaded
        if not current_app.config.get('LAST_UPLOADED_FILE'):
            return jsonify({
                "success": False,
                "message": "لم يتم رفع أي ملف بعد"
            }), 400
        
        # Start processing in a separate thread
        processing_thread = threading.Thread(target=process_data_pipeline)
        processing_thread.daemon = True
        processing_thread.start()
        
        return jsonify({
            "success": True,
            "message": "بدأت معالجة البيانات"
        }), 200
        
    except Exception as e:
        print(f"Error starting data processing: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"حدث خطأ أثناء بدء معالجة البيانات: {str(e)}"
        }), 500

@upload_bp.route('/admin/process-status', methods=['GET'])
@token_required
@admin_required
def get_process_status():
    """Get the current status of the data processing pipeline."""
    return jsonify({
        "success": True,
        "processes": process_status
    }), 200