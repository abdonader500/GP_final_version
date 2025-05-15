from flask import Blueprint, request, jsonify, current_app
import os
import sys
import pandas as pd
import csv
from werkzeug.utils import secure_filename
from datetime import datetime
import subprocess
import threading
import time
import json
from app.models.database import init_db, insert_data, fetch_data, get_collection
from app.routes.auth import token_required, admin_required
import threading
from app.utils.process_data_pipeline import run_pipeline, get_pipeline_status

upload_bp = Blueprint('upload', __name__)

# Initialize process status
process_status = get_pipeline_status()

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

def append_to_collection(collection_name, new_records):
    """Append new records to existing collection instead of replacing data."""
    try:
        # Get collection
        collection = get_collection(collection_name)
        
        # Insert new records without dropping existing ones
        result = collection.insert_many(new_records)
        
        return len(result.inserted_ids)
    except Exception as e:
        print(f"❌ Error appending data to {collection_name}: {str(e)}")
        raise

def run_python_script_as_module(script_name, module_path):
    """Run Python script as a module to avoid import issues."""
    global process_status
    
    # Update status to processing
    process_status[script_name]["status"] = "processing"
    process_status[script_name]["message"] = "جاري المعالجة..."
    
    try:
        # Run the script as a module
        process = subprocess.Popen(
            [sys.executable, "-m", module_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            # Script executed successfully
            process_status[script_name]["status"] = "complete"
            process_status[script_name]["message"] = "تمت المعالجة بنجاح"
            print(f"✅ Script {script_name} completed successfully")
            print(f"Output: {stdout}")
            return True
        else:
            # Script execution failed
            process_status[script_name]["status"] = "error"
            process_status[script_name]["message"] = f"حدث خطأ: {stderr}"
            print(f"❌ Error running script {script_name}: {stderr}")
            return False
    except Exception as e:
        # Exception occurred
        process_status[script_name]["status"] = "error"
        process_status[script_name]["message"] = f"حدث خطأ: {str(e)}"
        print(f"❌ Exception running script {script_name}: {str(e)}")
        return False

def process_data_pipeline():
    """Run the data processing pipeline in sequence as modules."""
    # Define the module paths for each script
    script_modules = {
        "price_classification": "app.models.price_classification",
        "profit_optimizer": "app.models.profit_optimizer",
        "aggregate_historical_demand": "app.models.aggregate_historical_demand",
        "predict_demand_2025": "app.models.predict_demand_2025"
    }
    
    # Process in sequence - IMPORTANT: each script must complete before the next starts
    for script_name, module_path in script_modules.items():
        print(f"Starting script: {script_name} as module: {module_path}")
        success = run_python_script_as_module(script_name, module_path)
        
        # If a script fails, stop the pipeline
        if not success:
            print(f"Pipeline stopped at {script_name} due to errors.")
            break
        
        # Add a small delay between scripts to ensure database operations complete
        time.sleep(2)

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
        data_type = request.form.get('dataType', 'sales')  # Get data type (sales or purchases)
        
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
        current_app.config['LAST_UPLOADED_TYPE'] = data_type
        
        # Save to database (APPEND to the specified collection based on data_type)
        try:
            # Read data with pandas
            df = pd.read_csv(file_path, encoding='utf-8')
            
            # Convert to list of dictionaries
            records = df.to_dict(orient='records')
            
            # Initialize database
            init_db()
            
            # Determine collection name based on data type
            collection_name = "sales" if data_type == "sales" else "purchases"
            
            # Get existing data count
            existing_count = len(fetch_data(collection_name))
            
            # Append to collection instead of replacing
            inserted_count = append_to_collection(collection_name, records)
            
            print(f"✅ Data appended to {collection_name} collection: {inserted_count} new records added to {existing_count} existing records")
        except Exception as e:
            print(f"❌ Error saving data to database: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"حدث خطأ أثناء حفظ البيانات: {str(e)}"
            }), 500
        
        # Return success response
        return jsonify({
            "success": True,
            "message": f"تم رفع الملف بنجاح وإضافة {validation_result} سجل إلى قاعدة البيانات",
            "filename": filename,
            "rows_count": validation_result,
            "data_type": data_type
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
        # Check if a file was uploaded
        if not current_app.config.get('LAST_UPLOADED_FILE'):
            return jsonify({
                "success": False,
                "message": "لم يتم رفع أي ملف بعد"
            }), 400
        
        # Start the pipeline in a separate thread
        processing_thread = threading.Thread(target=run_pipeline)
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
        "processes": get_pipeline_status()
    }), 200

@upload_bp.route('/admin/collection-stats', methods=['GET'])
@token_required
@admin_required
def get_collection_stats():
    """Get stats about the collections (count of records)."""
    try:
        # Initialize database
        init_db()
        
        # Get counts
        sales_count = len(fetch_data("sales"))
        purchases_count = len(fetch_data("purchases"))
        
        return jsonify({
            "success": True,
            "stats": {
                "sales": sales_count,
                "purchases": purchases_count
            }
        }), 200
    except Exception as e:
        print(f"Error getting collection stats: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"حدث خطأ أثناء جلب إحصائيات البيانات: {str(e)}"
        }), 500