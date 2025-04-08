from flask import Blueprint, request, jsonify, Response
import json
import logging
from datetime import datetime
from app.models.demand_forecast.forecast_service import ForecastService
from app.models.database import fetch_data, get_collection, init_db

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('forecast_integration')

# Create Flask blueprint
forecast_bp = Blueprint('demand_forecasting', __name__)

# Initialize the forecast service
forecast_service = ForecastService()

@forecast_bp.route('/run-ai-forecast', methods=['POST'])
def run_ai_forecast():
    """
    API endpoint to run the AI-based demand forecasting workflow.
    This is a long-running task that trains models and generates forecasts.
    
    Returns:
        JSON response with the status of the request
    """
    try:
        # Initialize DB connection
        init_db()
        
        # Get request parameters
        data = request.get_json() or {}
        
        # Optional parameters
        train_models = data.get('train_models', True)
        generate_forecasts = data.get('generate_forecasts', True)
        save_to_mongodb = data.get('save_to_mongodb', True)
        forecast_horizon = data.get('forecast_horizon', 12)
        
        # Log request
        logger.info(f"Received request to run AI forecast: {data}")
        
        # Run the forecasting workflow (in background in production)
        results = forecast_service.run_forecasting_workflow(
            train_models=train_models,
            generate_forecasts=generate_forecasts,
            save_to_mongodb=save_to_mongodb,
            forecast_horizon=forecast_horizon
        )
        
        # Return success response
        return jsonify({
            "success": True,
            "message": "Demand forecasting process completed successfully",
            "completed_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"Error running AI forecast: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error running AI forecast: {str(e)}"
        }), 500

@forecast_bp.route('/get-forecast', methods=['GET'])
def get_forecast():
    """
    API endpoint to get forecast results for a category.
    
    Query parameters:
    - category: Category to get forecast for (optional)
    - year: Year to get forecast for (optional, defaults to 2025)
    - months: Comma-separated list of months to include (optional, defaults to all)
    
    Returns:
        JSON response with forecast data
    """
    try:
        # Get query parameters
        category = request.args.get('category')
        year = request.args.get('year', '2025')
        months_str = request.args.get('months')
        
        # Parse months if provided
        months = None
        if months_str:
            months = [int(m.strip()) for m in months_str.split(',')]
            
        # Build the query
        query = {"year": int(year)}
        
        if category:
            query["القسم"] = category
            
        if months:
            query["month"] = {"$in": months}
            
        # Fetch forecast data
        forecast_data = fetch_data("predicted_demand_2025", query=query, projection={"_id": 0})
        
        if not forecast_data:
            return jsonify({
                "success": False,
                "message": "No forecast data found for the specified parameters",
                "data": []
            }), 404
            
        # Return data
        return jsonify({
            "success": True,
            "message": "Forecast data retrieved successfully",
            "data": forecast_data
        })
        
    except Exception as e:
        logger.error(f"Error getting forecast data: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error getting forecast data: {str(e)}"
        }), 500

@forecast_bp.route('/get-item-forecast', methods=['GET'])
def get_item_forecast():
    """
    API endpoint to get item-level forecast results.
    
    Query parameters:
    - category: Category to get forecast for (optional)
    - specification: Product specification to get forecast for (optional)
    - year: Year to get forecast for (optional, defaults to 2025)
    - months: Comma-separated list of months to include (optional, defaults to all)
    
    Returns:
        JSON response with forecast data
    """
    try:
        # Get query parameters
        category = request.args.get('category')
        specification = request.args.get('specification')
        year = request.args.get('year', '2025')
        months_str = request.args.get('months')
        
        # Parse months if provided
        months = None
        if months_str:
            months = [int(m.strip()) for m in months_str.split(',')]
            
        # Build the query
        query = {"year": int(year)}
        
        if category:
            query["القسم"] = category
            
        if specification:
            query["product_specification"] = specification
            
        if months:
            query["month"] = {"$in": months}
            
        # Fetch forecast data
        forecast_data = fetch_data("predicted_item_demand_2025", query=query, projection={"_id": 0})
        
        if not forecast_data:
            return jsonify({
                "success": False,
                "message": "No item forecast data found for the specified parameters",
                "data": []
            }), 404
            
        # Return data
        return jsonify({
            "success": True,
            "message": "Item forecast data retrieved successfully",
            "data": forecast_data
        })
        
    except Exception as e:
        logger.error(f"Error getting item forecast data: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error getting item forecast data: {str(e)}"
        }), 500

@forecast_bp.route('/get-model-metrics', methods=['GET'])
def get_model_metrics():
    """
    API endpoint to get model evaluation metrics.
    
    Query parameters:
    - category: Category to get metrics for (optional)
    - model_type: Type of model to get metrics for (optional)
    
    Returns:
        JSON response with model metrics
    """
    try:
        # Get query parameters
        category = request.args.get('category')
        model_type = request.args.get('model_type')
        
        # Load model registry
        forecast_service.load_model_registry()
        
        # Get models filtered by parameters
        models = forecast_service.get_registered_models(
            category=category,
            model_type=model_type
        )
        
        if not models:
            return jsonify({
                "success": False,
                "message": "No models found for the specified parameters",
                "data": []
            }), 404
            
        # Return data
        return jsonify({
            "success": True,
            "message": "Model metrics retrieved successfully",
            "data": models
        })
        
    except Exception as e:
        logger.error(f"Error getting model metrics: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error getting model metrics: {str(e)}"
        }), 500

@forecast_bp.route('/get-forecast-comparison', methods=['GET'])
def get_forecast_comparison():
    """
    API endpoint to get a comparison of actual vs forecast values.
    
    Query parameters:
    - category: Category to get comparison for (required)
    - start_date: Start date for comparison (format: YYYY-MM-DD)
    - end_date: End date for comparison (format: YYYY-MM-DD)
    
    Returns:
        JSON response with comparison data
    """
    try:
        # Get query parameters
        category = request.args.get('category')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not category:
            return jsonify({
                "success": False,
                "message": "Category parameter is required",
                "data": []
            }), 400
            
        # Build the query for actual data
        actual_query = {}
        actual_query["القسم"] = category
        
        if start_date or end_date:
            actual_query["التاريخ"] = {}
            if start_date:
                actual_query["التاريخ"]["$gte"] = start_date
            if end_date:
                actual_query["التاريخ"]["$lte"] = end_date
            
        # Fetch actual data
        actual_data = fetch_data("category_monthly_demand", query=actual_query, projection={"_id": 0})
        
        # Build the query for forecast data
        forecast_query = {}
        forecast_query["القسم"] = category
        
        # Fetch forecast data (from the latest available forecast)
        forecast_data = fetch_data("predicted_demand_2025", query=forecast_query, projection={"_id": 0})
        
        if not actual_data and not forecast_data:
            return jsonify({
                "success": False,
                "message": "No data found for the specified parameters",
                "data": {
                    "actual": [],
                    "forecast": []
                }
            }), 404
            
        # Return data
        return jsonify({
            "success": True,
            "message": "Comparison data retrieved successfully",
            "data": {
                "actual": actual_data,
                "forecast": forecast_data
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting forecast comparison: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error getting forecast comparison: {str(e)}"
        }), 500

@forecast_bp.route('/get-seasonal-patterns', methods=['GET'])
def get_seasonal_patterns():
    """
    API endpoint to get seasonal patterns for a category.
    
    Query parameters:
    - category: Category to get patterns for (optional)
    
    Returns:
        JSON response with seasonal pattern data
    """
    try:
        # Get query parameters
        category = request.args.get('category')
        
        # Build the query
        query = {}
        if category:
            query["القسم"] = category
            
        # Fetch data from category_monthly_demand
        monthly_data = fetch_data("category_monthly_demand", query=query, projection={"_id": 0})
        
        if not monthly_data:
            return jsonify({
                "success": False,
                "message": "No monthly data found for the specified parameters",
                "data": []
            }), 404
            
        # Process data to extract seasonal patterns
        # Group by month across all years
        monthly_totals = {}
        for record in monthly_data:
            month = record.get('month')
            quantity = record.get('total_quantity', 0)
            
            if month not in monthly_totals:
                monthly_totals[month] = []
                
            monthly_totals[month].append(quantity)
            
        # Calculate average for each month
        seasonal_patterns = []
        for month, quantities in monthly_totals.items():
            avg_quantity = sum(quantities) / len(quantities)
            seasonal_patterns.append({
                "month": month,
                "average_quantity": avg_quantity
            })
            
        # Sort by month
        seasonal_patterns.sort(key=lambda x: x['month'])
        
        # Return data
        return jsonify({
            "success": True,
            "message": "Seasonal patterns retrieved successfully",
            "data": seasonal_patterns
        })
        
    except Exception as e:
        logger.error(f"Error getting seasonal patterns: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error getting seasonal patterns: {str(e)}"
        }), 500
@forecast_bp.route('/api/demand-forecasting/run-ai-forecast', methods=['POST'])
def run_ai_forecast_api():
    """Alias for run-ai-forecast for API compatibility."""
    return ForecastService.run_ai_forecast()

@forecast_bp.route('/api/demand-forecasting/get-forecast', methods=['GET'])
def get_forecast_api():
    """Alias for get-forecast for API compatibility."""
    return get_forecast()

@forecast_bp.route('/api/demand-forecasting/get-item-forecast', methods=['GET'])
def get_item_forecast_api():
    """Alias for get-item-forecast for API compatibility."""
    return get_item_forecast()