from flask import Blueprint, request, jsonify
from app.models.profit_optimizer import classify_price_level, load_profit_model
from app.models.database import get_collection, init_db
from datetime import datetime

price_analysis_bp = Blueprint('price_analysis', __name__)

# Inflation rates based on general inflation data for Egypt
INFLATION_RATES = {
    2024: 0.145   # 14.5% from 2024 to 2025 (example; replace with actual/projected rate)
}
BASE_YEAR = 2024

def reverse_inflation(price, current_year):
    """Adjust price from current_year to BASE_YEAR (2024) using reverse inflation."""
    if current_year == BASE_YEAR:
        return price
    cumulative_factor = 1.0
    for y in range(BASE_YEAR, current_year):
        cumulative_factor *= (1 + INFLATION_RATES.get(y, 0))
    return price / cumulative_factor

@price_analysis_bp.route('/get-optimal-profit', methods=['POST'])
def get_optimal_profit():
    init_db()
    data = request.get_json()
    category = data.get('category')
    product_specification = data.get('product_specification')
    purchase_price = float(data.get('purchase_price'))

    if not all([category, product_specification, purchase_price]):
        return jsonify({"error": "Missing required fields"}), 400

    # Adjust 2025 price to 2024 equivalent
    current_year = datetime.now().year  # Assuming 2025 as current year
    adjusted_price = reverse_inflation(purchase_price, current_year)

    # Fetch price ranges for 2024
    price_ranges_collection = get_collection("price_ranges")
    price_range = price_ranges_collection.find_one({
        "category": category,
        "product_specification": product_specification,
        "year": str(BASE_YEAR)
    })

    # Fallback: Use "غير محدد" specification if specific one not found
    if not price_range:
        price_range = price_ranges_collection.find_one({
            "category": category,
            "product_specification": "غير محدد",
            "year": str(BASE_YEAR)
        })
        if not price_range:
            return jsonify({"error": "No price range found for the given category, even with fallback"}), 404

    # Classify price level with linear interpolation
    price_ranges = {
        "low": price_range["low"],
        "moderate": price_range["moderate"],
        "high": price_range["high"]
    }
    
    # Get both price level and interpolation data
    classified_price_level, interpolation_data = classify_price_level(adjusted_price, price_ranges, return_interpolation=True)

    # Check profit_models for a matching category and product_specification
    models_collection = get_collection("profit_models")
    profit_model = models_collection.find_one({
        "category": category,
        "product_specification": product_specification
    })

    if not profit_model:
        # Fallback to generic product specification
        profit_model = models_collection.find_one({
            "category": category,
            "product_specification": "غير محدد"
        })
        
        if not profit_model:
            return jsonify({"error": "No profit model found for the given category and specification"}), 404

    # Load optimal profit percentage with linear scaling
    optimal_profit_percentage = load_profit_model(
        category, 
        product_specification, 
        classified_price_level,
        interpolation_data
    )

    # Create response
    response_data = {
        "category": category,
        "product_specification": product_specification,
        "original_price": purchase_price,
        "adjusted_price": adjusted_price,
        "classified_price_level": classified_price_level,
        "optimal_profit_percentage": optimal_profit_percentage,
    }
    
    # Add debugging information about price ranges and interpolation if present
    if interpolation_data and interpolation_data["adjacent_level"]:
        response_data["price_ranges"] = {
            "low_threshold": price_range["low"],
            "moderate_threshold": price_range["moderate"],
            "high_threshold": price_range["high"]
        }
        
        response_data["interpolation"] = {
            "base_level": interpolation_data["base_level"],
            "adjacent_level": interpolation_data["adjacent_level"],
            "position_ratio": round(interpolation_data["interpolation_factor"], 4)
        }
        
        # Add profit percentages for both levels from the model
        if profit_model:
            base_profit = profit_model.get(interpolation_data["base_level"], 0)
            adjacent_profit = profit_model.get(interpolation_data["adjacent_level"], 0)
            response_data["interpolation"]["base_profit"] = base_profit
            response_data["interpolation"]["adjacent_profit"] = adjacent_profit
    
    return jsonify(response_data)