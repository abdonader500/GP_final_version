import csv
from pymongo import MongoClient

# MongoDB connection
client = MongoClient("mongodb://localhost:27017")
db = client["consult_your_data"]

# Define the collections for sales and purchases
sales_collection = db["sales"]
purchases_collection = db["purchases"]

# Paths to the CSV files
csv_sales_path = "backend/CSVs/المبيعات.csv"  # Replace with the actual path to your sales CSV file
csv_purchases_path = "backend/CSVs/المشتريات.csv"  # Replace with the actual path to your purchases CSV file

def load_csv_to_mongodb(csv_file_path, collection):
    """Loads a CSV file into the specified MongoDB collection."""
    with open(csv_file_path, mode='r', encoding='utf-8-sig') as file:
        csv_reader = csv.DictReader(file)
        data = []
        for row in csv_reader:
            data.append(row)

        if data:
            result = collection.insert_many(data)
            print(f"{len(result.inserted_ids)} records inserted successfully into the {collection.name} collection.")
        else:
            print(f"No data found in the CSV file: {csv_file_path}")

if __name__ == "__main__":
    # Load sales data
    print("Loading sales data...")
    load_csv_to_mongodb(csv_sales_path, sales_collection)

    # Load purchases data
    print("Loading purchases data...")
    load_csv_to_mongodb(csv_purchases_path, purchases_collection)
