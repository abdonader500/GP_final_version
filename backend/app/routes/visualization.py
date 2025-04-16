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

<<<<<<< HEAD
@visualization_bp.route('/item-specifications', methods=['GET'])
def get_item_specifications():
    try:
        # Get query parameter
        category = request.args.get('category')
        
        if not category:
            return jsonify({
                "success": False,
                "message": "Category parameter is required",
                "specifications": []
            }), 400
        
        # Fetch data from item_specification_monthly_demand collection
        item_specs_data = fetch_data(
            "item_specification_monthly_demand", 
            query={"القسم": category}, 
            projection={"_id": 0, "product_specification": 1}
        )
        
        if not item_specs_data:
            return jsonify({
                "success": True,
                "message": f"No specifications found for category '{category}'",
                "specifications": []
            }), 200
        
        # Extract unique specifications for the category
        specifications = list(set([item.get("product_specification") for item in item_specs_data if item.get("product_specification")]))
        
        # Sort alphabetically
        specifications.sort()
        
        return jsonify({
            "success": True,
            "message": f"Found {len(specifications)} specifications for category '{category}'",
            "specifications": specifications
        }), 200
        
    except Exception as e:
        print(f"❌ Error fetching item specifications: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Failed to fetch specifications: {str(e)}",
            "specifications": []
        }), 500

=======
>>>>>>> parent of 64b3f98 (start demand model)
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

@visualization_bp.route('/category-performance', methods=['GET'])
def get_category_performance():
    try:
        # Get query parameters
        categories = request.args.get('categories', '').split(',')
        start_year = request.args.get('start_year', '')
        end_year = request.args.get('end_year', '')
        group_by = request.args.get('group_by', 'monthly')  # Options: monthly, quarterly, yearly
        
        # Build the query
        query = {}
        
        # Filter by categories if provided and not empty
        if categories and categories[0]:
            query["القسم"] = {"$in": categories}
        
        # Year filtering - simpler than month-year filtering
        if start_year:
            query["year"] = {"$gte": int(start_year)}
            
        if end_year:
            if "year" not in query:
                query["year"] = {}
            query["year"]["$lte"] = int(end_year)
        
        # Fetch data from category_monthly_demand collection
        category_data = fetch_data("category_monthly_demand", query=query, projection={"_id": 0})
        
        if not category_data:
            return jsonify({
                "status": "success",
                "message": "لا توجد بيانات متاحة للمعايير المحددة",
                "performance_data": []
            })
        
        # Process data based on group_by parameter
        processed_data = []
        
        if group_by == 'yearly':
            # Group by year and category
            yearly_data = {}
            for item in category_data:
                key = (item['year'], item['القسم'])
                if key not in yearly_data:
                    yearly_data[key] = {
                        'year': item['year'],
                        'Category': item['القسم'],
                        'Date': f"{item['year']}-01-01",
                        'Sales': 0,
                        'Quantity': 0
                    }
                yearly_data[key]['Sales'] += item['total_money_sold']
                yearly_data[key]['Quantity'] += item['total_quantity']
            
            processed_data = list(yearly_data.values())
            
        elif group_by == 'quarterly':
            # Group by year, quarter and category
            quarterly_data = {}
            for item in category_data:
                # Calculate quarter (1-4)
                quarter = (item['month'] - 1) // 3 + 1
                key = (item['year'], quarter, item['القسم'])
                
                # First month of the quarter for the date
                quarter_month = ((quarter - 1) * 3) + 1
                
                if key not in quarterly_data:
                    quarterly_data[key] = {
                        'year': item['year'],
                        'quarter': quarter,
                        'Category': item['القسم'],
                        'Date': f"{item['year']}-{quarter_month:02d}-01",
                        'Sales': 0,
                        'Quantity': 0
                    }
                quarterly_data[key]['Sales'] += item['total_money_sold']
                quarterly_data[key]['Quantity'] += item['total_quantity']
            
            processed_data = list(quarterly_data.values())
            
        else:  # monthly (default)
            # Format the data needed for the frontend
            for item in category_data:
                processed_data.append({
                    'year': item['year'],
                    'month': item['month'],
                    'Category': item['القسم'],
                    'Date': f"{item['year']}-{item['month']:02d}-01",
                    'Sales': item['total_money_sold'],
                    'Quantity': item['total_quantity']
                })
        
        # Sort data by date
        processed_data.sort(key=lambda x: x['Date'])
        
        # Calculate sales distribution data (aggregated by category)
        sales_distribution_data = {}
        for item in processed_data:
            category = item['Category']
            if category not in sales_distribution_data:
                sales_distribution_data[category] = 0
            sales_distribution_data[category] += item['Sales']
        
        # Convert to list of dictionaries
        sales_distribution = [{"name": k, "value": v} for k, v in sales_distribution_data.items()]
        
        # Calculate year-over-year growth rates
        # Group data by category and year
        category_yearly_data = {}
        for item in processed_data:
            category = item['Category']
            year = item['year']
            if category not in category_yearly_data:
                category_yearly_data[category] = {}
            if year not in category_yearly_data[category]:
                category_yearly_data[category][year] = 0
            category_yearly_data[category][year] += item['Sales']
        
        # Calculate growth rates
        growth_rates = []
        for category, yearly_data in category_yearly_data.items():
            years = sorted(yearly_data.keys())
            for i in range(1, len(years)):
                prev_year = years[i-1]
                curr_year = years[i]
                prev_sales = yearly_data[prev_year]
                curr_sales = yearly_data[curr_year]
                
                if prev_sales > 0:
                    growth_rate = ((curr_sales - prev_sales) / prev_sales) * 100
                else:
                    growth_rate = 0
                
                growth_rates.append({
                    'Category': category,
                    'year': curr_year,
                    'previousYear': prev_year,
                    'growthRate': round(growth_rate, 2),
                    'currentSales': curr_sales,
                    'previousSales': prev_sales
                })
        
        return jsonify({
            "status": "success",
            "performance_data": processed_data,
            "market_share": sales_distribution,  # Keep the field name as market_share for backwards compatibility
            "growth_rates": growth_rates
        })
        
    except Exception as e:
        print(f"Error in category performance endpoint: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@visualization_bp.route('/item-demand-forecasting', methods=['GET'])
def get_item_demand_forecasting():
    try:
        # Get query parameters
        category = request.args.get('category')
        specification = request.args.get('specification')
        
        # Build the query
        query = {"year": 2025}
        
        if category:
            query["القسم"] = category
            
        if specification:
            query["product_specification"] = specification
        
        # Fetch predicted item demand data for 2025
        item_predicted_data = fetch_data("predicted_item_demand_2025", query=query, projection={"_id": 0})

        # If no data is found, return an empty result with a warning
        if not item_predicted_data:
            print("⚠ No predicted item demand data found for 2025")
            return jsonify({
                "item_demand_data": {},
                "message": "No predicted item demand data available for 2025. Please run the AI-based prediction first."
            }), 200

        # Convert to DataFrame
        df = pd.DataFrame(item_predicted_data)
        
        # Format the response data - group by category and specification
        result = {}
        
        # Process the data
        for _, row in df.iterrows():
            category = row['القسم']
            spec = row['product_specification']
            month = row['month']
            
            if category not in result:
                result[category] = {}
                
            if spec not in result[category]:
                result[category][spec] = {}
                
            result[category][spec][str(month)] = {
                "quantity": row['predicted_quantity'],
                "money_sold": row['predicted_money_sold']
            }

        # Convert to JSON with UTF-8 encoding
        json_response = json.dumps({"item_demand_data": result}, ensure_ascii=False, indent=4)
        return Response(json_response, content_type="application/json; charset=utf-8")

    except Exception as e:
        print(f"❌ Error fetching predicted item demand data: {str(e)}")
        return jsonify({"error": f"Failed to fetch predicted item demand data: {str(e)}"}), 500

@visualization_bp.route('/daily-item-demand-forecasting', methods=['GET'])
def get_daily_item_demand_forecasting():
    try:
        # Get query parameters
        category = request.args.get('category')
        specification = request.args.get('specification')
        month = request.args.get('month')
        
        # Build the query
        query = {"year": 2025}
        
        if category:
            query["القسم"] = category
            
        if specification:
            query["product_specification"] = specification
            
        if month:
            query["month"] = int(month)
            
        # Fetch predicted daily demand data for 2025
        daily_predicted_data = fetch_data("predicted_daily_demand_2025", query=query, projection={"_id": 0})

        # If no data is found, return an empty result with a warning
        if not daily_predicted_data:
            print("⚠ No predicted daily item demand data found for 2025")
            return jsonify({
                "daily_item_demand_data": {},
                "message": "No predicted daily item demand data available for 2025. Please run the AI-based prediction first."
            }), 200

        # Convert to DataFrame
        df = pd.DataFrame(daily_predicted_data)
        
        # Convert date strings to datetime objects for proper sorting
        if 'date' in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            # Sort by date
            df = df.sort_values(by="date")
        
        # Format the response data - group by category, specification and date
        result = {}
        
        # Filter out the 'all' marker for category-level predictions if specification is requested
        if specification:
            df = df[df['product_specification'] != 'all']
        
        # Process the data
        for _, row in df.iterrows():
            category = row['القسم']
            spec = row['product_specification']
            
            if 'date' in row:
                date_str = row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], datetime) else row['date']
            else:
                # Skip rows without date information
                continue
                
            if category not in result:
                result[category] = {}
                
            if spec not in result[category]:
                result[category][spec] = {}
                
            result[category][spec][date_str] = {
                "quantity": row['predicted_quantity'],
                "money_sold": row['predicted_money_sold'],
                "day_of_week": row['day_of_week'] if 'day_of_week' in row else None
            }

        # Convert to JSON with UTF-8 encoding
        json_response = json.dumps({"daily_item_demand_data": result}, ensure_ascii=False, indent=4)
        return Response(json_response, content_type="application/json; charset=utf-8")

    except Exception as e:
        print(f"❌ Error fetching predicted daily item demand data: {str(e)}")
        return jsonify({"error": f"Failed to fetch predicted daily item demand data: {str(e)}"}), 500