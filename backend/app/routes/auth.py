# backend/app/routes/auth.py
from flask import Blueprint, request, jsonify
from pymongo import MongoClient
import jwt
import bcrypt
from datetime import datetime, timedelta
import os
from bson import ObjectId
from functools import wraps



# Create blueprint
auth_bp = Blueprint('auth', __name__)

# MongoDB connection
client = MongoClient('mongodb://localhost:27017')
db = client['consult_your_data']
users_collection = db.users

# JWT configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your_jwt_secret')
JWT_EXPIRATION = 24  # hours

# Authentication decorator
# Add these debug prints in your decorators in auth.py

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        print(f"Auth header: {auth_header}")
        
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        
        print(f"Token: {token}")
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'الوصول مرفوض. يرجى تسجيل الدخول'
            }), 401
        
        try:
            # Decode token
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            print(f"Decoded payload: {payload}")
            
            # Get user from database - Try with ObjectId
            user_id = payload['id']
            print(f"Looking for user with ID: {user_id}")
            
            # Try with ObjectId
            user = users_collection.find_one({'_id': ObjectId(user_id)})
            
            if not user:
                print(f"User not found with ID: {user_id}")
                all_users = list(users_collection.find({}, {'_id': 1, 'username': 1}))
                print(f"Available users: {all_users}")
                
                return jsonify({
                    'success': False,
                    'message': 'المستخدم غير موجود'
                }), 404
            
            print(f"User found: {user['username']}")
            
            # Check if user is active
            if not user.get('active', True):
                return jsonify({
                    'success': False,
                    'message': 'الحساب معطل. يرجى التواصل مع المسؤول'
                }), 403
            
            # Add user info to request context
            request.user = {
                'id': str(user['_id']),
                'username': user['username'],
                'role': user['role']
            }
            print(f"User added to request: {request.user}")
            
            return f(*args, **kwargs)
        
        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'message': 'انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى'
            }), 401
        
        except Exception as e:
            print(f"Error in token validation: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'جلسة غير صالحة. يرجى تسجيل الدخول مرة أخرى',
                'error': str(e)
            }), 401
    
    return decorated

# Admin authorization decorator
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(request, 'user') or request.user.get('role') != 'admin':
            return jsonify({
                'success': False,
                'message': 'غير مصرح. يتطلب صلاحيات المسؤول'
            }), 403
        return f(*args, **kwargs)
    
    return decorated

# Generate JWT token
def generate_token(user):
    # Debug
    print(f"Generating token for user: {user['username']} with ID: {user['_id']}")
    
    payload = {
        'id': str(user['_id']),  # Ensure ID is converted to string
        'username': user['username'],
        'role': user['role'],
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

# Login route
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    
    # Validate request
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({
            'success': False,
            'message': 'يرجى إدخال اسم المستخدم وكلمة المرور'
        }), 400
    
    # Find user
    user = users_collection.find_one({'username': data['username']})
    if not user:
        return jsonify({
            'success': False,
            'message': 'اسم المستخدم أو كلمة المرور غير صحيحة'
        }), 401
    
    # Verify role if provided
    if data.get('role') and user['role'] != data['role']:
        return jsonify({
            'success': False,
            'message': f"ليس لديك صلاحية للوصول كـ {data['role']}"
        }), 403
    
    # Check if account is active
    if not user.get('active', True):
        return jsonify({
            'success': False,
            'message': 'الحساب معطل. يرجى التواصل مع المسؤول'
        }), 403
    
    # Verify password
    if not bcrypt.checkpw(data['password'].encode('utf-8'), user['password']):
        return jsonify({
            'success': False,
            'message': 'اسم المستخدم أو كلمة المرور غير صحيحة'
        }), 401
    
    # Update last login time
    users_collection.update_one(
        {'_id': user['_id']},
        {'$set': {'lastLogin': datetime.now()}}
    )
    
    # User data to return (excluding password)
    user_data = {
        '_id': str(user['_id']),
        'username': user['username'],
        'role': user['role'],
        'name': user.get('name', ''),
        'email': user.get('email', '')
    }
    
    # Generate token
    token = generate_token(user)
    
    return jsonify({
        'success': True,
        'message': 'تم تسجيل الدخول بنجاح',
        'token': token,
        'user': user_data
    }), 200

# Get user profile
@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    # Get user from database using ID from token
    user = users_collection.find_one({'_id': request.user['id']})
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'المستخدم غير موجود'
        }), 404
    
    # User data to return (excluding password)
    user_data = {
        '_id': str(user['_id']),
        'username': user['username'],
        'role': user['role'],
        'name': user.get('name', ''),
        'email': user.get('email', ''),
        'active': user.get('active', True),
        'lastLogin': user.get('lastLogin', None)
    }
    
    return jsonify({
        'success': True,
        'user': user_data
    }), 200