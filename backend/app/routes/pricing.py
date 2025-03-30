# app/routes/pricing.py
from flask import Blueprint, jsonify, request
from app.models.database import fetch_data
from app.models.profit_optimizer import classify_price_level, load_profit_model

pricing_bp = Blueprint('pricing', __name__)

@pricing_bp.route('/api/price-analysis/get-optimal-profit', methods=['POST'])
def get_optimal_profit():
    try:
        data = request.get_json()
        category = data.get('category')
        product_specification = data.get('product_specification')
        purchase_price = data.get('purchase_price')

        # Validate inputs
        if not category or not product_specification or purchase_price is None:
            return jsonify({
                "error": "يرجى التأكد من إدخال القسم، المواصفات، وسعر الجملة"
            }), 400
        
        if purchase_price <= 0:
            return jsonify({
                "error": "سعر الجملة يجب أن يكون أكبر من صفر"
            }), 400

        # Define price ranges for classification (adjust as needed)
        price_ranges = {
            "low": (0, 50),
            "moderate": (50, 100),
            "high": (100, float('inf'))
        }

        # Classify the price level
        price_level = classify_price_level(purchase_price, price_ranges)

        # Load the optimal profit percentage from the profit model
        optimal_profit_percentage = load_profit_model(category, product_specification, price_level)

        if optimal_profit_percentage == 0.0:
            return jsonify({
                "error": "لا يوجد نطاق سعر متاح لهذا القسم والمواصفات. يرجى التحقق من المدخلات أو إضافة البيانات."
            }), 404

        return jsonify({
            "category": category,
            "product_specification": product_specification,
            "original_price": purchase_price,
            "classified_price_level": price_level,
            "optimal_profit_percentage": optimal_profit_percentage
        }), 200

    except Exception as e:
        return jsonify({
            "error": f"خطأ أثناء حساب نسبة الربح المثلى: {str(e)}"
        }), 500

# Existing endpoints (from previous responses)
@pricing_bp.route('/api/visualization/demand-forecasting', methods=['GET'])
def demand_forecasting():
    try:
        demand_data = fetch_data("predicted_demand_2025", projection={"_id": 0})
        if not demand_data:
            return jsonify({
                "message": "لا توجد بيانات توقعات لعام 2025",
                "demand_data": {}
            }), 200

        demand_dict = {}
        for record in demand_data:
            category = record.get("القسم")
            month = str(record.get("month"))
            quantity = record.get("predicted_quantity", 0)
            if category not in demand_dict:
                demand_dict[category] = {}
            demand_dict[category][month] = quantity

        return jsonify({
            "message": "تم جلب بيانات توقعات الطلب بنجاح",
            "demand_data": demand_dict
        }), 200
    except Exception as e:
        return jsonify({
            "message": f"خطأ أثناء جلب بيانات التوقعات: {str(e)}",
            "demand_data": {}
        }), 500

@pricing_bp.route('/api/visualization/sales-rate', methods=['GET'])
def sales_rate():
    return jsonify({
        "message": "لم يتم تنفيذ هذا المسار بعد",
        "sales_rate_data": []
    }), 200