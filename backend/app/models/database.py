from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MongoDB connection setup
# Set a direct default connection string
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# Fix: Replace placeholder if present
if "your_mongodb_connection_string" in MONGO_URI:
    MONGO_URI="mongodb://localhost:27017"

client = None
db = None

def init_db():
    global client, db
    try:
        if client is None:
            print(f"Attempting to connect to MongoDB with URI: {MONGO_URI}")
            client = MongoClient(MONGO_URI)
            db = client['consult_your_data']
            print("MongoDB connection initialized successfully")
    except Exception as e:
        print(f"Error initializing MongoDB connection: {str(e)}")
        raise

def get_collection(collection_name):
    """
    Get a MongoDB collection object.
    
    :param collection_name: Name of the collection to retrieve.
    :return: MongoDB collection object.
    """
    try:
        if db is None:
            init_db()
        return db[collection_name]
    except Exception as e:
        print(f"Error getting collection {collection_name}: {str(e)}")
        raise

def fetch_data(collection_name, query=None, projection=None):
    """
    Fetch data from a MongoDB collection.
    
    :param collection_name: Name of the collection to query.
    :param query: MongoDB query filter (default: None, fetches all documents).
    :param projection: Fields to include/exclude in the result (default: None).
    :return: List of documents.
    """
    try:
        if db is None:
            init_db()
        collection = db[collection_name]
        query = query or {}
        projection = projection or {}
        data = list(collection.find(query, projection))
        return data
    except Exception as e:
        print(f"Error fetching data from {collection_name}: {str(e)}")
        return []

def insert_data(collection_name, data):
    """
    Insert data into a MongoDB collection.
    
    :param collection_name: Name of the collection to insert into.
    :param data: Data to insert (can be a single document or a list of documents).
    :return: Number of documents inserted.
    """
    try:
        if db is None:
            init_db()
        collection = db[collection_name]
        # Drop the collection to avoid duplicates (optional, depending on your use case)
        collection.drop()
        # If data is a single document, convert it to a list
        if isinstance(data, dict):
            data = [data]
        result = collection.insert_many(data)
        print(f"Inserted {len(result.inserted_ids)} documents into {collection_name}")
        return len(result.inserted_ids)
    except Exception as e:
        print(f"Error inserting data into {collection_name}: {str(e)}")
        return 0

def close_connection():
    """
    Close the MongoDB connection.
    
    :return: None
    """
    global client
    if client is not None:
        client.close()
        client = None
        print("MongoDB connection closed")