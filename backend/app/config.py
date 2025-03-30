import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class Config:
    MONGO_URI = os.getenv("MONGO_URI")  # MongoDB connection string
    SECRET_KEY = os.getenv("SECRET_KEY", "your_default_secret_key")