from pymongo import MongoClient

try:
    client = MongoClient("mongodb://localhost:27017")
    print("Connected to MongoDB successfully!")
except Exception as e:
    print("Failed to connect to MongoDB:", e)
