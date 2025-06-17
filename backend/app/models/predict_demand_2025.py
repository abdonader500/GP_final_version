import pandas as pd
from app.models.database import fetch_data, insert_data

def predict_demand_2025():
    try:
        # Predict demand for categories
        print(" Fetching historical category demand data...")
        category_data = fetch_data("category_monthly_demand", projection={"_id": 0})

        if not category_data:
            print(" No records found in category_monthly_demand")
            return

        # Convert to DataFrame
        df_category = pd.DataFrame(category_data)

        # Group by category and month to calculate the average demand and money sold across years
        predicted_category_demand = df_category.groupby(['القسم', 'month']).agg({
            'total_quantity': 'mean',
            'total_money_sold': 'mean'
        }).reset_index()
        predicted_category_demand['year'] = 2025
        predicted_category_demand = predicted_category_demand.rename(columns={
            'total_quantity': 'predicted_quantity',
            'total_money_sold': 'predicted_money_sold'
        })

        # Predict demand for item specifications within each category
        print("Fetching historical item specification demand data...")
        item_data = fetch_data("item_specification_monthly_demand", projection={"_id": 0})

        if not item_data:
            print("⚠ No records found in item_specification_monthly_demand")
        else:
            # Convert to DataFrame
            df_item = pd.DataFrame(item_data)

            # Group by category, item_specification, and month to calculate the average demand and money sold
            predicted_item_demand = df_item.groupby(['القسم', 'product_specification', 'month']).agg({
                'total_quantity': 'mean',
                'total_money_sold': 'mean'
            }).reset_index()
            predicted_item_demand['year'] = 2025
            predicted_item_demand = predicted_item_demand.rename(columns={
                'total_quantity': 'predicted_quantity',
                'total_money_sold': 'predicted_money_sold'
            })

            # Store predicted item specification demand
            predicted_item_records = predicted_item_demand.to_dict(orient="records")
            print(" Storing predicted item specification demand for 2025...")
            insert_data("predicted_item_demand_2025", predicted_item_records)

        # Store predicted category demand
        predicted_category_records = predicted_category_demand.to_dict(orient="records")
        print(" Storing predicted category demand for 2025...")
        insert_data("predicted_demand_2025", predicted_category_records)

        print(" Demand prediction for 2025 complete")

    except Exception as e:
        print(f" Error predicting demand: {str(e)}")

if __name__ == "__main__":
    predict_demand_2025()