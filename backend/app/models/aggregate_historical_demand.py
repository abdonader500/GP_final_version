import pandas as pd
from app.models.database import fetch_data, insert_data
from datetime import datetime

def aggregate_historical_demand():
    try:
        print("📦 Fetching data from classified_sales...")
        sales_data = fetch_data("classified_sales", projection={"_id": 0})

        if not sales_data:
            print("⚠ No records found in classified_sales")
            return

        # Convert to DataFrame
        df = pd.DataFrame(sales_data)
        df["الكمية"] = pd.to_numeric(df["الكمية"], errors="coerce")
        df["الصافي"] = pd.to_numeric(df["الصافي"], errors="coerce")
        df["التاريخ"] = pd.to_datetime(df["التاريخ"], format="%d/%m/%Y")
        df.dropna(subset=["الكمية", "الصافي", "التاريخ", "القسم", "product_specification"], inplace=True)

        # Filter for years 2021 to 2024
        df = df[df['التاريخ'].dt.year.between(2021, 2024)]

        if df.empty:
            print("⚠ No data found for years 2021-2024")
            return

        # Extract year and month
        df['year'] = df['التاريخ'].dt.year
        df['month'] = df['التاريخ'].dt.month

        # Aggregate by category, year, and month for both total_quantity and total_money_sold
        category_demand = df.groupby(['القسم', 'year', 'month']).agg({
            'الكمية': 'sum',
            'الصافي': 'sum'
        }).reset_index()
        category_demand = category_demand.rename(columns={'الكمية': 'total_quantity', 'الصافي': 'total_money_sold'})

        # Aggregate by category, item_specification, year, and month for both total_quantity and total_money_sold
        item_demand = df.groupby(['القسم', 'product_specification', 'year', 'month']).agg({
            'الكمية': 'sum',
            'الصافي': 'sum'
        }).reset_index()
        item_demand = item_demand.rename(columns={'الكمية': 'total_quantity', 'الصافي': 'total_money_sold'})

        # Convert to dictionary for MongoDB storage
        category_records = category_demand.to_dict(orient="records")
        item_records = item_demand.to_dict(orient="records")

        # Store in MongoDB
        print("Storing category monthly demand...")
        insert_data("category_monthly_demand", category_records)
        print("Storing item specification monthly demand (per category)...")
        insert_data("item_specification_monthly_demand", item_records)

        print(" Historical demand aggregation complete")

    except Exception as e:
        print(f"Error aggregating historical demand: {str(e)}")

if __name__ == "__main__":
    aggregate_historical_demand()