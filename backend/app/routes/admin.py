# backend/app/routes/admin.py
from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import bcrypt
import os
from datetime import datetime
from app.routes.auth import token_required, admin_required

# Create blueprint
admin_bp = Blueprint('admin', __name__)

# Add this to the top of your admin.py file
print("Attempting to connect to MongoDB...")
# MongoDB connection
try:
    client = MongoClient('mongodb://localhost:27017')
    db = client['consult_your_data']
    # Try a simple query to test connection
    result = db.command('ping')
    print("MongoDB connection successful!")
    print(f"DB collections: {db.list_collection_names()}")
    
    # Count users in the collection
    users_count = db.users.count_documents({})
    print(f"Found {users_count} users in the database")
    
    # List all users for debugging
    all_users = list(db.users.find({}, {'_id': 1, 'username': 1, 'role': 1}))
    for user in all_users:
        user['_id'] = str(user['_id'])  # Convert ObjectId to string for printing
    print(f"Users: {all_users}")
    
    # Define the users_collection variable for use in routes
    users_collection = db.users
    
except Exception as e:
    print(f"MongoDB connection failed: {str(e)}")

# Helper functions
def format_user_for_response(user):
    """Format user document for API response (exclude password)"""
    if not user:
        return None
    
    return {
        '_id': str(user['_id']),
        'username': user['username'],
        'role': user['role'],
        'name': user.get('name', ''),
        'email': user.get('email', ''),
        'active': user.get('active', True),
        'createdAt': user.get('createdAt', None),
        'lastLogin': user.get('lastLogin', None)
    }

@admin_bp.route('/users', methods=['GET'])
@token_required
@admin_required
def get_all_users():
    try:
        print("Getting all users...")
        # Get all users from database
        users_cursor = users_collection.find().sort('createdAt', -1)
        
        # Convert cursor to list
        users_list = []
        for user in users_cursor:
            # Format user for response
            user_data = format_user_for_response(user)
            users_list.append(user_data)
        
        print(f"Found {len(users_list)} users")
        
        return jsonify({
            'success': True,
            'count': len(users_list),
            'users': users_list
        }), 200
    
    except Exception as e:
        print(f"Error in get_all_users: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': 'خطأ في استرجاع بيانات المستخدمين',
            'error': str(e)
        }), 500

# Get user by ID
@admin_bp.route('/users/<user_id>', methods=['GET'])
@token_required
@admin_required
def get_user_by_id(user_id):
    try:
        # Find user by ID
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'المستخدم غير موجود'
            }), 404
        
        # Format user for response
        user_data = format_user_for_response(user)
        
        return jsonify({
            'success': True,
            'user': user_data
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'خطأ في استرجاع بيانات المستخدم',
            'error': str(e)
        }), 500

# Create new user
@admin_bp.route('/users', methods=['POST'])
@token_required
@admin_required
def create_user():
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('username') or not data.get('password'):
            return jsonify({
                'success': False,
                'message': 'اسم المستخدم وكلمة المرور مطلوبة'
            }), 400
        
        # Check if username already exists
        if users_collection.find_one({'username': data['username']}):
            return jsonify({
                'success': False,
                'message': 'اسم المستخدم مسجل بالفعل'
            }), 400
        
        # Validate role
        if data.get('role') and data['role'] not in ['user', 'admin']:
            return jsonify({
                'success': False,
                'message': 'دور المستخدم غير صالح'
            }), 400
        
        # Hash password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), salt)
        
        # Create user document
        new_user = {
            'username': data['username'],
            'password': hashed_password,
            'role': data.get('role', 'user'),
            'name': data.get('name', ''),
            'email': data.get('email', ''),
            'active': data.get('active', True),
            'createdAt': datetime.now()
        }
        
        # Insert user into database
        result = users_collection.insert_one(new_user)
        
        if not result.inserted_id:
            return jsonify({
                'success': False,
                'message': 'فشل في إنشاء المستخدم'
            }), 500
        
        # Get created user
        created_user = users_collection.find_one({'_id': result.inserted_id})
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء المستخدم بنجاح',
            'user': format_user_for_response(created_user)
        }), 201
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'خطأ في إنشاء المستخدم',
            'error': str(e)
        }), 500

# Update user
@admin_bp.route('/users/<user_id>', methods=['PUT'])
@token_required
@admin_required
def update_user(user_id):
    try:
        data = request.json
        
        # Find user
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'المستخدم غير موجود'
            }), 404
        
        # Check if username is being changed and already exists
        if data.get('username') and data['username'] != user['username']:
            if users_collection.find_one({'username': data['username']}):
                return jsonify({
                    'success': False,
                    'message': 'اسم المستخدم مسجل بالفعل'
                }), 400
        
        # Validate role
        if data.get('role') and data['role'] not in ['user', 'admin']:
            return jsonify({
                'success': False,
                'message': 'دور المستخدم غير صالح'
            }), 400
        
        # Update fields
        update_data = {}
        for field in ['username', 'name', 'email', 'role']:
            if field in data:
                update_data[field] = data[field]
        
        if 'active' in data:
            update_data['active'] = bool(data['active'])
        
        # Update user in database
        if update_data:
            result = users_collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            
            if result.modified_count == 0:
                return jsonify({
                    'success': False,
                    'message': 'لم يتم تحديث أي بيانات'
                }), 400
        
        # Get updated user
        updated_user = users_collection.find_one({'_id': ObjectId(user_id)})
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث بيانات المستخدم بنجاح',
            'user': format_user_for_response(updated_user)
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'خطأ في تحديث بيانات المستخدم',
            'error': str(e)
        }), 500

# Change user password
@admin_bp.route('/users/<user_id>/change-password', methods=['PUT'])
@token_required
@admin_required
def change_password(user_id):
    try:
        data = request.json
        
        # Validate password
        if not data.get('password'):
            return jsonify({
                'success': False,
                'message': 'كلمة المرور مطلوبة'
            }), 400
        
        if len(data['password']) < 6:
            return jsonify({
                'success': False,
                'message': 'كلمة المرور يجب أن تكون 6 أحرف على الأقل'
            }), 400
        
        # Find user
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'المستخدم غير موجود'
            }), 404
        
        # Hash new password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), salt)
        
        # Update password in database
        result = users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'password': hashed_password}}
        )
        
        if result.modified_count == 0:
            return jsonify({
                'success': False,
                'message': 'فشل في تغيير كلمة المرور'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'تم تغيير كلمة المرور بنجاح'
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'خطأ في تغيير كلمة المرور',
            'error': str(e)
        }), 500

# Delete user
@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(user_id):
    try:
        # Find user
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'المستخدم غير موجود'
            }), 404
        
        # Delete user from database
        result = users_collection.delete_one({'_id': ObjectId(user_id)})
        
        if result.deleted_count == 0:
            return jsonify({
                'success': False,
                'message': 'فشل في حذف المستخدم'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'تم حذف المستخدم بنجاح'
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'خطأ في حذف المستخدم',
            'error': str(e)
        }), 500