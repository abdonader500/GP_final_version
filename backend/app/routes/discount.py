from flask import Blueprint, request, jsonify
from app.models.ml_model import suggest_discount
from app.utils.helper import validate_request  # Import helper functions

discount_bp = Blueprint('discount', __name__)

@discount_bp.route('/suggest', methods=['POST'])
def suggest_discount_route():
    data = request.get_json()
    required_fields = ["feature1", "feature2", "feature3"]  # Replace with actual features
    valid, error = validate_request(data, required_fields)
    if not valid:
        return jsonify(error), 400

    features = [data[field] for field in required_fields]
    suggested_discount = suggest_discount(features)
    return jsonify({"suggested_discount": suggested_discount})
