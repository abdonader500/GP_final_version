"""
Data Processing Pipeline Script

This script orchestrates the execution of data processing steps in the correct sequence:
1. price_classification.py - Classifies pricing data
2. profit_optimizer.py - Optimizes profit models
3. aggregate_historical_demand.py - Aggregates historical demand data
4. predict_demand_2025.py - Predicts demand for 2025

Each step will only proceed if the previous step completed successfully.
"""

import os
import sys
import importlib.util
import time
import logging
from datetime import datetime

# Add the project root directory to the Python path
# This ensures we can import app modules regardless of where this script is run from
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging
log_dir = os.path.join(project_root, "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

# Status dictionary that will be updated and can be accessed by the API
process_status = {
    "price_classification": {"status": "pending", "message": "Waiting to start"},
    "profit_optimizer": {"status": "pending", "message": "Waiting to start"},
    "aggregate_historical_demand": {"status": "pending", "message": "Waiting to start"},
    "predict_demand_2025": {"status": "pending", "message": "Waiting to start"}
}

def load_module_by_path(file_path):
    """Load a Python module directly from a file path."""
    module_name = os.path.basename(file_path).replace('.py', '')
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run_module(module_name, module_path):
    """
    Runs a Python module and updates its status in the process_status dictionary.
    
    Args:
        module_name: Name of the process in the status dictionary
        module_path: Import path for the module
        
    Returns:
        bool: True if the module executed successfully, False otherwise
    """
    logging.info(f"Starting module: {module_name}")
    
    # Update status to processing
    process_status[module_name]["status"] = "processing"
    process_status[module_name]["message"] = "جاري المعالجة..."
    
    try:
        start_time = time.time()
        
        # Convert module path to file path
        module_name_only = module_path.split('.')[-1]
        module_file_path = os.path.join(project_root, 'app', 'models', f"{module_name_only}.py")
        
        if not os.path.exists(module_file_path):
            raise FileNotFoundError(f"Could not find module file at {module_file_path}")
        
        logging.info(f"Loading module from file: {module_file_path}")
        
        # Execute the specific function based on the module name
        if module_name == "price_classification":
            # Import the price_classification module
            module = load_module_by_path(module_file_path)
            # Call the classify_price_levels function
            module.classify_price_levels()
            
        elif module_name == "profit_optimizer":
            # Import the profit_optimizer module
            module = load_module_by_path(module_file_path)
            # Call the train_profit_models function
            module.train_profit_models()
            
        elif module_name == "aggregate_historical_demand":
            # Import the aggregate_historical_demand module
            module = load_module_by_path(module_file_path)
            # Call the aggregate_historical_demand function
            module.aggregate_historical_demand()
            
        elif module_name == "predict_demand_2025":
            # Import the predict_demand_2025 module
            module = load_module_by_path(module_file_path)
            # Call the predict_demand_2025 function
            module.predict_demand_2025()
            
        else:
            raise ValueError(f"Unknown module name: {module_name}")
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Update status to complete
        process_status[module_name]["status"] = "complete"
        process_status[module_name]["message"] = f"تمت المعالجة بنجاح في {elapsed_time:.2f} ثانية"
        
        logging.info(f"Module {module_name} completed successfully in {elapsed_time:.2f} seconds")
        return True
        
    except Exception as e:
        # Update status to error
        process_status[module_name]["status"] = "error"
        process_status[module_name]["message"] = f"فشل في المعالجة: {str(e)}"
        
        logging.error(f"Error in module {module_name}: {str(e)}")
        logging.exception("Exception details:")
        return False

def run_pipeline():
    """
    Runs the full data processing pipeline in sequence.
    Each step only runs if the previous step was successful.
    """
    logging.info("Starting data processing pipeline")
    
    # Define the module paths and execution order
    pipeline_steps = [
        ("price_classification", "app.models.price_classification"),
        ("profit_optimizer", "app.models.profit_optimizer"),
        ("aggregate_historical_demand", "app.models.aggregate_historical_demand"),
        ("predict_demand_2025", "app.models.predict_demand_2025")
    ]
    
    for step_name, module_path in pipeline_steps:
        # Run the module
        success = run_module(step_name, module_path)
        
        # If the module failed, stop the pipeline
        if not success:
            logging.error(f"Pipeline stopped at {step_name} due to errors")
            return False
        
        # Small delay between steps to ensure database operations complete
        time.sleep(2)
    
    logging.info("Pipeline completed successfully")
    return True

def get_pipeline_status():
    """Returns the current status of all pipeline steps."""
    return process_status

if __name__ == "__main__":
    try:
        # Run the pipeline
        run_pipeline()
    except Exception as e:
        logging.error(f"Unhandled error in pipeline: {str(e)}")
        logging.exception("Exception details:")
        sys.exit(1)