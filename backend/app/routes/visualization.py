from flask import Blueprint, request, jsonify, Response
import json
from app.models.database import fetch_data
import pandas as pd
from datetime import datetime

visualization_bp = Blueprint('visualization', __name__)

@visualization_bp.route('/demand-forecasting', methods=['GET'])
def get_demand_forecasting():
    try:
        # Fetch predicted demand data for 2025
        predicted_data = fetch_data("predicted_demand_2025", projection={"_id": 0})

        # If no data is found, return an empty result with a warning
        if not predicted_data:
            print("⚠ No predicted demand data found for 2025")
            return jsonify({
                "demand_data": {},
                "message": "No predicted demand data available for 2025. Please ensure historical data is available and predictions have been generated."
            }), 200

        # Convert to DataFrame
        df = pd.DataFrame(predicted_data)

        # Prepare data for all months (1 to 12) for each category
        categories = df['القسم'].unique()
        result = {}
        for category in categories:
            category_data = df[df['القسم'] == category]
            monthly_demand = {str(i): {"quantity": 0, "money_sold": 0} for i in range(1, 13)}  # Initialize with both quantity and money_sold
            for _, row in category_data.iterrows():
                month = str(row['month'])
                monthly_demand[month]["quantity"] = row['predicted_quantity']
                monthly_demand[month]["money_sold"] = row['predicted_money_sold']
            result[category] = monthly_demand

        # Convert to JSON with UTF-8 encoding
        json_response = json.dumps({"demand_data": result}, ensure_ascii=False, indent=4)
        return Response(json_response, content_type="application/json; charset=utf-8")

    except Exception as e:
        print(f"❌ Error fetching predicted demand data: {str(e)}")
        return jsonify({"error": f"Failed to fetch predicted demand data: {str(e)}"}), 500

@visualization_bp.route('/demand-forecasting-items', methods=['GET'])
def get_demand_forecasting_items():
    try:
        # Fetch predicted demand data for 2025 (item specifications within categories)
        predicted_data = fetch_data("predicted_item_demand_2025", projection={"_id": 0})

        # If no data is found, return an empty result with a warning
        if not predicted_data:
            print("⚠ No predicted item demand data found for 2025")
            return jsonify({
                "demand_data_items": {},
                "message": "No predicted item demand data available for 2025. Please ensure historical data is available and predictions have been generated."
            }), 200

        # Convert to DataFrame
        df = pd.DataFrame(predicted_data)

        # Prepare data for all months (1 to 12) for each category and item_specification
        categories = df['القسم'].unique()
        result = {}
        for category in categories:
            category_data = df[df['القسم'] == category]
            items = category_data['product_specification'].unique()
            category_result = {}
            for item in items:
                item_data = category_data[category_data['product_specification'] == item]
                monthly_demand = {str(i): {"quantity": 0, "money_sold": 0} for i in range(1, 13)}  # Initialize with both quantity and money_sold
                for _, row in item_data.iterrows():
                    month = str(row['month'])
                    monthly_demand[month]["quantity"] = row['predicted_quantity']
                    monthly_demand[month]["money_sold"] = row['predicted_money_sold']
                category_result[item] = monthly_demand
            result[category] = category_result

        # Convert to JSON with UTF-8 encoding
        json_response = json.dumps({"demand_data_items": result}, ensure_ascii=False, indent=4)
        return Response(json_response, content_type="application/json; charset=utf-8")

    except Exception as e:
        print(f"❌ Error fetching predicted item demand data: {str(e)}")
        return jsonify({"error": f"Failed to fetch predicted item demand data: {str(e)}"}), 500

@visualization_bp.route('/sales-rate', methods=['GET'])
def get_sales_rate():
    try:
        # Get query parameters
        category = request.args.get('category')
        start_date = request.args.get('start_date')  # Format: DD/MM/YYYY
        end_date = request.args.get('end_date')      # Format: DD/MM/YYYY

        # Fetch sales data from classified_sales
        sales_data = fetch_data("classified_sales", projection={"_id": 0, "القسم": 1, "الكمية": 1, "التاريخ": 1})

        if not sales_data:
            print("⚠ No records found in classified_sales")
            return jsonify({
                "sales_rate_data": [],
                "message": "No sales data found in the 'classified_sales' collection."
            }), 200

        # Convert to DataFrame
        df = pd.DataFrame(sales_data)
        df["الكمية"] = pd.to_numeric(df["الكمية"], errors="coerce")
        df["التاريخ"] = pd.to_datetime(df["التاريخ"], format="%d/%m/%Y")
        df.dropna(subset=["الكمية", "التاريخ", "القسم"], inplace=True)

        # Filter by category if provided
        if category:
            df = df[df['القسم'] == category]

        # Filter by date range if provided
        if start_date and end_date:
            start = pd.to_datetime(start_date, format="%d/%m/%Y")
            end = pd.to_datetime(end_date, format="%d/%m/%Y")
            df = df[(df['التاريخ'] >= start) & (df['التاريخ'] <= end)]

        # Calculate total quantity
        total_quantity = df["الكمية"].sum()
        if total_quantity == 0:
            return jsonify({
                "sales_rate_data": [],
                "message": "No sales data found within the specified range."
            }), 200

        # Calculate sales rate by date
        df['sales_rate'] = (df['الكمية'] / total_quantity) * 100
        result = df.groupby('التاريخ').agg({'sales_rate': 'sum'}).reset_index().to_dict(orient="records")

        # Convert to JSON with UTF-8 encoding
        json_response = json.dumps({"sales_rate_data": result}, ensure_ascii=False, indent=4)
        return Response(json_response, content_type="application/json; charset=utf-8")

    except Exception as e:
        print(f"❌ Error fetching sales rate data: {str(e)}")
        return jsonify({"error": f"Failed to fetch sales rate data: {str(e)}"}), 500

@visualization_bp.route('/monthly-demand', methods=['GET'])
def get_monthly_demand():
    try:
        # Get query parameters
        categories = request.args.get('categories', '').split(',')
        start_month_year = request.args.get('start_month_year')  # Format: YYYY-MM
        end_month_year = request.args.get('end_month_year')      # Format: YYYY-MM

        # Validate parameters
        if not categories or not start_month_year or not end_month_year:
            return jsonify({"message": "Missing parameters"}), 400

        # Parse month-year to extract year and month
        start = datetime.strptime(start_month_year + '-01', '%Y-%m-%d')
        end = datetime.strptime(end_month_year + '-01', '%Y-%m-%d')

        # Fetch data from category_monthly_demand
        demand_data = fetch_data("category_monthly_demand", projection={"_id": 0})

        if not demand_data:
            print("⚠ No records found in category_monthly_demand")
            return jsonify({
                "monthly_demand_data": [],
                "message": "No data found in the 'category_monthly_demand' collection."
            }), 200

        # Convert to DataFrame
        df = pd.DataFrame(demand_data)
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
        df["total_quantity"] = pd.to_numeric(df["total_quantity"], errors="coerce")
        df["total_money_sold"] = pd.to_numeric(df["total_money_sold"], errors="coerce")
        df.dropna(subset=["القسم", "year", "month", "total_quantity", "total_money_sold"], inplace=True)

        # Filter by categories
        if categories[0]:  # Check if categories list is not empty
            df = df[df['القسم'].isin(categories)]

        # Filter by month-year range
        df = df[
            (df['year'] > start.year) |
            ((df['year'] == start.year) & (df['month'] >= start.month)) &
            (df['year'] < end.year) |
            ((df['year'] == end.year) & (df['month'] <= end.month))
        ]

        # Group by category, year, and month to sum total_quantity and total_money_sold
        result = df.groupby(['القسم', 'year', 'month']).agg({
            'total_quantity': 'sum',
            'total_money_sold': 'sum'
        }).reset_index()

        if result.empty:
            return jsonify({
                "monthly_demand_data": [],
                "message": "No data found within the specified range."
            }), 200

        # Convert to JSON with UTF-8 encoding
        json_response = json.dumps({"monthly_demand_data": result.to_dict(orient="records")}, ensure_ascii=False, indent=4)
        return Response(json_response, content_type="application/json; charset=utf-8")

    except Exception as e:
        print(f"❌ Error fetching monthly demand data: {str(e)}")
        return jsonify({"error": f"Failed to fetch monthly demand data: {str(e)}"}), 500

@visualization_bp.route('/seasonal-analysis', methods=['GET'])
def get_seasonal_analysis():
    try:
        # Get optional query parameters
        category = request.args.get('category')
        year = request.args.get('year')
        
        # Fetch data from category_monthly_demand
        demand_data = fetch_data("category_monthly_demand", projection={"_id": 0})

        if not demand_data:
            print("⚠ No records found in category_monthly_demand")
            return jsonify({
                "monthly_demand_data": [],
                "message": "No data found in the 'category_monthly_demand' collection."
            }), 200

        # Convert to DataFrame
        df = pd.DataFrame(demand_data)
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
        df["total_quantity"] = pd.to_numeric(df["total_quantity"], errors="coerce")
        df["total_money_sold"] = pd.to_numeric(df["total_money_sold"], errors="coerce")
        df.dropna(subset=["القسم", "year", "month", "total_quantity", "total_money_sold"], inplace=True)

        # Apply filters if provided
        if category and category != 'all':
            df = df[df['القسم'] == category]
        if year and year != 'all':
            df = df[df['year'] == int(year)]

        # Convert to JSON with UTF-8 encoding
        json_response = json.dumps({
            "monthly_demand_data": df.to_dict(orient="records"),
            "message": None
        }, ensure_ascii=False, indent=4)
        
        return Response(json_response, content_type="application/json; charset=utf-8")

    except Exception as e:
        print(f"❌ Error fetching seasonal analysis data: {str(e)}")
        return jsonify({"error": f"Failed to fetch seasonal analysis data: {str(e)}"}), 500