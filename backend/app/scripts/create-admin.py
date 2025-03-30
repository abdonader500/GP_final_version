# backend/scripts/create_admin.py
import sys
import os
import hashlib
import bcrypt
from pymongo import MongoClient
from datetime import datetime

# Add parent directory to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Get MongoDB connection string from environment or use default
mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/consult_your_data')

def create_default_admin():
    """Create a default admin user in the database if it doesn't exist"""
    try:
        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        db = client.get_database()
        users_collection = db.users
        
        # Check if admin already exists
        existing_admin = users_collection.find_one({"username": "admin"})
        if existing_admin:
            print("✅ Default admin user already exists")
            return
        
        # Hash password with bcrypt
        password = "admin123"
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        # Create admin user document
        admin_user = {
            "username": "admin",
            "password": hashed_password,
            "role": "admin",
            "name": "Administrator",
            "email": "admin@example.com",
            "active": True,
            "createdAt": datetime.now()
        }
        
        # Insert into database
        result = users_collection.insert_one(admin_user)
        
        if result.inserted_id:
            print(f"✅ Default admin user created successfully with ID: {result.inserted_id}")
        else:
            print("❌ Failed to create default admin user")
    
    except Exception as e:
        print(f"❌ Error creating default admin: {str(e)}")
    finally:
        # Close the connection
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    create_default_admin()